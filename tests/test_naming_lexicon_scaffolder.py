from __future__ import annotations

import unittest

from star_ring_codex_trpg.naming_lexicon_scaffolder import (
    build_initial_ui_naming_lexicon,
    scaffold_external_lexicon_from_canonical_sources,
)


class NamingLexiconScaffolderTests(unittest.TestCase):
    def test_scaffold_creates_person_display_text_and_preserves_source_terms(self) -> None:
        payload = {
            "seed": 1729,
            "seasons": 10,
            "archetype": "balanced",
            "groups": {
                "person": [
                    {
                        "label": "停戦執行官セルカ",
                        "source_terms": ["停戦執行官セルカ"],
                        "role_label": "停戦執行官",
                        "note": "街道を止めたくない。",
                    }
                ],
                "place": [],
                "equipment": [],
                "item": [],
            },
        }

        draft = scaffold_external_lexicon_from_canonical_sources(payload)
        entry = draft["entries"][0]
        self.assertEqual(entry["surface_name"], "セルカ")
        self.assertEqual(entry["display_text"], "セルカ〈停戦執行官〉")
        self.assertEqual(entry["source_terms"], ["停戦執行官セルカ"])
        self.assertEqual(entry["annotation"], "《停戦執行官》")

    def test_scaffold_creates_item_annotations_from_group(self) -> None:
        payload = {
            "seed": 1729,
            "seasons": 10,
            "archetype": "balanced",
            "groups": {
                "person": [],
                "place": [],
                "equipment": [],
                "item": [
                    {
                        "label": "塩見の小瓶",
                        "source_terms": ["塩見の小瓶"],
                        "group": "消耗品",
                        "description": "札と印泥の筋を見分ける。",
                    }
                ],
            },
        }

        draft = scaffold_external_lexicon_from_canonical_sources(payload)
        entry = draft["entries"][0]
        self.assertEqual(entry["annotation"], "《消耗品》")
        self.assertEqual(entry["display_text"], "塩見の小瓶")

    def test_initial_ui_lexicon_applies_place_overrides(self) -> None:
        payload = {
            "seed": 1729,
            "seasons": 10,
            "archetype": "balanced",
            "groups": {
                "place": [
                    {
                        "label": "環鈴宿（カンレイ）",
                        "source_terms": ["環鈴宿（カンレイ）"],
                        "subtype": "hub",
                        "description": "街道が交差する宿場。",
                    }
                ],
                "person": [],
                "equipment": [],
                "item": [],
            },
        }

        lexicon = build_initial_ui_naming_lexicon(payload)
        entry = lexicon["entries"][0]
        self.assertEqual(entry["surface_name"], "セルミアの宿場")
        self.assertEqual(entry["display_text"], "セルミアの宿場")
        self.assertEqual(entry["annotation"], "《街道の宿場》")
        self.assertTrue(entry["ui_only"])

    def test_initial_ui_lexicon_applies_event_and_institution_overrides(self) -> None:
        payload = {
            "seed": 1729,
            "seasons": 10,
            "archetype": "balanced",
            "groups": {
                "place": [],
                "person": [],
                "event": [
                    {
                        "label": "賠償履行争議",
                        "source_terms": ["賠償履行争議"],
                        "subtype": "active_node",
                        "stakes": "責任の押し付け合いが続く。",
                    },
                    {
                        "label": "捕虜交換破綻への介入",
                        "source_terms": ["捕虜交換破綻への介入"],
                        "subtype": "quest_offer",
                        "parent_event": "捕虜交換破綻",
                    }
                ],
                "faction": [],
                "institution": [
                    {
                        "label": "白祠宗務会＝瘴冠魔域封鎖令",
                        "source_terms": ["白祠宗務会＝瘴冠魔域封鎖令"],
                        "institution_kind": "blockade",
                        "status": "broken",
                    }
                ],
                "equipment": [],
                "item": [],
            },
        }

        lexicon = build_initial_ui_naming_lexicon(payload)
        event_entries = [entry for entry in lexicon["entries"] if entry["category"] == "event"]
        event_entry = next(entry for entry in event_entries if "賠償履行争議" in entry["source_terms"])
        quest_entry = next(entry for entry in event_entries if "捕虜交換破綻への介入" in entry["source_terms"])
        institution_entry = next(entry for entry in lexicon["entries"] if entry["category"] == "institution")

        self.assertEqual(event_entry["display_text"], "賠償争議")
        self.assertEqual(event_entry["annotation"], "《局面》")
        self.assertEqual(quest_entry["display_text"], "捕虜交換の決裂への対処")
        self.assertEqual(quest_entry["annotation"], "《依頼》")
        self.assertEqual(institution_entry["display_text"], "白祠教会による瘴冠領封鎖令")
        self.assertEqual(institution_entry["annotation"], "《制度》")


if __name__ == "__main__":
    unittest.main()
