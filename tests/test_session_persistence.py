from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.gameplay_experience import _compress_session_archive, prepare_next_session
from star_ring_codex_trpg.playable_loop import play_choice, play_free_action
from star_ring_codex_trpg.read_only_ui.controller import (
    build_load_session_payload,
    build_next_session_payload,
    build_play_payload,
    build_save_session_payload,
    build_ui_payload,
    load_session_request_from_body,
    next_session_request_from_body,
    play_request_from_body,
    save_session_request_from_body,
    viewer_request_from_query,
)
from star_ring_codex_trpg.runner import build_bundle


class SessionPersistenceTests(unittest.TestCase):
    def _write_world(self, path: Path, world_state: dict) -> None:
        path.write_text(json.dumps(world_state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _play_session_to_world(
        self,
        seed: int,
        choices: list[str],
        world_json: Path,
        free_action_text: str | None = None,
    ) -> dict:
        current_world = build_bundle(seed=seed, seasons=10)["world_state"]
        if free_action_text:
            self._write_world(world_json, current_world)
            current_world = play_free_action(free_action_text, seed=None, world_json=world_json)["after"]["bundle"]["world_state"]
        for choice_id in choices:
            self._write_world(world_json, current_world)
            result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
            current_world = result["after"]["bundle"]["world_state"]
        self._write_world(world_json, current_world)
        return current_world

    def test_save_then_load_reproduces_same_state(self) -> None:
        original = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        saved = build_save_session_payload(
            save_session_request_from_body({"world_json": original["playSource"]["world_json"]})
        )
        loaded = build_load_session_payload(load_session_request_from_body({"saveId": saved["saveId"]}))

        original_campaign = original["bundle"]["world_state"]["campaign_state"]
        loaded_campaign = loaded["bundle"]["world_state"]["campaign_state"]

        self.assertEqual(
            original["bundle"]["scene_output"]["player_facing"]["scene_title"],
            loaded["bundle"]["scene_output"]["player_facing"]["scene_title"],
        )
        self.assertEqual(original_campaign["session"], loaded_campaign["session"])
        self.assertEqual(original_campaign["hub"], loaded_campaign["hub"])
        self.assertEqual(original_campaign["dungeon"], loaded_campaign["dungeon"])
        self.assertEqual(original_campaign["currentEventId"], loaded_campaign["currentEventId"])
        self.assertEqual(saved["saveId"], loaded["saveMeta"]["saveId"])

    def test_same_save_and_same_choice_is_reproducible(self) -> None:
        original = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        saved = build_save_session_payload(
            save_session_request_from_body({"world_json": original["playSource"]["world_json"]})
        )

        left_load = build_load_session_payload(load_session_request_from_body({"saveId": saved["saveId"]}))
        right_load = build_load_session_payload(load_session_request_from_body({"saveId": saved["saveId"]}))

        left = build_play_payload(
            play_request_from_body(
                {"choiceId": "observe", "seed": None, "world_json": left_load["playSource"]["world_json"]}
            )
        )
        right = build_play_payload(
            play_request_from_body(
                {"choiceId": "observe", "seed": None, "world_json": right_load["playSource"]["world_json"]}
            )
        )

        self.assertEqual(
            left["bundle"]["world_state"]["campaign_state"]["lastTransition"],
            right["bundle"]["world_state"]["campaign_state"]["lastTransition"],
        )
        self.assertEqual(left["bundle"]["world_state"]["campaign_state"]["hub"], right["bundle"]["world_state"]["campaign_state"]["hub"])
        self.assertEqual(
            left["bundle"]["world_state"]["campaign_state"]["dungeon"],
            right["bundle"]["world_state"]["campaign_state"]["dungeon"],
        )
        self.assertEqual(
            left["bundle"]["scene_output"]["player_facing"]["scene_title"],
            right["bundle"]["scene_output"]["player_facing"]["scene_title"],
        )

    def test_next_session_adds_archive_and_hook(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "completed_session.json"
            completed_world = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                world_json,
            )
            before_campaign = completed_world["campaign_state"]
            self.assertFalse(before_campaign["sessionArchive"])
            self.assertIsNone(before_campaign["nextSessionHook"])

            payload = build_next_session_payload(next_session_request_from_body({"world_json": str(world_json)}))

        after_campaign = payload["bundle"]["world_state"]["campaign_state"]
        self.assertEqual(payload["sessionArchiveSize"], 1)
        self.assertEqual(len(after_campaign["sessionArchive"]), 1)
        self.assertIsNotNone(after_campaign["nextSessionHook"])
        self.assertIn("nextMainEventCandidates", after_campaign["nextSessionHook"])
        self.assertIn("carriedPressures", after_campaign["nextSessionHook"])
        self.assertIn("npcCarryOvers", after_campaign["nextSessionHook"])
        self.assertIn("scarsRemaining", after_campaign["nextSessionHook"])
        self.assertIn("protectedAssets", after_campaign["nextSessionHook"])
        self.assertIn("archivedCauseEchoes", after_campaign["nextSessionHook"])
        self.assertIn("resurfacingRisks", after_campaign["nextSessionHook"])
        self.assertIn("unresolvedVice", after_campaign["nextSessionHook"])
        self.assertIn("unresolvedTaboo", after_campaign["nextSessionHook"])
        self.assertIn("archiveReview", payload["display"])
        self.assertIn("resurfacingSpark", payload["display"]["archiveReview"])
        self.assertIn("hiddenWound", payload["display"]["archiveReview"])
        self.assertEqual(
            after_campaign["sessionArchive"][0]["sessionNumber"],
            before_campaign["lastEnding"]["sessionNumber"],
        )

    def test_archive_entry_contains_carry_over_fields_without_raw_text(self) -> None:
        raw_text = "夜中に宿の裏から入り、裏帳面を盗み出す"
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "completed_session.json"
            completed_world = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene"],
                world_json,
                free_action_text=raw_text,
            )
            prepared = prepare_next_session(completed_world)

        archive = prepared["campaign_state"]["sessionArchive"][0]
        for key in [
            "freeActionSummary",
            "freeActionResidueLabel",
            "openingSummary",
            "viceSummary",
            "tabooSummary",
            "publicInfamySummary",
            "hiddenCrimeSummary",
            "ritualPollutionSummary",
            "keyRoleSlotId",
            "keyOccupantLabel",
            "protected",
            "lost",
            "carriedForward",
            "roleSlotPressureSnapshot",
            "roleSlotPressureSummary",
        ]:
            self.assertIn(key, archive)
        self.assertNotEqual(archive["freeActionSummary"], raw_text)
        combined = " ".join(
            str(archive[key])
            for key in [
                "summary",
                "whatRemained",
                "freeActionSummary",
                "freeActionResidueLabel",
                "archivedCauseEcho",
                "resurfacingRisk",
            ]
        )
        self.assertNotIn(raw_text, combined)

    def test_archived_causes_resurface_in_later_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_world_json = Path(temp_dir) / "base_session.json"
            vice_world_json = Path(temp_dir) / "vice_session.json"
            taboo_world_json = Path(temp_dir) / "taboo_session.json"

            base_completed = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                base_world_json,
            )
            vice_completed = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene"],
                vice_world_json,
                free_action_text="夜中に宿の裏から入り、裏帳面を盗み出す",
            )
            taboo_completed = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene"],
                taboo_world_json,
                free_action_text="封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
            )

            base_next = prepare_next_session(base_completed)
            vice_next = prepare_next_session(vice_completed)
            taboo_next = prepare_next_session(taboo_completed)

        vice_archive = vice_next["campaign_state"]["sessionArchive"][0]
        institution_id = vice_archive["institutionIds"][0]
        completed_breach = float(vice_completed["resolved_world"]["institutions"][institution_id]["breach_risk"])
        next_breach = float(vice_next["resolved_world"]["institutions"][institution_id]["breach_risk"])
        self.assertGreaterEqual(next_breach, completed_breach)
        if next_breach == completed_breach:
            self.assertEqual(next_breach, 100.0)
        self.assertTrue(vice_next["campaign_state"]["nextSessionHook"]["resurfacingRisks"])
        self.assertTrue(vice_next["campaign_state"]["nextSessionHook"]["unresolvedVice"])

        def ritual_pressure(world_state: dict) -> float:
            return max(
                float(event["pressure"])
                for event in world_state["campaign_state"]["events"]["catalog"].values()
                if any(keyword in f"{event['label']} {event['summary']}" for keyword in ("封", "祈", "遺物", "鐘"))
            )

        completed_ritual_pressure = ritual_pressure(taboo_completed)
        next_ritual_pressure = ritual_pressure(taboo_next)
        self.assertGreaterEqual(next_ritual_pressure, completed_ritual_pressure)
        if next_ritual_pressure == completed_ritual_pressure:
            self.assertEqual(next_ritual_pressure, 100.0)
        self.assertTrue(taboo_next["campaign_state"]["nextSessionHook"]["archivedCauseEchoes"])
        self.assertTrue(taboo_next["campaign_state"]["nextSessionHook"]["unresolvedTaboo"])

    def test_role_slot_repercussions_persist_into_later_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "campaign_chain.json"
            current_world = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                world_json,
                free_action_text="夜中に宿の裏から入り、裏帳面を盗み出す",
            )
            current_world = prepare_next_session(current_world)

            first_next_campaign = current_world["campaign_state"]
            self.assertGreater(float(first_next_campaign["roleSlotSuspicion"]["slot_ledger_clerk"]), 0.0)
            self.assertGreater(float(first_next_campaign["roleSlotDistrust"]["slot_ledger_clerk"]), 0.0)

            for choice_id in ["observe", "observe", "inspect", "inspect", "observe", "inspect"]:
                self._write_world(world_json, current_world)
                current_world = play_choice(choice_id=choice_id, seed=None, world_json=world_json)["after"]["bundle"]["world_state"]
            current_world = prepare_next_session(current_world)

        second_next_campaign = current_world["campaign_state"]
        self.assertGreater(float(second_next_campaign["roleSlotSuspicion"]["slot_ledger_clerk"]), 0.0)
        self.assertTrue(
            any("目録官" in line for line in second_next_campaign["nextSessionHook"]["npcCarryOvers"])
            or any("目録官" in line for line in second_next_campaign["nextSessionHook"]["carriedPressures"])
        )

    def test_role_slot_repercussions_decay_without_disappearing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "balance_chain.json"
            current_world = self._play_session_to_world(
                1729,
                ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                world_json,
                free_action_text="夜中に宿の裏から入り、裏帳面を拝借する",
            )
            current_world = prepare_next_session(current_world)
            first_campaign = current_world["campaign_state"]
            first_suspicion = float(first_campaign["roleSlotSuspicion"]["slot_ledger_clerk"])

            for _ in range(3):
                for choice_id in ["observe", "observe", "inspect", "inspect", "observe", "inspect"]:
                    self._write_world(world_json, current_world)
                    current_world = play_choice(choice_id=choice_id, seed=None, world_json=world_json)["after"]["bundle"]["world_state"]
                current_world = prepare_next_session(current_world)

        later_campaign = current_world["campaign_state"]
        later_suspicion = float(later_campaign["roleSlotSuspicion"]["slot_ledger_clerk"])
        later_retaliation = float(later_campaign["roleSlotRetaliation"]["slot_ledger_clerk"])

        self.assertGreater(first_suspicion, later_suspicion)
        self.assertGreater(later_suspicion, 0.0)
        self.assertLess(later_retaliation, 40.0)

    def test_archive_keeps_latest_ten_and_tracks_compression(self) -> None:
        campaign = build_bundle(seed=1729, seasons=10)["world_state"]["campaign_state"]
        campaign["sessionArchive"] = [
            {
                "sessionNumber": index,
                "title": f"節{index}",
                "tone": "mixed",
                "summary": f"第{index}節の記録。",
            }
            for index in range(1, 13)
        ]
        _compress_session_archive(campaign)
        self.assertEqual(len(campaign["sessionArchive"]), 10)
        self.assertEqual(campaign["sessionArchive"][0]["sessionNumber"], 3)
        self.assertEqual(campaign["archiveCompression"]["compressedCount"], 2)
        self.assertEqual(campaign["archiveCompression"]["oldestSessionNumber"], 1)
        self.assertEqual(campaign["archiveCompression"]["newestSessionNumber"], 2)
        self.assertTrue(campaign["archiveCompression"]["latestSummary"])

    def test_legacy_fixed_npc_save_migrates_to_role_slots(self) -> None:
        bundle = build_bundle(seed=1729, seasons=10)
        legacy_world = bundle["world_state"]
        npcs = legacy_world["campaign_state"]["npcs"]
        legacy_world["campaign_state"]["npcs"] = {
            "npc_warden_serka": {key: value for key, value in npcs["slot_truce_warden"].items() if key not in {"roleSlotId", "roleLabel", "occupantId", "occupantIndex", "occupantSerial", "occupantStatus", "ageState", "occupantHistory", "lastReplacement", "conflictTargetSlotId", "conflictsWithRoleLabel", "legacyNpcId", "factionAffinity", "regionAffinity", "successionRule", "mortalityRisk", "replacementConditions", "function"}},
            "npc_cantor_lys": {key: value for key, value in npcs["slot_cantor"].items() if key not in {"roleSlotId", "roleLabel", "occupantId", "occupantIndex", "occupantSerial", "occupantStatus", "ageState", "occupantHistory", "lastReplacement", "conflictTargetSlotId", "conflictsWithRoleLabel", "legacyNpcId", "factionAffinity", "regionAffinity", "successionRule", "mortalityRisk", "replacementConditions", "function"}},
            "npc_clerk_basha": {key: value for key, value in npcs["slot_ledger_clerk"].items() if key not in {"roleSlotId", "roleLabel", "occupantId", "occupantIndex", "occupantSerial", "occupantStatus", "ageState", "occupantHistory", "lastReplacement", "conflictTargetSlotId", "conflictsWithRoleLabel", "legacyNpcId", "factionAffinity", "regionAffinity", "successionRule", "mortalityRisk", "replacementConditions", "function"}},
            "npc_guide_norv": {key: value for key, value in npcs["slot_tunnel_guide"].items() if key not in {"roleSlotId", "roleLabel", "occupantId", "occupantIndex", "occupantSerial", "occupantStatus", "ageState", "occupantHistory", "lastReplacement", "conflictTargetSlotId", "conflictsWithRoleLabel", "legacyNpcId", "factionAffinity", "regionAffinity", "successionRule", "mortalityRisk", "replacementConditions", "function"}},
        }
        for legacy_id, target_id in {
            "npc_warden_serka": "npc_clerk_basha",
            "npc_cantor_lys": "npc_guide_norv",
            "npc_clerk_basha": "npc_warden_serka",
            "npc_guide_norv": "npc_cantor_lys",
        }.items():
            legacy_world["campaign_state"]["npcs"][legacy_id]["npcId"] = legacy_id
            legacy_world["campaign_state"]["npcs"][legacy_id]["conflictsWithNpcId"] = target_id

        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "legacy_world.json"
            world_json.write_text(json.dumps(legacy_world, ensure_ascii=False, indent=2), encoding="utf-8")
            migrated = build_bundle(world_json=world_json)

        migrated_npcs = migrated["world_state"]["campaign_state"]["npcs"]
        self.assertIn("slot_truce_warden", migrated_npcs)
        self.assertIn("slot_cantor", migrated_npcs)
        self.assertEqual(migrated_npcs["slot_truce_warden"]["npcId"], "slot_truce_warden")
        self.assertEqual(migrated_npcs["slot_truce_warden"]["conflictsWithNpcId"], "slot_ledger_clerk")
        self.assertIn("occupantId", migrated_npcs["slot_truce_warden"])


if __name__ == "__main__":
    unittest.main()
