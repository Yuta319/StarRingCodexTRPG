from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.naming_dictionary_importer import detect_dictionary_role, import_naming_bundle, import_naming_dictionary


class NamingDictionaryImporterTests(unittest.TestCase):
    def test_detect_core_dictionary(self) -> None:
        payload = {
            "schema_version": "1.0",
            "races": {"human": {}},
            "generation_rules": {"city": "{phoneme}+{city_suffix}"},
        }
        self.assertEqual(detect_dictionary_role(payload), "core")

    def test_detect_external_lexicon(self) -> None:
        payload = {
            "schema_version": "1.0",
            "entries": [],
        }
        self.assertEqual(detect_dictionary_role(payload), "lexicon")

    def test_detect_bundle_index(self) -> None:
        payload = {
            "schema_version": "1.0",
            "files": ["a.json"],
            "recommended_load_order": ["a.json"],
        }
        self.assertEqual(detect_dictionary_role(payload), "bundle_index")

    def test_detect_city_dictionary(self) -> None:
        payload = {
            "schema_version": "1.0",
            "name": "Fantasy_City_Naming_Dictionary",
            "races": {"human": {}},
            "generation_order": ["race", "phoneme_root", "city_suffix"],
        }
        self.assertEqual(detect_dictionary_role(payload), "city_dictionary")

    def test_detect_person_dictionary(self) -> None:
        payload = {
            "schema_version": "1.0",
            "name": "Fantasy_Personal_Name_Dictionary",
            "races": {"human": {}},
            "generation_order": ["race", "phoneme_root", "person_suffix"],
        }
        self.assertEqual(detect_dictionary_role(payload), "personal_name_dictionary")

    def test_detect_equipment_dictionary(self) -> None:
        payload = {
            "schema_version": "1.0",
            "name": "Fantasy_Equipment_Naming_Dictionary",
            "races": {"human": {}},
            "generation_order": ["race", "phoneme_root", "item_suffix"],
        }
        self.assertEqual(detect_dictionary_role(payload), "equipment_dictionary")

    def test_import_core_dictionary_overwrites_core_target_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "incoming_core.json"
            source.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "races": {"human": {}},
                        "generation_rules": {"city": "{phoneme}+{city_suffix}"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result = import_naming_dictionary(source, target_root=root / "target")
            self.assertEqual(result["role"], "core")
            self.assertTrue(Path(result["destination_path"]).name == "Fantasy_Naming_System_Core.json")

    def test_import_lexicon_preserves_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "places.json"
            source.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [{"surface_name": "ベルファスト", "category": "place"}],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            result = import_naming_dictionary(source, target_root=root / "target")
            self.assertEqual(result["role"], "lexicon")
            self.assertEqual(Path(result["destination_path"]).name, "places.json")

    def test_import_bundle_imports_index_and_referenced_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "fantasy_naming_external_dictionary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "races": {"human": {}},
                        "generation_rules": {"city": "{phoneme}+{city_suffix}"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (root / "fantasy_city_naming_dictionary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "Fantasy_City_Naming_Dictionary",
                        "races": {"human": {}},
                        "generation_order": ["race", "phoneme_root", "city_suffix"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            index = root / "fantasy_naming_bundle_index.json"
            index.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "Fantasy_Naming_System_Bundle_Index",
                        "files": [
                            "fantasy_naming_external_dictionary.json",
                            "fantasy_city_naming_dictionary.json",
                        ],
                        "recommended_load_order": [
                            "fantasy_naming_external_dictionary.json",
                            "fantasy_city_naming_dictionary.json",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            payload = import_naming_bundle(index, target_root=root / "target")
            self.assertEqual(payload["imported_count"], 3)
            imported_files = {Path(result["destination_path"]).name for result in payload["results"]}
            self.assertIn("Fantasy_Naming_System_Core.json", imported_files)
            self.assertIn("fantasy_city_naming_dictionary.json", imported_files)
            self.assertIn("fantasy_naming_bundle_index.json", imported_files)


if __name__ == "__main__":
    unittest.main()
