"""Command line entry point for hermes-ephemeral."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from .configuration import rebuild_configuration
from .environment import ConfigurationError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="hermes-ephemeral",
        description="Rebuild Hermes configuration from the injected environment.",
    )
    result.add_argument("command", choices=("configure",))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser().parse_args(argv)
    try:
        result = rebuild_configuration(os.environ)
    except ConfigurationError as error:
        raise SystemExit(f"Hermes configuration error: {error}") from error

    print("Hermes config rebuilt atomically")
    print(f"Hermes model: {result.full_model}")
    print(f"Hermes OpenAI-v1 providers configured: {result.provider_count}")
    print(f"Hermes MCP servers configured: {result.mcp_server_count}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
    return 0

