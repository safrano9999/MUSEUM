"""Tests for the web runner — JSON schema export and validation."""

from pathlib import Path

from prettyconfi.schema import load_schemas
from prettyconfi.composer import compose
from prettyconfi.web import WebRunner

FIXTURES = Path(__file__).parent / "fixtures"


def test_to_json_schema_basic():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)

    assert "fields" in js
    assert "groups" in js
    assert "required" in js
    assert len(js["fields"]) == 3


def test_to_json_schema_field_properties():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)

    stack = js["fields"][0]
    assert stack["key"] == "STACK_NAME"
    assert stack["type"] == "str"
    assert stack["default"] == "web-stack"
    assert stack["required"] is True


def test_to_json_schema_choices():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)

    network = [f for f in js["fields"] if f["key"] == "NETWORK"][0]
    assert network["choices"] == ["host", "bridge", "custom"]


def test_to_json_schema_when():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)

    bridge = [f for f in js["fields"] if f["key"] == "BRIDGE_NAME"][0]
    assert "when" in bridge
    assert bridge["when"][0]["key"] == "NETWORK"
    assert bridge["when"][0]["eq"] == "bridge"


def test_to_json_schema_groups():
    schemas = load_schemas([
        FIXTURES / "base.toml",
        FIXTURES / "module_a.toml",
    ])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)
    assert "base" in js["groups"]
    assert "api" in js["groups"]


def test_to_json_schema_retry():
    schemas = load_schemas([FIXTURES / "module_a.toml"])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)

    api_key = [f for f in js["fields"] if f["key"] == "OPENAI_API_KEY"][0]
    assert api_key["retry_on_no"] == 2
    assert "Really skip" in api_key["retry_prompt"]


def test_to_json_schema_triggered_by():
    schemas = load_schemas([FIXTURES / "module_a.toml"])
    composed = compose(schemas)
    js = WebRunner.to_json_schema(composed)

    api_key = [f for f in js["fields"] if f["key"] == "OPENAI_API_KEY"][0]
    assert "module_a" in api_key["triggered_by"]


def test_validate_valid_data():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)

    data = {"STACK_NAME": "test", "NETWORK": "host"}
    validated, errors = WebRunner.validate(composed, data)
    assert errors == []
    assert validated["STACK_NAME"] == "test"


def test_validate_missing_required():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)

    data = {"STACK_NAME": "", "NETWORK": "host"}
    _, errors = WebRunner.validate(composed, data)
    assert any("STACK_NAME" in e for e in errors)


def test_validate_invalid_choice():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)

    data = {"STACK_NAME": "test", "NETWORK": "invalid"}
    _, errors = WebRunner.validate(composed, data)
    assert any("NETWORK" in e for e in errors)


def test_validate_skips_conditional():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)

    # NETWORK=host → BRIDGE_NAME condition not met → no error even if missing
    data = {"STACK_NAME": "test", "NETWORK": "host"}
    _, errors = WebRunner.validate(composed, data)
    assert errors == []


def test_validate_conditional_when_met():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)

    # NETWORK=bridge → BRIDGE_NAME is visible, has a default, so valid
    data = {"STACK_NAME": "test", "NETWORK": "bridge"}
    validated, errors = WebRunner.validate(composed, data)
    assert errors == []
    assert validated["BRIDGE_NAME"] == "my-bridge"  # default
