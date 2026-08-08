#!/usr/bin/env python3
"""CALENDAR init.

Adds calendar entries to .env. The first entry uses CALENDAR_*, then
CALENDAR_2_*, CALENDAR_3_*, and so on.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parent


def env_path() -> Path:
    raw = os.environ.get("CALENDAR_ENV") or os.environ.get("CALENDAR_CALENV")
    path = Path(raw) if raw else ROOT_DIR / ".env"
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


def configured_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def next_calendar_prefix(lines: Iterable[str]) -> str:
    seen: set[int] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip().upper()
        if key == "CALENDAR_URL":
            seen.add(1)
        elif key.startswith("CALENDAR_"):
            num, _, field = key[len("CALENDAR_") :].partition("_")
            if num.isdigit() and field == "URL":
                seen.add(int(num))
    if not seen:
        return "CALENDAR"
    return f"CALENDAR_{max(seen) + 1}"


def has_calendar(lines: Iterable[str]) -> bool:
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().upper()
        if value.strip() and (key == "CALENDAR_URL" or (key.startswith("CALENDAR_") and key.endswith("_URL"))):
            return True
    return False


def ask(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{question}{suffix}: ").strip()
    return value or default


def ask_choice(question: str, options: tuple[str, ...], default: str) -> str:
    pretty = "/".join(options)
    while True:
        value = ask(f"{question} ({pretty})", default).lower()
        if value in options:
            return value


def add_calendar(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = configured_lines(path)
    prefix = next_calendar_prefix(lines)

    url = ask("Calendar URL")
    if not url:
        raise SystemExit("Calendar URL required.")
    user = ask("User")
    password = getpass.getpass("Password: ").strip() if sys.stdin.isatty() else input("Password: ").strip()
    block = ["", f"# calendar {prefix}", f"{prefix}_URL={url}"]
    if user:
        block.append(f"{prefix}_USER={user}")
    if password:
        block.append(f"{prefix}_PASSWORD={password}")

    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(block).rstrip() + "\n")
    path.chmod(0o600)
    print(f"Added calendar {prefix} to {path}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize CALENDAR entries.")
    parser.add_argument("--new", action="store_true", help="add the next calendar")
    parser.add_argument("--skip", action="store_true", help="do nothing")
    args = parser.parse_args()

    if args.skip:
        print("CALENDAR init skipped.")
        return 0

    path = env_path()
    if not args.new:
        if not sys.stdin.isatty():
            print("CALENDAR init skipped: no interactive terminal.")
            return 0
        default_mode = "skip" if has_calendar(configured_lines(path)) else "new"
        mode = ask_choice("CALENDAR init", ("skip", "new"), default_mode)
        if mode == "skip":
            print("CALENDAR init skipped.")
            return 0

    add_calendar(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
