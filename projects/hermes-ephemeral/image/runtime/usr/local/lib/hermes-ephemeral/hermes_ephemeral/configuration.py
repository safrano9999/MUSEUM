"""Build and atomically publish a fresh Hermes configuration."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .environment import (
    ConfigurationError,
    clean,
    expand_api_key_aliases,
    without_secret_values,
)
from .mcp import mcp_servers_config
from .providers import (
    OpenAIV1Provider,
    discover_openai_v1_providers,
    select_default,
)


@dataclass(frozen=True)
class HermesPaths:
    """Runtime paths derived only from the injected environment."""

    home: Path
    config: Path
    template: Path | None


@dataclass(frozen=True)
class BuildResult:
    """One secret-free configuration build and its diagnostic metadata."""

    config: dict[str, Any]
    full_model: str
    provider_count: int
    mcp_server_count: int
    warnings: tuple[str, ...]


def _expand_path(raw: str, process_home: Path) -> Path:
    if raw == "~" or raw.startswith("~/"):
        raw = str(process_home) + raw[1:]
    path = Path(raw)
    if not path.is_absolute():
        path = process_home / path
    return path.resolve()


def _template_from_executable(environ: Mapping[str, str]) -> Path | None:
    raw_executable = clean(environ.get("HERMES_BIN")) or "hermes"
    executable = shutil.which(raw_executable, path=environ.get("PATH"))
    if not executable:
        return None
    candidate = (
        Path(executable).parent.parent
        / "lib"
        / "hermes-agent"
        / "cli-config.yaml.example"
    )
    return candidate if candidate.is_file() else None


def paths_from_environment(environ: Mapping[str, str]) -> HermesPaths:
    """Resolve Hermes paths without an operating-system or image-specific root."""

    raw_process_home = clean(environ.get("HOME")) or str(Path.home())
    if not Path(raw_process_home).is_absolute():
        raise ConfigurationError("HOME must be an absolute path")
    process_home = Path(raw_process_home).resolve()
    home = process_home / ".hermes"
    config = home / "config.yaml"

    raw_template = clean(environ.get("HERMES_CONFIG_TEMPLATE"))
    template = (
        _expand_path(raw_template, process_home)
        if raw_template
        else _template_from_executable(environ)
    )
    return HermesPaths(home=home, config=config, template=template)


def _fresh_template(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ConfigurationError("HERMES_CONFIG_TEMPLATE must contain a YAML mapping")
    return payload


def _requested_model(
    environ: Mapping[str, str],
    providers: tuple[OpenAIV1Provider, ...],
) -> str:
    explicit = clean(environ.get("HERMES_MODEL"))
    if explicit:
        return explicit
    for provider in providers:
        if provider.models:
            return provider.models[0]
    raise ConfigurationError(
        "HERMES_MODEL is required when provider model discovery returns no models"
    )


def build_configuration(
    raw_environ: Mapping[str, str],
    *,
    template: Mapping[str, Any] | None = None,
    opener: Callable[..., Any] | None = None,
) -> BuildResult:
    """Create a complete fresh configuration without reading the old config."""

    environ = expand_api_key_aliases(raw_environ)
    mcp_servers = mcp_servers_config(environ)
    discovery_options: dict[str, Any] = {}
    if opener is not None:
        discovery_options["opener"] = opener
    providers, warnings = discover_openai_v1_providers(
        environ,
        **discovery_options,
    )
    if not providers:
        raise ConfigurationError(
            "Hermes requires at least one injected OPENAI_V1_URL/KEY provider"
        )

    requested = _requested_model(environ, providers)
    selected = select_default(providers, requested)
    if selected is None:
        raise ConfigurationError("Hermes could not select an OpenAI-v1 model")
    full_model, providers = selected
    selected_provider_id, selected_model = full_model.split("/", 1)
    selected_provider = next(
        provider
        for provider in providers
        if provider.provider_id == selected_provider_id
    )

    config = dict(template or {})
    available = list(selected_provider.models)
    if selected_model not in available:
        available.insert(0, selected_model)
    config["model"] = {
        "provider": selected_provider.provider_id,
        "default": selected_model,
        "base_url": selected_provider.base_url,
        "ssl_verify": True,
        "available": available,
    }
    config["providers"] = {
        provider.provider_id: provider.hermes_config()
        for provider in providers
    }
    config["providers"][selected_provider.provider_id]["default_model"] = selected_model

    if mcp_servers:
        config["mcp_servers"] = mcp_servers
    else:
        config.pop("mcp_servers", None)

    secret_values = {
        clean(value)
        for name, value in environ.items()
        if clean(value)
        and (
            name.endswith("_API_KEY")
            or name.startswith("OPENAI_V1_KEY")
            or name.startswith("MCP_SERVER_BEARER")
            or name in {"HERMES_API_SERVER_KEY", "HERMES_TELEGRAMTOKEN"}
        )
    }
    if not without_secret_values(config, secret_values):
        raise ConfigurationError("refusing to persist a resolved secret value")

    return BuildResult(
        config=config,
        full_model=full_model,
        provider_count=len(providers),
        mcp_server_count=len(mcp_servers),
        warnings=warnings,
    )


def _atomic_write(destination: Path, config: Mapping[str, Any]) -> None:
    parent_existed = destination.parent.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed:
        os.chmod(destination.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            yaml.safe_dump(dict(config), handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def rebuild_configuration(environ: Mapping[str, str]) -> BuildResult:
    """Build from the current environment and atomically replace config.yaml."""

    paths = paths_from_environment(environ)
    result = build_configuration(
        environ,
        template=_fresh_template(paths.template),
    )
    _atomic_write(paths.config, result.config)
    return result
