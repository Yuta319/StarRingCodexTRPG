from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping
import copy
import re


STAT_CAP_RULES = [
    ("攻撃", "starterAttackCap"),
    ("防御", "starterDefenseCap"),
    ("物理", "starterDefenseCap"),
    ("精神", "starterDefenseCap"),
    ("信仰補正", "starterSupportCap"),
    ("詠唱補助", "starterSupportCap"),
    ("手順補正", "starterSupportCap"),
    ("発見力", "starterSupportCap"),
    ("耐候", "starterSupportCap"),
    ("静歩", "starterSupportCap"),
    ("機動", "starterSupportCap"),
    ("器用", "starterSupportCap"),
]


def _safe_text(value: object, limit: int) -> str:
    text = str(value or "").replace("\r", "\n")
    text = "\n".join(part.strip() for part in text.split("\n"))
    text = "\n".join(part for part in text.split("\n") if part)
    return text[:limit].strip()


def _safe_lines(values: object, *, max_count: int, max_len: int) -> list[str]:
    if not isinstance(values, list):
        return []
    lines: list[str] = []
    for raw in values[:max_count]:
        text = _safe_text(raw, max_len)
        if text:
            lines.append(text)
    return lines


def _safe_variants(values: object) -> list[Dict[str, str]]:
    if not isinstance(values, list):
        return []
    variants: list[Dict[str, str]] = []
    for raw in values[:4]:
        if not isinstance(raw, Mapping):
            continue
        label = _safe_text(raw.get("label"), 24)
        summary = _safe_text(raw.get("summary"), 140)
        if label and summary:
            variants.append({"label": label, "summary": summary})
    return variants


def _clamp_stat_text(text: str, constraints: Mapping[str, Any]) -> str:
    current = text
    for keyword, cap_key in STAT_CAP_RULES:
        if keyword not in current:
            continue
        cap = int(constraints.get(cap_key, 0) or 0)
        if cap <= 0:
            continue

        def _replace(match: re.Match[str]) -> str:
            return str(min(int(match.group(0)), cap))

        current = re.sub(r"\d+", _replace, current)
        return current
    return current


def _merge_boon_seed(existing: Mapping[str, Any], proposal: Mapping[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(dict(existing))
    visible = proposal.get("visibleBoon")
    dormant = proposal.get("dormantGrace")
    if isinstance(visible, Mapping):
        label = _safe_text(visible.get("label"), 32)
        summary = _safe_text(visible.get("summary"), 140)
        if label:
            merged["visibleBoon"] = {
                "label": label,
                "summary": summary or merged.get("visibleBoon", {}).get("summary", ""),
                "kind": "恩恵",
            }
    if isinstance(dormant, Mapping):
        label = _safe_text(dormant.get("label"), 32)
        summary = _safe_text(dormant.get("summary"), 140)
        if label:
            merged["dormantGrace"] = {
                "label": label,
                "summary": summary or merged.get("dormantGrace", {}).get("summary", ""),
                "kind": "恩寵",
            }
    return merged


def _sanitize_loadout(
    equipment_hub: Mapping[str, Any],
    proposal: Mapping[str, Any],
    constraints: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    slot_lookup = {
        str(item.get("slotId") or "").strip(): item
        for item in (equipment_hub.get("slots") or [])
        if str(item.get("slotId") or "").strip()
    }
    raw_items = proposal.get("starterLoadout") or proposal.get("equipment") or []
    if not isinstance(raw_items, list):
        return {}
    max_items = int(constraints.get("starterLoadoutPieces", 6) or 6)
    overrides: Dict[str, Dict[str, Any]] = {}
    for raw in raw_items[:max_items]:
        if not isinstance(raw, Mapping):
            continue
        slot_id = str(raw.get("slotId") or "").strip()
        if slot_id not in slot_lookup:
            continue
        current = slot_lookup[slot_id]
        entry: Dict[str, Any] = {}
        name = _safe_text(raw.get("name"), 40)
        subtitle = _safe_text(raw.get("subtitle"), 32)
        rarity_label = _safe_text(raw.get("rarityLabel"), 20)
        flavor_text = _safe_text(raw.get("flavorText"), 180)
        stats = _safe_lines(raw.get("stats"), max_count=4, max_len=32)
        stats = [_clamp_stat_text(line, constraints) for line in stats]
        if name:
            entry["name"] = name
        if subtitle:
            entry["subtitle"] = subtitle
        if rarity_label:
            entry["rarityLabel"] = rarity_label
        if flavor_text:
            entry["flavorText"] = flavor_text
        if stats:
            entry["stats"] = stats
        if entry:
            entry["slotLabel"] = current.get("slotLabel")
            overrides[slot_id] = entry
    return overrides


def sanitize_character_genesis(
    *,
    character_profile: Mapping[str, Any],
    equipment_hub: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> Dict[str, Any]:
    constraints = dict(character_profile.get("generationConstraints") or {})
    sanitized: Dict[str, Any] = {}

    custom_headline = _safe_text(proposal.get("openingHeadline"), 40)
    custom_lines = _safe_lines(proposal.get("openingLines"), max_count=4, max_len=140)
    opening_variants = _safe_variants(proposal.get("openingVariants"))
    selected_opening_variant_label = _safe_text(proposal.get("selectedOpeningVariantLabel"), 24)
    opening_prompt_hint = _safe_text(proposal.get("openingPromptHint"), 520)
    loadout_name = _safe_text(proposal.get("loadoutName"), 32)
    flavor_notes = _safe_lines(proposal.get("flavorNotes"), max_count=3, max_len=140)

    if custom_headline:
        sanitized["customOpeningHeadline"] = custom_headline
    if custom_lines:
        sanitized["customOpeningLines"] = custom_lines
    if opening_variants:
        sanitized["openingVariants"] = opening_variants
    if selected_opening_variant_label:
        sanitized["selectedOpeningVariantLabel"] = selected_opening_variant_label
    if opening_prompt_hint:
        sanitized["openingPromptHint"] = opening_prompt_hint
    if loadout_name:
        sanitized["loadoutNameOverride"] = loadout_name
    if flavor_notes:
        sanitized["starterFlavorNotes"] = flavor_notes

    starter_loadout = _sanitize_loadout(equipment_hub, proposal, constraints)
    if starter_loadout:
        sanitized["starterEquipmentOverrides"] = starter_loadout

    raw_boon_seed = proposal.get("starterBoonSeed") or {}
    if isinstance(raw_boon_seed, Mapping):
        merged_boon_seed = _merge_boon_seed(character_profile.get("starterBoonSeed") or {}, raw_boon_seed)
        if merged_boon_seed:
            sanitized["starterBoonSeed"] = merged_boon_seed

    if sanitized:
        sanitized["genesisApplied"] = True
    return sanitized


def apply_character_genesis(
    world_state: Dict[str, Any],
    *,
    equipment_hub: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    patched = copy.deepcopy(world_state)
    protagonist = patched.get("resolved_world", {}).get("protagonist", {})
    profile = copy.deepcopy(protagonist.get("character_profile") or {})
    applied = sanitize_character_genesis(
        character_profile=profile,
        equipment_hub=equipment_hub,
        proposal=proposal,
    )
    if applied:
        profile.update(applied)
        protagonist["character_profile"] = profile
    return patched, applied
