from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.fantasy_naming_generator import NAMING_CORE_PATH
from star_ring_codex_trpg.naming_lexicon_validator import (
    iter_external_lexicon_paths,
    validate_lexicon_collection,
    validate_lexicon_file,
)


class NamingLexiconValidatorTests(unittest.TestCase):
    def _write_core(self, root: Path) -> Path:
        core_copy = root / NAMING_CORE_PATH.name
        core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        return core_copy

    def test_validate_good_lexicon_file_returns_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = self._write_core(root)
            lexicon = root / "good_lexicon.json"
            lexicon.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "GoodLexicon",
                        "entries": [
                            {
                                "surface_name": "ベルファスト",
                                "category": "city",
                                "race": "human",
                                "source_terms": ["環鈴宿"],
                                "semantic_tags": ["王権", "誓約"],
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
            report = validate_lexicon_file(lexicon, core_path=core_copy)
            self.assertTrue(report.ok)
            self.assertEqual(len(report.errors), 0)
            self.assertEqual(len(report.warnings), 0)

    def test_validate_missing_surface_name_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = self._write_core(root)
            lexicon = root / "bad_lexicon.json"
            lexicon.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "BadLexicon",
                        "entries": [{"category": "person", "race": "human"}],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            report = validate_lexicon_file(lexicon, core_path=core_copy)
            self.assertFalse(report.ok)
            self.assertTrue(any(issue.code == "missing-surface-name" for issue in report.errors))

    def test_validate_raw_english_name_returns_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = self._write_core(root)
            lexicon = root / "english_lexicon.json"
            lexicon.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "EnglishLexicon",
                        "entries": [
                            {
                                "surface_name": "White Oath Ring",
                                "category": "item",
                                "race": "human",
                                "item_type": "ring",
                                "source_terms": ["白誓の指輪"],
                                "semantic_tags": ["誓約"],
                                "annotation": "《白い誓いの指輪》",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            report = validate_lexicon_file(lexicon, core_path=core_copy)
            warning_codes = {issue.code for issue in report.warnings}
            self.assertIn("raw-ascii-name", warning_codes)
            self.assertIn("raw-english-name", warning_codes)

    def test_validate_duplicate_entry_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = self._write_core(root)
            lexicon = root / "duplicate_lexicon.json"
            lexicon.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "DuplicateLexicon",
                        "entries": [
                            {
                                "surface_name": "セルカ",
                                "category": "person",
                                "race": "human",
                                "source_terms": ["停戦執行官セルカ"],
                                "semantic_tags": ["騎士"],
                                "annotation": "《停戦守》",
                            },
                            {
                                "surface_name": "セルカ",
                                "category": "person",
                                "race": "human",
                                "source_terms": ["停戦執行官セルカ"],
                                "semantic_tags": ["騎士"],
                                "annotation": "《街門の守り手》",
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            report = validate_lexicon_file(lexicon, core_path=core_copy)
            self.assertTrue(any(issue.code == "duplicate-entry" for issue in report.errors))

    def test_validate_equipment_category_is_accepted_via_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_copy = self._write_core(root)
            lexicon = root / "equipment_lexicon.json"
            lexicon.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "EquipmentLexicon",
                        "entries": [
                            {
                                "surface_name": "白誓の指輪",
                                "category": "equipment",
                                "race": "human",
                                "item_type": "ring",
                                "source_terms": ["白誓の指輪"],
                                "semantic_tags": ["誓約"],
                                "annotation": "《白い誓い》",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            report = validate_lexicon_file(lexicon, core_path=core_copy)
            self.assertTrue(report.ok)

    def test_validate_collection_ignores_core_and_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_core(root)
            (root / "External_Naming_Lexicon.template.json").write_text(
                json.dumps({"schema_version": "1.0", "entries": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (root / "usable.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "UsableLexicon",
                        "entries": [
                            {
                                "surface_name": "ベルファスト",
                                "category": "city",
                                "race": "human",
                                "source_terms": ["環鈴宿"],
                                "semantic_tags": ["王権"],
                                "annotation": "《平和の壁の街》",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            paths = iter_external_lexicon_paths(root)
            self.assertEqual([path.name for path in paths], ["usable.json"])

            payload = validate_lexicon_collection(root=root)
            self.assertEqual(payload["file_count"], 1)
            self.assertEqual(payload["error_count"], 0)

    def test_validate_collection_ignores_specialized_bundle_components_without_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_core(root)
            (root / "fantasy_city_naming_dictionary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "name": "Fantasy_City_Naming_Dictionary",
                        "races": {"human": {"roots": ["bel"], "suffixes": {"city": ["gard"]}}},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            payload = validate_lexicon_collection(root=root)
            self.assertEqual(payload["file_count"], 0)

    def test_validate_collection_ignores_ui_only_lexicon_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / NAMING_CORE_PATH.name).write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "ui_only_display_names.json").write_text(
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
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            payload = validate_lexicon_collection(root=root)
            self.assertEqual(payload["file_count"], 0)


if __name__ == "__main__":
    unittest.main()
