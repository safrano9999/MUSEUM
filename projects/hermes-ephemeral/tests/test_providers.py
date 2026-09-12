from __future__ import annotations

import json
import unittest
from typing import Any

from hermes_ephemeral.environment import ConfigurationError
from hermes_ephemeral.providers import (
    discover_openai_v1_providers,
    normalize_openai_v1_url,
    select_default,
)


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.closed = False

    def read(self, _limit: int) -> bytes:
        return json.dumps(self.payload).encode()

    def close(self) -> None:
        self.closed = True


class ProviderTests(unittest.TestCase):
    def test_url_normalization_is_generic(self) -> None:
        self.assertEqual(
            normalize_openai_v1_url("host.containers.internal", "4000"),
            "http://host.containers.internal:4000/v1",
        )
        self.assertEqual(
            normalize_openai_v1_url("https://models.example/v1", "443"),
            "https://models.example:443/v1",
        )
        with self.assertRaisesRegex(ConfigurationError, "credentials"):
            normalize_openai_v1_url("https://user:secret@example.test")

    def test_repeated_providers_discover_models_without_persisting_keys(self) -> None:
        requests: list[tuple[str, str | None, str | None]] = []

        def opener(request: Any, *, timeout: float) -> FakeResponse:
            self.assertEqual(timeout, 2.5)
            requests.append(
                (
                    request.full_url,
                    request.get_header("Authorization"),
                    request.get_header("User-agent"),
                )
            )
            return FakeResponse({"data": [{"id": "luna"}, {"id": "spark"}]})

        providers, warnings = discover_openai_v1_providers(
            {
                "OPENAI_V1_PROVIDER": "LiteLLM",
                "OPENAI_V1_URL": "http://host.containers.internal",
                "OPENAI_V1_PORT": "4000",
                "OPENAI_V1_KEY": "first-secret",
                "OPENAI_V1_PROVIDER_2": "Secondary",
                "OPENAI_V1_URL_2": "https://second.example/v1",
                "OPENAI_V1_KEY_2": "second-secret",
            },
            opener=opener,
            timeout=2.5,
        )
        self.assertEqual(warnings, ())
        self.assertEqual([item.provider_id for item in providers], ["litellm", "secondary"])
        self.assertEqual(providers[0].key_env, "OPENAI_V1_KEY")
        self.assertEqual(providers[1].key_env, "OPENAI_V1_KEY_2")
        serialized = json.dumps([item.hermes_config() for item in providers])
        self.assertNotIn("first-secret", serialized)
        self.assertNotIn("second-secret", serialized)
        self.assertEqual(requests[0][2], "hermes-ephemeral/1.0")

    def test_configured_models_are_used_when_discovery_is_unavailable(self) -> None:
        def unavailable(_request: Any, *, timeout: float) -> FakeResponse:
            del timeout
            raise TimeoutError

        providers, warnings = discover_openai_v1_providers(
            {
                "OPENAI_V1_URL": "https://offline.example",
                "OPENAI_V1_KEY": "secret",
                "OPENAI_V1_MODELS": "luna,spark",
            },
            opener=unavailable,
        )
        self.assertEqual(providers[0].models, ("luna", "spark"))
        self.assertEqual(len(warnings), 1)

    def test_discovery_headers_cannot_replace_authorization(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "Authorization"):
            discover_openai_v1_providers(
                {
                    "OPENAI_V1_URL": "https://models.example",
                    "OPENAI_V1_KEY": "secret",
                    "OPENAI_V1_DISCOVERY_HEADERS": '{"Authorization":"unsafe"}',
                },
                opener=lambda *_args, **_kwargs: self.fail("must not request"),
            )

    def test_default_can_select_provider_qualified_model(self) -> None:
        def opener(_request: Any, *, timeout: float) -> FakeResponse:
            del timeout
            return FakeResponse({"data": [{"id": "luna"}]})

        providers, _ = discover_openai_v1_providers(
            {
                "OPENAI_V1_PROVIDER": "LiteLLM",
                "OPENAI_V1_URL": "https://models.example",
                "OPENAI_V1_KEY": "secret",
            },
            opener=opener,
        )
        selected = select_default(providers, "litellm/spark")
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected[0], "litellm/spark")
        self.assertEqual(selected[1][0].models, ("spark", "luna"))


if __name__ == "__main__":
    unittest.main()
