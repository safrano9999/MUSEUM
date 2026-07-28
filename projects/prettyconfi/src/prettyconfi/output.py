"""Output — write and read configuration results."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def to_dict(answers: dict) -> dict[str, str]:
    """Return a clean dict with all values stringified."""
    return {str(k): str(v) for k, v in answers.items()}


def to_env(answers: dict, path: Path) -> None:
    """Write answers as a KEY=VALUE .env file."""
    lines = []
    for key, value in answers.items():
        # Escape values containing special characters
        val = str(value)
        if any(c in val for c in (" ", '"', "'", "\n", "#", "$")):
            val = '"' + val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        lines.append(f"{key}={val}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def to_toml(answers: dict, path: Path, *, meta: dict | None = None) -> None:
    """Write answers as a structured TOML config.

    Output format:
        schema_version = 1
        [meta]
        key = "value"
        [env]
        KEY = "value"
    """
    lines = ["schema_version = 1", ""]
    if meta:
        lines.append("[meta]")
        for k, v in meta.items():
            lines.append(f'{k} = {_toml_value(v)}')
        lines.append("")
    lines.append("[env]")
    for k, v in answers.items():
        lines.append(f'{k} = {_toml_value(v)}')
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def to_json(answers: dict, path: Path, *, meta: dict | None = None) -> None:
    """Write answers as JSON."""
    data: dict = {}
    if meta:
        data["meta"] = meta
    data["env"] = {str(k): _json_safe(v) for k, v in answers.items()}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def from_toml(path: Path) -> dict:
    """Load answers from a saved TOML config.

    Reads [env] section. Returns flat dict.
    """
    text = path.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    if not isinstance(data, dict):
        return {}
    env = data.get("env", {})
    if isinstance(env, dict):
        return {str(k): v for k, v in env.items()}
    return {}


def from_env(path: Path) -> dict:
    """Load answers from a .env file. Handles quoted values."""
    result: dict[str, str] = OrderedDict()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            quote_char = value[0]
            value = value[1:-1]
            if quote_char == '"':
                value = value.replace("\\\\", "\x00").replace('\\"', '"').replace("\\n", "\n").replace("\x00", "\\")
        result[key] = value
    return result


def _toml_value(v) -> str:
    """Format a value for TOML output."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        items = ", ".join(_toml_value(x) for x in v)
        return f"[{items}]"
    # String — escape backslashes and quotes
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _json_safe(v):
    """Ensure value is JSON-serializable."""
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, list):
        return [_json_safe(x) for x in v]
    return str(v)
