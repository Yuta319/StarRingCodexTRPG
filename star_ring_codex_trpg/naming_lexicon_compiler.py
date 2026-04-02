from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .fantasy_naming_generator import USER_NAMING_ROOT, load_external_lexicon_entries
from .naming_lexicon_validator import validate_lexicon_collection


def _entry_sort_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -int(entry.get("priority") or 0),
        str(entry.get("surface_name") or ""),
        str(entry.get("source_file") or ""),
        str(entry.get("source_label") or ""),
    )


def _dedupe_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("surface_name") or ""),
        str(entry.get("category") or ""),
        str(entry.get("race") or ""),
        str(entry.get("item_type") or ""),
    )


def compile_external_lexicons(
    *,
    root: Path | None = None,
    fail_on_errors: bool = True,
) -> dict[str, Any]:
    target_root = root or USER_NAMING_ROOT
    validation = validate_lexicon_collection(root=target_root)
    if fail_on_errors and validation["error_count"] > 0:
        raise ValueError("validation errors exist in external naming lexicons")

    raw_entries = list(load_external_lexicon_entries(target_root, include_ui_only=False))
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in raw_entries:
        grouped[_dedupe_key(entry)].append(dict(entry))

    compiled_entries: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    for key, candidates in sorted(grouped.items(), key=lambda item: item[0]):
        ranked = sorted(candidates, key=_entry_sort_key)
        kept = dict(ranked[0])
        compiled_entries.append(kept)
        if len(ranked) > 1:
            resolutions.append(
                {
                    "surface_name": key[0],
                    "category": key[1],
                    "race": key[2],
                    "item_type": key[3],
                    "kept_source_file": kept.get("source_file", ""),
                    "kept_source_label": kept.get("source_label", ""),
                    "discarded": [
                        {
                            "source_file": candidate.get("source_file", ""),
                            "source_label": candidate.get("source_label", ""),
                            "priority": int(candidate.get("priority") or 0),
                        }
                        for candidate in ranked[1:]
                    ],
                }
            )

    compiled_entries.sort(
        key=lambda entry: (
            str(entry.get("category") or ""),
            str(entry.get("race") or ""),
            str(entry.get("item_type") or ""),
            str(entry.get("surface_name") or ""),
        )
    )

    return {
        "schema_version": "1.0",
        "name": "Compiled_External_Naming_Lexicon",
        "source_root": str(target_root),
        "validation_summary": {
            "file_count": validation["file_count"],
            "error_count": validation["error_count"],
            "warning_count": validation["warning_count"],
            "ok": validation["ok"],
        },
        "entry_count": len(compiled_entries),
        "duplicate_resolution_count": len(resolutions),
        "duplicate_resolutions": resolutions,
        "entries": compiled_entries,
    }
