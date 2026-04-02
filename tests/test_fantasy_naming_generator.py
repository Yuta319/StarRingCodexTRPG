from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.fantasy_naming_generator import (
    NAMING_CORE_PATH,
    generate_batch,
    generate_name,
    generate_plan_batches,
    load_external_lexicon_entries,
    load_naming_core,
)


class FantasyNamingGeneratorTests(unittest.TestCase):
    def test_core_file_exists_and_loads(self) -> None:
        self.assertTrue(NAMING_CORE_PATH.exists())
        core = load_naming_core()
        self.assertEqual(core["schema_version"], "1.0")
        self.assertIn("human", core["races"])

    def test_generate_city_name_returns_katakana_and_annotation(self) -> None:
        entry = generate_name(race="human", category="city", seed=1729)
        self.assertTrue(entry.surface_name)
        self.assertTrue(entry.annotation.startswith("《"))
        self.assertTrue(entry.annotation.endswith("》"))
        self.assertEqual(entry.category, "city")

    def test_generate_item_name_accepts_item_type_and_semantic_tag(self) -> None:
        entry = generate_name(
            race="elf",
            category="item",
            seed=1729,
            item_type="bow",
            semantic_tags=["月"],
        )
        self.assertEqual(entry.semantic_tags, ["月"])
        self.assertTrue(entry.annotation.startswith("《"))
        self.assertTrue(entry.annotation.endswith("》"))
        self.assertIn("《", entry.full_display)

    def test_generate_place_and_equipment_alias_categories_are_supported(self) -> None:
        place_entry = generate_name(race="human", category="place", seed=1729)
        equipment_entry = generate_name(race="elf", category="equipment", seed=1729, item_type="bow")
        self.assertEqual(place_entry.category, "place")
        self.assertEqual(equipment_entry.category, "item")

    def test_generate_batch_returns_unique_surface_names(self) -> None:
        payload = generate_batch(race="dwarf", category="person", count=5, seed=1729)
        names = [entry["surface_name"] for entry in payload]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(payload), 5)

    def test_generate_batch_filters_repetitive_names(self) -> None:
        payload = generate_batch(race="human", category="person", count=20, seed=1730)
        names = [entry["surface_name"] for entry in payload]
        self.assertNotIn("イオンイオン", names)
        self.assertNotIn("アルドアルド", names)
        self.assertNotIn("レオンイオン", names)

    def test_external_lexicon_entries_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / NAMING_CORE_PATH.name).write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "custom_city_dict.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "ベルファスト",
                                "category": "city",
                                "race": "human",
                                "source_terms": ["環鈴宿"],
                                "semantic_tags": ["王権"],
                                "annotation": "《平和の壁の街》",
                                "priority": 100,
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            entries = load_external_lexicon_entries(root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["surface_name"], "ベルファスト")
            self.assertEqual(entries[0]["source_terms"], ["環鈴宿"])

    def test_generate_name_prefers_external_entry_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = root / NAMING_CORE_PATH.name
            core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "custom_item_dict.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "ルナフェル",
                                "category": "item",
                                "race": "elf",
                                "item_type": "bow",
                                "source_terms": ["月枝の歌弓"],
                                "semantic_tags": ["月"],
                                "annotation": "《月枝の歌》",
                                "priority": 100,
                                "source_label": "user_item_dictionary",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            load_external_lexicon_entries.cache_clear()
            result = generate_name(
                race="elf",
                category="item",
                seed=1729,
                item_type="bow",
                semantic_tags=["月"],
                core_path=core_copy,
            )
            self.assertEqual(result.surface_name, "ルナフェル")
            self.assertEqual(result.origin, "external")
            self.assertEqual(result.annotation, "《月枝の歌》")
            self.assertEqual(result.source_label, "user_item_dictionary")
            load_external_lexicon_entries.cache_clear()

    def test_generate_name_ignores_ui_only_external_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = root / NAMING_CORE_PATH.name
            core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "ui_only_people.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "セルカ",
                                "display_text": "セルカ〈停戦執行官〉",
                                "category": "person",
                                "ui_only": True,
                                "source_terms": ["停戦執行官セルカ"],
                                "annotation": "《停戦執行官》",
                                "priority": 100,
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            load_external_lexicon_entries.cache_clear()
            result = generate_name(race="human", category="person", seed=1729, core_path=core_copy)
            self.assertNotEqual(result.surface_name, "セルカ")
            self.assertEqual(result.origin, "generated")
            load_external_lexicon_entries.cache_clear()

    def test_generate_name_uses_specialized_city_dictionary_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = root / NAMING_CORE_PATH.name
            core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "fantasy_city_naming_dictionary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "Fantasy_City_Naming_Dictionary",
                        "races": {
                            "human": {
                                "roots": ["bel"],
                                "suffixes": {"city": ["gard"], "town": ["ford"]},
                                "annotation_pool": ["白獅子の城塞"],
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result = generate_name(race="human", category="city", seed=1729, core_path=core_copy, prefer_external=False)
            self.assertEqual(result.surface_name, "ベルガルド")
            self.assertEqual(result.annotation, "《白獅子の城塞》")
            self.assertEqual(result.source_file, "fantasy_city_naming_dictionary.json")

    def test_generate_name_uses_specialized_person_dictionary_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = root / NAMING_CORE_PATH.name
            core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "fantasy_personal_name_dictionary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "Fantasy_Personal_Name_Dictionary",
                        "races": {
                            "elf": {
                                "given_roots": ["ele"],
                                "given_suffixes": ["sia"],
                                "titles": ["月歌守"],
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result = generate_name(race="elf", category="person", seed=1729, core_path=core_copy, prefer_external=False)
            self.assertEqual(result.surface_name, "エレシア")
            self.assertEqual(result.annotation, "《月歌守》")
            self.assertEqual(result.source_file, "fantasy_personal_name_dictionary.json")

    def test_generate_name_uses_specialized_equipment_dictionary_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = root / NAMING_CORE_PATH.name
            core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "fantasy_equipment_naming_dictionary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "Fantasy_Equipment_Naming_Dictionary",
                        "races": {
                            "fallen": {
                                "roots": ["ash"],
                                "suffixes": ["fel"],
                                "annotations": ["断翼"],
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result = generate_name(race="fallen", category="item", seed=1729, item_type="sword", core_path=core_copy, prefer_external=False)
            self.assertEqual(result.surface_name, "アッシュフェル")
            self.assertEqual(result.annotation, "《断翼》")
            self.assertEqual(result.source_file, "fantasy_equipment_naming_dictionary.json")

    def test_generate_plan_batches_returns_grouped_payload(self) -> None:
        plan = {
            "schema_version": "1.0",
            "name": "test_plan",
            "seed": 1729,
            "batches": [
                {"label": "human_cities", "race": "human", "category": "city", "count": 2},
                {"label": "elf_people", "race": "elf", "category": "person", "count": 2},
            ],
        }
        payload = generate_plan_batches(plan)
        self.assertEqual(payload["plan_name"], "test_plan")
        self.assertEqual(payload["batch_count"], 2)
        self.assertEqual(len(payload["batches"][0]["entries"]), 2)
        self.assertEqual(payload["batches"][0]["label"], "human_cities")


if __name__ == "__main__":
    unittest.main()
