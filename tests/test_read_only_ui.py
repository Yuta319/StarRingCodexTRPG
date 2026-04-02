from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from star_ring_codex_trpg.errors import UiRequestError
from star_ring_codex_trpg.playable_loop import play_choice
from star_ring_codex_trpg.read_only_ui.controller import (
    build_front_free_action_payload,
    build_front_finalize_character_payload,
    build_front_load_session_payload,
    build_front_next_session_payload,
    build_front_play_payload,
    build_front_snapshot_payload,
    build_gpt_free_action_payload,
    build_gpt_finalize_character_payload,
    build_gpt_load_session_payload,
    build_gpt_next_session_payload,
    build_gpt_play_payload,
    build_play_payload,
    build_save_session_payload,
    build_ui_payload,
    finalize_character_request_from_body,
    free_action_request_from_body,
    load_session_request_from_body,
    next_session_request_from_body,
    play_request_from_body,
    save_session_request_from_body,
    viewer_request_from_query,
)
from star_ring_codex_trpg.runner import build_bundle
from star_ring_codex_trpg.read_only_ui.server import ReadOnlyUiHandler


class ReadOnlyUiTests(unittest.TestCase):
    def test_viewer_request_defaults_to_seed(self) -> None:
        request = viewer_request_from_query({})
        self.assertEqual(request.seed, 1729)
        self.assertIsNone(request.world_json)
        self.assertEqual(request.seasons, 10)
        self.assertIsNone(request.character_profile)

    def test_viewer_request_accepts_world_json(self) -> None:
        world_json = Path(".sources/handoff/PBW_Codex_Handoff_Pack_v1/pbw_generated_world_seed1729_v9_mythic_integration.json")
        request = viewer_request_from_query({"world_json": [str(world_json)], "seasons": ["10"]})
        self.assertIsNone(request.seed)
        self.assertEqual(request.world_json, world_json)
        self.assertIsNone(request.character_profile)

    def test_viewer_request_accepts_character_profile(self) -> None:
        request = viewer_request_from_query(
            {
                "seed": ["1729"],
                "character_name": ["セリル"],
                "character_race": ["elf"],
                "character_style": ["seeker"],
                "character_temperament": ["prudence"],
                "character_origin": ["shrine"],
                "character_loadout": ["ritescribe"],
                "character_source_mode": ["reincarnated"],
                "character_source_title": ["黒い砂漠"],
                "character_source_name": ["セリル"],
                "character_appearance_notes": ["長い銀髪、眠そうな目"],
                "character_reinterpretation_notes": ["弓使いではなく杖使いに置き換える"],
            }
        )
        self.assertEqual(request.character_profile.name, "セリル")
        self.assertEqual(request.character_profile.race, "elf")
        self.assertEqual(request.character_profile.style, "seeker")
        self.assertEqual(request.character_profile.temperament, "prudence")
        self.assertEqual(request.character_profile.origin, "shrine")
        self.assertEqual(request.character_profile.loadout, "ritescribe")
        self.assertEqual(request.character_profile.source_mode, "reincarnated")
        self.assertEqual(request.character_profile.source_title, "黒い砂漠")
        self.assertEqual(request.character_profile.appearance_notes, "長い銀髪、眠そうな目")

    def test_viewer_request_rejects_seed_and_world_json(self) -> None:
        with self.assertRaises(UiRequestError):
            viewer_request_from_query({"seed": ["1729"], "world_json": ["sample.json"]})

    def test_build_ui_payload_contains_display_sections(self) -> None:
        payload = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        self.assertIn("display", payload)
        self.assertIn("worldSpine", payload["display"])
        self.assertIn("scenePacket", payload["display"])
        self.assertIn("activeNode", payload["display"])
        self.assertIn("storyGuide", payload["display"])
        self.assertIn("sessionOpeningGuide", payload["display"])
        self.assertIn("actionGuide", payload["display"])
        self.assertIn("worldPulsePanel", payload["display"])
        self.assertIn("activeNodeGuide", payload["display"])
        self.assertIn("institutionAlertGuide", payload["display"])
        self.assertIn("currentEvent", payload["display"])
        self.assertIn("newGameGenesis", payload["display"])
        self.assertIn("archiveInspector", payload["display"])
        self.assertIn("equipmentHub", payload["display"])
        self.assertIn("inventoryHub", payload["display"])
        self.assertIn("assetPromptPack", payload["display"])
        self.assertTrue(payload["display"]["npcBeats"])
        self.assertTrue(payload["display"]["namedCast"][0]["summaryText"])
        self.assertTrue(payload["display"]["namedCast"][0]["attitudeText"])
        self.assertTrue(payload["display"]["newGameGenesis"]["openingSummary"])
        self.assertTrue(payload["playSource"]["world_json"])
        self.assertTrue(payload["display"]["equipmentHub"]["slots"])
        self.assertGreater(payload["display"]["assetPromptPack"]["entryCount"], 8)
        self.assertIn("portraitGuide", payload["display"]["assetPromptPack"])
        self.assertTrue(
            any(
                entry["kind"] in {"portrait_icon", "portrait_plate"}
                for entry in payload["display"]["assetPromptPack"]["entries"]
            )
        )

    def test_build_front_snapshot_payload_contains_display_without_bundle(self) -> None:
        payload = build_front_snapshot_payload(viewer_request_from_query({"seed": ["1729"]}))
        self.assertIn("display", payload)
        self.assertIn("playSource", payload)
        self.assertNotIn("bundle", payload)
        self.assertIn("worldSpine", payload["display"])
        self.assertIn("scenePacket", payload["display"])

    def test_front_snapshot_applies_character_creation_profile(self) -> None:
        payload = build_front_snapshot_payload(
            viewer_request_from_query(
                {
                    "seed": ["1729"],
                    "character_name": ["ルナ"],
                    "character_race": ["elf"],
                    "character_style": ["seeker"],
                    "character_temperament": ["prudence"],
                    "character_origin": ["shrine"],
                    "character_loadout": ["ritescribe"],
                    "character_source_mode": ["reincarnated"],
                    "character_source_title": ["MMOの自キャラ"],
                    "character_source_name": ["ルナ"],
                    "character_appearance_notes": ["長い銀髪、細身、濃紺と金の配色"],
                    "character_reinterpretation_notes": ["落ち着いた顔つきと前髪の影は残したい"],
                }
            )
        )
        actor = payload["display"]["actorRail"]
        profile = payload["display"]["characterProfile"]
        self.assertEqual(actor["label"], "ルナ")
        self.assertEqual(profile["race"], "elf")
        self.assertEqual(profile["style"], "seeker")
        self.assertEqual(profile["loadout"], "ritescribe")
        self.assertEqual(profile["sourceMode"], "reincarnated")
        self.assertTrue(profile["openingVariants"])
        self.assertIn("visibleBoon", profile["starterBoonSeed"])
        self.assertEqual(actor["quickSlots"][0]["label"], "調べる")
        self.assertIn("ルナ", payload["display"]["sessionOpeningGuide"]["headline"])
        self.assertIn("ルナ", "".join(payload["display"]["sessionOpeningGuide"]["lines"]))
        self.assertIn("MMOの自キャラ", payload["display"]["assetPromptPack"]["entries"][0]["prompt"])

    def test_front_snapshot_is_smaller_than_full_ui_payload(self) -> None:
        full_payload = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        front_payload = build_front_snapshot_payload(viewer_request_from_query({"seed": ["1729"]}))
        full_size = len(json.dumps(full_payload, ensure_ascii=False))
        front_size = len(json.dumps(front_payload, ensure_ascii=False))
        self.assertLess(front_size, full_size)

    def test_finalize_character_request_accepts_world_json_and_proposal(self) -> None:
        request = finalize_character_request_from_body(
            {
                "world_json": "runtime/world.json",
                "proposal": {
                    "openingHeadline": "導入案",
                    "starterLoadout": [{"slotId": "main_hand", "name": "境界の弓"}],
                },
            }
        )
        self.assertEqual(str(request.world_json), "runtime\\world.json")
        self.assertEqual(request.proposal["openingHeadline"], "導入案")

    def test_front_finalize_character_payload_applies_safe_overrides(self) -> None:
        initial = build_front_snapshot_payload(
            viewer_request_from_query(
                {
                    "seed": ["1729"],
                    "character_name": ["アリア"],
                    "character_race": ["fallen"],
                    "character_style": ["shadow"],
                    "character_temperament": ["rebellious"],
                    "character_origin": ["harbor"],
                    "character_loadout": ["tailored"],
                    "character_source_mode": ["reincarnated"],
                    "character_source_title": ["MMO自キャラ"],
                    "character_source_name": ["Aria"],
                    "character_appearance_notes": ["長い黒髪、片目を隠す前髪、細身、弓使い"],
                    "character_reinterpretation_notes": ["暗い海色と銀の差し色、静かな目つき"],
                }
            )
        )
        request = finalize_character_request_from_body(
            {
                "world_json": initial["playSource"]["world_json"],
                "proposal": {
                    "openingHeadline": "アリアの始まり",
                    "openingLines": ["港の風がまだ前世の癖を覚えている。", "今回は弓と索具で入る。"],
                    "openingVariants": [{"label": "静かな導入", "summary": "港の風の中で、アリアはまだ前世の気配を引いている。"}],
                    "selectedOpeningVariantLabel": "静かな導入",
                    "openingPromptHint": "アリアの導入を2〜4文で語る。港の風と前世の名残を核にする。",
                    "loadoutName": "影織りの旅装",
                    "starterLoadout": [
                        {
                            "slotId": "main_hand",
                            "name": "夜潮の弓",
                            "subtitle": "弓 / 影",
                            "stats": ["攻撃 220", "静歩 80"],
                            "flavorText": "港の夜気を吸ったような反りの長い弓。",
                        }
                    ],
                    "starterBoonSeed": {
                        "visibleBoon": {"label": "影潮の勘", "summary": "見えない水際の流れを読む。"},
                        "dormantGrace": {"label": "異界の返り火", "summary": "前の世界の勘が、時々だけ答えを先に示す。"},
                    },
                },
            }
        )
        payload = build_front_finalize_character_payload(request)
        profile = payload["display"]["characterProfile"]
        main_hand = payload["display"]["equipmentHub"]["slots"][0]
        self.assertEqual(payload["transition"]["outcome"], "applied")
        self.assertEqual(profile["customOpeningHeadline"], "アリアの始まり")
        self.assertEqual(profile["selectedOpeningVariantLabel"], "静かな導入")
        self.assertIn("港の風", profile["openingPromptHint"])
        self.assertEqual(profile["starterBoonSeed"]["visibleBoon"]["label"], "影潮の勘")
        self.assertEqual(payload["display"]["equipmentHub"]["loadoutName"], "影織りの旅装")
        self.assertEqual(main_hand["name"], "夜潮の弓")
        self.assertIn("攻撃 165", main_hand["stats"])
        self.assertIn("静歩 48", main_hand["stats"])

    def test_gpt_finalize_character_payload_returns_updated_read_model(self) -> None:
        initial = build_front_snapshot_payload(viewer_request_from_query({"seed": ["1729"]}))
        request = finalize_character_request_from_body(
            {
                "world_json": initial["playSource"]["world_json"],
                "proposal": {
                    "openingHeadline": "新しい導入",
                    "openingLines": ["静かな朝に局面が始まる。"],
                },
            }
        )
        payload = build_gpt_finalize_character_payload(request)
        self.assertEqual(payload["transition"]["outcome"], "applied")
        self.assertEqual(payload["readModel"]["guidance"]["sessionOpeningGuide"]["headline"], "新しい導入")
        self.assertIn("openingPromptHint", payload["readModel"]["guidance"]["characterGenesis"])
        self.assertIn("openingPackage", payload["readModel"]["guidance"])
        self.assertTrue(payload["readModel"]["guidance"]["openingPackage"]["promptHint"])

    def test_build_play_payload_returns_after_bundle(self) -> None:
        payload = build_play_payload(play_request_from_body({"choiceId": "observe", "seed": 1729, "world_json": None}))
        self.assertIn("bundle", payload)
        self.assertIn("display", payload)
        self.assertIn("transition", payload)
        self.assertTrue(payload["playSource"]["world_json"])
        self.assertIn("shell_snapshot", payload["bundle"])
        self.assertIn("campaign", payload["transition"])

    def test_build_front_play_payload_returns_compact_display(self) -> None:
        payload = build_front_play_payload(play_request_from_body({"choiceId": "observe", "seed": 1729, "world_json": None}))
        self.assertIn("playSource", payload)
        self.assertIn("display", payload)
        self.assertIn("transition", payload)
        self.assertNotIn("bundle", payload)
        self.assertEqual(payload["transition"]["choiceId"], "observe")
        self.assertTrue(payload["playSource"]["world_json"])

    def test_build_gpt_play_payload_returns_compact_state(self) -> None:
        payload = build_gpt_play_payload(play_request_from_body({"choiceId": "observe", "seed": 1729, "world_json": None}))
        self.assertIn("playSource", payload)
        self.assertIn("transition", payload)
        self.assertIn("readModel", payload)
        self.assertNotIn("bundle", payload)
        self.assertNotIn("display", payload)
        self.assertEqual(payload["transition"]["choiceId"], "observe")
        self.assertTrue(payload["playSource"]["world_json"])
        self.assertIn("scene", payload["readModel"])

    def test_gpt_play_request_prefers_world_json_when_both_are_present(self) -> None:
        initial = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        request = play_request_from_body(
            {"choiceId": "observe", "seed": 1729, "world_json": initial["playSource"]["world_json"]},
            prefer_world_json_when_both=True,
        )
        self.assertIsNone(request.seed)
        self.assertIsNotNone(request.world_json)

    def test_ui_static_copy_avoids_internal_labels(self) -> None:
        app_js = Path("star_ring_codex_trpg/read_only_ui/static/app.js").read_text(encoding="utf-8")
        self.assertNotIn('["識別子"', app_js)
        self.assertNotIn("読み込み完了: world_json:", app_js)
        self.assertNotIn("読み込み完了: seed:", app_js)
        self.assertIn("保存した世界の続きから読み込みました。", app_js)
        self.assertIn("セッション記録", app_js)
        self.assertIn("残った因果", app_js)
        self.assertIn("いまの hook への効き方", app_js)
        self.assertIn("セッション記録の絞り込み", app_js)
        self.assertIn("セッションの始まり", app_js)
        self.assertIn("優先の理由", app_js)
        self.assertIn("このセッションの入り口", app_js)
        self.assertIn("進め方の目安", app_js)
        self.assertIn("次の一手の見方", app_js)
        self.assertIn("約定が崩れると", app_js)
        self.assertIn("保存した続きから開きました。まずは「このセッションの入り口」を確認してください。", app_js)
        index_html = Path("star_ring_codex_trpg/read_only_ui/static/index.html").read_text(encoding="utf-8")
        self.assertIn("進め方", index_html)
        self.assertIn("選択肢にない手を試したいときだけ自由行動を使います。", index_html)

    def test_play_api_returns_after_bundle(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/play",
                data=json.dumps({"choiceId": "observe", "seed": 1729, "world_json": None}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("bundle", payload)
            self.assertIn("display", payload)
            self.assertEqual(payload["transition"]["choiceId"], "observe")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_gpt_play_api_returns_compact_state(self) -> None:
        initial = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/gpt/play",
                data=json.dumps(
                    {
                        "choiceId": "observe",
                        "seed": 1729,
                        "world_json": initial["playSource"]["world_json"],
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("playSource", payload)
            self.assertIn("transition", payload)
            self.assertIn("readModel", payload)
            self.assertNotIn("bundle", payload)
            self.assertEqual(payload["transition"]["choiceId"], "observe")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_front_snapshot_api_returns_compact_display(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/front/snapshot?seed=1729") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("display", payload)
            self.assertIn("playSource", payload)
            self.assertNotIn("bundle", payload)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_front_play_api_returns_compact_display(self) -> None:
        initial = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/front/play",
                data=json.dumps(
                    {
                        "choiceId": "observe",
                        "seed": 1729,
                        "world_json": initial["playSource"]["world_json"],
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("playSource", payload)
            self.assertIn("display", payload)
            self.assertIn("transition", payload)
            self.assertNotIn("bundle", payload)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_gpt_free_action_payload_returns_compact_state(self) -> None:
        payload = build_gpt_free_action_payload(
            free_action_request_from_body({"actionText": "夜中に宿の裏から入り、裏帳面を盗み出す", "seed": 1729, "world_json": None})
        )
        self.assertIn("playSource", payload)
        self.assertIn("transition", payload)
        self.assertIn("structuredResult", payload)
        self.assertIn("readModel", payload)
        self.assertNotIn("bundle", payload)
        self.assertNotIn("display", payload)
        self.assertTrue(payload["structuredResult"]["summary"])

    def test_front_free_action_payload_returns_compact_display(self) -> None:
        payload = build_front_free_action_payload(
            free_action_request_from_body({"actionText": "夜中に宿の裏から入り、裏帳面を盗み出す", "seed": 1729, "world_json": None})
        )
        self.assertIn("playSource", payload)
        self.assertIn("display", payload)
        self.assertIn("structuredResult", payload)
        self.assertIn("transition", payload)
        self.assertNotIn("bundle", payload)

    def test_gpt_read_model_api_returns_read_only_surface(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/gpt-read-model?seed=1729") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("readModel", payload)
            self.assertIn("scene", payload["readModel"])
            self.assertIn("guidance", payload["readModel"])
            self.assertIn("memory", payload["readModel"])
            self.assertEqual(payload["readModel"]["contracts"]["truthMutation"], "backend_only")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_gpt_load_session_payload_returns_compact_state(self) -> None:
        initial = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        saved = save_session_state = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            save_request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/save-session",
                data=json.dumps({"world_json": initial["playSource"]["world_json"]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(save_request) as response:
                saved = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)
        self.assertIsNotNone(saved)
        payload = build_gpt_load_session_payload(load_session_request_from_body({"saveId": saved["saveId"]}))
        self.assertIn("playSource", payload)
        self.assertIn("readModel", payload)
        self.assertIn("saveMeta", payload)
        self.assertNotIn("bundle", payload)
        self.assertNotIn("display", payload)

    def test_front_load_session_payload_returns_compact_display(self) -> None:
        initial = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        saved = build_save_session_payload(save_session_request_from_body({"world_json": initial["playSource"]["world_json"]}))
        payload = build_front_load_session_payload(load_session_request_from_body({"saveId": saved["saveId"]}))
        self.assertIn("playSource", payload)
        self.assertIn("display", payload)
        self.assertIn("saveMeta", payload)
        self.assertNotIn("bundle", payload)

    def test_save_and_load_session_api_contracts(self) -> None:
        initial = build_ui_payload(viewer_request_from_query({"seed": ["1729"]}))
        server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            save_request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/save-session",
                data=json.dumps({"world_json": initial["playSource"]["world_json"]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(save_request) as response:
                save_payload = json.loads(response.read().decode("utf-8"))

            load_request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/load-session",
                data=json.dumps({"saveId": save_payload["saveId"]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(load_request) as response:
                load_payload = json.loads(response.read().decode("utf-8"))

            self.assertIn("saveId", save_payload)
            self.assertIn("savePath", save_payload)
            self.assertIn("savedAt", save_payload)
            self.assertIn("sessionSummary", save_payload)
            self.assertIn("bundle", load_payload)
            self.assertIn("display", load_payload)
            self.assertIn("playSource", load_payload)
            self.assertEqual(load_payload["saveMeta"]["saveId"], save_payload["saveId"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def test_next_session_api_returns_archive_and_hook(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "completed_session.json"
            current_world = build_bundle(seed=1729, seasons=10)["world_state"]
            for choice_id in ["observe", "inspect", "speak", "observe", "intervene", "inspect"]:
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
            world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")

            server = ThreadingHTTPServer(("127.0.0.1", 0), ReadOnlyUiHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/next-session",
                    data=json.dumps({"world_json": str(world_json)}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertIn("bundle", payload)
                self.assertIn("display", payload)
                self.assertEqual(payload["sessionArchiveSize"], 1)
                self.assertIn("nextMainEventCandidates", payload["nextSessionHook"])
                self.assertIsNotNone(payload["display"]["archiveInspector"])
                archive = payload["bundle"]["world_state"]["campaign_state"]["sessionArchive"][0]
                for key in ("sessionNumber", "openingSummary", "title", "tone", "keyRoleLabel", "protected", "lost", "carriedForward"):
                    self.assertIn(key, archive)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=1)

    def test_front_next_session_payload_returns_compact_display(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "completed_session.json"
            current_world = build_bundle(seed=1729, seasons=10)["world_state"]
            for choice_id in ["observe", "inspect", "speak", "observe", "intervene", "inspect"]:
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
            world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")

            payload = build_front_next_session_payload(next_session_request_from_body({"world_json": str(world_json)}))
            self.assertIn("playSource", payload)
            self.assertIn("display", payload)
            self.assertIn("nextSessionHook", payload)
            self.assertIn("sessionArchiveSize", payload)
            self.assertNotIn("bundle", payload)

    def test_gpt_next_session_payload_returns_compact_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_json = Path(temp_dir) / "completed_session.json"
            current_world = build_bundle(seed=1729, seasons=10)["world_state"]
            for choice_id in ["observe", "inspect", "speak", "observe", "intervene", "inspect"]:
                world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")
                result = play_choice(choice_id=choice_id, seed=None, world_json=world_json)
                current_world = result["after"]["bundle"]["world_state"]
            world_json.write_text(json.dumps(current_world, ensure_ascii=False, indent=2), encoding="utf-8")

            payload = build_gpt_next_session_payload(next_session_request_from_body({"world_json": str(world_json)}))
            self.assertIn("playSource", payload)
            self.assertIn("readModel", payload)
            self.assertIn("nextSessionHook", payload)
            self.assertIn("sessionArchiveSize", payload)
            self.assertNotIn("bundle", payload)
            self.assertNotIn("display", payload)


if __name__ == "__main__":
    unittest.main()
