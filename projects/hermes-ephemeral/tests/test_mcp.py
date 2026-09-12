from __future__ import annotations

import json
import unittest

from hermes_ephemeral.environment import ConfigurationError
from hermes_ephemeral.mcp import discover_mcp_servers, mcp_servers_config


class McpTests(unittest.TestCase):
    def test_suffixless_and_suffix02_groups_are_projected_globally(self) -> None:
        environ = {
            "MCP_SERVER_NAME": "calendar",
            "MCP_SERVER_URL": "http://nextcloud-ssh1:48005/mcp",
            "MCP_SERVER_BEARER": "first-secret",
            "MCP_SERVER_URL_02": "http://kachelmann-ssh1:48006/mcp",
        }
        servers = discover_mcp_servers(environ)
        self.assertEqual([server.name for server in servers], ["calendar", "kachelmann-ssh1"])
        config = mcp_servers_config(environ)
        serialized = json.dumps(config)
        self.assertIn("${MCP_SERVER_BEARER}", serialized)
        self.assertNotIn("first-secret", serialized)
        self.assertTrue(config["calendar"]["supports_parallel_tool_calls"])

    def test_duplicate_names_and_embedded_credentials_are_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "duplicate"):
            discover_mcp_servers(
                {
                    "MCP_SERVER_NAME": "same",
                    "MCP_SERVER_URL": "http://one.example/mcp",
                    "MCP_SERVER_NAME_02": "SAME",
                    "MCP_SERVER_URL_02": "http://two.example/mcp",
                }
            )
        with self.assertRaisesRegex(ConfigurationError, "credentials"):
            discover_mcp_servers(
                {"MCP_SERVER_URL": "http://user:secret@example.test/mcp"}
            )


if __name__ == "__main__":
    unittest.main()

