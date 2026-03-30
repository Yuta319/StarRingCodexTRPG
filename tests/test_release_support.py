from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.release_support import build_release_samples, cleanup_runtime_artifacts


class ReleaseSupportTests(unittest.TestCase):
    def test_build_release_samples_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "samples"
            manifest = build_release_samples(root)
            for key in ("bundle1729", "bundle2048", "sampleSave", "sampleCampaignWorld", "sampleGptReadModel", "manifest"):
                with self.subTest(key=key):
                    self.assertTrue(Path(manifest[key]).exists())

            sample_manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("samples", sample_manifest)
            self.assertIn("sampleGptReadModel", sample_manifest["samples"])

    def test_cleanup_runtime_artifacts_dry_run_respects_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_root = Path(temp_dir) / ".runtime"
            save_root = runtime_root / "session_saves"
            ui_root = runtime_root / "ui_sessions"
            save_root.mkdir(parents=True, exist_ok=True)
            ui_root.mkdir(parents=True, exist_ok=True)
            for index in range(5):
                (save_root / f"save_{index}.json").write_text("{}", encoding="utf-8")
                (ui_root / f"world_{index}.json").write_text("{}", encoding="utf-8")

            report = cleanup_runtime_artifacts(
                runtime_root=runtime_root,
                keep_recent_saves=2,
                keep_recent_ui_sessions=3,
                dry_run=True,
            )

            self.assertEqual(report.removed_saves, 3)
            self.assertEqual(report.removed_ui_sessions, 2)
            self.assertEqual(report.kept_saves, 2)
            self.assertEqual(report.kept_ui_sessions, 3)
            self.assertEqual(len(report.removed_paths), 5)
            self.assertEqual(len(list(save_root.glob("save_*.json"))), 5)
            self.assertEqual(len(list(ui_root.glob("world_*.json"))), 5)


if __name__ == "__main__":
    unittest.main()
