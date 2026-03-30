from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.playable_loop import play_choice, play_free_action
from star_ring_codex_trpg.gameplay_experience import (
    _archive_role_slot_overlays,
    _prioritized_archive_entries,
    build_campaign_display,
    build_next_session_hook,
    prepare_next_session,
    scene_archive_brief,
)
from star_ring_codex_trpg.runner import build_bundle, build_bundle_from_world_state
from star_ring_codex_trpg.assets import load_canonical_assets


class GameplayExperienceTests(unittest.TestCase):
    def _play_session_world(self, seed: int, choices: list[str], free_action_text: str | None = None) -> dict:
        bundle = build_bundle(seed=seed, seasons=10)
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "session_world.json"
            current_world = bundle["world_state"]
            result = None
            if free_action_text:
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_free_action(free_action_text, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
            for choice_id in choices:
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
        self.assertIsNotNone(result)
        return current_world

    def _play_session(self, seed: int, choices: list[str]) -> dict:
        return self._play_session_world(seed, choices)["campaign_state"]

    def _play_session_chain(self, seed: int, session_specs: list[dict[str, object]]) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "campaign_chain.json"
            current_world = build_bundle(seed=seed, seasons=10)["world_state"]
            for spec in session_specs:
                free_action_text = spec.get("free_action_text")
                if isinstance(free_action_text, str) and free_action_text.strip():
                    world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                    result = play_free_action(free_action_text, seed=None, world_json=world_json)
                    current_world = result["after"]["bundle"]["world_state"]
                for choice_id in spec["choices"]:
                    world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                    result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                    current_world = result["after"]["bundle"]["world_state"]
                current_world = prepare_next_session(current_world)
        return current_world

    def test_bundle_contains_campaign_content(self) -> None:
        bundle = build_bundle(seed=1729, seasons=10)
        campaign = bundle["world_state"]["campaign_state"]
        self.assertEqual(campaign["version"], 2)
        self.assertEqual(len(campaign["npcs"]), 9)
        self.assertEqual(len(campaign["events"]["catalog"]), 9)
        self.assertEqual(len(campaign["hubCatalog"]), 3)
        self.assertEqual(len(campaign["dungeonCatalog"]), 3)
        self.assertIn("label", campaign["hub"])
        self.assertIn("label", campaign["dungeon"])
        self.assertEqual(len(campaign["events"]["catalog"][campaign["currentEventId"]]["branches"]), 5)
        for event in campaign["events"]["catalog"].values():
            self.assertEqual(len(event["branches"]), 5)
        truce_warden = campaign["npcs"]["slot_truce_warden"]
        self.assertIn("roleSlotId", truce_warden)
        self.assertIn("roleLabel", truce_warden)
        self.assertIn("occupantId", truce_warden)
        self.assertIn("secret", truce_warden)
        self.assertIn("hintTrigger", truce_warden)
        self.assertIn("weaknessTrigger", truce_warden)
        self.assertIn("conflictDetail", truce_warden)
        self.assertIn("successionRule", truce_warden)
        self.assertIn("replacementConditions", truce_warden)
        self.assertEqual(truce_warden["conflictsWithNpcId"], "slot_ledger_clerk")
        oath_scribe = campaign["npcs"]["slot_oath_scribe"]
        ferrymaster = campaign["npcs"]["slot_ferrymaster"]
        ward_mason = campaign["npcs"]["slot_ward_mason"]
        for npc in (oath_scribe, ferrymaster, ward_mason):
            self.assertIn("occupantId", npc)
            self.assertTrue(npc["viceExposure"] or npc["tabooExposure"])
            self.assertTrue(npc["exposureProfile"]["viceIds"] or npc["exposureProfile"]["tabooIds"])

    def test_play_choice_advances_campaign_turn_and_mutation(self) -> None:
        result = play_choice(choice_id="observe", seed=1729, seasons=10)
        before_campaign = result["before"]["bundle"]["world_state"]["campaign_state"]
        after_campaign = result["after"]["bundle"]["world_state"]["campaign_state"]
        self.assertEqual(before_campaign["session"]["turnInSession"], 1)
        self.assertEqual(after_campaign["session"]["turnInSession"], 2)
        self.assertTrue(after_campaign["events"]["history"])
        self.assertIsNotNone(after_campaign["lastTransition"])
        self.assertTrue(
            before_campaign["hub"] != after_campaign["hub"]
            or before_campaign["dungeon"] != after_campaign["dungeon"]
            or before_campaign["events"]["catalog"] != after_campaign["events"]["catalog"]
        )

    def test_same_world_json_and_choice_is_reproducible(self) -> None:
        bundle = build_bundle(seed=1729, seasons=10)
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "seed1729_world.json"
            world_json.write_text(json.dumps(bundle["world_state"], ensure_ascii=False, indent=2), encoding="utf-8")
            left = play_choice(choice_id="inspect", seed=None, world_json=world_json)
            right = play_choice(choice_id="inspect", seed=None, world_json=world_json)
        self.assertEqual(left["after"]["bundle"]["world_state"]["campaign_state"]["lastTransition"], right["after"]["bundle"]["world_state"]["campaign_state"]["lastTransition"])
        self.assertEqual(left["after"]["bundle"]["world_state"]["campaign_state"]["hub"], right["after"]["bundle"]["world_state"]["campaign_state"]["hub"])
        self.assertEqual(left["after"]["bundle"]["world_state"]["campaign_state"]["dungeon"], right["after"]["bundle"]["world_state"]["campaign_state"]["dungeon"])
        self.assertEqual(left["after"]["bundle"]["scene_output"]["player_facing"]["scene_title"], right["after"]["bundle"]["scene_output"]["player_facing"]["scene_title"])

    def test_ui_payload_exposes_story_guidance(self) -> None:
        from star_ring_codex_trpg.read_only_ui.controller import build_ui_payload, viewer_request_from_query

        payload = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        self.assertIn("playCycle", payload["display"])
        self.assertIn("storyGuide", payload["display"])
        self.assertIn("currentEvent", payload["display"])
        self.assertIn("hub", payload["display"])
        self.assertIn("dungeon", payload["display"])
        self.assertIn("playerTrace", payload["display"])
        self.assertIn("endingForecast", payload["display"])
        self.assertEqual(len(payload["display"]["namedCast"]), 9)

    def test_seed_changes_active_content_loadout(self) -> None:
        seeds = [1729, 2048, 3141]
        campaigns = [build_bundle(seed=seed, seasons=10)["world_state"]["campaign_state"] for seed in seeds]
        self.assertEqual(len({campaign["hub"]["hubId"] for campaign in campaigns}), 3)
        self.assertEqual(len({campaign["dungeon"]["dungeonId"] for campaign in campaigns}), 3)
        self.assertEqual(len({campaign["currentEventId"] for campaign in campaigns}), 3)

    def test_all_phase1_events_are_selected_across_three_seed_sessions(self) -> None:
        seen_events: set[str] = set()
        for seed in (1729, 2048, 3141):
            with tempfile.TemporaryDirectory() as temp_dir:
                world_json = Path(temp_dir) / f"phase1_seed_{seed}.json"
                current_world = build_bundle(seed=seed, seasons=10)["world_state"]
                seen_events.add(current_world["campaign_state"]["currentEventId"])
                for choice_id in ["observe", "inspect", "speak", "observe", "intervene", "inspect"]:
                    world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                    result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                    current_world = result["after"]["bundle"]["world_state"]
                    seen_events.add(current_world["campaign_state"]["currentEventId"])
        self.assertEqual(
            seen_events,
            {
                "evt_black_envoy_delay",
                "evt_ledger_gap",
                "evt_bell_resonance",
                "evt_oath_paper_fray",
                "evt_checkpoint_queue_freeze",
                "evt_mire_vault_glare",
                "evt_quarantine_pass_split",
                "evt_wharf_manifest_drift",
                "evt_salt_oracle_backwash",
            },
        )

    def test_six_turns_generate_session_ending(self) -> None:
        campaign = self._play_session(1729, ["observe", "inspect", "speak", "observe", "intervene", "inspect"])
        self.assertIsNotNone(campaign["lastEnding"])
        self.assertEqual(campaign["lastEnding"]["sessionNumber"], 1)
        self.assertTrue(campaign["sessionEndings"])
        self.assertIn("小結末", campaign["worldMarks"][-1])
        self.assertEqual(campaign["session"]["sessionNumber"], 2)
        self.assertIn("keyRoleSlotId", campaign["lastEnding"])
        self.assertEqual(campaign["lastEnding"]["keyRoleSlotId"], campaign["lastEnding"]["keyNpcId"])
        self.assertIn("whatRemained", campaign["lastEnding"])
        self.assertIn("protected", campaign["lastEnding"])
        self.assertIn("lost", campaign["lastEnding"])
        self.assertIn("carriedForward", campaign["lastEnding"])
        self.assertIn(campaign["lastEnding"]["keyNpcLabel"], campaign["lastEnding"]["summary"])

    def test_later_turn_can_select_added_branch(self) -> None:
        campaign = self._play_session(1729, ["inspect", "observe", "inspect", "speak"])
        branch_id = campaign["lastTransition"]["branchId"]
        self.assertIn(branch_id, {"branch_scapegoat_store", "branch_pilgrim_detour", "branch_quarantine_salt_mark"})

    def test_relevant_choices_advance_npc_secret_and_weakness_arcs(self) -> None:
        campaign = self._play_session(1729, ["inspect", "observe", "inspect", "speak", "observe", "inspect"])
        serka = campaign["npcs"]["slot_truce_warden"]
        lys = campaign["npcs"]["slot_cantor"]
        self.assertIn(serka["secretState"], {"hinted", "exposed"})
        self.assertTrue(serka["lastSecretTrigger"])
        self.assertIsNotNone(lys["knownWeakness"])
        self.assertTrue(lys["lastWeaknessTrigger"])

    def test_next_session_can_replace_current_occupant(self) -> None:
        world_state = self._play_session_world(1729, ["intervene", "observe", "intervene", "speak", "intervene", "inspect"])
        next_state = prepare_next_session(world_state)
        replacements = [
            npc["lastReplacement"]
            for npc in next_state["campaign_state"]["npcs"].values()
            if npc.get("lastReplacement")
        ]
        self.assertTrue(replacements)
        self.assertTrue(any(item["newOccupantName"] != item["previousOccupantName"] for item in replacements))
        self.assertEqual(
            next_state["campaign_state"]["sessionArchive"][0]["keyRoleSlotId"],
            next_state["campaign_state"]["lastEnding"]["keyRoleSlotId"],
        )

    def test_next_session_rotates_active_content(self) -> None:
        start = build_bundle(seed=1729, seasons=10)["world_state"]["campaign_state"]
        finished_world = self._play_session_world(1729, ["observe", "inspect", "speak", "observe", "intervene", "inspect"])
        next_state = prepare_next_session(finished_world)["campaign_state"]
        self.assertNotEqual(start["hub"]["hubId"], next_state["hub"]["hubId"])
        self.assertNotEqual(start["dungeon"]["dungeonId"], next_state["dungeon"]["dungeonId"])
        self.assertNotEqual(start["currentEventId"], next_state["currentEventId"])

    def test_session_endings_vary_by_choice_sequence(self) -> None:
        grim_campaign = self._play_session(2048, ["intervene", "observe", "intervene", "speak", "intervene", "inspect"])
        steady_campaign = self._play_session(2048, ["observe", "observe", "inspect", "inspect", "observe", "inspect"])
        self.assertLess(float(grim_campaign["lastEnding"]["score"]), float(steady_campaign["lastEnding"]["score"]))
        self.assertNotEqual(grim_campaign["lastEnding"]["tone"], steady_campaign["lastEnding"]["tone"])
        self.assertNotEqual(grim_campaign["lastEnding"]["title"], steady_campaign["lastEnding"]["title"])

    def test_balance_sample_covers_all_three_tones(self) -> None:
        scenarios = [
            (1729, ["observe", "inspect", "speak", "observe", "intervene", "inspect"], "mixed"),
            (2048, ["observe", "observe", "inspect", "inspect", "observe", "inspect"], "steady"),
            (3141, ["intervene", "observe", "intervene", "speak", "intervene", "inspect"], "grim"),
        ]
        observed = set()
        for seed, choices, expected_tone in scenarios:
            with self.subTest(seed=seed, expected_tone=expected_tone):
                campaign = self._play_session(seed, choices)
                observed.add(campaign["lastEnding"]["tone"])
                self.assertEqual(campaign["lastEnding"]["tone"], expected_tone)
        self.assertEqual(observed, {"steady", "mixed", "grim"})

    def test_ending_summary_matches_tone(self) -> None:
        grim_campaign = self._play_session(3141, ["intervene", "observe", "intervene", "speak", "intervene", "inspect"])
        mixed_campaign = self._play_session(1729, ["observe", "inspect", "speak", "observe", "intervene", "inspect"])
        steady_campaign = self._play_session(2048, ["observe", "observe", "inspect", "inspect", "observe", "inspect"])

        grim = grim_campaign["lastEnding"]
        mixed = mixed_campaign["lastEnding"]
        steady = steady_campaign["lastEnding"]

        self.assertIn(grim["lost"], grim["summary"])
        self.assertIn("守り切れず", grim["summary"])
        self.assertIn(grim["protected"], grim["summary"])

        self.assertIn(mixed["protected"], mixed["summary"])
        self.assertIn(mixed["lost"], mixed["summary"])
        self.assertIn("借り", mixed["summary"])

        self.assertIn(steady["protected"], steady["summary"])
        self.assertIn(steady["lost"], steady["summary"])
        self.assertIn("踏みとどまり", steady["summary"])

    def test_vice_free_action_reaches_ending_and_next_hook(self) -> None:
        world_state = self._play_session_world(
            1729,
            ["observe", "inspect", "speak", "observe", "intervene"],
            free_action_text="夜中に宿の裏から入り、裏帳面を盗み出す",
        )
        campaign = world_state["campaign_state"]
        ending = campaign["lastEnding"]
        hook = build_next_session_hook(world_state)
        free_action_summary = campaign["lastFreeAction"]["freeActionSummary"]

        self.assertIn(free_action_summary, ending["summary"])
        self.assertTrue("隠" in ending["whatRemained"] or "疑" in ending["whatRemained"])
        self.assertTrue(
            any(
                free_action_summary in line and ("痕の洗い出し" in line or "悪評" in line)
                for line in hook["nextMainEventCandidates"]
            )
        )
        self.assertTrue(any("目録官" in line for line in hook["npcCarryOvers"]))
        self.assertGreater(float(campaign["hiddenCrimes"]), 0.0)
        self.assertTrue(campaign["viceTrace"])

    def test_taboo_free_action_pushes_tone_and_hook_into_ritual_fallout(self) -> None:
        base_campaign = self._play_session(2048, ["observe", "inspect", "speak", "observe", "intervene", "inspect"])
        world_state = self._play_session_world(
            2048,
            ["observe", "inspect", "speak", "observe", "intervene"],
            free_action_text="封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
        )
        campaign = world_state["campaign_state"]
        ending = campaign["lastEnding"]
        hook = build_next_session_hook(world_state)

        self.assertLess(float(ending["score"]), float(base_campaign["lastEnding"]["score"]))
        self.assertNotEqual(ending["tone"], "steady")
        self.assertIn("濁り", ending["legacyEffect"])
        self.assertTrue(any("禁じ手の検分" in line for line in hook["nextMainEventCandidates"]))
        self.assertTrue(any("祈鐘士" in line for line in hook["npcCarryOvers"]))
        self.assertTrue(campaign["tabooTrace"])

    def test_archive_priority_exposes_requested_axes_and_limits_hook_lines(self) -> None:
        world_state = self._play_session_chain(
            1729,
            [
                {
                    "free_action_text": "夜中に宿の裏から入り、裏帳面を盗み出す",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "choices": ["observe", "observe", "inspect", "inspect", "observe", "inspect"],
                },
                {
                    "free_action_text": "封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
            ],
        )
        state_for_hook = copy.deepcopy(world_state)
        ritual_event_id = next(
            event_id
            for event_id, event in state_for_hook["campaign_state"]["events"]["catalog"].items()
            if any(keyword in f"{event['label']} {event['summary']}" for keyword in ("封", "祈", "遺物", "鐘"))
        )
        state_for_hook["campaign_state"]["currentEventId"] = ritual_event_id

        ranked = _prioritized_archive_entries(state_for_hook["campaign_state"])
        self.assertEqual(len(state_for_hook["campaign_state"]["sessionArchive"]), 3)
        self.assertLessEqual(len(ranked), 3)
        for key in (
            "recency",
            "severity",
            "visibility",
            "roleSlotRelevance",
            "institutionRelevance",
            "currentEventRelevance",
            "total",
        ):
            self.assertIn(key, ranked[0]["_priority"])

        hook = build_next_session_hook(state_for_hook)
        self.assertTrue(hook["archivedCauseEchoes"])
        self.assertTrue(hook["resurfacingRisks"])
        self.assertTrue(hook["unresolvedTaboo"])
        self.assertLessEqual(len(hook["archivedCauseEchoes"]), 3)
        self.assertLessEqual(len(hook["resurfacingRisks"]), 3)
        self.assertLessEqual(len(hook["unresolvedVice"]), 3)
        self.assertLessEqual(len(hook["unresolvedTaboo"]), 3)
        self.assertTrue(hook["archivedCauseEchoes"][0].startswith("第3節"))

    def test_archive_review_separates_latest_record_resurfacing_spark_and_hidden_wound(self) -> None:
        raw_texts = [
            "夜中に宿の裏から入り、裏帳面を盗み出す",
            "封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
        ]
        world_state = self._play_session_chain(
            1729,
            [
                {
                    "free_action_text": raw_texts[0],
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "choices": ["observe", "observe", "inspect", "inspect", "observe", "inspect"],
                },
                {
                    "free_action_text": raw_texts[1],
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
            ],
        )
        display = build_campaign_display(world_state, "検証場面")
        review = display["archiveReview"]

        self.assertIsNotNone(review)
        self.assertIn("latestArchiveSummary", review)
        self.assertIn("resurfacingSpark", review)
        self.assertIn("hiddenWound", review)
        self.assertTrue(review["latestArchiveSummary"].startswith("第3節"))
        self.assertTrue(review["resurfacingSpark"].strip())
        self.assertTrue(review["hiddenWound"].strip())
        combined = " ".join(review.values())
        for raw_text in raw_texts:
            self.assertNotIn(raw_text, combined)

    def test_archive_priority_keeps_top_three_even_after_five_sessions(self) -> None:
        world_state = self._play_session_chain(
            1729,
            [
                {
                    "free_action_text": "夜中に宿の裏から入り、裏帳面を盗み出す",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "choices": ["observe", "observe", "inspect", "inspect", "observe", "inspect"],
                },
                {
                    "free_action_text": "封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "free_action_text": "宿場差配の弱みを突き、寝床札を先に回すよう脅す",
                    "choices": ["intervene", "observe", "intervene", "speak", "intervene", "inspect"],
                },
                {
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
            ],
        )

        ranked = _prioritized_archive_entries(world_state["campaign_state"])
        self.assertEqual(len(world_state["campaign_state"]["sessionArchive"]), 5)
        self.assertLessEqual(len(ranked), 3)
        totals = [float(entry["_priority"]["total"]) for entry in ranked]
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_archive_inspector_exposes_filter_and_priority_data(self) -> None:
        world_state = self._play_session_chain(
            1729,
            [
                {
                    "free_action_text": "夜中に宿の裏から入り、裏帳面を盗み出す",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "free_action_text": "封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
            ],
        )
        display = build_campaign_display(world_state, "検証場面")
        inspector = display["archiveInspector"]
        self.assertIsNotNone(inspector)
        self.assertTrue(inspector["entries"])
        first = inspector["entries"][0]
        self.assertIn("openingSummary", first)
        self.assertIn("priorityDebug", first)
        self.assertIn("filterTags", first)
        self.assertIn("hookConnections", first)
        self.assertIn("roleFilters", inspector)

    def test_archive_echo_reflects_into_scene_story_guide_and_current_event(self) -> None:
        finished_world = self._play_session_world(
            1729,
            ["observe", "inspect", "speak", "observe", "intervene"],
            free_action_text="封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
        )
        world_state = prepare_next_session(finished_world)
        bundle = build_bundle_from_world_state(world_state, load_canonical_assets())
        display = build_campaign_display(world_state, bundle["scene_output"]["player_facing"]["scene_title"])
        archive_brief = scene_archive_brief(world_state)
        scene_lines = bundle["scene_packet"]["playerFacing"]["lines"]
        scene_record = bundle["scene_output"]["player_facing"]["scene_record"]

        self.assertTrue(archive_brief["openingLines"])
        for line in archive_brief["openingLines"]:
            self.assertIn(line, scene_lines)
            self.assertIn(line, scene_record)
        self.assertIn(archive_brief["headlineText"], bundle["scene_packet"]["playerFacing"]["headline"])
        if archive_brief["storyNowText"]:
            self.assertIn(archive_brief["storyNowText"].rstrip("。"), display["storyGuide"]["now"])
        if archive_brief["storyStakesText"]:
            self.assertIn(archive_brief["storyStakesText"].rstrip("。"), display["storyGuide"]["stakes"])
        if archive_brief["worldStateText"]:
            self.assertIn(archive_brief["worldStateText"].rstrip("。"), display["storyGuide"]["worldState"])
        if archive_brief["eventSummaryText"]:
            self.assertIn(archive_brief["eventSummaryText"].rstrip("。"), display["currentEvent"]["summaryText"])
        if archive_brief["eventImportanceText"]:
            self.assertIn(archive_brief["eventImportanceText"].rstrip("。"), display["currentEvent"]["importanceText"])

    def test_archive_priority_changes_current_occupant_reactions(self) -> None:
        world_state = self._play_session_chain(
            1729,
            [
                {
                    "free_action_text": "夜中に宿の裏から入り、裏帳面を盗み出す",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "free_action_text": "封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "choices": ["observe", "observe", "inspect", "inspect", "observe", "inspect"],
                },
            ],
        )
        bundle = build_bundle_from_world_state(world_state, load_canonical_assets())
        display = build_campaign_display(world_state, bundle["scene_output"]["player_facing"]["scene_title"])
        overlays = _archive_role_slot_overlays(world_state["campaign_state"])
        named_cast = {npc["npcId"]: npc for npc in display["namedCast"]}
        scene_beats = {beat["npcId"]: beat for beat in bundle["scene_packet"]["npcBeats"]}

        self.assertGreaterEqual(len(overlays), 1)
        self.assertLessEqual(len(overlays), 3)

        matched_trace_slots = 0
        for role_slot_id, overlay in overlays.items():
            self.assertIn(role_slot_id, named_cast)
            self.assertIn(overlay["archiveReactionText"].rstrip("。"), named_cast[role_slot_id]["traceText"])
            if role_slot_id in scene_beats:
                self.assertIn(overlay["archiveRoleText"].rstrip("。"), scene_beats[role_slot_id]["roleBeat"])
                self.assertIn(overlay["archiveRelationText"].rstrip("。"), scene_beats[role_slot_id]["relationBeat"])
                self.assertIn(overlay["archiveEmotionText"].rstrip("。"), scene_beats[role_slot_id]["emotionBeat"])
            matched_trace_slots += 1

        self.assertEqual(matched_trace_slots, len(overlays))

    def test_role_slot_repercussions_reappear_in_later_scene_echo(self) -> None:
        world_state = self._play_session_chain(
            1729,
            [
                {
                    "free_action_text": "夜中に宿の裏から入り、裏帳面を盗み出す",
                    "choices": ["observe", "inspect", "speak", "observe", "intervene", "inspect"],
                },
                {
                    "choices": ["observe", "observe", "inspect", "inspect", "observe", "inspect"],
                },
            ],
        )
        campaign = world_state["campaign_state"]
        self.assertGreater(float(campaign["roleSlotSuspicion"]["slot_ledger_clerk"]), 0.0)
        self.assertGreater(float(campaign["roleSlotDistrust"]["slot_ledger_clerk"]), 0.0)

        bundle = build_bundle_from_world_state(world_state, load_canonical_assets())
        display = build_campaign_display(world_state, bundle["scene_output"]["player_facing"]["scene_title"])
        named_cast = {npc["npcId"]: npc for npc in display["namedCast"]}
        current_lines = " ".join(
            [
                display["storyGuide"]["now"],
                display["storyGuide"]["stakes"],
                display["currentEvent"]["summaryText"],
                display["currentEvent"]["importanceText"],
            ]
        )
        self.assertIn("slot_ledger_clerk", named_cast)
        self.assertTrue(any(keyword in named_cast["slot_ledger_clerk"]["traceText"] for keyword in ("疑い", "不信", "報い")))
        self.assertTrue(any(keyword in current_lines for keyword in ("疑い", "不信", "報い")))


if __name__ == "__main__":
    unittest.main()
