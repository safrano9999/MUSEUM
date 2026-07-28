"""Tests for output — .env, TOML, JSON writers and readers."""

import json
from pathlib import Path

from prettyconfi.output import to_env, to_toml, to_json, to_dict, from_env, from_toml


def test_to_dict():
    result = to_dict({"PORT": 5001, "NAME": "test", "FLAG": True})
    assert result == {"PORT": "5001", "NAME": "test", "FLAG": "True"}


def test_to_env_and_from_env(tmp_path):
    answers = {"APP_PORT": 5001, "APP_NAME": "test", "FLAG": True}
    path = tmp_path / "output.env"
    to_env(answers, path)

    content = path.read_text()
    assert "APP_PORT=5001" in content
    assert "APP_NAME=test" in content

    loaded = from_env(path)
    assert loaded["APP_PORT"] == "5001"
    assert loaded["APP_NAME"] == "test"


def test_to_env_quotes_special_chars(tmp_path):
    answers = {"MSG": 'hello "world"', "PATH": "/usr/bin:/usr/local/bin"}
    path = tmp_path / "output.env"
    to_env(answers, path)

    loaded = from_env(path)
    assert loaded["MSG"] == 'hello "world"'


def test_to_env_skips_comments(tmp_path):
    path = tmp_path / "test.env"
    path.write_text("# comment\nKEY=value\n\n  # another\nKEY2=val2\n")
    loaded = from_env(path)
    assert loaded == {"KEY": "value", "KEY2": "val2"}


def test_to_toml_and_from_toml(tmp_path):
    answers = {"APP_PORT": "5001", "APP_NAME": "test"}
    meta = {"stack": "web-stack", "version": 1}
    path = tmp_path / "config.toml"
    to_toml(answers, path, meta=meta)

    content = path.read_text()
    assert "[meta]" in content
    assert "[env]" in content
    assert 'stack = "web-stack"' in content
    assert 'APP_PORT = "5001"' in content

    loaded = from_toml(path)
    assert loaded["APP_PORT"] == "5001"
    assert loaded["APP_NAME"] == "test"


def test_to_toml_without_meta(tmp_path):
    answers = {"KEY": "value"}
    path = tmp_path / "config.toml"
    to_toml(answers, path)

    content = path.read_text()
    assert "[meta]" not in content
    assert "[env]" in content


def test_to_json(tmp_path):
    answers = {"PORT": 5001, "NAME": "test"}
    meta = {"stack": "my-stack"}
    path = tmp_path / "config.json"
    to_json(answers, path, meta=meta)

    data = json.loads(path.read_text())
    assert data["meta"]["stack"] == "my-stack"
    assert data["env"]["PORT"] == 5001
    assert data["env"]["NAME"] == "test"


def test_to_json_without_meta(tmp_path):
    answers = {"KEY": "val"}
    path = tmp_path / "config.json"
    to_json(answers, path)

    data = json.loads(path.read_text())
    assert "meta" not in data
    assert data["env"]["KEY"] == "val"


def test_from_env_handles_quoted_values(tmp_path):
    path = tmp_path / "test.env"
    path.write_text('KEY1="hello world"\nKEY2=\'single\'\nKEY3=plain\n')
    loaded = from_env(path)
    assert loaded["KEY1"] == "hello world"
    assert loaded["KEY2"] == "single"
    assert loaded["KEY3"] == "plain"


def test_roundtrip_toml(tmp_path):
    original = {"A": "1", "B": "hello", "C": "true"}
    path = tmp_path / "roundtrip.toml"
    to_toml(original, path, meta={"test": True})
    loaded = from_toml(path)
    assert loaded == original
