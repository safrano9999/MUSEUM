"""Tests for schema loading and parsing."""

from pathlib import Path
import pytest
from prettyconfi.schema import load_schema, load_schemas, WhenCondition, FieldDef

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_base_schema():
    schema = load_schema(FIXTURES / "base.toml")
    assert schema.name == "base"
    assert schema.scope == "global"
    assert schema.order == 1
    assert len(schema.fields) == 3


def test_load_module_schema():
    schema = load_schema(FIXTURES / "module_a.toml")
    assert schema.name == "module_a"
    assert schema.scope == "module"
    assert len(schema.fields) == 3


def test_field_properties():
    schema = load_schema(FIXTURES / "base.toml")
    stack = schema.fields[0]
    assert stack.key == "STACK_NAME"
    assert stack.type == "str"
    assert stack.default == "web-stack"
    assert stack.required is True
    assert stack.scope == "global"
    assert stack.group == "base"


def test_field_choices():
    schema = load_schema(FIXTURES / "base.toml")
    network = schema.fields[1]
    assert network.key == "NETWORK"
    assert network.type == "choice"
    assert network.choices == ["host", "bridge", "custom"]


def test_field_when_condition():
    schema = load_schema(FIXTURES / "base.toml")
    bridge = schema.fields[2]
    assert bridge.key == "BRIDGE_NAME"
    assert bridge.when is not None
    assert len(bridge.when) == 1
    assert bridge.when[0].key == "NETWORK"
    assert bridge.when[0].eq == "bridge"


def test_field_retry():
    schema = load_schema(FIXTURES / "module_a.toml")
    api_key = [f for f in schema.fields if f.key == "OPENAI_API_KEY"][0]
    assert api_key.retry_on_no == 2
    assert "Really skip" in api_key.retry_prompt


def test_field_triggered_by():
    schema = load_schema(FIXTURES / "module_a.toml")
    api_key = [f for f in schema.fields if f.key == "OPENAI_API_KEY"][0]
    assert api_key.triggered_by == ["module_a", "module_b"]


def test_load_multiple_schemas():
    schemas = load_schemas([
        FIXTURES / "base.toml",
        FIXTURES / "module_a.toml",
        FIXTURES / "module_b.toml",
    ])
    assert len(schemas) == 3
    assert schemas[0].name == "base"
    assert schemas[1].name == "module_a"
    assert schemas[2].name == "module_b"


def test_when_condition_evaluate_eq():
    cond = WhenCondition(key="MODE", eq="proxy")
    assert cond.evaluate({"MODE": "proxy"}) is True
    assert cond.evaluate({"MODE": "sdk"}) is False
    assert cond.evaluate({}) is False


def test_when_condition_evaluate_neq():
    cond = WhenCondition(key="NET", neq="host")
    assert cond.evaluate({"NET": "bridge"}) is True
    assert cond.evaluate({"NET": "host"}) is False


def test_when_condition_evaluate_in():
    cond = WhenCondition(key="NET", in_=["bridge", "custom"])
    assert cond.evaluate({"NET": "bridge"}) is True
    assert cond.evaluate({"NET": "custom"}) is True
    assert cond.evaluate({"NET": "host"}) is False


def test_when_condition_evaluate_truthy():
    cond = WhenCondition(key="ENABLE", truthy=True)
    assert cond.evaluate({"ENABLE": True}) is True
    assert cond.evaluate({"ENABLE": "yes"}) is True
    assert cond.evaluate({"ENABLE": False}) is False
    assert cond.evaluate({"ENABLE": ""}) is False
    assert cond.evaluate({}) is False


def test_invalid_field_type():
    with pytest.raises(ValueError, match="Unknown field type"):
        FieldDef(key="X", type="invalid_type")


def test_field_label_defaults_to_key():
    f = FieldDef(key="MY_VAR")
    assert f.label == "MY_VAR"
