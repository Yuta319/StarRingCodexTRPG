from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.display_naming import apply_fantasy_display_naming
from star_ring_codex_trpg.fantasy_naming_generator import load_external_lexicon_entries


class DisplayNamingTests(unittest.TestCase):
    def tearDown(self) -> None:
        load_external_lexicon_entries.cache_clear()

    def test_named_cast_is_reformatted_to_name_plus_role(self) -> None:
        display = {
            "namedCast": [
                {
                    "displayName": "停戦執行官セルカ",
                    "roleLabel": "停戦執行官",
                }
            ],
            "currentEvent": {"label": "停戦執行官セルカが列を止めている"},
        }
        updated = apply_fantasy_display_naming(display)
        self.assertEqual(updated["namedCast"][0]["displayName"], "セルカ〈停戦執行官〉")
        self.assertIn("セルカ〈停戦執行官〉", updated["currentEvent"]["label"])

    def test_external_source_terms_override_display_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "display_aliases.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "ベルファスト",
                                "category": "city",
                                "source_terms": ["環鈴宿", "環鈴宿（カンレイ）"],
                                "annotation": "《平和の壁の街》",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            display = {
                "namedCast": [],
                "sceneTitle": "環鈴宿（カンレイ）",
                "currentEvent": {"label": "環鈴宿の広場で騒ぎが起きている"},
            }
            updated = apply_fantasy_display_naming(display, naming_root=root)
            self.assertEqual(updated["sceneTitle"], "ベルファスト")
            self.assertIn("ベルファスト", updated["currentEvent"]["label"])

    def test_external_display_text_is_used_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "display_aliases.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "セルカ",
                                "display_text": "セルカ〈停戦執行官〉",
                                "category": "person",
                                "source_terms": ["停戦執行官セルカ"],
                                "annotation": "《停戦執行官》",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            display = {
                "namedCast": [],
                "currentEvent": {"label": "停戦執行官セルカが列を止めている"},
            }
            updated = apply_fantasy_display_naming(display, naming_root=root)
            self.assertIn("セルカ〈停戦執行官〉", updated["currentEvent"]["label"])

    def test_external_event_and_faction_terms_replace_globally(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "display_aliases.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "賠償争議",
                                "category": "event",
                                "source_terms": ["賠償履行争議"],
                                "annotation": "《局面》",
                            },
                            {
                                "surface_name": "白祠教会",
                                "category": "faction",
                                "source_terms": ["白祠宗務会"],
                                "annotation": "《勢力》",
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            display = {
                "namedCast": [],
                "sceneTitle": "賠償履行争議",
                "summary": "白祠宗務会が賠償履行争議の責任を押し付けている",
            }
            updated = apply_fantasy_display_naming(display, naming_root=root)
            self.assertEqual(updated["sceneTitle"], "賠償争議")
            self.assertIn("白祠教会", updated["summary"])
            self.assertIn("賠償争議", updated["summary"])


if __name__ == "__main__":
    unittest.main()
