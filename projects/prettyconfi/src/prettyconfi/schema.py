"""Schema loading — FieldDef, WhenCondition, SchemaFile, TOML parser."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from prettyconfi.types import FieldType, Scope

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclasses.dataclass(frozen=True)
class WhenCondition:
    """A single visibility condition for a field."""
    key: str
    eq: str | None = None
    neq: str | None = None
    in_: list[str] | None = None
    truthy: bool | None = None

    def evaluate(self, answers: dict) -> bool:
        """Check if this condition is satisfied by current answers."""
        value = answers.get(self.key)
        if self.truthy is not None:
            return bool(value) == self.truthy
        if value is None:
            return False
        val_str = str(value).strip()
        if self.eq is not None:
            return val_str == self.eq
        if self.neq is not None:
            return val_str != self.neq
        if self.in_ is not None:
            return val_str in self.in_
        return True


@dataclasses.dataclass
class FieldDef:
    """Definition of a single configuration field."""
    key: str
    type: str = "str"
    default: str | int | bool = ""
    label: str = ""
    help: str = ""
    required: bool = False
    scope: str = "module"
    group: str = ""
    order: int = 100
    choices: list[str] | None = None
    when: list[WhenCondition] | None = None
    retry_on_no: int = 0
    retry_prompt: str = ""
    triggered_by: list[str] | None = None
    publish_port: bool = False

    def __post_init__(self):
        if not self.label:
            self.label = self.key
        if self.type not in {t.value for t in FieldType}:
            raise ValueError(f"Unknown field type: {self.type!r} for key {self.key!r}")


@dataclasses.dataclass
class SchemaFile:
    """A parsed schema file with its fields."""
    name: str
    scope: str = "module"
    order: int = 50
    fields: list[FieldDef] = dataclasses.field(default_factory=list)


def _parse_when(raw) -> list[WhenCondition] | None:
    """Parse 'when' from TOML — can be a dict or list of dicts."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return None
    conditions = []
    for item in raw:
        if not isinstance(item, dict) or "key" not in item:
            continue
        conditions.append(WhenCondition(
            key=str(item["key"]),
            eq=str(item["eq"]) if "eq" in item else None,
            neq=str(item["neq"]) if "neq" in item else None,
            in_=[str(x) for x in item["in"]] if "in" in item and isinstance(item["in"], list) else None,
            truthy=bool(item["truthy"]) if "truthy" in item else None,
        ))
    return conditions if conditions else None


def _parse_field(raw: dict, schema_scope: str) -> FieldDef:
    """Parse a single field from a TOML [[fields]] entry."""
    key = str(raw.get("key", "")).strip()
    if not key:
        raise ValueError("Field missing required 'key'")

    field_type = str(raw.get("type", "str")).strip().lower()
    default = raw.get("default", "")
    choices_raw = raw.get("choices")
    choices = [str(c) for c in choices_raw] if isinstance(choices_raw, list) else None

    triggered_raw = raw.get("triggered_by")
    triggered_by = [str(t) for t in triggered_raw] if isinstance(triggered_raw, list) else None

    return FieldDef(
        key=key,
        type=field_type,
        default=default,
        label=str(raw.get("label", "")).strip(),
        help=str(raw.get("help", "")).strip(),
        required=bool(raw.get("required", False)),
        scope=str(raw.get("scope", schema_scope)).strip().lower(),
        group=str(raw.get("group", "")).strip(),
        order=int(raw.get("order", 100)),
        choices=choices,
        when=_parse_when(raw.get("when")),
        retry_on_no=int(raw.get("retry_on_no", 0)),
        retry_prompt=str(raw.get("retry_prompt", "")).strip(),
        triggered_by=triggered_by,
        publish_port=bool(raw.get("publish_port", False)),
    )


def load_schema(path: Path) -> SchemaFile:
    """Load a single TOML schema file and return a SchemaFile."""
    text = path.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Schema {path} is not a TOML table")

    name = str(data.get("schema_name", path.stem)).strip()
    scope = str(data.get("schema_scope", "module")).strip().lower()
    order = int(data.get("schema_order", 50))

    fields_raw = data.get("fields", [])
    if not isinstance(fields_raw, list):
        raise ValueError(f"Schema {path}: 'fields' must be an array of tables")

    fields = []
    for i, raw in enumerate(fields_raw):
        if not isinstance(raw, dict):
            raise ValueError(f"Schema {path}: fields[{i}] is not a table")
        fields.append(_parse_field(raw, scope))

    return SchemaFile(name=name, scope=scope, order=order, fields=fields)


def load_schemas(paths: list[Path]) -> list[SchemaFile]:
    """Load multiple TOML schema files."""
    return [load_schema(p) for p in paths]
