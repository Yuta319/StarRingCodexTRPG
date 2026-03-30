from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.playable_loop import play_choice, play_free_action
from star_ring_codex_trpg.campaign_content import EVENT_BLUEPRINTS
from star_ring_codex_trpg.gameplay_experience import prepare_next_session
from star_ring_codex_trpg.read_only_ui.controller import (
    build_play_payload,
    build_ui_payload,
    play_request_from_body,
    viewer_request_from_query,
)
from star_ring_codex_trpg.runner import build_bundle
from star_ring_codex_trpg.text.copy_checks import collect_copy_issues
from star_ring_codex_trpg.text.terminology_registry import get_term, natural_phrase, ui_label
from star_ring_codex_trpg.text.text_composer import compose_world_pulse_copy


def _strings_from_display(display: dict) -> list[tuple[str, str, str]]:
    values: list[tuple[str, str, str]] = []
    story = display["storyGuide"]
    for key in ("now", "stakes", "worldState", "trace", "forecast", "objective"):
        values.append((f"storyGuide.{key}", story[key], "explanation"))

    current_event = display["currentEvent"]
    values.extend(
        [
            ("currentEvent.statusLabel", current_event["statusLabel"], "status"),
            ("currentEvent.summaryText", current_event["summaryText"], "explanation"),
            ("currentEvent.importanceText", current_event["importanceText"], "explanation"),
            ("currentEvent.lastOutcomeText", current_event["lastOutcomeText"], "afterglow"),
        ]
    )
    for index, branch in enumerate(current_event["branchPreview"]):
        values.extend(
            [
                (f"branchPreview[{index}].summaryText", branch["summaryText"], "explanation"),
                (f"branchPreview[{index}].riskText", branch["riskText"], "explanation"),
                (f"branchPreview[{index}].resultText", branch["resultText"], "afterglow"),
            ]
        )

    for prefix in ("hub", "dungeon"):
        values.extend(
            [
                (f"{prefix}.statusLabel", display[prefix]["statusLabel"], "status"),
                (f"{prefix}.statusText", display[prefix]["statusText"], "afterglow"),
                (f"{prefix}.supportText", display[prefix]["supportText"], "explanation"),
            ]
        )

    values.extend(
        [
            ("worldPulseGuide.statusLabel", display["worldPulseGuide"]["statusLabel"], "status"),
            ("worldPulseGuide.summaryText", display["worldPulseGuide"]["summaryText"], "explanation"),
            ("playerTrace.dominantChoiceText", display["playerTrace"]["dominantChoiceText"], "explanation"),
            ("playerTrace.afterglowText", display["playerTrace"]["afterglowText"], "afterglow"),
            ("playerTrace.summary", display["playerTrace"]["summary"], "explanation"),
        ]
    )

    archive_review = display.get("archiveReview") or {}
    for key in ("latestArchiveSummary", "resurfacingSpark", "hiddenWound"):
        if archive_review.get(key):
            values.append((f"archiveReview.{key}", archive_review[key], "afterglow"))

    session_opening = display.get("sessionOpeningGuide") or {}
    if session_opening.get("headline"):
        values.append(("sessionOpeningGuide.headline", session_opening["headline"], "ui"))
    for index, line in enumerate(session_opening.get("lines", [])):
        values.append((f"sessionOpeningGuide.lines[{index}]", line, "explanation"))

    action_guide = display.get("actionGuide") or {}
    for key in ("choiceMode", "freeActionMode", "sessionFlow"):
        if action_guide.get(key):
            values.append((f"actionGuide.{key}", action_guide[key], "explanation"))

    world_pulse_panel = display.get("worldPulsePanel") or {}
    for key in ("summary", "focus", "read"):
        if world_pulse_panel.get(key):
            values.append((f"worldPulsePanel.{key}", world_pulse_panel[key], "explanation"))

    active_node_guide = display.get("activeNodeGuide") or {}
    for key in ("summary", "action", "timing"):
        if active_node_guide.get(key):
            values.append((f"activeNodeGuide.{key}", active_node_guide[key], "explanation"))

    institution_alert_guide = display.get("institutionAlertGuide") or {}
    for key in ("summary", "consequence"):
        if institution_alert_guide.get(key):
            values.append((f"institutionAlertGuide.{key}", institution_alert_guide[key], "explanation"))

    next_session_hook = display.get("nextSessionHook") or {}
    for key in ("archivedCauseEchoes", "resurfacingRisks", "unresolvedVice", "unresolvedTaboo"):
        for index, text in enumerate(next_session_hook.get(key, [])):
            values.append((f"nextSessionHook.{key}[{index}]", text, "afterglow"))

    for index, npc in enumerate(display["namedCast"]):
        values.extend(
            [
                (f"namedCast[{index}].trustText", npc["trustText"], "afterglow"),
                (f"namedCast[{index}].stressText", npc["stressText"], "afterglow"),
                (f"namedCast[{index}].secretText", npc["secretText"], "afterglow"),
                (f"namedCast[{index}].weaknessText", npc["weaknessText"], "afterglow"),
                (f"namedCast[{index}].conflictText", npc["conflictText"], "afterglow"),
                (f"namedCast[{index}].traceText", npc["traceText"], "afterglow"),
            ]
        )
    return values


