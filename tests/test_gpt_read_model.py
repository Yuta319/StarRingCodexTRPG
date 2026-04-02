from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.assets import load_canonical_assets
from star_ring_codex_trpg.gpt_read_model import build_gpt_read_model, build_gpt_read_model_from_bundle
from star_ring_codex_trpg.playable_loop import play_free_action
from star_ring_codex_trpg.runner import build_bundle, build_bundle_from_world_state


class GptReadModelTests(unittest.TestCase):
    def test_build_gpt_read_model_contains_required_surfaces(self) -> None:
        read_model = build_gpt_read_model(seed=1729, seasons=10, archetype="balanced")
        self.assertEqual(read_model["version"], "gpt_read_model_v1")
        self.assertEqual(read_model["contracts"]["truthMutation"], "backend_only")
        self.assertFalse(read_model["contracts"]["rawFreeTextPersisted"])
        self.assertIn("scene", read_model)
        self.assertIn("guidance", read_model)
        self.assertIn("world", read_model)
        self.assertIn("cast", read_model)
        self.assertIn("memory", read_model)
        self.assertIn("freeActionSurface", read_model)
        self.assertIn("characterGenesis", read_model["guidance"])
        self.assertIn("newGameGenesis", read_model["guidance"])
        self.assertIn("openingPackage", read_model["guidance"])
        self.assertTrue(read_model["scene"]["openingLines"])
        self.assertTrue(read_model["guidance"]["storyGuide"]["now"])
        self.assertTrue(read_model["world"]["currentEvent"]["summaryText"])
        self.assertTrue(read_model["cast"])
        self.assertTrue(read_model["cast"][0]["summaryText"])
        self.assertTrue(read_model["cast"][0]["attitudeText"])
        self.assertIn("gptTasks", read_model["guidance"]["characterGenesis"])
        self.assertIn("constraints", read_model["guidance"]["characterGenesis"])
        self.assertTrue(read_model["guidance"]["newGameGenesis"]["openingSummary"])
        self.assertTrue(read_model["guidance"]["newGameGenesis"]["phaseEventLabels"])
        self.assertTrue(read_model["guidance"]["openingPackage"]["promptHint"])
        self.assertIn("outputRules", read_model["guidance"]["openingPackage"])

    def test_gpt_read_model_does_not_store_raw_free_action_text(self) -> None:
        raw_text = "夜中に宿の裏から入り、裏帳面を盗み出す"
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "free_action_world.json"
            current_world = build_bundle(seed=1729, seasons=10)["world_state"]
            world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
            result = play_free_action(raw_text, seed=None, world_json=world_json)
            bundle = build_bundle_from_world_state(result["after"]["bundle"]["world_state"], load_canonical_assets())

        read_model = build_gpt_read_model_from_bundle(bundle, request_seed=None, request_world_json=None)
        serialized = json.dumps(read_model, ensure_ascii=False)
        self.assertNotIn(raw_text, serialized)
        self.assertTrue(read_model["freeActionSurface"]["latest"]["summary"])


if __name__ == "__main__":
    unittest.main()
