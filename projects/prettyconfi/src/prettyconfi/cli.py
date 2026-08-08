"""CLI runner — interactive terminal prompts via questionary."""

from __future__ import annotations

from typing import Any

from prettyconfi.runner import Runner, _BACK, _SAVE
from prettyconfi.schema import FieldDef
from prettyconfi.types import FieldType, PORT_MAX, PORT_MIN

try:
    import questionary
    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False


class CLIRunner(Runner):
    """Interactive CLI runner using questionary for pretty terminal prompts.

    Requires: pip install prettyconfi[cli]

    Navigation:
    - Type '<' or 'back' at any text prompt to go back
    - Type '!save' at any text prompt to save & quit
    - For choice/confirm prompts, extra options are shown
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not _HAS_QUESTIONARY:
            raise ImportError(
                "questionary is required for CLI mode. "
                "Install it with: pip install prettyconfi[cli]"
            )

    def ask_field(self, field: FieldDef, current_value: Any) -> Any:
        label = field.label or field.key
        if field.help:
            label = f"{label} ({field.help})"

        match field.type:
            case FieldType.STR:
                return self._ask_text(label, current_value, field)

            case FieldType.INT:
                return self._ask_int(label, current_value, field)

            case FieldType.PORT:
                return self._ask_port(label, current_value, field)

            case FieldType.BOOL:
                return self._ask_bool(label, current_value, field)

            case FieldType.CHOICE:
                return self._ask_choice(label, current_value, field)

            case _:
                return self._ask_text(label, current_value, field)

    def ask_retry(self, field: FieldDef, attempt: int) -> Any:
        prompt = field.retry_prompt or f"{field.label} -- really skip? ({attempt}/{field.retry_on_no})"
        result = questionary.confirm(prompt, default=True).ask()
        if result is None:
            return False
        if not result:
            return False
        return self.ask_field(field, field.default)

    def _check_nav(self, raw: str | None) -> Any | None:
        """Check for navigation commands in text input."""
        if raw is None:
            return _SAVE
        s = raw.strip().lower()
        if s in ("<", "back"):
            return _BACK
        if s == "!save":
            return _SAVE
        return None

    def _ask_text(self, label: str, current_value: Any, field: FieldDef) -> Any:
        hint = "  (< back | !save)"
        raw = questionary.text(label + hint, default=str(current_value or "")).ask()
        nav = self._check_nav(raw)
        if nav is not None:
            return nav
        return raw

    def _ask_int(self, label: str, current_value: Any, field: FieldDef) -> Any:
        default = str(current_value) if current_value is not None else ""
        hint = "  (< back | !save)"
        while True:
            raw = questionary.text(label + hint, default=default).ask()
            nav = self._check_nav(raw)
            if nav is not None:
                return nav
            raw = raw.strip()
            if not raw and current_value is not None:
                return int(current_value)
            try:
                return int(raw)
            except ValueError:
                print("  Please enter a number.")
                default = raw

    def _ask_port(self, label: str, current_value: Any, field: FieldDef) -> Any:
        default = str(current_value) if current_value is not None else ""
        hint = "  (< back | !save)"
        while True:
            raw = questionary.text(label + hint, default=default).ask()
            nav = self._check_nav(raw)
            if nav is not None:
                return nav
            raw = raw.strip()
            if not raw and current_value is not None:
                return int(current_value)
            try:
                port = int(raw)
            except ValueError:
                print("  Please enter a number.")
                default = raw
                continue
            if not (PORT_MIN <= port <= PORT_MAX):
                print(f"  Port must be {PORT_MIN}-{PORT_MAX}.")
                default = raw
                continue
            return port

    def _ask_bool(self, label: str, current_value: Any, field: FieldDef) -> Any:
        default = current_value if isinstance(current_value, bool) else True
        choices = [
            questionary.Choice("Yes", value="yes"),
            questionary.Choice("No", value="no"),
            questionary.Choice("< Back", value="_back"),
            questionary.Choice("Save & Quit", value="_save"),
        ]
        result = questionary.select(
            label, choices=choices,
            default="yes" if default else "no",
        ).ask()
        if result is None or result == "_save":
            return _SAVE
        if result == "_back":
            return _BACK
        return result == "yes"

    def _ask_choice(self, label: str, current_value: Any, field: FieldDef) -> Any:
        choices = [questionary.Choice(c, value=c) for c in (field.choices or [])]
        choices.append(questionary.Choice("< Back", value="_back"))
        choices.append(questionary.Choice("Save & Quit", value="_save"))
        default_val = str(current_value) if current_value else None
        result = questionary.select(label, choices=choices, default=default_val).ask()
        if result is None or result == "_save":
            return _SAVE
        if result == "_back":
            return _BACK
        return result
