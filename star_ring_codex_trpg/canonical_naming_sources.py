from __future__ import annotations

from pathlib import Path
from typing import Any

from .assets import load_canonical_assets
from .campaign_content import DUNGEON_BLUEPRINTS, EVENT_BLUEPRINTS_RAW, HUB_BLUEPRINTS, ROLE_SLOT_BLUEPRINTS
from .read_only_ui.controller import _raw_display_from_bundle
from .runner import build_bundle


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    ordered: list[dict[str, Any]] = []
    for entry in entries:
        source_terms = tuple(entry.get("source_terms", []))
        key = (str(entry.get("category") or ""), str(entry.get("label") or ""), source_terms)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(entry)
    return ordered


def _entry(category: str, label: str, source_terms: list[str], **extra: Any) -> dict[str, Any]:
    payload = {
        "category": category,
        "label": label,
        "source_terms": [term for term in source_terms if str(term or "").strip()],
    }
    payload.update(extra)
    return payload


def export_canonical_naming_sources(
    *,
    seed: int = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
) -> dict[str, Any]:
    bundle = build_bundle(
        seed=seed,
        seasons=seasons,
        archetype=archetype,
        world_json=None,
    )
    display = _raw_display_from_bundle(bundle)
    resolved_world = bundle["world_state"].get("resolved_world", {})

    place_entries: list[dict[str, Any]] = []
    for hub in HUB_BLUEPRINTS:
        place_entries.append(
            _entry(
                "place",
                hub["label"],
                [hub["label"]],
                subtype="hub",
                description=hub["description"],
            )
        )
    for dungeon in DUNGEON_BLUEPRINTS:
        place_entries.append(
            _entry(
                "place",
                dungeon["label"],
                [dungeon["label"]],
                subtype="dungeon",
                description=dungeon["description"],
            )
        )

    dynamic_place_terms = {
        str(display.get("scenePacket", {}).get("locationLabel") or "").strip(),
    }
    for region in (resolved_world.get("regions") or {}).values():
        label = str(region.get("label_ja") or "").strip()
        if not label or label in dynamic_place_terms:
            continue
        dynamic_place_terms.add(label)
        place_entries.append(
            _entry(
                "place",
                label,
                [label],
                subtype="region",
                description="地方・辺境・州などの広域地名。",
            )
        )
    for label in sorted(term for term in dynamic_place_terms if term):
        if any(entry["label"] == label for entry in place_entries):
            continue
        place_entries.append(
            _entry(
                "place",
                label,
                [label],
                subtype="region",
                description="現在の局面で表示されている地域名。",
            )
        )

    person_entries: list[dict[str, Any]] = []
    for role in ROLE_SLOT_BLUEPRINTS:
        for occupant in role.get("occupantTemplates", []):
            person_entries.append(
                _entry(
                    "person",
                    occupant["displayName"],
                    [occupant["displayName"]],
                    role_label=role["roleLabel"],
                    note=role["conflictDetail"],
                )
            )

    event_entries: list[dict[str, Any]] = []
    for event in EVENT_BLUEPRINTS_RAW:
        event_entries.append(
            _entry(
                "event",
                event["label"],
                [event["label"]],
                stakes=str(event.get("stakes") or ""),
            )
        )
        for branch in event.get("branches", []):
            event_entries.append(
                _entry(
                    "event",
                    branch["label"],
                    [branch["label"]],
                    parent_event=event["label"],
                )
            )
    current_event_label = str(display.get("currentEvent", {}).get("label") or "").strip()
    if current_event_label:
        event_entries.append(
            _entry(
                "event",
                current_event_label,
                [current_event_label],
                subtype="scene_event",
                stakes=str(display.get("currentEvent", {}).get("stakes") or ""),
            )
        )
    active_node_title = str(display.get("activeNode", {}).get("title") or "").strip()
    if active_node_title:
        event_entries.append(
            _entry(
                "event",
                active_node_title,
                [active_node_title],
                subtype="active_node",
                stakes=str(display.get("currentEvent", {}).get("summary") or ""),
            )
        )
    for node in (resolved_world.get("active_nodes") or {}).values():
        title = str(node.get("title") or "").strip()
        if title:
            event_entries.append(
                _entry(
                    "event",
                    title,
                    [title],
                    subtype="historical_node",
                    stakes=str(node.get("description") or ""),
                )
            )
        for quest in node.get("quest_offers", []):
            quest_title = str(quest.get("title") or "").strip()
            if not quest_title:
                continue
            event_entries.append(
                _entry(
                    "event",
                    quest_title,
                    [quest_title],
                    subtype="quest_offer",
                    parent_event=title,
                )
            )

    faction_entries: list[dict[str, Any]] = []
    for faction in (resolved_world.get("factions") or {}).values():
        label = str(faction.get("label_ja") or "").strip()
        if not label:
            continue
        faction_entries.append(
            _entry(
                "faction",
                label,
                [label],
                faction_type=str(faction.get("faction_type") or ""),
                dominant_race=str(faction.get("dominant_race") or ""),
            )
        )

    institution_entries: list[dict[str, Any]] = []
    for institution in (resolved_world.get("institutions") or {}).values():
        label = str(institution.get("label_ja") or "").strip()
        if not label:
            continue
        institution_entries.append(
            _entry(
                "institution",
                label,
                [label],
                institution_kind=str(institution.get("institution_kind") or ""),
                status=str(institution.get("status") or ""),
            )
        )

    equipment_entries: list[dict[str, Any]] = []
    for item in display["equipmentHub"]["slots"]:
        equipment_entries.append(
            _entry(
                "equipment",
                item["name"],
                [item["name"]],
                slot=item["slotLabel"],
                subtitle=item["subtitle"],
            )
        )
    for item in display["equipmentHub"]["relics"]:
        equipment_entries.append(
            _entry(
                "equipment",
                item["name"],
                [item["name"]],
                subtype="relic",
                subtitle=item["subtitle"],
            )
        )

    item_entries: list[dict[str, Any]] = []
    for group in display["inventoryHub"]["groups"]:
        for item in group["items"]:
            item_entries.append(
                _entry(
                    "item",
                    item["name"],
                    [item["name"]],
                    group=group["label"],
                    description=item["description"],
                )
            )
    for spell in display["equipmentHub"]["attunedSpells"]:
        item_entries.append(
            _entry(
                "item",
                spell["name"],
                [spell["name"]],
                subtype="spell",
                description=spell["description"],
            )
        )

    groups = {
        "place": _dedupe_entries(sorted(place_entries, key=lambda entry: entry["label"])),
        "person": _dedupe_entries(sorted(person_entries, key=lambda entry: entry["label"])),
        "event": _dedupe_entries(sorted(event_entries, key=lambda entry: (entry["label"], entry.get("parent_event", "")))),
        "faction": _dedupe_entries(sorted(faction_entries, key=lambda entry: entry["label"])),
        "institution": _dedupe_entries(sorted(institution_entries, key=lambda entry: entry["label"])),
        "equipment": _dedupe_entries(sorted(equipment_entries, key=lambda entry: entry["label"])),
        "item": _dedupe_entries(sorted(item_entries, key=lambda entry: entry["label"])),
    }
    return {
        "schema_version": "1.0",
        "name": "Canonical_Naming_Sources",
        "seed": seed,
        "seasons": seasons,
        "archetype": archetype,
        "counts": {key: len(value) for key, value in groups.items()},
        "groups": groups,
    }
