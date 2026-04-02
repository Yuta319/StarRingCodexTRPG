from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.custom_gpt_bundle_support import (
    build_custom_gpt_editor_paste_pack,
    export_custom_gpt_publish_packet,
    export_custom_gpt_editor_field_fragments,
    validate_custom_gpt_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CustomGptBundleSupportTests(unittest.TestCase):
    def test_validate_actual_bundle_is_ok(self) -> None:
        bundle_root = PROJECT_ROOT / ".tmp_custom_gpt_actions_bundle" / "custom_gpt_actions_bundle_v1"
        report = validate_custom_gpt_bundle(bundle_root)
        self.assertTrue(report.ok, msg=f"errors: {report.errors}")
        self.assertIn("finalizeCharacter", report.operations_found)

    def test_export_actual_bundle_builds_paste_ready_pack(self) -> None:
        bundle_root = PROJECT_ROOT / ".tmp_custom_gpt_actions_bundle" / "custom_gpt_actions_bundle_v1"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "paste_pack.md"
            pack = build_custom_gpt_editor_paste_pack(bundle_root, output_path=output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("## Instructions", pack.markdown)
            self.assertIn("guidance.openingPackage", pack.markdown)
            self.assertIn("finalizeCharacter", pack.markdown)
            self.assertGreaterEqual(pack.starters_count, 6)

    def test_export_actual_bundle_builds_field_fragments(self) -> None:
        bundle_root = PROJECT_ROOT / ".tmp_custom_gpt_actions_bundle" / "custom_gpt_actions_bundle_v1"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "fragments"
            fragments = export_custom_gpt_editor_field_fragments(bundle_root, output_dir=output_dir)
            self.assertTrue(Path(fragments.files["instructions"]).exists())
            self.assertTrue(Path(fragments.files["conversation_starters"]).exists())
            self.assertIn("name", fragments.files)
            instructions = Path(fragments.files["instructions"]).read_text(encoding="utf-8")
            self.assertIn("guidance.openingPackage", instructions)

    def test_export_publish_packet_builds_self_contained_folder(self) -> None:
        bundle_root = PROJECT_ROOT / ".tmp_custom_gpt_actions_bundle" / "custom_gpt_actions_bundle_v1"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "publish_packet"
            packet = export_custom_gpt_publish_packet(bundle_root, output_dir=output_dir, include_live_smoke=False)
            self.assertTrue(Path(packet.files["summary"]).exists())
            self.assertTrue(Path(packet.files["paste_pack"]).exists())
            self.assertTrue(Path(packet.files["openapi"]).exists())
            self.assertTrue(Path(packet.files["handoff"]).exists())
            summary = Path(packet.files["summary"]).read_text(encoding="utf-8")
            self.assertIn("GPT editor", summary)
            self.assertIsNone(packet.smoke_ok)

    def test_validate_bundle_reports_missing_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "01_custom_gpt_system_prompt_v1.md").write_text(
                "guidance.openingPackage\nfinalizeCharacter\nguidance.characterGenesis.constraints\n",
                encoding="utf-8",
            )
            (root / "02_custom_gpt_conversation_starters_v1.md").write_text(
                "\n".join(
                    [
                        "- 転生したい",
                        "- 自由行動を試したい",
                        "- 続きから再開したい",
                        "- 現在の状況を知りたい",
                        "- 恩恵を決めたい",
                        "- 保存したい",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "03_custom_gpt_builder_fields_v1.json").write_text(
                """
                {
                  "description": "desc",
                  "instructions_file": "01_custom_gpt_system_prompt_v1.md",
                  "conversation_starters_file": "02_custom_gpt_conversation_starters_v1.md",
                  "actions_openapi_file": "04_openapi_pbw_actions_v1.yaml",
                  "builder_profile_website": "https://example.com",
                  "privacy_policy_url_candidate": "https://example.com/privacy"
                }
                """,
                encoding="utf-8",
            )
            (root / "04_openapi_pbw_actions_v1.yaml").write_text(
                """
openapi: 3.1.0
servers:
  - url: https://starringcodextrpg.onrender.com
paths:
  /api/gpt-read-model:
    get:
      operationId: getGptReadModel
  /api/gpt/play:
    post:
      operationId: playChoice
  /api/gpt/free-action:
    post:
      operationId: playFreeAction
  /api/save-session:
    post:
      operationId: saveSession
  /api/gpt/load-session:
    post:
      operationId: loadSession
  /api/gpt/next-session:
    post:
      operationId: nextSession
                """.strip(),
                encoding="utf-8",
            )
            (root / "08_gpt_editor_final_input_pack_v1.md").write_text(
                """
# GPT Editor Final Input Pack v1

## 2. Description
```text
desc
```

## 5. Actions
```text
https://starringcodextrpg.onrender.com
```

finalizeCharacter guidance.openingPackage
                """.strip(),
                encoding="utf-8",
            )

            report = validate_custom_gpt_bundle(root)
            self.assertFalse(report.ok)
            self.assertTrue(any("missing OpenAPI operations" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
