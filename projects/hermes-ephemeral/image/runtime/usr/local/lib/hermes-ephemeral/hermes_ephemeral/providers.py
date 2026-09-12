"""Generic discovery of repeated OpenAI-v1 providers for Hermes."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .environment import (
    ConfigurationError,
    clean,
    floating,
    openai_group_name,
)


MAX_DISCOVERY_RESPONSE_BYTES = 8 * 1024 * 1024
HTTP_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


def _clean_openai_v1(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


@dataclass(frozen=True)
class OpenAIV1Provider:
    """One OpenAI-compatible provider represented without its secret."""

    index: int
    provider_id: str
    configured_name: str
    base_url: str
    key_env: str
    models: tuple[str, ...]
    streaming: bool

    def hermes_config(self) -> dict[str, Any]:
        """Return the provider block expected by Hermes."""

        models = {model: {} for model in self.models}
        result: dict[str, Any] = {
            "name": self.configured_name or self.provider_id,
            "base_url": self.base_url,
            "key_env": self.key_env,
            "api_mode": "chat_completions",
            "models": models,
        }
        if self.models:
            result["default_model"] = self.models[0]
        return result


def _indexes(environ: Mapping[str, str]) -> tuple[int, ...]:
    indexes = {1}
    pattern = re.compile(
        r"^OPENAI_V1_(?:PROVIDER|URL|PORT|KEY|API_KEY_ALIAS|STREAM|"
        r"DISCOVERY_HEADERS|MODELS)_(\d+)$"
    )
    for name in environ:
        match = pattern.fullmatch(name)
        if match:
            index = int(match.group(1), 10)
            if index < 2:
                raise ConfigurationError(f"{name} has an unsupported numeric suffix")
            indexes.add(index)
    return tuple(sorted(indexes))


def _group_value(
    environ: Mapping[str, str],
    field: str,
    index: int,
) -> str:
    return _clean_openai_v1(
        environ.get(openai_group_name(environ, field, index))
    )


def _streaming_value(environ: Mapping[str, str], index: int) -> bool:
    name = openai_group_name(environ, "STREAM", index)
    raw = _group_value(environ, "STREAM", index).lower()
    if not raw:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean value")


def _discovery_headers(
    environ: Mapping[str, str],
    index: int,
) -> dict[str, str]:
    name = openai_group_name(environ, "DISCOVERY_HEADERS", index)
    raw = _group_value(environ, "DISCOVERY_HEADERS", index)
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{name} must be a JSON object") from exc
    if not isinstance(decoded, Mapping):
        raise ConfigurationError(f"{name} must be a JSON object")

    headers: dict[str, str] = {}
    for raw_header, raw_value in decoded.items():
        if not isinstance(raw_header, str) or not HTTP_HEADER_NAME.fullmatch(raw_header):
            raise ConfigurationError(f"{name} contains an invalid HTTP header name")
        if raw_header.lower() == "authorization":
            raise ConfigurationError(
                f"{name} must not override the generated Authorization header"
            )
        if not isinstance(raw_value, str) or "\r" in raw_value or "\n" in raw_value:
            raise ConfigurationError(f"{name} contains an invalid HTTP header value")
        headers[raw_header] = raw_value
    return headers


def _model_ids(decoded: Any) -> tuple[str, ...]:
    rows: Any = decoded
    if isinstance(decoded, Mapping):
        rows = decoded.get("data")
        if rows is None:
            rows = decoded.get("models")
    if isinstance(rows, Mapping):
        rows = list(rows)
    if not isinstance(rows, list):
        return ()

    model_ids: set[str] = set()
    for row in rows:
        if isinstance(row, str):
            model_id = clean(row)
        elif isinstance(row, Mapping):
            model_id = ""
            for field in ("id", "model", "name"):
                value = row.get(field)
                if isinstance(value, str) and clean(value):
                    model_id = clean(value)
                    break
        else:
            model_id = ""
        if model_id:
            model_ids.add(model_id)
    return tuple(sorted(model_ids))


def _configured_models(
    environ: Mapping[str, str],
    index: int,
) -> tuple[str, ...]:
    name = openai_group_name(environ, "MODELS", index)
    raw = _group_value(environ, "MODELS", index)
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = [part.strip() for part in raw.replace("\n", ",").split(",")]
    models = _model_ids(decoded)
    if not models:
        raise ConfigurationError(f"{name} must contain at least one model id")
    return models


def normalize_openai_v1_url(raw_url: str, raw_port: str = "") -> str:
    """Normalize one endpoint to an OpenAI-v1 API base URL."""

    value = clean(raw_url).rstrip("/")
    port = clean(raw_port)
    if not value:
        return ""
    if "://" not in value:
        value = f"http://{value}"
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigurationError("OPENAI_V1_URL must be an HTTP(S) endpoint")
    if parsed.username is not None or parsed.password is not None:
        raise ConfigurationError("OPENAI_V1_URL must not contain credentials")

    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ConfigurationError("OPENAI_V1_URL contains an invalid port") from exc
    if port:
        try:
            requested_port = int(port, 10)
        except ValueError as exc:
            raise ConfigurationError("OPENAI_V1_PORT must be an integer") from exc
        if not 1 <= requested_port <= 65_535:
            raise ConfigurationError("OPENAI_V1_PORT must be between 1 and 65535")
    else:
        requested_port = None

    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    effective_port = parsed_port if parsed_port is not None else requested_port
    netloc = host if effective_port is None else f"{host}:{effective_port}"
    path = parsed.path.rstrip("/") or "/v1"
    return urlunsplit((parsed.scheme, netloc, path, "", ""))


def _provider_id(raw: str, index: int, used: set[str]) -> str:
    fallback = "openai_v1" if index == 1 else f"openai_v1_{index}"
    candidate = re.sub(r"[^a-z0-9._-]+", "_", raw.lower()).strip("._-")
    candidate = candidate or fallback
    if candidate in used:
        candidate = f"{candidate}_{index}"
    counter = 2
    unique = candidate
    while unique in used:
        unique = f"{candidate}_{counter}"
        counter += 1
    used.add(unique)
    return unique


def _read_models_response(response: Any) -> tuple[str, ...]:
    payload = response.read(MAX_DISCOVERY_RESPONSE_BYTES + 1)
    if len(payload) > MAX_DISCOVERY_RESPONSE_BYTES:
        raise ValueError("model discovery response is too large")
    return _model_ids(json.loads(payload.decode("utf-8")))


def _discover_models(
    base_url: str,
    *,
    key: str,
    headers: Mapping[str, str],
    opener: Callable[..., Any],
    timeout: float,
) -> tuple[str, ...]:
    request = Request(
        f"{base_url.rstrip('/')}/models",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "hermes-ephemeral/1.0",
            **headers,
        },
        method="GET",
    )
    response = opener(request, timeout=timeout)
    close = getattr(response, "close", None)
    try:
        return _read_models_response(response)
    finally:
        if callable(close):
            close()


def discover_openai_v1_providers(
    environ: Mapping[str, str],
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float | None = None,
) -> tuple[tuple[OpenAIV1Provider, ...], tuple[str, ...]]:
    """Discover every repeated OPENAI_V1 group through its models API."""

    request_timeout = timeout or floating(
        environ,
        "HERMES_OPENAI_V1_DISCOVERY_TIMEOUT",
        default=5.0,
    )
    providers: list[OpenAIV1Provider] = []
    warnings: list[str] = []
    used_ids: set[str] = set()

    for index in _indexes(environ):
        raw_url = _group_value(environ, "URL", index)
        if not raw_url:
            continue
        key_env = openai_group_name(environ, "KEY", index)
        key = _clean_openai_v1(environ.get(key_env))
        if not key:
            raise ConfigurationError(f"{key_env} must not be empty")
        configured_name = _group_value(environ, "PROVIDER", index)
        provider_id = _provider_id(configured_name, index, used_ids)
        configured_models = _configured_models(environ, index)
        discovery_headers = _discovery_headers(environ, index)
        base_url = normalize_openai_v1_url(
            raw_url,
            _group_value(environ, "PORT", index),
        )
        try:
            models = _discover_models(
                base_url,
                key=key,
                headers=discovery_headers,
                opener=opener,
                timeout=request_timeout,
            )
        except Exception:
            models = configured_models
            suffix = (
                f"; using {len(configured_models)} configured model(s)"
                if configured_models
                else ""
            )
            warnings.append(
                f"OpenAI-v1 model discovery failed for provider {provider_id}{suffix}"
            )
        else:
            models = tuple(sorted({*models, *configured_models}))
        providers.append(
            OpenAIV1Provider(
                index=index,
                provider_id=provider_id,
                configured_name=configured_name,
                base_url=base_url,
                key_env=key_env,
                models=models,
                streaming=_streaming_value(environ, index),
            )
        )
    return tuple(providers), tuple(warnings)


def select_default(
    providers: Sequence[OpenAIV1Provider],
    configured_model: str,
) -> tuple[str, tuple[OpenAIV1Provider, ...]] | None:
    """Resolve a Hermes model against the discovered repeated groups."""

    wanted = clean(configured_model)
    if not wanted or not providers:
        return None

    selected: OpenAIV1Provider | None = None
    selected_model = wanted
    for provider in providers:
        aliases = {provider.provider_id}
        if provider.configured_name:
            aliases.add(provider.configured_name.lower())
        for alias in aliases:
            prefix = f"{alias}/"
            if wanted.lower().startswith(prefix):
                selected = provider
                selected_model = wanted[len(prefix) :].strip()
                break
        if selected is not None:
            break

    if selected is None:
        selected = next(
            (provider for provider in providers if wanted in provider.models),
            providers[0],
        )
    if not selected_model:
        raise ConfigurationError("HERMES_MODEL must include a model name")

    if selected_model not in selected.models:
        replacement = OpenAIV1Provider(
            index=selected.index,
            provider_id=selected.provider_id,
            configured_name=selected.configured_name,
            base_url=selected.base_url,
            key_env=selected.key_env,
            models=(selected_model, *selected.models),
            streaming=selected.streaming,
        )
        providers = tuple(
            replacement if provider == selected else provider
            for provider in providers
        )
        selected = replacement
    return f"{selected.provider_id}/{selected_model}", tuple(providers)
