from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import copy

from .fantasy_naming_generator import USER_NAMING_ROOT, load_external_lexicon_entries


@lru_cache(maxsize=8)
def _external_replacements(root: Path) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for entry in load_external_lexicon_entries(root):
        replacement_text = str(entry.get("display_text") or entry.get("surface_name") or "").strip()
        for source_term in entry.get("source_terms", []):
            source_text = str(source_term or "").strip()
            if source_text and replacement_text and source_text not in replacements:
                replacements[source_text] = replacement_text
    return replacements


def _person_display_label(display_name: str, role_label: str) -> str:
    name = str(display_name or "").strip()
    role = str(role_label or "").strip()
    if not name or not role:
        return name
    if name.startswith(role):
        bare_name = name[len(role) :].strip()
        if bare_name:
            return f"{bare_name}〈{role}〉"
    return name


def _replacement_map(display: dict[str, Any], naming_root: Path) -> dict[str, str]:
    replacements = dict(_external_replacements(naming_root))
    for npc in display.get("namedCast", []):
        display_name = str(npc.get("displayName") or "").strip()
        role_label = str(npc.get("roleLabel") or npc.get("role") or "").strip()
        if display_name and role_label and display_name not in replacements:
            replacements[display_name] = _person_display_label(display_name, role_label)
    return replacements


def _replace_text(text: str, replacements: dict[str, str]) -> str:
    updated = str(text)
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if old and old in updated:
            updated = updated.replace(old, new)
    return updated


def _walk(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        return _replace_text(value, replacements)
    if isinstance(value, list):
        return [_walk(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _walk(item, replacements) for key, item in value.items()}
    return value


def apply_fantasy_display_naming(
    display: dict[str, Any],
    *,
    naming_root: Path | None = None,
) -> dict[str, Any]:
    root = naming_root or USER_NAMING_ROOT
    replacements = _replacement_map(display, root)
    return _walk(copy.deepcopy(display), replacements)
