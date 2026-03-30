from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from star_ring_codex_trpg.free_action_adjudicator import adjudicate_free_action, validate_structured_result
from star_ring_codex_trpg.free_action_parser import parse_free_action
from star_ring_codex_trpg.playable_loop import play_choice, play_free_action
from star_ring_codex_trpg.read_only_ui.controller import build_free_action_payload, free_action_request_from_body
from star_ring_codex_trpg.read_only_ui.server import ReadOnlyUiHandler
from star_ring_codex_trpg.runner import build_bundle


class FreeActionTests(unittest.TestCase):
    def _runtime_context(self) -> tuple[dict, dict, object]:
        bundle = build_bundle(seed=1729, include_runtime_context=True)
        return bundle["world_state"], bundle["world_state"]["campaign_state"], bundle["scene_context"]

    def test_campaign_state_contains_vice_taboo_metrics(self) -> None:
        bundle = build_bundle(seed=1729)
        campaign = bundle["world_state"]["campaign_state"]
        self.assertIn("vicePressure", campaign)
        self.assertIn("tabooPressure", campaign)
        self.assertIn("publicInfamy", campaign)
        self.assertIn("hiddenCrimes", campaign)
        self.assertIn("viceTrace", campaign)
        self.assertIn("tabooTrace", campaign)
        self.assertIn("roleSlotSuspicion", campaign)
        self.assertIn("roleSlotDistrust", campaign)
        self.assertIn("roleSlotRetaliation", campaign)

    def test_parse_free_action_produces_structured_intent_without_raw_text(self) -> None:
        world_state, campaign_state, scene_context = self._runtime_context()
        raw_text = "夜中に宿の裏から入り、裏帳面を盗み出す"
        parsed = parse_free_action(raw_text, world_state, campaign_state, scene_context)
        self.assertEqual(parsed["source"]["input_mode"], "free_text")
        self.assertFalse(parsed["source"]["persist_raw_text"])
        self.assertNotEqual(parsed["source"]["player_summary"], raw_text)
        self.assertEqual(parsed["normalized_intent"]["intent_type"], "custom_action")
        self.assertEqual(parsed["normalized_intent"]["action_family"], "theft")
        self.assertTrue(parsed["normalized_intent"]["target_role_slots"])

    def test_parser_handles_synonym_families_consistently(self) -> None:
        world_state, campaign_state, scene_context = self._runtime_context()
        cases = {
            "theft": [
                "夜中に宿の裏から入り、裏帳面を盗み出す",
                "夜更けに裏手から入り、帳面を拝借する",
                "誰にも気づかれず帳面を失敬する",
            ],
            "coercion": [
                "停戦執行官の弱みを突いて従わせる",
                "停戦執行官を揺さぶって譲歩させる",
                "停戦執行官に圧をかけて判断を曲げる",
            ],
            "taboo_ritual": [
                "封印札を剥がして禁譜を鳴らす",
                "結界を破って禁術を試す",
                "魂を縛って封路をこじ開ける",
            ],
        }
        for family, phrases in cases.items():
            for phrase in phrases:
                with self.subTest(family=family, phrase=phrase):
                    parsed = parse_free_action(phrase, world_state, campaign_state, scene_context)
                    self.assertEqual(parsed["normalized_intent"]["action_family"], family)
                    self.assertNotEqual(parsed["source"]["player_summary"], phrase)

    def test_parser_separates_vice_taboo_and_role_targets(self) -> None:
        world_state, campaign_state, scene_context = self._runtime_context()
        bribery = parse_free_action("誓紙検分官に袖の下を渡して見逃しを買う", world_state, campaign_state, scene_context)
        self.assertIn("bribery_corruption", bribery["normalized_intent"]["vice_tags"])
        self.assertIn("slot_oath_scribe", bribery["normalized_intent"]["target_role_slots"])

        smuggling = parse_free_action("渡し守の目を盗んで隠し荷を舟に紛らせる", world_state, campaign_state, scene_context)
        self.assertIn("smuggling", smuggling["normalized_intent"]["vice_tags"])
        self.assertIn("slot_ferrymaster", smuggling["normalized_intent"]["target_role_slots"])

        taboo = parse_free_action("墓を荒らして遺体から護符を剥ぎ取る", world_state, campaign_state, scene_context)
        self.assertIn("corpse_desecration", taboo["normalized_intent"]["taboo_tags"])
        self.assertEqual(taboo["normalized_intent"]["action_family"], "taboo_ritual")

    def test_adjudicator_returns_schema_valid_structured_result(self) -> None:
        world_state, campaign_state, scene_context = self._runtime_context()
        parsed = parse_free_action("夜中に宿の裏から入り、裏帳面を盗み出す", world_state, campaign_state, scene_context)
        result = adjudicate_free_action(parsed, world_state, campaign_state, scene_context)
        validate_structured_result(result)
        self.assertEqual(result["schema_version"], "1.0")
        self.assertFalse(result["recording"]["persist_raw_text"])

    def test_adjudicator_produces_concealed_success_exposed_and_backlash(self) -> None:
        scenarios = [
            (1729, "夜中に宿の裏から入り、裏帳面を拝借する", "concealed_success"),
            (2048, "皆の前で停戦執行官の弱みを突いて従わせる", "exposed"),
            (3141, "封印札を剥がして禁譜を鳴らし、封路をこじ開ける", "backlash"),
        ]
        for seed, text, expected_outcome in scenarios:
            with self.subTest(seed=seed, expected_outcome=expected_outcome):
                bundle = build_bundle(seed=seed, include_runtime_context=True)
                parsed = parse_free_action(text, bundle["world_state"], bundle["world_state"]["campaign_state"], bundle["scene_context"])
                result = adjudicate_free_action(parsed, bundle["world_state"], bundle["world_state"]["campaign_state"], bundle["scene_context"])
                self.assertEqual(result["adjudication"]["outcome"], expected_outcome)

    def test_allowability_changes_outcome_by_current_context(self) -> None:
        text = "渡し守の目を盗んで隠し荷を舟に紛らせる"
        results = {}
        for seed in (1729, 3141):
            bundle = build_bundle(seed=seed, include_runtime_context=True)
            parsed = parse_free_action(text, bundle["world_state"], bundle["world_state"]["campaign_state"], bundle["scene_context"])
            results[seed] = adjudicate_free_action(parsed, bundle["world_state"], bundle["world_state"]["campaign_state"], bundle["scene_context"])

        self.assertIn(results[1729]["adjudication"]["outcome"], {"concealed_success", "partial_success"})
        self.assertIn(results[3141]["adjudication"]["outcome"], {"partial_success", "failure", "exposed"})
        self.assertGreater(results[1729]["adjudication"]["delta"], results[3141]["adjudication"]["delta"])

    def test_free_action_does_not_become_default_best_line_in_seed_sample(self) -> None:
        hidden_theft = "夜中に宿の裏から入り、裏帳面を拝借する"
        seeds = (1729, 2048, 3141, 4096)
        improvements = 0
        for seed in seeds:
            with self.subTest(seed=seed):
                normal_world = build_bundle(seed=seed)["world_state"]
                free_world = build_bundle(seed=seed)["world_state"]
                with tempfile.TemporaryDirectory() as temp_dir:
                    world_json = Path(temp_dir) / "balance_world.json"
                    for current_world, use_free in ((normal_world, False), (free_world, True)):
                        if use_free:
                            world_json.write_text(json.dumps(current_world, ensure_ascii=False), encoding="utf-8")
                            current_world = play_free_action(hidden_theft, seed=None, world_json=world_json)["after"]["bundle"]["world_state"]
                        for choice_id in ["observe", "inspect", "speak", "observe", "intervene", "inspect"]:
                            world_json.write_text(json.dumps(current_world, ensure_ascii=False), encoding="utf-8")
                            current_world = play_choice(choice_id=choice_id, seed=None, world_json=world_json)["after"]["bundle"]["world_state"]
                        if use_free:
                            free_world = current_world
                        else:
                            normal_world = current_world
                normal_score = float(normal_world["campaign_state"]["lastEnding"]["score"])
                free_score = float(free_world["campaign_state"]["lastEnding"]["score"])
                if free_score > normal_score:
                    improvements += 1
                self.assertLessEqual(free_score - normal_score, 0.5)
        self.assertLessEqual(improvements, 1)

    def test_play_free_action_is_reproducible_for_same_world_and_text(self) -> None:
        bundle = build_bundle(seed=1729)
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "world.json"
            world_json.write_text(json.dumps(bundle["world_state"], ensure_ascii=False, indent=2), encoding="utf-8")
            left = play_free_action("夜中に宿の裏から入り、裏帳面を盗み出す", seed=None, world_json=world_json)
            right = play_free_action("夜中に宿の裏から入り、裏帳面を盗み出す", seed=None, world_json=world_json)
        self.assertEqual(left["structured_result"], right["structured_result"])
        self.assertEqual(left["after"]["bundle"]["world_state"]["campaign_state"]["lastTransition"], right["after"]["bundle"]["world_state"]["campaign_state"]["lastTransition"])

    def test_play_free_action_records_history_and_traces(self) -> None:
        result = play_free_action("夜中に宿の裏から入り、裏帳面を盗み出す", seed=1729)
        campaign = result["after"]["bundle"]["world_state"]["campaign_state"]
        self.assertTrue(campaign["freeActionHistory"])
        self.assertIsNotNone(campaign["lastFreeAction"])
        self.assertTrue(campaign["viceTrace"] or campaign["tabooTrace"])
        self.assertIn("customActionSummary", campaign["lastTransition"])
        self.assertTrue(any(float(value) > 0.0 for value in campaign["roleSlotSuspicion"].values()))
        self.assertTrue(any(float(value) > 0.0 for value in campaign["roleSlotDistrust"].values()))

    def test_free_action_payload_exposes_display_and_structured_result(self) -> None:
        payload = build_free_action_payload(
            free_action_request_from_body(
                {"actionText": "夜中に宿の裏から入り、裏帳面を盗み出す", "seed": 1729, "world_json": None}
            )
        )
        self.assertIn("bundle", payload)
        self.assertIn("display", payload)
        self.assertIn("structuredResult", payload)
        self.assertEqual(payload["structuredResult"]["normalized_intent"]["intent_type"], "custom_action")

    def test_free_action_api_contract(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/free-action",
                data=json.dumps(
                    {
                        "actionText": "夜中に宿の裏から入り、裏帳面を盗み出す",
                        "seed": 1729,
                        "world_json": None,
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("bundle", payload)
            self.assertIn("display", payload)
            self.assertIn("structuredResult", payload)
            self.assertEqual(payload["structuredResult"]["source"]["input_mode"], "free_text")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)


if __name__ == "__main__":
    unittest.main()
