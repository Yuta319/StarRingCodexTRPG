from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from star_ring_codex_trpg.fantasy_naming_generator import NAMING_CORE_PATH, load_external_lexicon_entries
from star_ring_codex_trpg.naming_lexicon_compiler import compile_external_lexicons


class NamingLexiconCompilerTests(unittest.TestCase):
    def tearDown(self) -> None:
        load_external_lexicon_entries.cache_clear()

    def _write_core(self, root: Path) -> Path:
        core_copy = root / NAMING_CORE_PATH.name
        core_copy.write_text(NAMING_CORE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        return core_copy

    def test_compile_collects_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_core(root)
            (root / "city_lexicon.json").write_text(
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
                                "source_label": "city_dictionary",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            payload = compile_external_lexicons(root=root)
            self.assertEqual(payload["entry_count"], 1)
            self.assertEqual(payload["entries"][0]["surface_name"], "ベルファスト")

    def test_compile_resolves_duplicates_by_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_core(root)
            (root / "first.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "セルカ",
                                "category": "person",
                                "race": "human",
                                "source_terms": ["停戦執行官セルカ"],
                                "semantic_tags": ["騎士"],
                                "annotation": "《停戦守》",
                                "priority": 10,
                                "source_label": "low_priority",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (root / "second.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [
                            {
                                "surface_name": "セルカ",
                                "category": "person",
                                "race": "human",
                                "source_terms": ["停戦執行官セルカ"],
                                "semantic_tags": ["騎士"],
                                "annotation": "《停戦執行官》",
                                "priority": 100,
                                "source_label": "high_priority",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            payload = compile_external_lexicons(root=root, fail_on_errors=False)
            self.assertEqual(payload["entry_count"], 1)
            self.assertEqual(payload["duplicate_resolution_count"], 1)
            self.assertEqual(payload["entries"][0]["source_label"], "high_priority")

    def test_compile_raises_on_validation_errors_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_core(root)
            (root / "broken.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entries": [{"category": "city"}],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                compile_external_lexicons(root=root)

    def test_compile_ignores_ui_only_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_core(root)
            (root / "ui_only_names.json").write_text(
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
            payload = compile_external_lexicons(root=root)
            self.assertEqual(payload["entry_count"], 0)


if __name__ == "__main__":
    unittest.main()
