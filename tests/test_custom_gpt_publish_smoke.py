from __future__ import annotations

from pathlib import Path
import unittest

from star_ring_codex_trpg.custom_gpt_publish_smoke import load_custom_gpt_publish_targets


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CustomGptPublishSmokeTests(unittest.TestCase):
    def test_load_publish_targets_from_actual_bundle(self) -> None:
        bundle_root = PROJECT_ROOT / ".tmp_custom_gpt_actions_bundle" / "custom_gpt_actions_bundle_v1"
        targets = load_custom_gpt_publish_targets(bundle_root)
        self.assertTrue(targets.builder_website.startswith("https://"))
        self.assertTrue(targets.privacy_policy_url.startswith("https://"))
        self.assertIn("starringcodextrpg.onrender.com", targets.api_server_url)


if __name__ == "__main__":
    unittest.main()
