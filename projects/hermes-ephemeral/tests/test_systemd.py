from __future__ import annotations

import unittest
from pathlib import Path


class SystemdUnitTests(unittest.TestCase):
    def test_oneshot_has_the_required_and_optional_ordering(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        unit = (
            repository
            / "image/runtime/etc/systemd/system/hermes-ephemeral.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", unit)
        self.assertIn("Requires=persistainer.service", unit)
        self.assertIn(
            "Wants=network-online.target fedora44-ai-init-hooks.service "
            "tailscale-up.service",
            unit,
        )
        self.assertIn(
            "After=network-online.target persistainer.service "
            "fedora44-ai-init-hooks.service tailscale-up.service",
            unit,
        )
        self.assertIn("Before=hermes.service", unit)
        self.assertNotIn("Environment=HOME=", unit)
        self.assertNotIn("ExecStartPre=", unit)
        self.assertNotIn("sleep", unit.lower())


if __name__ == "__main__":
    unittest.main()
