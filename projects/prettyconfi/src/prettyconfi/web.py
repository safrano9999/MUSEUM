"""Web runner — JSON Schema export and non-interactive validation."""

from __future__ import annotations

from typing import Any

from prettyconfi.composer import ComposedSchema
from prettyconfi.runner import Runner
from prettyconfi.schema import FieldDef, WhenCondition
from prettyconfi.types import FieldType, PORT_MAX, PORT_MIN


class WebRunner(Runner):
    """Non-interactive runner for web/API usage.

    Takes pre-filled answers (from POST data) and validates them.
    Does not prompt — just returns current values.
    """

    def ask_field(self, field: FieldDef, current_value: Any) -> Any:
        return current_value

    def ask_retry(self, field: FieldDef, attempt: int) -> bool:
        # Web UI handles retry via its own JS logic
        return False

    @staticmethod
    def to_json_schema(schema: ComposedSchema) -> dict:
        """Export ComposedSchema as a JSON Schema-like structure for web form rendering.

        Returns a dict with:
        - fields: ordered list of field definitions
        - groups: unique group names in order
        - required: list of required field keys

        Each field in 'fields' includes:
        - key, type, default, label, help, required, scope, group, order
        - choices (for choice type)
        - when (conditional rules, serialized)
        - retry_on_no, retry_prompt
        - triggered_by
        - publish_port
        """
        fields = []
        groups_seen: list[str] = []
        required: list[str] = []

        for f in schema.fields:
            entry: dict[str, Any] = {
                "key": f.key,
                "type": f.type,
                "default": f.default,
                "label": f.label,
                "help": f.help,
                "required": f.required,
                "scope": f.scope,
                "group": f.group,
                "order": f.order,
            }

            if f.choices:
                entry["choices"] = f.choices
            if f.when:
                entry["when"] = [_serialize_when(w) for w in f.when]
            if f.retry_on_no:
                entry["retry_on_no"] = f.retry_on_no
                entry["retry_prompt"] = f.retry_prompt
            if f.triggered_by:
                entry["triggered_by"] = f.triggered_by
            if f.publish_port:
                entry["publish_port"] = True

            fields.append(entry)

            if f.group and f.group not in groups_seen:
                groups_seen.append(f.group)
            if f.required:
                required.append(f.key)

        return {
            "fields": fields,
            "groups": groups_seen,
            "required": required,
        }

    @staticmethod
    def validate(schema: ComposedSchema, data: dict) -> tuple[dict, list[str]]:
        """Validate submitted data against the schema.

        Returns (validated_data, error_list).
        Skips validation for fields whose when-conditions aren't met.
        """
        runner = WebRunner(schema, seed=data)
        answers = runner.run()
        errors = runner.validate_all(answers)
        return answers, errors


def _serialize_when(w: WhenCondition) -> dict:
    """Serialize a WhenCondition to a JSON-safe dict."""
    d: dict[str, Any] = {"key": w.key}
    if w.eq is not None:
        d["eq"] = w.eq
    if w.neq is not None:
        d["neq"] = w.neq
    if w.in_ is not None:
        d["in"] = w.in_
    if w.truthy is not None:
        d["truthy"] = w.truthy
    return d
