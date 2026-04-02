from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from .fantasy_naming_generator import NAMING_CORE_PATH, USER_NAMING_ROOT


CORE_ROLE = "core"
LEXICON_ROLE = "lexicon"
BUNDLE_INDEX_ROLE = "bundle_index"
CITY_ROLE = "city_dictionary"
PERSON_ROLE = "personal_name_dictionary"
EQUIPMENT_ROLE = "equipment_dictionary"
CODEX_REFERENCE_ROLE = "codex_reference"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("dictionary file must contain a JSON object")
    return payload


def detect_dictionary_role(payload: dict[str, Any]) -> str:
    name = str(payload.get("name") or "")

    if (
        name == "Fantasy_City_Naming_Dictionary"
        and isinstance(payload.get("races"), dict)
        and isinstance(payload.get("generation_order"), list)
    ):
        return CITY_ROLE
    if (
        name == "Fantasy_Personal_Name_Dictionary"
        and isinstance(payload.get("races"), dict)
        and isinstance(payload.get("generation_order"), list)
    ):
        return PERSON_ROLE
    if (
        name == "Fantasy_Equipment_Naming_Dictionary"
        and isinstance(payload.get("races"), dict)
        and isinstance(payload.get("generation_order"), list)
    ):
        return EQUIPMENT_ROLE
    if isinstance(payload.get("races"), dict) and isinstance(payload.get("generation_rules"), dict):
        return CORE_ROLE
    if isinstance(payload.get("entries"), list):
        return LEXICON_ROLE
    if isinstance(payload.get("recommended_load_order"), list) and isinstance(payload.get("files"), list):
        return BUNDLE_INDEX_ROLE
    if isinstance(payload.get("file_dependencies"), dict):
        return CODEX_REFERENCE_ROLE
    raise ValueError("unsupported dictionary format")


def import_naming_dictionary(source_path: Path, *, target_root: Path | None = None) -> dict[str, str]:
    source = Path(source_path).resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    payload = _load_json(source)
    role = detect_dictionary_role(payload)
    root = (target_root or USER_NAMING_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)

    if role == CORE_ROLE:
        destination = root / NAMING_CORE_PATH.name
    else:
        destination = root / source.name

    shutil.copyfile(source, destination)
    return {
        "role": role,
        "source_path": str(source),
        "destination_path": str(destination),
    }


def import_naming_bundle(index_path: Path, *, target_root: Path | None = None) -> dict[str, Any]:
    index_source = Path(index_path).resolve()
    payload = _load_json(index_source)
    if detect_dictionary_role(payload) != BUNDLE_INDEX_ROLE:
        raise ValueError("bundle index is required")

    results: list[dict[str, str]] = []
    base_dir = index_source.parent
    results.append(import_naming_dictionary(index_source, target_root=target_root))
    for file_name in payload.get("recommended_load_order", []):
        source = (base_dir / str(file_name)).resolve()
        if not source.exists():
            continue
        results.append(import_naming_dictionary(source, target_root=target_root))
    return {
        "bundle_name": str(payload.get("name") or index_source.stem),
        "imported_count": len(results),
        "results": results,
    }
