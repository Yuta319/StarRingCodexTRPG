from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping
import copy

from .campaign_content import (
    DUNGEON_BLUEPRINTS,
    EVENT_BLUEPRINTS,
    EVENT_ORDER,
    HUB_BLUEPRINTS,
    PHASE_EVENT_GROUPS,
    ROLE_SLOT_BLUEPRINTS,
)


def _stable_text_weight(value: object) -> int:
    raw = str(value or "")
    total = 0
    for index, char in enumerate(raw):
        total += (index + 1) * ord(char)
    return total


def _profile_entropy(profile: Mapping[str, Any]) -> int:
    fields = (
        profile.get("name"),
        profile.get("race"),
        profile.get("style"),
        profile.get("temperament"),
        profile.get("origin"),
        profile.get("loadout"),
        profile.get("sourceMode"),
        profile.get("sourceTitle"),
        profile.get("sourceName"),
        profile.get("appearanceNotes"),
        profile.get("reinterpretationNotes"),
    )
    return sum((index + 3) * _stable_text_weight(value) for index, value in enumerate(fields))


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    rows: List[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


HUB_BIAS_BY_ORIGIN: Dict[str, Dict[str, int]] = {
    "ford": {"hub_tide_wharf": 5, "hub_kanrei": 2},
    "shrine": {"hub_kanrei": 5, "hub_tide_wharf": 1},
    "mine": {"hub_ember_checkpoint": 5, "hub_kanrei": 1},
    "road": {"hub_kanrei": 4, "hub_ember_checkpoint": 3},
    "marsh": {"hub_tide_wharf": 5},
    "court": {"hub_kanrei": 5},
    "harbor": {"hub_tide_wharf": 5, "hub_kanrei": 1},
    "caravan": {"hub_kanrei": 3, "hub_ember_checkpoint": 3},
    "cloister": {"hub_kanrei": 5},
    "frontier": {"hub_ember_checkpoint": 5},
}

HUB_BIAS_BY_STYLE: Dict[str, Dict[str, int]] = {
    "vanguard": {"hub_ember_checkpoint": 4},
    "envoy": {"hub_kanrei": 4},
    "seeker": {"hub_kanrei": 2, "hub_tide_wharf": 1},
    "shadow": {"hub_tide_wharf": 3},
    "warden": {"hub_ember_checkpoint": 3, "hub_kanrei": 2},
}

HUB_BIAS_BY_LOADOUT: Dict[str, Dict[str, int]] = {
    "oathblade": {"hub_kanrei": 2},
    "trailbow": {"hub_tide_wharf": 2, "hub_ember_checkpoint": 1},
    "ritescribe": {"hub_kanrei": 2},
    "wardenhammer": {"hub_ember_checkpoint": 2},
    "shadowknife": {"hub_tide_wharf": 2},
    "tailored": {"hub_kanrei": 1, "hub_tide_wharf": 1, "hub_ember_checkpoint": 1},
}

DUNGEON_BIAS_BY_ORIGIN: Dict[str, Dict[str, int]] = {
    "ford": {"dungeon_salt_oracle_crypt": 4, "dungeon_mirror_mire_vault": 2},
    "shrine": {"dungeon_salt_oracle_crypt": 5},
    "mine": {"dungeon_white_ash_tunnel": 5},
    "road": {"dungeon_white_ash_tunnel": 2, "dungeon_mirror_mire_vault": 1},
    "marsh": {"dungeon_mirror_mire_vault": 5},
    "court": {"dungeon_salt_oracle_crypt": 2, "dungeon_white_ash_tunnel": 1},
    "harbor": {"dungeon_mirror_mire_vault": 4, "dungeon_salt_oracle_crypt": 2},
    "caravan": {"dungeon_white_ash_tunnel": 2, "dungeon_mirror_mire_vault": 1},
    "cloister": {"dungeon_salt_oracle_crypt": 4},
    "frontier": {"dungeon_white_ash_tunnel": 4},
}

DUNGEON_BIAS_BY_STYLE: Dict[str, Dict[str, int]] = {
    "vanguard": {"dungeon_white_ash_tunnel": 4},
    "envoy": {"dungeon_salt_oracle_crypt": 2},
    "seeker": {"dungeon_salt_oracle_crypt": 4, "dungeon_mirror_mire_vault": 2},
    "shadow": {"dungeon_mirror_mire_vault": 4},
    "warden": {"dungeon_white_ash_tunnel": 3, "dungeon_salt_oracle_crypt": 1},
}

DUNGEON_BIAS_BY_LOADOUT: Dict[str, Dict[str, int]] = {
    "oathblade": {"dungeon_white_ash_tunnel": 2},
    "trailbow": {"dungeon_mirror_mire_vault": 2},
    "ritescribe": {"dungeon_salt_oracle_crypt": 2},
    "wardenhammer": {"dungeon_white_ash_tunnel": 2},
    "shadowknife": {"dungeon_mirror_mire_vault": 2},
    "tailored": {"dungeon_white_ash_tunnel": 1, "dungeon_salt_oracle_crypt": 1, "dungeon_mirror_mire_vault": 1},
}

EVENT_BIAS_BY_STYLE: Dict[str, Dict[str, int]] = {
    "vanguard": {
        "evt_checkpoint_queue_freeze": 5,
        "evt_bell_resonance": 3,
        "evt_black_envoy_delay": 2,
    },
    "envoy": {
        "evt_oath_paper_fray": 5,
        "evt_ledger_gap": 4,
        "evt_black_envoy_delay": 3,
    },
    "seeker": {
        "evt_bell_resonance": 5,
        "evt_mire_vault_glare": 4,
        "evt_salt_oracle_backwash": 3,
    },
    "shadow": {
        "evt_quarantine_pass_split": 4,
        "evt_wharf_manifest_drift": 4,
        "evt_mire_vault_glare": 3,
    },
    "warden": {
        "evt_checkpoint_queue_freeze": 4,
        "evt_ledger_gap": 3,
        "evt_salt_oracle_backwash": 2,
    },
}

EVENT_BIAS_BY_ORIGIN: Dict[str, Dict[str, int]] = {
    "ford": {"evt_quarantine_pass_split": 5, "evt_wharf_manifest_drift": 3},
    "shrine": {"evt_bell_resonance": 4, "evt_salt_oracle_backwash": 4},
    "mine": {"evt_checkpoint_queue_freeze": 3, "evt_mire_vault_glare": 4},
    "road": {"evt_black_envoy_delay": 4, "evt_ledger_gap": 3},
    "marsh": {"evt_wharf_manifest_drift": 4, "evt_mire_vault_glare": 4},
    "court": {"evt_oath_paper_fray": 4, "evt_black_envoy_delay": 3},
    "harbor": {"evt_quarantine_pass_split": 4, "evt_wharf_manifest_drift": 4},
    "caravan": {"evt_ledger_gap": 4, "evt_checkpoint_queue_freeze": 3},
    "cloister": {"evt_bell_resonance": 4, "evt_oath_paper_fray": 2},
    "frontier": {"evt_black_envoy_delay": 3, "evt_checkpoint_queue_freeze": 4},
}

EVENT_BIAS_BY_LOADOUT: Dict[str, Dict[str, int]] = {
    "oathblade": {"evt_oath_paper_fray": 3},
    "trailbow": {"evt_wharf_manifest_drift": 2, "evt_black_envoy_delay": 1},
    "ritescribe": {"evt_bell_resonance": 3, "evt_salt_oracle_backwash": 2},
    "wardenhammer": {"evt_checkpoint_queue_freeze": 3, "evt_ledger_gap": 2},
    "shadowknife": {"evt_ledger_gap": 2, "evt_quarantine_pass_split": 2},
    "tailored": {"evt_black_envoy_delay": 1, "evt_oath_paper_fray": 1, "evt_mire_vault_glare": 1},
}

PREFERRED_FACTIONS_BY_RACE: Dict[str, List[str]] = {
    "human": ["kingdom", "march_clans"],
    "elf": ["shrine_synod", "mire_circle"],
    "dwarf": ["miners_compact", "kingdom"],
    "werebeast": ["march_clans", "mire_circle"],
    "birdfolk": ["kingdom", "shrine_synod"],
    "fishfolk": ["mire_circle", "march_clans"],
    "dragonewt": ["kingdom", "demon_domain"],
    "fey": ["shrine_synod", "mire_circle"],
    "demonian": ["demon_domain", "mire_circle"],
    "fallen": ["demon_domain", "shrine_synod"],
    "plantfolk": ["mire_circle", "shrine_synod"],
    "gemfolk": ["miners_compact", "kingdom"],
}

PREFERRED_FACTIONS_BY_ORIGIN: Dict[str, List[str]] = {
    "ford": ["march_clans", "kingdom"],
    "shrine": ["shrine_synod"],
    "mine": ["miners_compact"],
    "road": ["kingdom", "march_clans"],
    "marsh": ["mire_circle"],
    "court": ["kingdom"],
    "harbor": ["march_clans", "mire_circle"],
    "caravan": ["kingdom", "miners_compact"],
    "cloister": ["shrine_synod"],
    "frontier": ["march_clans", "kingdom"],
}

PREFERRED_FACTIONS_BY_STYLE: Dict[str, List[str]] = {
    "vanguard": ["kingdom", "march_clans"],
    "envoy": ["kingdom", "shrine_synod"],
    "seeker": ["shrine_synod", "mire_circle"],
    "shadow": ["mire_circle", "march_clans"],
    "warden": ["miners_compact", "kingdom"],
}


def _weighted_choice_index(base_index: int, count: int, bias_total: int) -> int:
    if count <= 0:
        return 0
    return (base_index + (bias_total % count)) % count


def _score_event(
    event_id: str,
    *,
    phase_index: int,
    seed: int,
    profile: Mapping[str, Any],
    hub_id: str,
    dungeon_id: str,
    event_catalog: Mapping[str, Mapping[str, Any]],
) -> float:
    blueprint = next(item for item in EVENT_BLUEPRINTS if item["eventId"] == event_id)
    catalog_entry = event_catalog.get(event_id, {})
    pressure = float(catalog_entry.get("pressure", blueprint["basePressure"]))
    base = pressure * 0.1
    base += 32.0 if hub_id in blueprint.get("hubAffinityIds", []) else 0.0
    base += 32.0 if dungeon_id in blueprint.get("dungeonAffinityIds", []) else 0.0
    base += float(EVENT_BIAS_BY_STYLE.get(str(profile.get("style") or ""), {}).get(event_id, 0))
    base += float(EVENT_BIAS_BY_ORIGIN.get(str(profile.get("origin") or ""), {}).get(event_id, 0))
    base += float(EVENT_BIAS_BY_LOADOUT.get(str(profile.get("loadout") or ""), {}).get(event_id, 0))
    base += ((seed + _profile_entropy(profile) + phase_index + EVENT_ORDER.index(event_id)) % 3) * 0.9
    return base


def _session_one_loadout(
    world_state: Mapping[str, Any],
    profile: Mapping[str, Any],
    event_catalog: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    seed = int(world_state["resolved_world"]["world"]["seed"])
    base_hub_index = (seed + 1) % len(HUB_BLUEPRINTS)
    base_dungeon_index = (seed + 1) % len(DUNGEON_BLUEPRINTS)
    hub_index = _weighted_choice_index(
        base_hub_index,
        len(HUB_BLUEPRINTS),
        sum(
            int(HUB_BIAS_BY_ORIGIN.get(str(profile.get("origin") or ""), {}).get(item["hubId"], 0))
            + int(HUB_BIAS_BY_STYLE.get(str(profile.get("style") or ""), {}).get(item["hubId"], 0))
            + int(HUB_BIAS_BY_LOADOUT.get(str(profile.get("loadout") or ""), {}).get(item["hubId"], 0))
            for item in HUB_BLUEPRINTS
        )
        + (_profile_entropy(profile) % 5),
    )
    dungeon_index = _weighted_choice_index(
        base_dungeon_index,
        len(DUNGEON_BLUEPRINTS),
        sum(
            int(DUNGEON_BIAS_BY_ORIGIN.get(str(profile.get("origin") or ""), {}).get(item["dungeonId"], 0))
            + int(DUNGEON_BIAS_BY_STYLE.get(str(profile.get("style") or ""), {}).get(item["dungeonId"], 0))
            + int(DUNGEON_BIAS_BY_LOADOUT.get(str(profile.get("loadout") or ""), {}).get(item["dungeonId"], 0))
            for item in DUNGEON_BLUEPRINTS
        )
        + ((_profile_entropy(profile) // 5) % 5),
    )
    hub_id = HUB_BLUEPRINTS[hub_index]["hubId"]
    dungeon_id = DUNGEON_BLUEPRINTS[dungeon_index]["dungeonId"]

    phase_event_ids: List[str] = []
    for phase_index, candidates in enumerate(PHASE_EVENT_GROUPS):
        ranked = sorted(
            candidates,
            key=lambda event_id: (
                -_score_event(
                    event_id,
                    phase_index=phase_index,
                    seed=seed,
                    profile=profile,
                    hub_id=hub_id,
                    dungeon_id=dungeon_id,
                    event_catalog=event_catalog,
                ),
                EVENT_ORDER.index(event_id),
            ),
        )
        phase_event_ids.append(ranked[0])

    return {
        "sessionNumber": 1,
        "hubId": hub_id,
        "dungeonId": dungeon_id,
        "phaseEventIds": phase_event_ids,
    }


def _preferred_factions(profile: Mapping[str, Any]) -> List[str]:
    return _dedupe(
        [
            *PREFERRED_FACTIONS_BY_RACE.get(str(profile.get("race") or ""), []),
            *PREFERRED_FACTIONS_BY_ORIGIN.get(str(profile.get("origin") or ""), []),
            *PREFERRED_FACTIONS_BY_STYLE.get(str(profile.get("style") or ""), []),
        ]
    )


def _npc_occupant_indices(
    seed: int,
    profile: Mapping[str, Any],
    session_one_loadout: Mapping[str, Any],
) -> Dict[str, int]:
    entropy = _profile_entropy(profile)
    hub_weight = next(index for index, item in enumerate(HUB_BLUEPRINTS) if item["hubId"] == session_one_loadout["hubId"])
    dungeon_weight = next(
        index for index, item in enumerate(DUNGEON_BLUEPRINTS) if item["dungeonId"] == session_one_loadout["dungeonId"]
    )
    indices: Dict[str, int] = {}
    for slot_index, blueprint in enumerate(ROLE_SLOT_BLUEPRINTS):
        template_count = max(1, len(blueprint.get("occupantTemplates", [])))
        raw = seed + entropy + hub_weight * 11 + dungeon_weight * 7 + (slot_index + 1) * 13
        indices[blueprint["roleSlotId"]] = raw % template_count
    return indices


def _opening_summary(
    profile: Mapping[str, Any],
    session_one_loadout: Mapping[str, Any],
    hub_catalog: Mapping[str, Mapping[str, Any]],
    dungeon_catalog: Mapping[str, Mapping[str, Any]],
    event_catalog: Mapping[str, Mapping[str, Any]],
) -> str:
    name = str(profile.get("name") or "旅人").strip() or "旅人"
    race_label = str(profile.get("raceLabel") or "旅人").strip()
    origin_label = str(profile.get("originLabel") or "境目育ち").strip()
    hub_label = hub_catalog[session_one_loadout["hubId"]]["label"]
    dungeon_label = dungeon_catalog[session_one_loadout["dungeonId"]]["label"]
    first_event = event_catalog[session_one_loadout["phaseEventIds"][0]]
    boon = (profile.get("starterBoonSeed") or {}).get("visibleBoon") or {}
    boon_text = f" 最初に目を覚ます力は『{boon.get('label')}』だ。" if boon.get("label") else ""
    if str(profile.get("sourceMode") or "") == "reincarnated":
        return (
            f"最初のセッションだ。別世界の面影を残す{name}は、{origin_label}の{race_label}として"
            f"{hub_label}へ流れ着いた。最初にぶつかるのは『{first_event['label']}』で、影は{dungeon_label}にも差している。"
            f"{boon_text}"
        )
    return (
        f"最初のセッションだ。{origin_label}の{race_label}である{name}は、{hub_label}を足場にして"
        f"『{first_event['label']}』へ踏み込む。事の余波は{dungeon_label}にも及びそうだ。{boon_text}"
    ).strip()


def build_new_game_genesis(
    world_state: Mapping[str, Any],
    *,
    hub_catalog: Mapping[str, Mapping[str, Any]],
    dungeon_catalog: Mapping[str, Mapping[str, Any]],
    event_catalog: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    protagonist = world_state.get("resolved_world", {}).get("protagonist", {})
    raw_profile = copy.deepcopy(protagonist.get("character_profile") or {})
    selection_profile = copy.deepcopy(raw_profile)
    profile = copy.deepcopy(raw_profile)
    if not profile:
        profile = {
            "name": protagonist.get("label_ja") or "旅人",
            "race": protagonist.get("race") or "",
            "raceLabel": protagonist.get("race") or "旅人",
            "style": protagonist.get("build_style") or "",
            "styleLabel": protagonist.get("build_style") or "",
            "origin": "",
            "originLabel": "境目育ち",
            "loadout": "",
            "sourceMode": "native",
            "starterBoonSeed": {},
        }
    if not raw_profile:
        selection_profile = {}
    seed = int(world_state["resolved_world"]["world"]["seed"])
    session_one_loadout = _session_one_loadout(world_state, selection_profile, event_catalog)
    opening_summary = _opening_summary(profile, session_one_loadout, hub_catalog, dungeon_catalog, event_catalog)
    first_event = event_catalog[session_one_loadout["phaseEventIds"][0]]
    hub = hub_catalog[session_one_loadout["hubId"]]
    dungeon = dungeon_catalog[session_one_loadout["dungeonId"]]
    return {
        "version": 1,
        "profileSurface": {
            "name": profile.get("name"),
            "raceLabel": profile.get("raceLabel"),
            "styleLabel": profile.get("styleLabel"),
            "originLabel": profile.get("originLabel"),
            "loadoutLabel": profile.get("loadoutLabel"),
            "sourceModeLabel": profile.get("sourceModeLabel"),
            "summaryText": profile.get("summaryText"),
        },
        "profileDigest": {
            "name": profile.get("name"),
            "race": profile.get("race"),
            "style": profile.get("style"),
            "origin": profile.get("origin"),
            "loadout": profile.get("loadout"),
            "sourceMode": profile.get("sourceMode"),
        },
        "biasTags": _dedupe(
            [
                str(profile.get("raceLabel") or ""),
                str(profile.get("styleLabel") or ""),
                str(profile.get("originLabel") or ""),
                str(profile.get("loadoutLabel") or ""),
            ]
        ),
        "preferredFactions": _preferred_factions(selection_profile),
        "sessionOneLoadout": session_one_loadout,
        "npcOccupantIndices": _npc_occupant_indices(seed, selection_profile, session_one_loadout),
        "openingSummary": opening_summary,
        "storyAxes": [
            str(hub.get("pressureStyle") or "").strip(),
            str(dungeon.get("pressureStyle") or "").strip(),
            str(first_event.get("stakes") or "").strip(),
        ],
        "incitingIncident": {
            "eventId": first_event.get("eventId"),
            "label": first_event.get("label"),
            "summary": first_event.get("summary"),
            "objective": first_event.get("objective"),
        },
    }
