"""Abstract runner — iterates fields, evaluates conditions, collects answers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from prettyconfi.composer import ComposedSchema
from prettyconfi.schema import FieldDef, WhenCondition
from prettyconfi.types import FieldType, PORT_MAX, PORT_MIN

# Sentinel values returned by ask_field to signal navigation
_BACK = object()
_SAVE = object()


class StopSave(Exception):
    """Raised when user wants to save and quit mid-flow."""
    def __init__(self, answers: dict):
        self.answers = answers


class Runner(ABC):
    """Base class for configuration runners (CLI, Web, etc.)."""

    def __init__(self, schema: ComposedSchema, seed: dict | None = None):
        self.schema = schema
        self.seed = seed or {}

    def evaluate_when(self, conditions: list[WhenCondition], answers: dict) -> bool:
        """Evaluate all conditions (AND logic). All must be true."""
        return all(c.evaluate(answers) for c in conditions)

    @abstractmethod
    def ask_field(self, field: FieldDef, current_value: Any) -> Any:
        """Ask the user for a field value. Implementation varies by runner type.

        May return _BACK to go to previous field, or _SAVE to save & quit.
        """

    def ask_retry(self, field: FieldDef, attempt: int) -> bool:
        """Ask user to reconsider a 'no' answer. Override in subclasses."""
        return False

    def validate_value(self, field: FieldDef, value: Any) -> tuple[Any, str | None]:
        """Validate and coerce a value. Returns (coerced_value, error_or_none)."""
        if field.required and (value is None or str(value).strip() == ""):
            return value, f"{field.key} is required"

        if value is None or str(value).strip() == "":
            return field.default, None

        match field.type:
            case FieldType.STR:
                return str(value), None

            case FieldType.INT:
                try:
                    return int(value), None
                except (ValueError, TypeError):
                    return value, f"{field.key}: expected integer, got {value!r}"

            case FieldType.BOOL:
                if isinstance(value, bool):
                    return value, None
                s = str(value).strip().lower()
                if s in {"1", "true", "yes", "y", "ja", "j"}:
                    return True, None
                if s in {"0", "false", "no", "n", "nein"}:
                    return False, None
                return value, f"{field.key}: expected boolean, got {value!r}"

            case FieldType.PORT:
                try:
                    port = int(value)
                except (ValueError, TypeError):
                    return value, f"{field.key}: expected port number, got {value!r}"
                if not (PORT_MIN <= port <= PORT_MAX):
                    return value, f"{field.key}: port must be {PORT_MIN}-{PORT_MAX}, got {port}"
                return port, None

            case FieldType.CHOICE:
                s = str(value).strip()
                if field.choices and s not in field.choices:
                    return value, f"{field.key}: must be one of {field.choices}, got {s!r}"
                return s, None

        return value, None

    def _visible_fields(self, answers: dict) -> list[FieldDef]:
        """Return list of fields whose conditions are currently met."""
        return [
            f for f in self.schema.fields
            if not f.when or self.evaluate_when(f.when, answers)
        ]

    def run(self) -> dict[str, Any]:
        """Iterate all fields, evaluate conditions, collect answers.

        Supports navigation:
        - _BACK: go to previous visible field
        - _SAVE: save current answers and raise StopSave

        Returns a dict of key -> validated value.
        """
        answers: dict[str, Any] = dict(self.seed)

        # We use index-based iteration to support going back
        visible = self._visible_fields(answers)
        idx = 0

        while idx < len(visible):
            field = visible[idx]

            # Re-check condition (answers may have changed from going back)
            if field.when and not self.evaluate_when(field.when, answers):
                idx += 1
                continue

            current = answers.get(field.key, field.default)
            value = self.ask_field(field, current)

            # Handle navigation
            if value is _SAVE:
                raise StopSave(answers)

            if value is _BACK:
                # Go back to previous visible field
                if idx > 0:
                    idx -= 1
                    # Recalculate visible fields since answers might differ
                    visible = self._visible_fields(answers)
                    idx = min(idx, len(visible) - 1)
                continue

            # Retry logic for fields where "no" should be reconsidered
            if field.retry_on_no and not value:
                for attempt in range(field.retry_on_no):
                    reconsidered = self.ask_retry(field, attempt + 1)
                    if reconsidered:
                        value = reconsidered
                        break

            # Validate and store
            coerced, error = self.validate_value(field, value)
            if error:
                answers[field.key] = value
            else:
                answers[field.key] = coerced

            # Recalculate visible fields (new answer may change conditions)
            visible = self._visible_fields(answers)

            # Find next index — the field we just answered might have shifted
            # Find first visible field after current one
            found_next = False
            for i, f in enumerate(visible):
                if f.key == field.key:
                    idx = i + 1
                    found_next = True
                    break
            if not found_next:
                idx += 1

        return answers

    def validate_all(self, answers: dict) -> list[str]:
        """Validate a complete answers dict against the schema.

        Returns list of error messages (empty = valid).
        Skips fields whose conditions aren't met.
        """
        errors = []
        for field in self.schema.fields:
            if field.when and not self.evaluate_when(field.when, answers):
                continue
            value = answers.get(field.key)
            _, error = self.validate_value(field, value)
            if error:
                errors.append(error)
        return errors
