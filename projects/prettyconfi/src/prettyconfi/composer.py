"""Composer — merge multiple SchemaFiles into a single ComposedSchema."""

from __future__ import annotations

import dataclasses

from prettyconfi.schema import FieldDef, SchemaFile
from prettyconfi.types import Scope


@dataclasses.dataclass
class ComposedSchema:
    """Merged, deduplicated, sorted schema ready for a runner."""
    fields: list[FieldDef]
    field_map: dict[str, FieldDef]
    sources: dict[str, str]

    def keys(self) -> list[str]:
        """Return all field keys in order."""
        return [f.key for f in self.fields]


def _sort_key(field: FieldDef, schema_order: int) -> tuple:
    """Sort fields: global first, then by schema order, then by field order."""
    scope_rank = 0 if field.scope == Scope.GLOBAL else 1
    return (scope_rank, schema_order, field.order, field.key)


def compose(schemas: list[SchemaFile]) -> ComposedSchema:
    """Merge multiple SchemaFiles into a single ComposedSchema.

    Deduplication rules:
    - Fields are keyed by `key`
    - If a key appears in multiple schemas, `triggered_by` lists are merged
    - First definition wins for all other properties
    - Fields are sorted: global scope first, then by schema_order, then by field order
    """
    field_map: dict[str, FieldDef] = {}
    sources: dict[str, str] = {}
    # Track schema order for each field (from the first schema that defines it)
    field_schema_order: dict[str, int] = {}

    for schema in schemas:
        for field in schema.fields:
            if field.key in field_map:
                # Deduplicate: merge triggered_by only
                existing = field_map[field.key]
                if field.triggered_by:
                    merged = list(existing.triggered_by or [])
                    for t in field.triggered_by:
                        if t not in merged:
                            merged.append(t)
                    existing.triggered_by = merged
            else:
                # First definition wins — make a copy to avoid mutating the original
                field_map[field.key] = dataclasses.replace(field)
                sources[field.key] = schema.name
                field_schema_order[field.key] = schema.order

    # Sort fields
    sorted_fields = sorted(
        field_map.values(),
        key=lambda f: _sort_key(f, field_schema_order.get(f.key, 50)),
    )

    return ComposedSchema(
        fields=sorted_fields,
        field_map=field_map,
        sources=sources,
    )
