"""Type definitions and enums for prettyconfi."""

from __future__ import annotations

from enum import Enum


class FieldType(str, Enum):
    """Supported field types."""
    STR = "str"
    INT = "int"
    BOOL = "bool"
    CHOICE = "choice"
    PORT = "port"


class Scope(str, Enum):
    """Field scope — determines merge priority and sort order."""
    GLOBAL = "global"
    MODULE = "module"


# Valid port range
PORT_MIN = 1
PORT_MAX = 65535