class TextOutputTests(unittest.TestCase):
    def test_terminology_registry_returns_internal_ui_and_natural(self) -> None:
        term = get_term("distortion")
        self.assertIsNotNone(term)
        self.assertEqual(term.internal_key, "distortion")
        self.assertEqual(ui_label("distortion"), "世界のゆらぎ")
        self.assertIn("綻び", natural_phrase("distortion"))

    def test_text_composer_does_not_return_internal_metric_names(self) -> None:
        pulse = compose_world_pulse_copy(
            {
                "distortion": 62.5,
                "apotheosis_flux": 54.1,
                "succession_pressure": 49.2,
                "divine_war_pressure": 70.0,
            }
        )
        self.assertEqual(collect_copy_issues(pulse["summaryText"], "explanation"), [])
        self.assertEqual(collect_copy_issues(pulse["statusLabel"], "status"), [])

    def test_story_guide_texts_are_not_empty(self) -> None:
        payload = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        guide = payload["display"]["storyGuide"]
        for key in ("now", "stakes", "worldState", "trace", "forecast", "objective"):
            with self.subTest(key=key):
                self.assertTrue(guide[key].strip())

    def test_transition_message_is_readable_short_text(self) -> None:
        payload = build_play_payload(play_request_from_body({"choiceId": "observe", "seed": 1729, "world_json": None}))
        message = payload["transition"]["message"]
        self.assertIn("。", message)
        self.assertLess(len(message), 96)
        self.assertEqual(collect_copy_issues(message, "explanation"), [])

    def test_ui_display_text_does_not_leak_forbidden_terms(self) -> None:
        payload = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        for label, text, kind in _strings_from_display(payload["display"]):
            with self.subTest(label=label):
                self.assertEqual(collect_copy_issues(text, kind), [])

    def test_session_ending_display_text_is_readable(self) -> None:
        bundle = build_bundle(seed=1729, seasons=10)
        choices = ["observe", "inspect", "speak", "observe", "intervene", "inspect"]
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "session_world.json"
            current_world = bundle["world_state"]
            for choice_id in choices:
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
            world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
            payload = build_ui_payload(viewer_request_from_query({"world_json": [str(world_json)]}))

        ending = payload["display"]["sessionEnding"]
        self.assertIsNotNone(ending)
        for key in ("summary", "whatRemained", "protected", "lost", "carriedForward", "keyNpcAftertaste", "legacyEffect"):
            with self.subTest(key=key):
                self.assertEqual(collect_copy_issues(ending[key], "afterglow"), [])

    def test_event_branch_copy_does_not_fix_to_initial_occupant_names(self) -> None:
        forbidden_names = ("セルカ", "リス", "バシャ", "ノルヴ", "エドラ", "ナミル", "コダ", "ヴァルダ", "メレク", "トア")
        for event in EVENT_BLUEPRINTS:
            for branch in event["branches"]:
                texts = [branch["summary"], *branch["notes"].values()]
                for text in texts:
                    with self.subTest(event=event["eventId"], branch=branch["branchId"], text=text):
                        self.assertFalse(any(name in text for name in forbidden_names))

    def test_archive_reflected_display_text_does_not_leak_raw_free_action_text(self) -> None:
        raw_texts = [
            "夜中に宿の裏から入り、裏帳面を盗み出す",
            "封印札を剥がして禁譜を鳴らし、封路をこじ開ける",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "archive_reflection_world.json"
            current_world = build_bundle(seed=1729, seasons=10)["world_state"]

            for free_action_text, choices in (
                (raw_texts[0], ["observe", "inspect", "speak", "observe", "intervene", "inspect"]),
                (raw_texts[1], ["observe", "inspect", "speak", "observe", "intervene", "inspect"]),
            ):
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_free_action(free_action_text, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
                for choice_id in choices:
                    world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                    result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                    current_world = result["after"]["bundle"]["world_state"]
                current_world = prepare_next_session(current_world)

            world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
            payload = build_ui_payload(viewer_request_from_query({"world_json": [str(world_json)]}))

        collected = " ".join(text for _, text, _ in _strings_from_display(payload["display"]))
        scene_lines = " ".join(payload["display"]["scenePacket"]["playerFacing"]["lines"])
        combined = f"{collected} {scene_lines}"
        for raw_text in raw_texts:
            self.assertNotIn(raw_text, combined)


if __name__ == "__main__":
    unittest.main()
