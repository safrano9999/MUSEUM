"""Tests for schema composition and merging."""

from pathlib import Path
from prettyconfi.schema import load_schemas
from prettyconfi.composer import compose

FIXTURES = Path(__file__).parent / "fixtures"


def test_compose_deduplicates_keys():
    schemas = load_schemas([
        FIXTURES / "module_a.toml",
        FIXTURES / "module_b.toml",
    ])
    composed = compose(schemas)
    # OPENAI_API_KEY appears in both — should be deduplicated
    keys = [f.key for f in composed.fields]
    assert keys.count("OPENAI_API_KEY") == 1


def test_compose_merges_triggered_by():
    schemas = load_schemas([
        FIXTURES / "module_a.toml",
        FIXTURES / "module_b.toml",
    ])
    composed = compose(schemas)
    api_key = composed.field_map["OPENAI_API_KEY"]
    # module_a defines triggered_by=["module_a", "module_b"]
    # module_b defines triggered_by=["module_b"]
    # merged should have all unique values
    assert "module_a" in api_key.triggered_by
    assert "module_b" in api_key.triggered_by


def test_compose_first_definition_wins():
    schemas = load_schemas([
        FIXTURES / "module_a.toml",
        FIXTURES / "module_b.toml",
    ])
    composed = compose(schemas)
    api_key = composed.field_map["OPENAI_API_KEY"]
    # First definition (module_a) should win for label
    assert api_key.label == "OpenAI API Key"  # not "OpenAI API Key (from B)"


def test_compose_sorts_global_first():
    schemas = load_schemas([
        FIXTURES / "base.toml",
        FIXTURES / "module_a.toml",
        FIXTURES / "module_b.toml",
    ])
    composed = compose(schemas)
    # Global fields should come before module fields
    scopes = [f.scope for f in composed.fields]
    global_indices = [i for i, s in enumerate(scopes) if s == "global"]
    module_indices = [i for i, s in enumerate(scopes) if s == "module"]
    if global_indices and module_indices:
        assert max(global_indices) < min(module_indices)


def test_compose_tracks_sources():
    schemas = load_schemas([
        FIXTURES / "base.toml",
        FIXTURES / "module_a.toml",
    ])
    composed = compose(schemas)
    assert composed.sources["STACK_NAME"] == "base"
    assert composed.sources["APP_PORT"] == "module_a"


def test_compose_keys_method():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)
    keys = composed.keys()
    assert "STACK_NAME" in keys
    assert "NETWORK" in keys
    assert "BRIDGE_NAME" in keys


def test_compose_empty():
    composed = compose([])
    assert composed.fields == []
    assert composed.field_map == {}
    assert composed.sources == {}


def test_compose_preserves_order_within_schema():
    schemas = load_schemas([FIXTURES / "base.toml"])
    composed = compose(schemas)
    keys = composed.keys()
    assert keys.index("STACK_NAME") < keys.index("NETWORK")
    assert keys.index("NETWORK") < keys.index("BRIDGE_NAME")
