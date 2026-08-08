"""prettyconfi — Schema-driven configuration wizard for CLI and web."""

from prettyconfi.schema import FieldDef, SchemaFile, WhenCondition, load_schema, load_schemas
from prettyconfi.composer import ComposedSchema, compose
from prettyconfi.runner import Runner, StopSave, _BACK, _SAVE
from prettyconfi.cli import CLIRunner
from prettyconfi.web import WebRunner
from prettyconfi.output import to_env, to_toml, to_json, to_dict, from_toml, from_env
from prettyconfi.types import FieldType, Scope

__version__ = "0.1.0"

__all__ = [
    # Schema
    "FieldDef",
    "SchemaFile",
    "WhenCondition",
    "load_schema",
    "load_schemas",
    # Composer
    "ComposedSchema",
    "compose",
    # Runners
    "Runner",
    "StopSave",
    "_BACK",
    "_SAVE",
    "CLIRunner",
    "WebRunner",
    # Output
    "to_env",
    "to_toml",
    "to_json",
    "to_dict",
    "from_toml",
    "from_env",
    # Types
    "FieldType",
    "Scope",
]
