from __future__ import annotations

import unittest

from hermes_ephemeral.environment import (
    ConfigurationError,
    expand_api_key_aliases,
    openai_group_name,
)


class EnvironmentTests(unittest.TestCase):
    def test_reverse_aliases_are_process_local_and_support_numbered_groups(self) -> None:
        original = {
            "OPENAI_V1_KEY": "first-secret",
            "OPENAI_V1_API_KEY_ALIAS": "LITELLM_API_KEY",
            "OPENAI_V1_KEY_2": "second-secret",
            "OPENAI_V1_API_KEY_ALIAS_2": "SECOND_API_KEY",
        }
        expanded = expand_api_key_aliases(original)
        self.assertEqual(expanded["LITELLM_API_KEY"], "first-secret")
        self.assertEqual(expanded["SECOND_API_KEY"], "second-secret")
        self.assertNotIn("LITELLM_API_KEY", original)

    def test_explicit_alias_value_wins(self) -> None:
        expanded = expand_api_key_aliases(
            {
                "OPENAI_V1_KEY": "shared-secret",
                "OPENAI_V1_API_KEY_ALIAS": "LITELLM_API_KEY",
                "LITELLM_API_KEY": "native-secret",
            }
        )
        self.assertEqual(expanded["LITELLM_API_KEY"], "native-secret")

    def test_alias_shape_is_strict(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "uppercase"):
            expand_api_key_aliases(
                {
                    "OPENAI_V1_KEY": "secret",
                    "OPENAI_V1_API_KEY_ALIAS": "not-an-env-name",
                }
            )

    def test_numbered_group_accepts_padded_or_unpadded_names(self) -> None:
        self.assertEqual(
            openai_group_name({"OPENAI_V1_URL_02": "x"}, "URL", 2),
            "OPENAI_V1_URL_02",
        )
        self.assertEqual(
            openai_group_name({"OPENAI_V1_URL_2": "x"}, "URL", 2),
            "OPENAI_V1_URL_2",
        )


if __name__ == "__main__":
    unittest.main()

