"""Strict parsing helpers for the injected Hermes environment."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


API_KEY_ALIAS = re.compile(r"^[A-Z][A-Z0-9_]*_API_KEY$")


class ConfigurationError(ValueError):
    """Raised when injected runtime configuration is invalid."""


def clean(value: str | None) -> str:
    """Return a stripped environment value."""

    return (value or "").strip()


def floating(
    environ: Mapping[str, str],
    name: str,
    *,
    default: float,
    minimum: float = 0.1,
    maximum: float = 300.0,
) -> float:
    """Parse one bounded floating-point environment value."""

    raw = clean(environ.get(name))
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum:g} and {maximum:g}"
        )
    return value


def openai_group_name(
    environ: Mapping[str, str],
    field: str,
    index: int,
) -> str:
    """Resolve the suffixless first and numbered later OpenAI-v1 fields."""

    field = field.upper()
    if index == 1:
        return f"OPENAI_V1_{field}"
    candidates = (
        f"OPENAI_V1_{field}_{index}",
        f"OPENAI_V1_{field}_{index:02d}",
    )
    for candidate in candidates:
        if clean(environ.get(candidate)):
            return candidate
    for candidate in candidates:
        if candidate in environ:
            return candidate
    return candidates[0]


def expand_api_key_aliases(environ: Mapping[str, str]) -> dict[str, str]:
    """Materialize OPENAI_V1 reverse aliases only in process memory."""

    expanded = dict(environ)
    indexes = {1}
    pattern = re.compile(r"^OPENAI_V1_API_KEY_ALIAS_(\d+)$")
    for name in environ:
        match = pattern.fullmatch(name)
        if match:
            indexes.add(int(match.group(1), 10))

    for index in sorted(indexes):
        alias_name = openai_group_name(environ, "API_KEY_ALIAS", index)
        alias = clean(environ.get(alias_name))
        if not alias:
            continue
        if not API_KEY_ALIAS.fullmatch(alias):
            raise ConfigurationError(
                f"{alias_name} must name an uppercase *_API_KEY variable"
            )
        key_name = openai_group_name(environ, "KEY", index)
        key_value = clean(environ.get(key_name))
        if key_value and not clean(expanded.get(alias)):
            expanded[alias] = key_value
    return expanded


def without_secret_values(value: Any, secret_values: set[str]) -> bool:
    """Return whether a nested structure contains none of the supplied secrets."""

    if isinstance(value, str):
        return value not in secret_values
    if isinstance(value, Mapping):
        return all(
            without_secret_values(key, secret_values)
            and without_secret_values(item, secret_values)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return all(without_secret_values(item, secret_values) for item in value)
    return True

