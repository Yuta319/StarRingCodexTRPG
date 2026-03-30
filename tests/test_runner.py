from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.assets import load_canonical_assets
from star_ring_codex_trpg.errors import AssetLoadError, SchemaValidationError, WorldStateError
from star_ring_codex_trpg.runner import build_bundle


class RunnerTests(unittest.TestCase):
    def test_generated_seed_bundle_validates(self) -> None:
        bundle = build_bundle(seed=1729, seasons=10)
        self.assertEqual(bundle["seed"], 1729)
        self.assertTrue(bundle["scene_packet"]["linkedNodeIds"])
        self.assertEqual(bundle["validation"]["scene_packet"], [])
        self.assertEqual(bundle["validation"]["shell_snapshot"], [])
        self.assertEqual(bundle["validation"]["ui_event"], [])

    def test_existing_world_json_bundle_validates(self) -> None:
        world_json = Path(".sources/handoff/PBW_Codex_Handoff_Pack_v1/pbw_generated_world_seed1729_v9_mythic_integration.json")
        bundle = build_bundle(world_json=world_json)
        self.assertEqual(bundle["seed"], 1729)
        self.assertEqual(bundle["validation"]["scene_packet"], [])
        self.assertEqual(bundle["validation"]["shell_snapshot"], [])
        self.assertEqual(bundle["validation"]["ui_event"], [])

    def test_same_seed_is_reproducible(self) -> None:
        left = build_bundle(seed=1729, seasons=10)
        right = build_bundle(seed=1729, seasons=10)
        self.assertEqual(left["shell_snapshot"]["worldSpine"], right["shell_snapshot"]["worldSpine"])
        self.assertEqual(left["shell_snapshot"]["contextRail"]["activeNode"], right["shell_snapshot"]["contextRail"]["activeNode"])
        self.assertEqual(left["scene_output"]["player_facing"]["scene_title"], right["scene_output"]["player_facing"]["scene_title"])
        self.assertEqual(
            [choice["id"] for choice in left["scene_output"]["player_facing"]["choices"]],
            [choice["id"] for choice in right["scene_output"]["player_facing"]["choices"]],
        )

    def test_invalid_world_json_returns_readable_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_world = Path(temp_dir) / "invalid_world.json"
            invalid_world.write_text("{}", encoding="utf-8")
            with self.assertRaises(WorldStateError) as ctx:
                build_bundle(world_json=invalid_world)
        self.assertIn("Invalid world JSON", str(ctx.exception))
        self.assertIn("resolved_world", str(ctx.exception))

    def test_missing_asset_returns_readable_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_root = Path(temp_dir)
            with self.assertRaises(AssetLoadError) as ctx:
                load_canonical_assets(canonical_root=empty_root, ui_contracts_root=empty_root / "pbw_ui_contracts_v1")
        self.assertIn("Required asset is missing", str(ctx.exception))
        self.assertIn("style engine", str(ctx.exception))

    def test_schema_mismatch_returns_readable_error(self) -> None:
        assets = load_canonical_assets()
        bad_assets = replace(
            assets,
            scene_packet_schema={
                "type": "object",
                "required": ["sceneId", "nonexistentField"],
                "properties": {"sceneId": {"type": "string"}, "nonexistentField": {"type": "string"}},
                "additionalProperties": True,
            },
        )
        with self.assertRaises(SchemaValidationError) as ctx:
            build_bundle(seed=1729, seasons=10, assets=bad_assets)
        self.assertIn("Schema validation failed", str(ctx.exception))
        self.assertIn("scene_packet", str(ctx.exception))
        self.assertIn("nonexistentField", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
