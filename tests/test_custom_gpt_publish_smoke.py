from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from star_ring_codex_trpg.custom_gpt_publish_smoke import (
    PublishTargetSet,
    load_custom_gpt_publish_targets,
    run_custom_gpt_publish_smoke,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CustomGptPublishSmokeTests(unittest.TestCase):
    def test_load_publish_targets_from_actual_bundle(self) -> None:
        bundle_root = PROJECT_ROOT / ".tmp_custom_gpt_actions_bundle" / "custom_gpt_actions_bundle_v1"
        targets = load_custom_gpt_publish_targets(bundle_root)
        self.assertTrue(targets.builder_website.startswith("https://"))
        self.assertTrue(targets.privacy_policy_url.startswith("https://"))
        self.assertIn("starringcodextrpg.onrender.com", targets.api_server_url)

    def test_smoke_retries_transient_finalize_failure(self) -> None:
        targets = PublishTargetSet(
            bundle_root="bundle",
            builder_website="https://example.com/builder",
            privacy_policy_url="https://example.com/privacy",
            api_server_url="https://example.com",
        )
        finalize_calls = {"count": 0}

        def fake_http_request(url: str, *, method: str = "GET", body: dict | None = None, timeout_seconds: float = 20.0):
            if url == targets.builder_website:
                return 200, "<html>builder</html>", "<html>builder</html>"
            if url == targets.privacy_policy_url:
                return 200, "<html>privacy</html>", "<html>privacy</html>"
            if url == "https://example.com/health":
                return 200, '{"ok": true}', {"ok": True}
            if url == "https://example.com/api/front/snapshot?seed=1729":
                return 200, '{"playSource": {"world_json": "world-1"}}', {"playSource": {"world_json": "world-1"}}
            if url == "https://example.com/api/gpt-read-model?seed=1729":
                return 200, '{"readModel": {"guidance": {"openingPackage": {"promptHint": "hint"}}}}', {
                    "readModel": {"guidance": {"openingPackage": {"promptHint": "hint"}}}
                }
            if url == "https://example.com/api/gpt/finalize-character":
                finalize_calls["count"] += 1
                if finalize_calls["count"] == 1:
                    return 502, "bad gateway", "bad gateway"
                return 200, '{"readModel": {"guidance": {"openingPackage": {"promptHint": "hint-2"}}}}', {
                    "readModel": {"guidance": {"openingPackage": {"promptHint": "hint-2"}}}
                }
            raise AssertionError(f"unexpected url: {url}")

        with (
            patch("star_ring_codex_trpg.custom_gpt_publish_smoke.load_custom_gpt_publish_targets", return_value=targets),
            patch("star_ring_codex_trpg.custom_gpt_publish_smoke._http_request", side_effect=fake_http_request),
        ):
            report = run_custom_gpt_publish_smoke(Path("."), retries=1, retry_delay_seconds=0.0)

        self.assertTrue(report.ok, msg=report.errors)
        self.assertEqual(finalize_calls["count"], 2)
        finalize_check = next(check for check in report.checks if check["name"] == "gpt_finalize_character")
        self.assertTrue(finalize_check["ok"])

    def test_smoke_fails_when_retry_budget_is_exhausted(self) -> None:
        targets = PublishTargetSet(
            bundle_root="bundle",
            builder_website="https://example.com/builder",
            privacy_policy_url="https://example.com/privacy",
            api_server_url="https://example.com",
        )

        def fake_http_request(url: str, *, method: str = "GET", body: dict | None = None, timeout_seconds: float = 20.0):
            if url == targets.builder_website:
                return 200, "<html>builder</html>", "<html>builder</html>"
            if url == targets.privacy_policy_url:
                return 200, "<html>privacy</html>", "<html>privacy</html>"
            if url == "https://example.com/health":
                return 200, '{"ok": true}', {"ok": True}
            if url == "https://example.com/api/front/snapshot?seed=1729":
                return 200, '{"playSource": {"world_json": "world-1"}}', {"playSource": {"world_json": "world-1"}}
            if url == "https://example.com/api/gpt-read-model?seed=1729":
                return 200, '{"readModel": {"guidance": {"openingPackage": {"promptHint": "hint"}}}}', {
                    "readModel": {"guidance": {"openingPackage": {"promptHint": "hint"}}}
                }
            if url == "https://example.com/api/gpt/finalize-character":
                return 502, "bad gateway", "bad gateway"
            raise AssertionError(f"unexpected url: {url}")

        with (
            patch("star_ring_codex_trpg.custom_gpt_publish_smoke.load_custom_gpt_publish_targets", return_value=targets),
            patch("star_ring_codex_trpg.custom_gpt_publish_smoke._http_request", side_effect=fake_http_request),
        ):
            report = run_custom_gpt_publish_smoke(Path("."), retries=1, retry_delay_seconds=0.0)

        self.assertFalse(report.ok)
        finalize_check = next(check for check in report.checks if check["name"] == "gpt_finalize_character")
        self.assertFalse(finalize_check["ok"])
        self.assertTrue(any("gpt_finalize_character failed" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
