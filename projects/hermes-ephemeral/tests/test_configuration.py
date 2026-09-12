from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

from hermes_ephemeral.configuration import (
    _atomic_write,
    build_configuration,
    paths_from_environment,
)
from hermes_ephemeral.environment import ConfigurationError


class FakeResponse:
    def read(self, _limit: int) -> bytes:
        return json.dumps({"data": [{"id": "luna"}, {"id": "spark"}]}).encode()

    def close(self) -> None:
        pass


def opener(_request: Any, *, timeout: float) -> FakeResponse:
    del timeout
    return FakeResponse()


class ModelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = json.dumps({"data": [{"id": "luna"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args: Any) -> None:
        pass


class ConfigurationTests(unittest.TestCase):
    def test_build_replaces_runtime_sections_and_keeps_only_secret_references(self) -> None:
        result = build_configuration(
            {
                "OPENAI_V1_PROVIDER": "LiteLLM",
                "OPENAI_V1_URL": "http://host.containers.internal",
                "OPENAI_V1_PORT": "4000",
                "OPENAI_V1_KEY": "provider-secret",
                "HERMES_MODEL": "spark",
                "MCP_SERVER_NAME": "calendar",
                "MCP_SERVER_URL": "http://calendar:48005/mcp",
                "MCP_SERVER_BEARER": "mcp-secret",
            },
            template={"model": {"old": True}, "custom": {"kept": True}},
            opener=opener,
        )
        self.assertEqual(result.full_model, "litellm/spark")
        self.assertEqual(result.config["model"]["default"], "spark")
        self.assertTrue(result.config["custom"]["kept"])
        serialized = yaml.safe_dump(result.config)
        self.assertIn("key_env: OPENAI_V1_KEY", serialized)
        self.assertIn("${MCP_SERVER_BEARER}", serialized)
        self.assertNotIn("provider-secret", serialized)
        self.assertNotIn("mcp-secret", serialized)

    def test_template_with_a_resolved_secret_is_refused(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "secret"):
            build_configuration(
                {
                    "OPENAI_V1_URL": "https://models.example",
                    "OPENAI_V1_KEY": "do-not-write-this",
                    "HERMES_MODEL": "luna",
                },
                template={"unsafe": "do-not-write-this"},
                opener=opener,
            )

    def test_paths_follow_injected_home_and_are_not_image_specific(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = paths_from_environment({"HOME": str(root), "PATH": ""})
            self.assertEqual(paths.home, root / ".hermes")
            self.assertEqual(paths.config, root / ".hermes" / "config.yaml")
            self.assertIsNone(paths.template)

    def test_paths_reject_relative_process_home(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "HOME must be an absolute"):
            paths_from_environment({"HOME": "relative", "PATH": ""})

    def test_atomic_write_sets_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw) / "state" / "config.yaml"
            _atomic_write(destination, {"model": {"default": "luna"}})
            self.assertEqual(oct(destination.stat().st_mode & 0o777), "0o600")
            self.assertEqual(oct(destination.parent.stat().st_mode & 0o777), "0o700")
            self.assertEqual(yaml.safe_load(destination.read_text())["model"]["default"], "luna")
            self.assertFalse(any(destination.parent.glob(".config.yaml.*")))

    def test_atomic_write_preserves_existing_parent_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw) / "existing"
            parent.mkdir(mode=0o750)
            destination = parent / "config.yaml"
            _atomic_write(destination, {"model": {"default": "luna"}})
            self.assertEqual(oct(parent.stat().st_mode & 0o777), "0o750")

    def test_installed_launcher_rebuilds_config_end_to_end(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        launcher = repository / "image/runtime/usr/local/bin/hermes-ephemeral"
        server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as raw:
                environ = dict(os.environ)
                environ.update(
                    {
                        "HOME": raw,
                        "HERMES_BIN": "missing-hermes-for-test",
                        "HERMES_MODEL": "luna",
                        "OPENAI_V1_URL": f"http://127.0.0.1:{server.server_port}",
                        "OPENAI_V1_KEY": "launcher-secret",
                    }
                )
                result = subprocess.run(
                    [str(launcher), "configure"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=environ,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                config = Path(raw) / ".hermes" / "config.yaml"
                serialized = config.read_text(encoding="utf-8")
                self.assertIn("default: luna", serialized)
                self.assertNotIn("launcher-secret", serialized)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
