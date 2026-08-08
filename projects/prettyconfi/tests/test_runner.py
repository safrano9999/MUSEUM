"""Tests for the abstract runner — validation, conditions, retry."""

from pathlib import Path
from typing import Any

from prettyconfi.schema import load_schemas, FieldDef, WhenCondition
from prettyconfi.composer import compose, ComposedSchema
from prettyconfi.runner import Runner

FIXTURES = Path(__file__).parent / "fixtures"


class DictRunner(Runner):
    """Test runner that returns pre-set answers instead of prompting."""

    def __init__(self, schema, seed=None, answers_override=None):
        super().__init__(schema, seed)
        self._answers = answers_override or {}
        self._retry_count = 0

    def ask_field(self, field: FieldDef, current_value: Any) -> Any:
        if field.key in self._answers:
            return self._answers[field.key]
        return current_value

    def ask_retry(self, field: FieldDef, attempt: int) -> Any:
        self._retry_count += 1
        # Simulate: accept on 2nd retry
        if attempt >= 2:
            return self._answers.get(f"_retry_{field.key}", True)
        return False


def _compose_fixtures(*names):
    paths = [FIXTURES / n for n in names]
    return compose(load_schemas(paths))


def test_run_basic():
    composed = _compose_fixtures("base.toml")
    runner = DictRunner(composed, answers_override={
        "STACK_NAME": "test-stack",
        "NETWORK": "host",
    })
    result = runner.run()
    assert result["STACK_NAME"] == "test-stack"
    assert result["NETWORK"] == "host"


def test_run_skips_conditional():
    composed = _compose_fixtures("base.toml")
    runner = DictRunner(composed, answers_override={
        "STACK_NAME": "test",
        "NETWORK": "host",  # Not bridge → BRIDGE_NAME should be skipped
    })
    result = runner.run()
    assert "BRIDGE_NAME" not in result


def test_run_includes_conditional_when_met():
    composed = _compose_fixtures("base.toml")
    runner = DictRunner(composed, answers_override={
        "STACK_NAME": "test",
        "NETWORK": "bridge",
        "BRIDGE_NAME": "my-net",
    })
    result = runner.run()
    assert result["BRIDGE_NAME"] == "my-net"


def test_run_uses_seed():
    composed = _compose_fixtures("base.toml")
    runner = DictRunner(
        composed,
        seed={"STACK_NAME": "seeded-stack"},
        answers_override={"NETWORK": "host"},
    )
    result = runner.run()
    assert result["STACK_NAME"] == "seeded-stack"


def test_run_uses_default():
    composed = _compose_fixtures("base.toml")
    runner = DictRunner(composed)  # No answers override, no seed
    result = runner.run()
    assert result["STACK_NAME"] == "web-stack"  # default from schema
    assert result["NETWORK"] == "host"


def test_validate_required():
    composed = _compose_fixtures("base.toml")
    runner = DictRunner(composed)
    errors = runner.validate_all({"STACK_NAME": "", "NETWORK": "host"})
    assert any("STACK_NAME" in e for e in errors)


def test_validate_port_range():
    field = FieldDef(key="PORT", type="port")
    runner = DictRunner(ComposedSchema(fields=[], field_map={}, sources={}))

    _, err = runner.validate_value(field, 80)
    assert err is None

    _, err = runner.validate_value(field, 0)
    assert err is not None

    _, err = runner.validate_value(field, 70000)
    assert err is not None


def test_validate_choice():
    field = FieldDef(key="MODE", type="choice", choices=["a", "b"])
    runner = DictRunner(ComposedSchema(fields=[], field_map={}, sources={}))

    _, err = runner.validate_value(field, "a")
    assert err is None

    _, err = runner.validate_value(field, "c")
    assert err is not None


def test_validate_int():
    field = FieldDef(key="COUNT", type="int")
    runner = DictRunner(ComposedSchema(fields=[], field_map={}, sources={}))

    val, err = runner.validate_value(field, "42")
    assert val == 42 and err is None

    _, err = runner.validate_value(field, "abc")
    assert err is not None


def test_validate_bool():
    field = FieldDef(key="FLAG", type="bool")
    runner = DictRunner(ComposedSchema(fields=[], field_map={}, sources={}))

    val, err = runner.validate_value(field, "yes")
    assert val is True and err is None

    val, err = runner.validate_value(field, "nein")
    assert val is False and err is None

    _, err = runner.validate_value(field, "maybe")
    assert err is not None


def test_retry_logic():
    """Test that retry_on_no asks again."""
    field = FieldDef(
        key="API_KEY", type="str", required=True,
        retry_on_no=3, retry_prompt="Really?",
    )
    composed = ComposedSchema(fields=[field], field_map={"API_KEY": field}, sources={})
    runner = DictRunner(
        composed,
        answers_override={"API_KEY": "", "_retry_API_KEY": "my-key-123"},
    )
    result = runner.run()
    assert runner._retry_count >= 1


def test_conditional_chain():
    """Test nested conditionals: A enables B, B enables C."""
    fields = [
        FieldDef(key="ENABLE_A", type="bool", default=True, order=1),
        FieldDef(key="SETTING_B", type="str", default="val_b", order=2,
                 when=[WhenCondition(key="ENABLE_A", truthy=True)]),
        FieldDef(key="SETTING_C", type="str", default="val_c", order=3,
                 when=[WhenCondition(key="SETTING_B", eq="val_b")]),
    ]
    composed = ComposedSchema(
        fields=fields,
        field_map={f.key: f for f in fields},
        sources={},
    )

    # A=True → B visible → C visible
    runner = DictRunner(composed, answers_override={"ENABLE_A": True})
    result = runner.run()
    assert "SETTING_B" in result
    assert "SETTING_C" in result

    # A=False → B skipped → C skipped (B never set so condition fails)
    runner = DictRunner(composed, answers_override={"ENABLE_A": False})
    result = runner.run()
    assert "SETTING_B" not in result
    assert "SETTING_C" not in result


def test_evaluate_when_and_logic():
    """All conditions must be true (AND)."""
    composed = ComposedSchema(fields=[], field_map={}, sources={})
    runner = DictRunner(composed)

    conditions = [
        WhenCondition(key="A", eq="yes"),
        WhenCondition(key="B", neq="no"),
    ]
    assert runner.evaluate_when(conditions, {"A": "yes", "B": "yes"}) is True
    assert runner.evaluate_when(conditions, {"A": "yes", "B": "no"}) is False
    assert runner.evaluate_when(conditions, {"A": "no", "B": "yes"}) is False
