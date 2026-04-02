from __future__ import annotations

from typing import Any, Dict, Iterable, List
import copy

from .campaign_content import (
    CAMPAIGN_STATE_VERSION,
    CHOICE_ORDER,
    DUNGEON_BLUEPRINTS,
    DUNGEON_REGION_PREFERENCE,
    EVENT_BLUEPRINTS,
    EVENT_ORDER,
    HUB_BLUEPRINTS,
    HUB_REGION_PREFERENCE,
    PHASE_LABELS,
    PHASE_EVENT_GROUPS,
    ROLE_SLOT_BLUEPRINTS,
    ROLE_SLOT_ORDER,
    SESSION_TURNS,
    canonical_role_slot_id,
)
from .errors import WorldStateError
from .new_game_genesis import build_new_game_genesis
from .text.copy_checks import ensure_copy_quality
from .text.text_composer import (
    choice_label,
    compose_dungeon_copy,
    compose_event_copy,
    compose_hub_copy,
    compose_npc_copy,
    compose_npc_emotion_line,
    compose_npc_relation_line,
    compose_npc_role_line,
    compose_player_trace,
    compose_story_guide_copy,
    compose_world_pulse_copy,
)
from .vice_taboo import derive_vice_taboo_state, exposure_profile_for_slot


NPC_ORDER = list(ROLE_SLOT_ORDER)
TRUCE_WARDEN_SLOT = "slot_truce_warden"
CANTOR_SLOT = "slot_cantor"
LEDGER_CLERK_SLOT = "slot_ledger_clerk"
TUNNEL_GUIDE_SLOT = "slot_tunnel_guide"
QUARTERMASTER_SLOT = "slot_quartermaster"
RELIC_KEEPER_SLOT = "slot_relic_keeper"
SESSION_ARCHIVE_MAX = 10


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 1)


def _pick_key(mapping: Dict[str, Any], preferred: Iterable[str]) -> str:
    for key in preferred:
        if key in mapping:
            return key
    return sorted(mapping)[0]


def _choose_affiliation(factions: Dict[str, Any], preferred: Iterable[str], used: set[str]) -> str:
    for faction_id in preferred:
        if faction_id in factions and faction_id not in used:
            used.add(faction_id)
            return faction_id
    for faction_id in sorted(factions):
        if faction_id not in used:
            used.add(faction_id)
            return faction_id
    return sorted(factions)[0]


def _merge_preferred_order(primary: Iterable[str], secondary: Iterable[str]) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    for source in (primary, secondary):
        for raw_value in source:
            value = str(raw_value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
    return ordered


def _choose_region(regions: Dict[str, Any], preferred: Iterable[str], used: set[str]) -> str:
    for region_id in preferred:
        if region_id in regions and region_id not in used:
            used.add(region_id)
            return region_id
    for region_id in sorted(regions):
        if region_id not in used:
            used.add(region_id)
            return region_id
    return sorted(regions)[0]


def _session_state(turn_counter: int) -> Dict[str, Any]:
    bounded_turn = max(1, int(turn_counter))
    session_number = ((bounded_turn - 1) // SESSION_TURNS) + 1
    turn_in_session = ((bounded_turn - 1) % SESSION_TURNS) + 1
    phase_index = min(2, (turn_in_session - 1) // 2)
    return {
        "turnCounter": bounded_turn,
        "sessionNumber": session_number,
        "turnInSession": turn_in_session,
        "maxTurns": SESSION_TURNS,
        "phaseIndex": phase_index,
        "phaseLabel": PHASE_LABELS[phase_index],
        "eventId": None,
        "remainingTurns": max(0, SESSION_TURNS - turn_in_session + 1),
        "loopUnit": "1 choice = 1 turn",
        "sessionGoal": "6手で制度・拠点・坑路の圧を裁き、小結末へ持ち込む。",
        "completedSessions": max(0, session_number - 1),
    }


def _choice_rank(choice_id: str) -> int:
    return CHOICE_ORDER.index(choice_id) if choice_id in CHOICE_ORDER else len(CHOICE_ORDER)


def _dominant_choice(choice_stats: Dict[str, int]) -> str:
    return sorted(CHOICE_ORDER, key=lambda item: (-int(choice_stats.get(item, 0)), _choice_rank(item)))[0]


def _event_status(pressure: float) -> str:
    if pressure >= 75:
        return "critical"
    if pressure >= 58:
        return "escalating"
    if pressure >= 38:
        return "unstable"
    return "contained"


def _hub_status(stability: float, heat: float) -> str:
    if stability <= 38 or heat >= 78:
        return "fracturing"
    if stability <= 55 or heat >= 60:
        return "tense"
    return "holding"


def _dungeon_status(seal_integrity: float, threat: float, depth: int, max_depth: int) -> str:
    if seal_integrity <= 38 or threat >= 78:
        return "breach_risk"
    if depth >= max_depth:
        return "mapped"
    if seal_integrity <= 58 or threat >= 60:
        return "unstable"
    return "sealed"


def _session_entries(campaign_state: Dict[str, Any], session_number: int) -> List[Dict[str, Any]]:
    return [entry for entry in campaign_state.get("choiceHistory", []) if entry.get("sessionNumber") == session_number]


def _secret_visibility(npc: Dict[str, Any]) -> str:
    state = npc.get("secretState", "hidden")
    if state == "exposed":
        return npc["secret"]
    if state == "hinted":
        return npc["secretHint"]
    return "まだ腹の底は見せていない。"


def _slot_blueprint_map() -> Dict[str, Dict[str, Any]]:
    return {blueprint["roleSlotId"]: blueprint for blueprint in ROLE_SLOT_BLUEPRINTS}


def _occupant_template(blueprint: Dict[str, Any], occupant_index: int) -> Dict[str, Any]:
    templates = list(blueprint.get("occupantTemplates", []))
    if not templates:
        raise RuntimeError(f"TODO: role slot has no occupant templates: {blueprint['roleSlotId']}")
    return templates[int(occupant_index) % len(templates)]


def _slot_metric_baseline(
    blueprint: Dict[str, Any],
    slot_index: int,
    occupant_serial: int,
    seed: int,
    trust_offset: float,
    stress_offset: float,
) -> tuple[float, float]:
    trust = _clamp(
        blueprint["baseTrust"]
        + trust_offset
        + ((seed + slot_index + occupant_serial * 2) % 5) * 1.7
        - occupant_serial * 0.4
    )
    stress = _clamp(
        blueprint["baseStress"]
        + stress_offset
        + ((seed + slot_index * 3 + occupant_serial) % 4) * 2.1
        + occupant_serial * 0.6
    )
    return trust, stress


def _hub_blueprint_map() -> Dict[str, Dict[str, Any]]:
    return {blueprint["hubId"]: blueprint for blueprint in HUB_BLUEPRINTS}


def _dungeon_blueprint_map() -> Dict[str, Dict[str, Any]]:
    return {blueprint["dungeonId"]: blueprint for blueprint in DUNGEON_BLUEPRINTS}


def _build_hub_catalog(world_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    resolved_world = world_state["resolved_world"]
    regions = resolved_world["regions"]
    seed = int(resolved_world["world"]["seed"])
    cycle_state = world_state.get("cycle_state", {})
    used: set[str] = set()
    catalog: Dict[str, Dict[str, Any]] = {}
    for index, blueprint in enumerate(HUB_BLUEPRINTS):
        region_id = _choose_region(regions, blueprint["regionPreference"], used)
        region = regions[region_id]
        stability = _clamp(
            blueprint["baseStability"]
            + (seed % (7 + index)) * 1.3
            - float(cycle_state.get("divine_war_pressure", 0.0)) * 0.05
        )
        supply = _clamp(
            blueprint["baseSupply"]
            + len(regions) * 1.6
            - float(cycle_state.get("distortion", 0.0)) * 0.04
            - index * 1.8
        )
        heat = _clamp(
            blueprint["baseHeat"]
            + float(cycle_state.get("succession_pressure", 0.0)) * 0.1
            + ((seed + index) % 6) * 1.4
        )
        catalog[blueprint["hubId"]] = {
            "hubId": blueprint["hubId"],
            "label": blueprint["label"],
            "regionId": region_id,
            "regionLabel": region.get("label_ja", region_id),
            "description": blueprint["description"],
            "pressureStyle": blueprint["pressureStyle"],
            "protectedAsset": blueprint["protectedAsset"],
            "lostAsset": blueprint["lostAsset"],
            "stability": stability,
            "supply": supply,
            "heat": heat,
            "status": _hub_status(stability, heat),
        }
    return catalog


def _build_dungeon_catalog(world_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    resolved_world = world_state["resolved_world"]
    regions = resolved_world["regions"]
    seed = int(resolved_world["world"]["seed"])
    cycle_state = world_state.get("cycle_state", {})
    used: set[str] = set()
    catalog: Dict[str, Dict[str, Any]] = {}
    for index, blueprint in enumerate(DUNGEON_BLUEPRINTS):
        region_id = _choose_region(regions, blueprint["regionPreference"], used)
        region = regions[region_id]
        seal_integrity = _clamp(
            blueprint["baseSealIntegrity"]
            - float(cycle_state.get("distortion", 0.0)) * 0.08
            + ((seed + index) % 5) * 1.4
        )
        threat = _clamp(
            blueprint["baseThreat"]
            + float(cycle_state.get("divine_war_pressure", 0.0)) * 0.1
            + ((seed + index * 2) % 6) * 1.6
        )
        catalog[blueprint["dungeonId"]] = {
            "dungeonId": blueprint["dungeonId"],
            "label": blueprint["label"],
            "regionId": region_id,
            "regionLabel": region.get("label_ja", region_id),
            "description": blueprint["description"],
            "pressureStyle": blueprint["pressureStyle"],
            "protectedAsset": blueprint["protectedAsset"],
            "lostAsset": blueprint["lostAsset"],
            "depth": 0,
            "maxDepth": blueprint["maxDepth"],
            "sealIntegrity": seal_integrity,
            "threat": threat,
            "status": _dungeon_status(seal_integrity, threat, 0, int(blueprint["maxDepth"])),
        }
    return catalog


def _sync_active_locations_to_catalog(campaign_state: Dict[str, Any]) -> None:
    hub_catalog = campaign_state.get("hubCatalog")
    dungeon_catalog = campaign_state.get("dungeonCatalog")
    current_hub_id = campaign_state.get("currentHubId")
    current_dungeon_id = campaign_state.get("currentDungeonId")
    if isinstance(hub_catalog, dict) and current_hub_id in hub_catalog and isinstance(campaign_state.get("hub"), dict):
        hub_catalog[current_hub_id] = copy.deepcopy(campaign_state["hub"])
    if isinstance(dungeon_catalog, dict) and current_dungeon_id in dungeon_catalog and isinstance(campaign_state.get("dungeon"), dict):
        dungeon_catalog[current_dungeon_id] = copy.deepcopy(campaign_state["dungeon"])


def _event_blueprint_map() -> Dict[str, Dict[str, Any]]:
    return {blueprint["eventId"]: blueprint for blueprint in EVENT_BLUEPRINTS}


def _choose_session_loadout(world_state: Dict[str, Any], campaign_state: Dict[str, Any], session_number: int) -> Dict[str, Any]:
    if session_number == 1:
        genesis = campaign_state.get("newGameGenesis")
        if isinstance(genesis, dict):
            loadout = genesis.get("sessionOneLoadout")
            if isinstance(loadout, dict) and loadout.get("hubId") and loadout.get("dungeonId"):
                return copy.deepcopy(loadout)
    resolved_world = world_state["resolved_world"]
    seed = int(resolved_world["world"]["seed"])
    dominant_choice = _dominant_choice(campaign_state.get("choiceStats", {}))
    choice_bias = _choice_rank(dominant_choice)
    hub_blueprints = HUB_BLUEPRINTS
    dungeon_blueprints = DUNGEON_BLUEPRINTS
    hub_index = (seed + session_number + choice_bias) % len(hub_blueprints)
    dungeon_index = (seed + session_number + choice_bias) % len(dungeon_blueprints)
    hub_id = hub_blueprints[hub_index]["hubId"]
    dungeon_id = dungeon_blueprints[dungeon_index]["dungeonId"]

    event_catalog = campaign_state.get("events", {}).get("catalog", {})
    event_blueprints = _event_blueprint_map()
    phase_event_ids: List[str] = []
    for phase_index, candidates in enumerate(PHASE_EVENT_GROUPS):
        ranked = sorted(
            candidates,
            key=lambda event_id: (
                -(
                    float(event_catalog.get(event_id, {}).get("pressure", event_blueprints[event_id]["basePressure"])) * 0.1
                    + (32.0 if hub_id in event_blueprints[event_id].get("hubAffinityIds", []) else 0.0)
                    + (32.0 if dungeon_id in event_blueprints[event_id].get("dungeonAffinityIds", []) else 0.0)
                    + ((seed + session_number + phase_index + EVENT_ORDER.index(event_id)) % 3)
                ),
                EVENT_ORDER.index(event_id),
            ),
        )
        phase_event_ids.append(ranked[0])

    return {
        "sessionNumber": session_number,
        "hubId": hub_id,
        "dungeonId": dungeon_id,
        "phaseEventIds": phase_event_ids,
    }


def _apply_session_loadout(world_state: Dict[str, Any], campaign_state: Dict[str, Any], session: Dict[str, Any]) -> None:
    hub_catalog = campaign_state["hubCatalog"]
    dungeon_catalog = campaign_state["dungeonCatalog"]
    loadout = campaign_state.get("sessionLoadout")
    if not isinstance(loadout, dict) or int(loadout.get("sessionNumber", -1)) != int(session["sessionNumber"]):
        loadout = _choose_session_loadout(world_state, campaign_state, int(session["sessionNumber"]))
        campaign_state["sessionLoadout"] = loadout
    campaign_state["currentHubId"] = loadout["hubId"]
    campaign_state["currentDungeonId"] = loadout["dungeonId"]
    campaign_state["hub"] = copy.deepcopy(hub_catalog[loadout["hubId"]])
    campaign_state["dungeon"] = copy.deepcopy(dungeon_catalog[loadout["dungeonId"]])
    phase_event_ids = list(loadout.get("phaseEventIds", []))
    current_event_id = phase_event_ids[session["phaseIndex"]]
    session["eventId"] = current_event_id
    campaign_state["currentEventId"] = current_event_id


def _build_role_slots(
    world_state: Dict[str, Any],
    hub_region_id: str,
    dungeon_region_id: str,
    *,
    genesis: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    resolved_world = world_state["resolved_world"]
    factions = resolved_world["factions"]
    used: set[str] = set()
    seed = int(resolved_world["world"]["seed"])
    cycle_state = world_state.get("cycle_state", {})
    stress_offset = float(cycle_state.get("divine_war_pressure", 0.0)) * 0.08
    trust_offset = float(cycle_state.get("distortion", 0.0)) * -0.04
    hub_region = resolved_world["regions"][hub_region_id]
    dungeon_region = resolved_world["regions"][dungeon_region_id]
    npcs: Dict[str, Dict[str, Any]] = {}
    for index, blueprint in enumerate(ROLE_SLOT_BLUEPRINTS):
        slot_id = blueprint["roleSlotId"]
        occupant_templates = list(blueprint.get("occupantTemplates", []))
        template_count = max(1, len(occupant_templates))
        occupant_index = int(
            (
                (genesis or {}).get("npcOccupantIndices", {}).get(slot_id)
                if isinstance(genesis, dict)
                else (seed + (index + 1) * 13)
            )
            or 0
        ) % template_count
        occupant_serial = 0
        occupant = _occupant_template(blueprint, occupant_index)
        preferred_affinity = _merge_preferred_order(
            blueprint["factionAffinity"],
            (genesis or {}).get("preferredFactions", []) if isinstance(genesis, dict) else [],
        )
        faction_id = _choose_affiliation(factions, preferred_affinity, used)
        faction = factions[faction_id]
        trust, stress = _slot_metric_baseline(blueprint, index, occupant_serial, seed, trust_offset, stress_offset)
        location_label = (
            hub_region["label_ja"]
            if blueprint["home"] == "hub"
            else dungeon_region["label_ja"]
            if blueprint["home"] == "dungeon"
            else "各地"
        )
        npcs[slot_id] = {
            "roleSlotId": slot_id,
            "npcId": slot_id,
            "legacyNpcId": blueprint["legacyNpcId"],
            "roleLabel": blueprint["roleLabel"],
            "role": blueprint["role"],
            "function": blueprint["function"],
            "factionAffinity": list(blueprint["factionAffinity"]),
            "regionAffinity": blueprint["regionAffinity"],
            "successionRule": blueprint["successionRule"],
            "mortalityRisk": blueprint["mortalityRisk"],
            "replacementConditions": list(blueprint["replacementConditions"]),
            "occupantId": occupant["occupantId"],
            "occupantIndex": occupant_index,
            "occupantSerial": occupant_serial,
            "occupantStatus": "alive",
            "displayName": occupant["displayName"],
            "ageState": occupant["ageState"],
            "agenda": blueprint["agenda"],
            "affiliationFactionId": faction_id,
            "affiliationLabel": faction.get("label_ja", faction_id),
            "locationKey": blueprint["home"],
            "locationLabel": location_label,
            "trust": trust,
            "stress": stress,
            "importance": "high" if index < 2 else "medium",
            "secret": occupant["secret"],
            "secretHint": occupant["secretHint"],
            "hintTrigger": occupant["hintTrigger"],
            "exposeTrigger": occupant["exposeTrigger"],
            "secretState": "hidden",
            "secretPressure": 0.0,
            "lastSecretTrigger": None,
            "weakness": occupant["weakness"],
            "weaknessTrigger": occupant["weaknessTrigger"],
            "knownWeakness": None,
            "weaknessPressure": 0.0,
            "lastWeaknessTrigger": None,
            "conflictTargetSlotId": blueprint["conflictTargetSlotId"],
            "conflictsWithNpcId": blueprint["conflictTargetSlotId"],
            "conflictsWithRoleLabel": "",
            "conflictsWithLabel": "",
            "conflictDetail": blueprint["conflictDetail"],
            "favoredApproach": blueprint["favoredApproach"],
            "resentedApproach": blueprint["resentedApproach"],
            "secretHintApproaches": list(blueprint.get("secretHintApproaches", [])),
            "secretExposeApproaches": list(blueprint.get("secretExposeApproaches", [])),
            "weaknessApproaches": list(blueprint.get("weaknessApproaches", [])),
            "reactionNotes": copy.deepcopy(blueprint.get("reactionNotes", {})),
            "viceExposure": list(blueprint.get("viceExposure", [])),
            "tabooExposure": list(blueprint.get("tabooExposure", [])),
            "lastReaction": "まだこちらの出方を測っている。",
            "lastReactionMode": "guarded",
            "memory": [],
            "scar": None,
            "occupantHistory": [],
            "lastReplacement": None,
        }
    for npc in npcs.values():
        conflict_target = npcs[npc["conflictTargetSlotId"]]
        npc["conflictsWithRoleLabel"] = conflict_target["roleLabel"]
        npc["conflictsWithLabel"] = conflict_target["displayName"]
    return npcs


def _event_catalog(world_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    cycle_state = world_state.get("cycle_state", {})
    pressure_bias = float(cycle_state.get("distortion", 0.0)) * 0.08 + float(cycle_state.get("divine_war_pressure", 0.0)) * 0.05
    catalog: Dict[str, Dict[str, Any]] = {}
    for index, blueprint in enumerate(EVENT_BLUEPRINTS):
        pressure = _clamp(blueprint["basePressure"] + pressure_bias + index * 2.4)
        catalog[blueprint["eventId"]] = {
            "eventId": blueprint["eventId"],
            "phaseGroup": blueprint["phaseGroup"],
            "label": blueprint["label"],
            "theme": blueprint["theme"],
            "hubAffinityIds": list(blueprint.get("hubAffinityIds", [])),
            "dungeonAffinityIds": list(blueprint.get("dungeonAffinityIds", [])),
            "summary": blueprint["summary"],
            "stakes": blueprint["stakes"],
            "whyImportant": blueprint["whyImportant"],
            "objective": blueprint["objective"],
            "recommendedChoices": list(blueprint["recommendedChoices"]),
            "pressure": pressure,
            "status": _event_status(pressure),
            "branches": copy.deepcopy(blueprint["branches"]),
            "lastBranchId": None,
            "lastOutcome": None,
            "lastOutcomeText": None,
        }
    return catalog


def _archive_compression_defaults(campaign_state: Dict[str, Any]) -> None:
    compression = campaign_state.setdefault("archiveCompression", {})
    compression.setdefault("compressedCount", 0)
    compression.setdefault("oldestSessionNumber", None)
    compression.setdefault("newestSessionNumber", None)
    compression.setdefault("latestSummary", "")


def _initial_session_opening_summary() -> str:
    return "最初のセッションだ。まだ前のセッションから強く持ち越された因果はない。"


def _session_opening_summary_from_hook(hook: Dict[str, Any] | None) -> str:
    if not isinstance(hook, dict):
        return "前のセッションから、いま強く引きずっている問題はまだない。"
    lines: List[str] = []
    if hook.get("archivedCauseEchoes"):
        lines.append(str(hook["archivedCauseEchoes"][0]))
    if hook.get("resurfacingRisks"):
        lines.append(str(hook["resurfacingRisks"][0]))
    if hook.get("carriedPressures"):
        lines.append(str(hook["carriedPressures"][0]))
    if not lines:
        return "前のセッションから、いま強く引きずっている問題はまだない。"
    if len(lines) == 1:
        return f"セッションの始まりに強く残っていたのは、{lines[0]}"
    return f"セッションの始まりに強く残っていたのは、{lines[0]} {lines[1]}"


ROLE_SLOT_REPERCUSSION_KEYS = (
    "roleSlotSuspicion",
    "roleSlotDistrust",
    "roleSlotRetaliation",
)


def ensure_role_slot_repercussions(campaign_state: Dict[str, Any]) -> None:
    for key in ROLE_SLOT_REPERCUSSION_KEYS:
        current = campaign_state.get(key)
        normalized: Dict[str, float] = {}
        if isinstance(current, dict):
            for slot_id in NPC_ORDER:
                normalized[slot_id] = _clamp(float(current.get(slot_id, 0.0)))
        else:
            normalized = {slot_id: 0.0 for slot_id in NPC_ORDER}
        campaign_state[key] = normalized


def _role_slot_repercussion_value(campaign_state: Dict[str, Any], key: str, role_slot_id: str) -> float:
    ensure_role_slot_repercussions(campaign_state)
    return float(campaign_state.get(key, {}).get(role_slot_id, 0.0))


def apply_role_slot_repercussions(
    campaign_state: Dict[str, Any],
    role_slot_ids: Iterable[str],
    *,
    suspicion_delta: float = 0.0,
    distrust_delta: float = 0.0,
    retaliation_delta: float = 0.0,
) -> None:
    ensure_role_slot_repercussions(campaign_state)
    valid_role_slot_ids = [
        role_slot_id
        for role_slot_id in dict.fromkeys(str(raw_role_slot_id).strip() for raw_role_slot_id in role_slot_ids)
        if role_slot_id in campaign_state.get("npcs", {})
    ]
    if not valid_role_slot_ids:
        return
    for role_slot_id in valid_role_slot_ids:
        campaign_state["roleSlotSuspicion"][role_slot_id] = _clamp(
            _role_slot_repercussion_value(campaign_state, "roleSlotSuspicion", role_slot_id) + suspicion_delta
        )
        campaign_state["roleSlotDistrust"][role_slot_id] = _clamp(
            _role_slot_repercussion_value(campaign_state, "roleSlotDistrust", role_slot_id) + distrust_delta
        )
        campaign_state["roleSlotRetaliation"][role_slot_id] = _clamp(
            _role_slot_repercussion_value(campaign_state, "roleSlotRetaliation", role_slot_id) + retaliation_delta
        )


def _age_role_slot_repercussions(campaign_state: Dict[str, Any]) -> None:
    ensure_role_slot_repercussions(campaign_state)
    for role_slot_id in NPC_ORDER:
        campaign_state["roleSlotSuspicion"][role_slot_id] = _clamp(
            _role_slot_repercussion_value(campaign_state, "roleSlotSuspicion", role_slot_id) * 0.88
        )
        campaign_state["roleSlotDistrust"][role_slot_id] = _clamp(
            _role_slot_repercussion_value(campaign_state, "roleSlotDistrust", role_slot_id) * 0.91
        )
        campaign_state["roleSlotRetaliation"][role_slot_id] = _clamp(
            _role_slot_repercussion_value(campaign_state, "roleSlotRetaliation", role_slot_id) * 0.94
        )


def _sync_vice_taboo_state(world_state: Dict[str, Any], campaign_state: Dict[str, Any]) -> None:
    campaign_state.setdefault("viceTrace", [])
    campaign_state.setdefault("tabooTrace", [])
    campaign_state.setdefault("freeActionHistory", [])
    campaign_state.setdefault("lastFreeAction", None)
    campaign_state.setdefault("nextSessionHookNotes", [])
    campaign_state.setdefault("archiveEchoAppliedSessions", [])
    campaign_state.setdefault("publicInfamy", 0.0)
    campaign_state.setdefault("hiddenCrimes", 0.0)
    campaign_state.setdefault("moralCorrosion", 0.0)
    campaign_state.setdefault("ritualPollution", 0.0)
    campaign_state.setdefault("vicePressure", 0.0)
    campaign_state.setdefault("tabooPressure", 0.0)
    campaign_state.setdefault("viceVisibility", 0.0)
    campaign_state.setdefault("publicShame", 0.0)
    campaign_state.setdefault("hiddenDepravity", 0.0)
    campaign_state.setdefault("collectiveEfficacy", 50.0)
    campaign_state.setdefault("publicLegitimacy", 50.0)
    ensure_role_slot_repercussions(campaign_state)
    for npc in campaign_state.get("npcs", {}).values():
        npc.setdefault("exposureProfile", exposure_profile_for_slot(npc))
    derived = derive_vice_taboo_state(world_state, campaign_state)
    for key, value in derived.items():
        campaign_state[key] = copy.deepcopy(value)

    cycle_state = world_state.setdefault("cycle_state", {})
    cycle_state["vice_pressure"] = float(campaign_state["vicePressure"])
    cycle_state["taboo_pressure"] = float(campaign_state["tabooPressure"])
    cycle_state["moral_corrosion"] = float(campaign_state["moralCorrosion"])
    cycle_state["vice_visibility"] = float(campaign_state["viceVisibility"])
    cycle_state["public_shame"] = float(campaign_state["publicShame"])
    cycle_state["hidden_depravity"] = float(campaign_state["hiddenDepravity"])
    cycle_state["ritual_pollution"] = float(campaign_state["ritualPollution"])
    cycle_state["collective_efficacy"] = float(campaign_state["collectiveEfficacy"])
    cycle_state["public_legitimacy"] = float(campaign_state["publicLegitimacy"])
    cycle_state["public_infamy"] = float(campaign_state["publicInfamy"])
    cycle_state["hidden_crimes"] = float(campaign_state["hiddenCrimes"])


def _build_campaign_state(world_state: Dict[str, Any]) -> Dict[str, Any]:
    session = _session_state(1)
    hub_catalog = _build_hub_catalog(world_state)
    dungeon_catalog = _build_dungeon_catalog(world_state)
    event_catalog = _event_catalog(world_state)
    new_game_genesis = build_new_game_genesis(
        world_state,
        hub_catalog=hub_catalog,
        dungeon_catalog=dungeon_catalog,
        event_catalog=event_catalog,
    )
    session_loadout = copy.deepcopy(new_game_genesis["sessionOneLoadout"])
    initial_hub = hub_catalog[session_loadout["hubId"]]
    initial_dungeon = dungeon_catalog[session_loadout["dungeonId"]]
    campaign = {
        "version": CAMPAIGN_STATE_VERSION,
        "session": session,
        "hubCatalog": copy.deepcopy(hub_catalog),
        "dungeonCatalog": copy.deepcopy(dungeon_catalog),
        "currentHubId": None,
        "currentDungeonId": None,
        "sessionLoadout": session_loadout,
        "newGameGenesis": copy.deepcopy(new_game_genesis),
        "hub": {},
        "dungeon": {},
        "npcs": _build_role_slots(
            world_state,
            initial_hub["regionId"],
            initial_dungeon["regionId"],
            genesis=new_game_genesis,
        ),
        "events": {"order": list(EVENT_ORDER), "catalog": event_catalog, "history": []},
        "currentEventId": None,
        "choiceHistory": [],
        "choiceStats": {choice_id: 0 for choice_id in CHOICE_ORDER},
        "sessionEndings": [],
        "lastEnding": None,
        "worldMarks": [],
        "viceTrace": [],
        "tabooTrace": [],
        "freeActionHistory": [],
        "lastFreeAction": None,
        "nextSessionHookNotes": [],
        "archiveEchoAppliedSessions": [],
        "vicePressure": 0.0,
        "tabooPressure": 0.0,
        "moralCorrosion": 0.0,
        "viceVisibility": 0.0,
        "publicShame": 0.0,
        "hiddenDepravity": 0.0,
        "ritualPollution": 0.0,
        "publicInfamy": 0.0,
        "hiddenCrimes": 0.0,
        "collectiveEfficacy": 50.0,
        "publicLegitimacy": 50.0,
        "roleSlotSuspicion": {slot_id: 0.0 for slot_id in NPC_ORDER},
        "roleSlotDistrust": {slot_id: 0.0 for slot_id in NPC_ORDER},
        "roleSlotRetaliation": {slot_id: 0.0 for slot_id in NPC_ORDER},
        "lastTransition": None,
        "sessionArchive": [],
        "archiveCompression": {
            "compressedCount": 0,
            "oldestSessionNumber": None,
            "newestSessionNumber": None,
            "latestSummary": "",
        },
        "sessionOpeningHooks": {"1": new_game_genesis.get("openingSummary") or _initial_session_opening_summary()},
        "saveMeta": {
            "saveId": None,
            "savePath": None,
            "savedAt": None,
        },
        "nextSessionHook": None,
    }
    _apply_session_loadout(world_state, campaign, session)
    _sync_vice_taboo_state(world_state, campaign)
    return campaign


def _normalize_npc_id_list(values: Iterable[str]) -> List[str]:
    return [canonical_role_slot_id(str(value)) for value in values]


def _migrate_legacy_npcs(campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    legacy_npcs = copy.deepcopy(campaign_state.get("npcs", {}))
    if not legacy_npcs:
        return {}

    blueprints = _slot_blueprint_map()
    migrated: Dict[str, Dict[str, Any]] = {}
    for slot_id in NPC_ORDER:
        blueprint = blueprints[slot_id]
        source = legacy_npcs.get(slot_id) or legacy_npcs.get(blueprint["legacyNpcId"])
        if source is None:
            continue
        npc = copy.deepcopy(source)
        npc["roleSlotId"] = slot_id
        npc["npcId"] = slot_id
        npc.setdefault("legacyNpcId", blueprint["legacyNpcId"])
        npc.setdefault("roleLabel", blueprint["roleLabel"])
        npc.setdefault("function", blueprint["function"])
        npc.setdefault("factionAffinity", list(blueprint["factionAffinity"]))
        npc.setdefault("regionAffinity", blueprint["regionAffinity"])
        npc.setdefault("successionRule", blueprint["successionRule"])
        npc.setdefault("mortalityRisk", blueprint["mortalityRisk"])
        npc.setdefault("replacementConditions", list(blueprint["replacementConditions"]))
        npc.setdefault("occupantId", f"legacy_{slot_id}")
        npc.setdefault("occupantIndex", 0)
        npc.setdefault("occupantSerial", 0)
        npc.setdefault("occupantStatus", "alive")
        npc.setdefault("ageState", "不詳")
        conflict_slot = canonical_role_slot_id(str(npc.get("conflictTargetSlotId") or npc.get("conflictsWithNpcId") or ""))
        npc["conflictTargetSlotId"] = conflict_slot or blueprint["conflictTargetSlotId"]
        npc["conflictsWithNpcId"] = npc["conflictTargetSlotId"]
        npc.setdefault("occupantHistory", [])
        npc.setdefault("lastReplacement", None)
        migrated[slot_id] = npc

    for slot_id, npc in migrated.items():
        target_slot = npc.get("conflictTargetSlotId")
        if target_slot in migrated:
            npc["conflictsWithRoleLabel"] = migrated[target_slot].get("roleLabel", "")
            npc["conflictsWithLabel"] = migrated[target_slot].get("displayName", "")
    return migrated


def _normalize_event_catalog(world_state: Dict[str, Any], campaign_state: Dict[str, Any]) -> None:
    canonical_events = _event_catalog(world_state)
    events = campaign_state.setdefault("events", {"order": list(EVENT_ORDER), "catalog": {}, "history": []})
    events["order"] = list(EVENT_ORDER)
    catalog = events.setdefault("catalog", {})
    for event_id, canonical in canonical_events.items():
        current = catalog.setdefault(event_id, {})
        current["eventId"] = event_id
        current["phaseGroup"] = canonical["phaseGroup"]
        current["label"] = canonical["label"]
        current["theme"] = canonical["theme"]
        current["hubAffinityIds"] = list(canonical.get("hubAffinityIds", []))
        current["dungeonAffinityIds"] = list(canonical.get("dungeonAffinityIds", []))
        current["summary"] = canonical["summary"]
        current["stakes"] = canonical["stakes"]
        current["whyImportant"] = canonical["whyImportant"]
        current["objective"] = canonical["objective"]
        current["recommendedChoices"] = list(canonical["recommendedChoices"])
        current["branches"] = copy.deepcopy(canonical["branches"])
        current.setdefault("pressure", float(canonical["pressure"]))
        current.setdefault("status", canonical["status"])
        current.setdefault("lastBranchId", None)
        current.setdefault("lastOutcome", None)
        current.setdefault("lastOutcomeText", None)

    for entry in events.setdefault("history", []):
        if "focusNpcIds" in entry:
            entry["focusNpcIds"] = _normalize_npc_id_list(entry["focusNpcIds"])

    for entry in campaign_state.setdefault("choiceHistory", []):
        if "focusNpcIds" in entry:
            entry["focusNpcIds"] = _normalize_npc_id_list(entry["focusNpcIds"])


def _refresh_campaign_state(world_state: Dict[str, Any], campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    campaign = copy.deepcopy(campaign_state)
    hub_catalog = copy.deepcopy(campaign.get("hubCatalog") or _build_hub_catalog(world_state))
    dungeon_catalog = copy.deepcopy(campaign.get("dungeonCatalog") or _build_dungeon_catalog(world_state))
    canonical_event_catalog = _event_catalog(world_state)
    new_game_genesis = campaign.get("newGameGenesis")
    if not isinstance(new_game_genesis, dict):
        new_game_genesis = build_new_game_genesis(
            world_state,
            hub_catalog=hub_catalog,
            dungeon_catalog=dungeon_catalog,
            event_catalog=canonical_event_catalog,
        )
    campaign["newGameGenesis"] = copy.deepcopy(new_game_genesis)
    if isinstance(campaign.get("hub"), dict) and campaign["hub"]:
        legacy_hub_id = str(campaign.get("currentHubId") or campaign["hub"].get("hubId") or next(iter(hub_catalog)))
        if legacy_hub_id in hub_catalog:
            merged_hub = copy.deepcopy(hub_catalog[legacy_hub_id])
            merged_hub.update(copy.deepcopy(campaign["hub"]))
            hub_catalog[legacy_hub_id] = merged_hub
    if isinstance(campaign.get("dungeon"), dict) and campaign["dungeon"]:
        legacy_dungeon_id = str(campaign.get("currentDungeonId") or campaign["dungeon"].get("dungeonId") or next(iter(dungeon_catalog)))
        if legacy_dungeon_id in dungeon_catalog:
            merged_dungeon = copy.deepcopy(dungeon_catalog[legacy_dungeon_id])
            merged_dungeon.update(copy.deepcopy(campaign["dungeon"]))
            dungeon_catalog[legacy_dungeon_id] = merged_dungeon
    campaign["hubCatalog"] = hub_catalog
    campaign["dungeonCatalog"] = dungeon_catalog
    campaign["currentHubId"] = campaign.get("currentHubId") or next(iter(hub_catalog))
    campaign["currentDungeonId"] = campaign.get("currentDungeonId") or next(iter(dungeon_catalog))
    _sync_active_locations_to_catalog(campaign)

    campaign["npcs"] = _migrate_legacy_npcs(campaign)
    if not campaign["npcs"]:
        active_hub_id = str(campaign.get("currentHubId") or next(iter(hub_catalog)))
        active_dungeon_id = str(campaign.get("currentDungeonId") or next(iter(dungeon_catalog)))
        campaign["npcs"] = _build_role_slots(
            world_state,
            hub_catalog[active_hub_id]["regionId"],
            dungeon_catalog[active_dungeon_id]["regionId"],
            genesis=new_game_genesis,
        )
    elif len(campaign["npcs"]) < len(NPC_ORDER):
        active_hub_id = str(campaign.get("currentHubId") or next(iter(hub_catalog)))
        active_dungeon_id = str(campaign.get("currentDungeonId") or next(iter(dungeon_catalog)))
        defaults = _build_role_slots(
            world_state,
            hub_catalog[active_hub_id]["regionId"],
            dungeon_catalog[active_dungeon_id]["regionId"],
            genesis=new_game_genesis,
        )
        for slot_id in NPC_ORDER:
            campaign["npcs"].setdefault(slot_id, defaults[slot_id])
    session = _session_state(campaign.get("session", {}).get("turnCounter", 1))
    campaign["session"] = session
    campaign.setdefault("choiceHistory", [])
    campaign.setdefault("choiceStats", {choice_id: 0 for choice_id in CHOICE_ORDER})
    campaign.setdefault("sessionEndings", [])
    campaign.setdefault("worldMarks", [])
    campaign.setdefault("viceTrace", [])
    campaign.setdefault("tabooTrace", [])
    campaign.setdefault("freeActionHistory", [])
    campaign.setdefault("lastFreeAction", None)
    campaign.setdefault("nextSessionHookNotes", [])
    campaign.setdefault("archiveEchoAppliedSessions", [])
    campaign.setdefault("vicePressure", 0.0)
    campaign.setdefault("tabooPressure", 0.0)
    campaign.setdefault("moralCorrosion", 0.0)
    campaign.setdefault("viceVisibility", 0.0)
    campaign.setdefault("publicShame", 0.0)
    campaign.setdefault("hiddenDepravity", 0.0)
    campaign.setdefault("ritualPollution", 0.0)
    campaign.setdefault("publicInfamy", 0.0)
    campaign.setdefault("hiddenCrimes", 0.0)
    campaign.setdefault("collectiveEfficacy", 50.0)
    campaign.setdefault("publicLegitimacy", 50.0)
    ensure_role_slot_repercussions(campaign)
    campaign.setdefault("lastEnding", None)
    campaign.setdefault("sessionArchive", [])
    _archive_compression_defaults(campaign)
    session_opening_hooks = campaign.setdefault("sessionOpeningHooks", {})
    session_opening_hooks.setdefault("1", new_game_genesis.get("openingSummary") or _initial_session_opening_summary())
    campaign.setdefault("nextSessionHook", None)
    save_meta = campaign.setdefault("saveMeta", {})
    save_meta.setdefault("saveId", None)
    save_meta.setdefault("savePath", None)
    save_meta.setdefault("savedAt", None)
    _normalize_event_catalog(world_state, campaign)
    _apply_session_loadout(world_state, campaign, session)
    for hub in campaign["hubCatalog"].values():
        hub["status"] = _hub_status(float(hub["stability"]), float(hub["heat"]))
    for dungeon in campaign["dungeonCatalog"].values():
        dungeon["status"] = _dungeon_status(
            float(dungeon["sealIntegrity"]),
            float(dungeon["threat"]),
            int(dungeon["depth"]),
            int(dungeon["maxDepth"]),
        )
    campaign["hub"] = copy.deepcopy(campaign["hubCatalog"][campaign["currentHubId"]])
    campaign["dungeon"] = copy.deepcopy(campaign["dungeonCatalog"][campaign["currentDungeonId"]])
    for npc in campaign["npcs"].values():
        npc.setdefault("roleSlotId", npc.get("npcId"))
        npc["npcId"] = npc.get("roleSlotId", npc.get("npcId"))
        npc.setdefault("roleLabel", npc.get("displayName", "役割不明"))
        npc.setdefault("function", npc.get("role", "役割不明"))
        npc.setdefault("factionAffinity", [])
        npc.setdefault("regionAffinity", npc.get("locationKey", "world"))
        npc.setdefault("successionRule", "継承者へ引き継がれる。")
        npc.setdefault("mortalityRisk", "medium")
        npc.setdefault("replacementConditions", [])
        npc.setdefault("occupantId", f"legacy_{npc['npcId']}")
        npc.setdefault("occupantIndex", 0)
        npc.setdefault("occupantSerial", 0)
        npc.setdefault("occupantStatus", "alive")
        npc.setdefault("ageState", "不詳")
        npc.setdefault("legacyNpcId", None)
        npc.setdefault("conflictTargetSlotId", canonical_role_slot_id(str(npc.get("conflictsWithNpcId") or "")))
        npc["conflictsWithNpcId"] = npc.get("conflictTargetSlotId")
        if npc.get("conflictTargetSlotId") in campaign["npcs"]:
            target = campaign["npcs"][npc["conflictTargetSlotId"]]
            npc["conflictsWithRoleLabel"] = target.get("roleLabel", "")
            npc["conflictsWithLabel"] = target["displayName"]
        npc.setdefault("secretState", "hidden")
        npc.setdefault("secretPressure", 0.0)
        npc.setdefault("lastSecretTrigger", None)
        npc.setdefault("knownWeakness", None)
        npc.setdefault("weaknessPressure", 0.0)
        npc.setdefault("lastWeaknessTrigger", None)
        npc.setdefault("hintTrigger", "")
        npc.setdefault("exposeTrigger", "")
        npc.setdefault("weaknessTrigger", "")
        npc.setdefault("conflictDetail", "")
        npc.setdefault("secretHintApproaches", [])
        npc.setdefault("secretExposeApproaches", [])
        npc.setdefault("weaknessApproaches", [])
        npc.setdefault("reactionNotes", {})
        npc.setdefault("viceExposure", [])
        npc.setdefault("tabooExposure", [])
        npc.setdefault("lastReaction", "まだこちらの出方を測っている。")
        npc.setdefault("lastReactionMode", "guarded")
        npc.setdefault("memory", [])
        npc.setdefault("scar", None)
        npc.setdefault("occupantHistory", [])
        npc.setdefault("lastReplacement", None)
        npc.setdefault("exposureProfile", exposure_profile_for_slot(npc))
        if npc.get("locationKey") == "hub":
            npc["locationLabel"] = campaign["hub"]["label"]
        elif npc.get("locationKey") == "dungeon":
            npc["locationLabel"] = campaign["dungeon"]["label"]
    for event in campaign["events"]["catalog"].values():
        event["status"] = _event_status(float(event["pressure"]))
        event.setdefault("lastBranchId", None)
        event.setdefault("lastOutcome", None)
        event.setdefault("lastOutcomeText", None)
    campaign["session"]["eventId"] = campaign["currentEventId"]
    _sync_vice_taboo_state(world_state, campaign)
    return campaign


def ensure_campaign_state(world_state: Dict[str, Any]) -> Dict[str, Any]:
    state = copy.deepcopy(world_state)
    campaign_state = state.get("campaign_state")
    if not isinstance(campaign_state, dict) or campaign_state.get("version") != CAMPAIGN_STATE_VERSION:
        state["campaign_state"] = _build_campaign_state(state)
        return state
    state["campaign_state"] = _refresh_campaign_state(state, campaign_state)
    return state


def _swing_for_outcome(outcome: str) -> float:
    return {"success": 8.0, "partial_success": 3.5, "failure": -7.0}.get(outcome, 0.0)


def _branch_lookup(event: Dict[str, Any], branch_id: str | None) -> Dict[str, Any] | None:
    if branch_id is None:
        return None
    for branch in event.get("branches", []):
        if branch["branchId"] == branch_id:
            return branch
    return None


def _current_event(campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    return campaign_state["events"]["catalog"][campaign_state["currentEventId"]]


def _branch_history_count(campaign_state: Dict[str, Any], event_id: str, branch_id: str) -> int:
    return sum(
        1
        for entry in campaign_state.get("events", {}).get("history", [])
        if entry.get("eventId") == event_id and entry.get("branchId") == branch_id
    )


def _branch_selector_score(branch: Dict[str, Any], campaign_state: Dict[str, Any]) -> float:
    selectors = branch.get("selectors", {})
    if not selectors:
        return 0.0

    score = 0.0
    npcs = campaign_state["npcs"]
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    session = campaign_state["session"]
    choice_stats = campaign_state.get("choiceStats", {})
    current_event = _current_event(campaign_state)

    for npc_id, states in selectors.get("secretStates", {}).items():
        score += 4.0 if npcs[npc_id].get("secretState") in states else -3.0
    for npc_id in selectors.get("knownWeaknessNpcIds", []):
        score += 3.5 if npcs[npc_id].get("knownWeakness") else -2.0
    for choice_id, minimum in selectors.get("choiceCountsAtLeast", {}).items():
        score += 1.6 if int(choice_stats.get(choice_id, 0)) >= int(minimum) else -1.0

    if selectors.get("heatAbove") is not None:
        score += 1.8 if float(hub["heat"]) >= float(selectors["heatAbove"]) else -1.0
    if selectors.get("supplyBelow") is not None:
        score += 1.8 if float(hub["supply"]) <= float(selectors["supplyBelow"]) else -1.0
    if selectors.get("threatAbove") is not None:
        score += 1.8 if float(dungeon["threat"]) >= float(selectors["threatAbove"]) else -1.0
    if selectors.get("depthAtLeast") is not None:
        score += 1.8 if int(dungeon["depth"]) >= int(selectors["depthAtLeast"]) else -1.0
    if selectors.get("turnAtLeast") is not None:
        score += 1.8 if int(session["turnInSession"]) >= int(selectors["turnAtLeast"]) else -1.0

    score -= _branch_history_count(campaign_state, current_event["eventId"], branch["branchId"]) * 1.2
    if current_event.get("lastBranchId") == branch["branchId"]:
        score -= 1.4
    return score


def _pick_branch(event: Dict[str, Any], intent_type: str, campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    dominant_choice = _dominant_choice(campaign_state.get("choiceStats", {}))
    return sorted(
        event.get("branches", []),
        key=lambda branch: (
            -(
                (10.0 if intent_type in branch["preferredIntents"] else 0.0)
                + (3.0 if dominant_choice in branch["preferredIntents"] else 0.0)
                + _branch_selector_score(branch, campaign_state)
            ),
            branch["branchId"],
        ),
    )[0]


def _npc_adjustments(intent_type: str, swing: float) -> Dict[str, Dict[str, float]]:
    base = {npc_id: {"trust": 0.0, "stress": 0.0} for npc_id in NPC_ORDER}
    if intent_type == "observe":
        base[TUNNEL_GUIDE_SLOT] = {"trust": swing * 0.6, "stress": -swing * 0.35}
        base[TRUCE_WARDEN_SLOT] = {"trust": swing * 0.2, "stress": -swing * 0.1}
        base[RELIC_KEEPER_SLOT] = {"trust": swing * 0.35, "stress": -swing * 0.18}
    elif intent_type == "speak":
        base[TRUCE_WARDEN_SLOT] = {"trust": swing * 0.7, "stress": -swing * 0.4}
        base[CANTOR_SLOT] = {"trust": swing * 0.5, "stress": -swing * 0.2}
        base[QUARTERMASTER_SLOT] = {"trust": swing * 0.6, "stress": -swing * 0.28}
    elif intent_type == "inspect":
        base[LEDGER_CLERK_SLOT] = {"trust": swing * 0.8, "stress": -swing * 0.3}
        base[CANTOR_SLOT] = {"trust": swing * 0.3, "stress": -swing * 0.15}
        base[RELIC_KEEPER_SLOT] = {"trust": swing * 0.7, "stress": -swing * 0.25}
    elif intent_type == "intervene":
        base[TUNNEL_GUIDE_SLOT] = {"trust": swing * 0.5, "stress": -swing * 0.5}
        base[TRUCE_WARDEN_SLOT] = {"trust": swing * 0.4, "stress": -swing * 0.25}
        base[QUARTERMASTER_SLOT] = {"trust": swing * 0.45, "stress": -swing * 0.22}
    return base


def _trace_adjustments(campaign_state: Dict[str, Any], npc: Dict[str, Any], intent_type: str) -> Dict[str, float]:
    prior_count = int(campaign_state.get("choiceStats", {}).get(intent_type, 0))
    trust = 0.0
    stress = 0.0
    if npc.get("favoredApproach") == intent_type:
        trust += min(2.4, prior_count * 0.8)
    if npc.get("resentedApproach") == intent_type:
        stress += min(2.8, prior_count * 0.9)
    return {"trust": trust, "stress": stress}


def _secret_update(npc: Dict[str, Any], mode: str) -> None:
    current = npc.get("secretState", "hidden")
    if mode == "expose":
        npc["secretState"] = "exposed"
    elif mode == "hint" and current == "hidden":
        npc["secretState"] = "hinted"


def _append_memory(npc: Dict[str, Any], memory_text: str) -> None:
    memory = list(npc.get("memory", []))
    memory.append(memory_text)
    npc["memory"] = memory[-3:]


def _advance_npc_arcs(campaign_state: Dict[str, Any], focus_npc_ids: List[str], intent_type: str, outcome: str) -> None:
    for npc in campaign_state["npcs"].values():
        focus_bonus = 1.2 if npc["npcId"] in focus_npc_ids else 0.0
        secret_gain = focus_bonus
        weakness_gain = focus_bonus * 0.6

        if intent_type in npc.get("secretHintApproaches", []):
            secret_gain += 1.0
        if intent_type in npc.get("secretExposeApproaches", []):
            secret_gain += 0.8 if outcome == "failure" else 0.3
        if intent_type in npc.get("weaknessApproaches", []):
            weakness_gain += 1.0
        if npc.get("resentedApproach") == intent_type:
            weakness_gain += 0.6
        if outcome == "failure":
            secret_gain += 0.6
            weakness_gain += 0.8

        npc["secretPressure"] = round(float(npc.get("secretPressure", 0.0)) + secret_gain, 1)
        npc["weaknessPressure"] = round(float(npc.get("weaknessPressure", 0.0)) + weakness_gain, 1)

        if npc.get("secretState") == "hidden" and float(npc["secretPressure"]) >= 2.6:
            npc["secretState"] = "hinted"
            npc["lastSecretTrigger"] = npc.get("hintTrigger")
            _append_memory(npc, f"秘密の糸口: {npc.get('hintTrigger')}")
        if npc.get("secretState") != "exposed" and float(npc["secretPressure"]) >= 5.0:
            npc["secretState"] = "exposed"
            npc["lastSecretTrigger"] = npc.get("exposeTrigger")
            _append_memory(npc, f"秘密の露見: {npc.get('exposeTrigger')}")
        if not npc.get("knownWeakness") and float(npc["weaknessPressure"]) >= 3.0:
            npc["knownWeakness"] = npc["weakness"]
            npc["lastWeaknessTrigger"] = npc.get("weaknessTrigger")
            _append_memory(npc, f"弱みが表に出た: {npc.get('weaknessTrigger')}")


def _reaction_for_npc(
    npc: Dict[str, Any],
    focus_npc_ids: List[str],
    intent_type: str,
    branch_label: str,
    outcome: str,
) -> tuple[str, str]:
    action_label = choice_label(intent_type)
    note = npc.get("reactionNotes", {}).get(intent_type, "まだこちらの出方を測っている。")
    is_focus = npc["npcId"] in focus_npc_ids
    favored = npc.get("favoredApproach") == intent_type
    resented = npc.get("resentedApproach") == intent_type

    if is_focus and favored and outcome == "success":
        return ("welcome", f"「{branch_label}」での「{action_label}」を、ひとまず役に立つ手と見ている。{note}")
    if is_focus and resented:
        return ("resent", f"「{branch_label}」での「{action_label}」に、話の筋を乱される警戒を強めた。{note}")
    if is_focus and outcome == "failure":
        return ("strained", f"「{branch_label}」の傷を自分の持ち場へ押し返されたと感じている。{note}")
    if is_focus:
        return ("guarded", f"「{branch_label}」のあとも、こちらの次の手を測っている。{note}")
    if favored:
        return ("warm", f"あなたが「{action_label}」を選んだことを、まだ好意的に見ている。{note}")
    if resented:
        return ("cold", f"こちらが「{action_label}」を重ねるたび、距離を取り直している。{note}")
    return ("guarded", f"まだこちらの出方を測っている。{note}")


def _apply_effect_bundle(
    campaign_state: Dict[str, Any],
    effect_bundle: Dict[str, Any],
    intent_type: str,
    branch_label: str,
    outcome: str,
    focus_npc_ids: List[str],
) -> None:
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    event = _current_event(campaign_state)
    hub["stability"] = _clamp(hub["stability"] + float(effect_bundle.get("hub_stability", 0.0)))
    hub["heat"] = _clamp(hub["heat"] + float(effect_bundle.get("hub_heat", 0.0)))
    hub["supply"] = _clamp(hub["supply"] + float(effect_bundle.get("hub_supply", 0.0)))
    dungeon["sealIntegrity"] = _clamp(dungeon["sealIntegrity"] + float(effect_bundle.get("dungeon_seal", 0.0)))
    dungeon["threat"] = _clamp(dungeon["threat"] + float(effect_bundle.get("dungeon_threat", 0.0)))
    event["pressure"] = _clamp(event["pressure"] + float(effect_bundle.get("pressure", 0.0)))
    depth_delta = int(effect_bundle.get("dungeon_depth", 0))
    if depth_delta:
        dungeon["depth"] = max(0, min(int(dungeon["maxDepth"]), int(dungeon["depth"]) + depth_delta))
    for npc_id, trust_delta in effect_bundle.get("trust", {}).items():
        campaign_state["npcs"][npc_id]["trust"] = _clamp(campaign_state["npcs"][npc_id]["trust"] + float(trust_delta))
    for npc_id, stress_delta in effect_bundle.get("stress", {}).items():
        campaign_state["npcs"][npc_id]["stress"] = _clamp(campaign_state["npcs"][npc_id]["stress"] + float(stress_delta))
    for update in effect_bundle.get("hints", []):
        npc = campaign_state["npcs"][update["npcId"]]
        _secret_update(npc, update["mode"])
        npc["lastSecretTrigger"] = npc.get("hintTrigger") if update["mode"] == "hint" else npc.get("exposeTrigger")
        npc["secretPressure"] = 2.6 if update["mode"] == "hint" else 5.0
        _append_memory(npc, f"秘密の気配: {npc['secretHint']}" if update["mode"] == "hint" else f"秘密が表に出た: {npc['secret']}")
    for weakness in effect_bundle.get("weaknesses", []):
        npc = campaign_state["npcs"][weakness["npcId"]]
        npc["knownWeakness"] = weakness["text"]
        npc["weaknessPressure"] = max(3.0, float(npc.get("weaknessPressure", 0.0)))
        npc["lastWeaknessTrigger"] = npc.get("weaknessTrigger")
        _append_memory(npc, f"弱点が露わになった: {weakness['text']}")
    marks = list(campaign_state.get("worldMarks", []))
    marks.extend(effect_bundle.get("marks", []))
    campaign_state["worldMarks"] = marks[-8:]
    _advance_npc_arcs(campaign_state, focus_npc_ids, intent_type, outcome)
    for npc in campaign_state["npcs"].values():
        trace_delta = _trace_adjustments(campaign_state, npc, intent_type)
        npc["trust"] = _clamp(npc["trust"] + trace_delta["trust"])
        npc["stress"] = _clamp(npc["stress"] + trace_delta["stress"])
        reaction_mode, reaction = _reaction_for_npc(npc, focus_npc_ids, intent_type, branch_label, outcome)
        if npc["npcId"] in effect_bundle.get("trust", {}):
            reaction = f"{reaction} 今回は恩義も感じている。"
        elif npc["npcId"] in effect_bundle.get("stress", {}):
            reaction = f"{reaction} 今回の傷は簡単には忘れない。"
        npc["lastReaction"] = reaction
        npc["lastReactionMode"] = reaction_mode
        _append_memory(npc, reaction)


def _session_score(campaign_state: Dict[str, Any]) -> float:
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    pressures = [float(event["pressure"]) for event in campaign_state["events"]["catalog"].values()]
    avg_pressure = sum(pressures) / max(1, len(pressures))
    npc_values = list(campaign_state["npcs"].values())
    avg_trust = sum(float(npc["trust"]) for npc in npc_values) / max(1, len(npc_values))
    avg_stress = sum(float(npc["stress"]) for npc in npc_values) / max(1, len(npc_values))
    return round(
        float(hub["stability"]) * 0.34
        + float(hub["supply"]) * 0.24
        - float(hub["heat"]) * 0.28
        + float(dungeon["sealIntegrity"]) * 0.36
        - float(dungeon["threat"]) * 0.32
        + int(dungeon["depth"]) * 3.2
        + avg_trust * 0.22
        - avg_stress * 0.18
        - avg_pressure * 0.26,
        1,
    )


def _ending_forecast(campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    score = round(_session_score(campaign_state) - _vice_taboo_ending_penalty(campaign_state), 1)
    dominant_choice = _dominant_choice(campaign_state.get("choiceStats", {}))
    if score >= -5.5:
        return {"title": "鐘路に猶予が残りそうだ", "tone": "steady", "score": score, "dominantChoice": dominant_choice, "summary": "拠点と坑路の両方にまだ持ち直しの余地がある。"}
    if score >= -12.0:
        return {"title": "借りで繋ぐ結末が見えている", "tone": "mixed", "score": score, "dominantChoice": dominant_choice, "summary": "どこかを救えば別の場所に負債が残る。"}
    return {"title": "歪みを抱えた終幕が近い", "tone": "grim", "score": score, "dominantChoice": dominant_choice, "summary": "次セッションまで重い余波を持ち越しそうだ。"}


def _apply_session_legacy(campaign_state: Dict[str, Any], tone: str) -> Dict[str, float]:
    if tone == "steady":
        return {"hub_stability": 4.0, "hub_heat": -4.0, "dungeon_seal": 3.5, "dungeon_threat": -3.0, "all_pressure": -4.0, "npc_trust": 1.6, "npc_stress": -1.6}
    if tone == "mixed":
        return {"hub_supply": 2.0, "hub_heat": 1.0, "dungeon_seal": 1.4, "dungeon_threat": 1.0, "all_pressure": -0.8, "npc_trust": 0.6, "npc_stress": 0.6}
    return {"hub_stability": -3.0, "hub_heat": 4.0, "dungeon_seal": -3.2, "dungeon_threat": 4.2, "all_pressure": 4.0, "npc_trust": -0.6, "npc_stress": 2.2}


def _mortality_risk_score(label: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(label, 2)


def _turnover_score(npc: Dict[str, Any], tone: str) -> float:
    score = float(npc.get("stress", 0.0)) - float(npc.get("trust", 0.0)) * 0.15
    score += _mortality_risk_score(str(npc.get("mortalityRisk", "medium"))) * 12.0
    score += {"grim": 10.0, "mixed": 4.0, "steady": 0.0}.get(tone, 0.0)
    if npc.get("secretState") == "exposed":
        score += 16.0
    elif npc.get("secretState") == "hinted":
        score += 6.0
    if npc.get("knownWeakness"):
        score += 8.0
    return round(score, 1)


def _replacement_reason(npc: Dict[str, Any], tone: str, session_number: int) -> str:
    occupant_status = str(npc.get("occupantStatus", "alive"))
    if occupant_status == "dead":
        return "死亡"
    if occupant_status == "missing":
        return "失踪"
    if occupant_status == "retired":
        return "引退"
    if occupant_status == "stripped":
        return "役職剥奪"
    if occupant_status == "suspended":
        return "役職剥奪"
    pivot = (session_number + len(str(npc.get("roleSlotId", "")))) % 6
    if npc.get("secretState") == "exposed" and npc.get("knownWeakness"):
        if tone == "grim" and float(npc.get("stress", 0.0)) >= 78:
            return "役職剥奪" if pivot % 2 == 0 else "粛清"
        return "引退" if pivot % 2 == 0 else "継承"
    if tone == "grim" and _mortality_risk_score(str(npc.get("mortalityRisk", "medium"))) >= 3:
        return ["死亡", "失踪", "粛清"][pivot % 3]
    if float(npc.get("stress", 0.0)) >= 74:
        return "引退"
    return "継承"


def _replacement_status(reason: str) -> str:
    return {
        "死亡": "dead",
        "失踪": "missing",
        "引退": "retired",
        "粛清": "dead",
        "昇神": "missing",
        "役職剥奪": "retired",
        "継承": "retired",
    }.get(reason, "retired")


def _replace_role_slot_occupant(campaign_state: Dict[str, Any], role_slot_id: str, reason: str, session_number: int) -> None:
    blueprints = _slot_blueprint_map()
    npc = campaign_state["npcs"][role_slot_id]
    blueprint = blueprints[role_slot_id]
    previous_name = npc["displayName"]
    previous_status = _replacement_status(reason)
    history = list(npc.get("occupantHistory", []))
    history.append(
        {
            "occupantId": npc["occupantId"],
            "displayName": previous_name,
            "ageState": npc.get("ageState", "不詳"),
            "finalStatus": previous_status,
            "sessionNumber": session_number,
            "reason": reason,
        }
    )
    npc["occupantHistory"] = history[-6:]

    next_index = int(npc.get("occupantIndex", 0)) + 1
    next_serial = int(npc.get("occupantSerial", 0)) + 1
    template = _occupant_template(blueprint, next_index)

    npc["occupantId"] = template["occupantId"]
    npc["occupantIndex"] = next_index % len(blueprint["occupantTemplates"])
    npc["occupantSerial"] = next_serial
    npc["occupantStatus"] = "alive"
    npc["displayName"] = template["displayName"]
    npc["ageState"] = template["ageState"]
    npc["secret"] = template["secret"]
    npc["secretHint"] = template["secretHint"]
    npc["hintTrigger"] = template["hintTrigger"]
    npc["exposeTrigger"] = template["exposeTrigger"]
    npc["weakness"] = template["weakness"]
    npc["weaknessTrigger"] = template["weaknessTrigger"]
    npc["secretState"] = "hidden"
    npc["secretPressure"] = 0.0
    npc["lastSecretTrigger"] = None
    npc["knownWeakness"] = None
    npc["weaknessPressure"] = 0.0
    npc["lastWeaknessTrigger"] = None
    npc["trust"] = _clamp((blueprint["baseTrust"] * 0.72) + float(npc.get("trust", 0.0)) * 0.18)
    npc["stress"] = _clamp((blueprint["baseStress"] * 0.78) + float(npc.get("stress", 0.0)) * 0.12 + 6.0)
    npc["memory"] = [f"{previous_name}が{reason}で退き、{npc['displayName']}が{npc['roleLabel']}の座に就いた。"]
    npc["lastReaction"] = f"{previous_name}が{reason}で退き、いまは{npc['displayName']}が様子を見ている。"
    npc["lastReactionMode"] = "guarded"
    npc["lastReplacement"] = {
        "previousOccupantName": previous_name,
        "newOccupantName": npc["displayName"],
        "reason": reason,
        "sessionNumber": session_number,
    }


def _advance_role_slot_occupants(campaign_state: Dict[str, Any], ending: Dict[str, Any]) -> None:
    for npc in campaign_state["npcs"].values():
        npc["lastReplacement"] = None

    ordered = sorted(
        campaign_state["npcs"].values(),
        key=lambda npc: (_turnover_score(npc, ending["tone"]), npc["roleSlotId"]),
        reverse=True,
    )
    threshold = 92.0 if ending["tone"] == "grim" else 104.0
    max_replacements = 2 if ending["tone"] == "grim" and float(ending.get("score", 0.0)) <= -18.0 else 1
    selected = [npc for npc in ordered if _turnover_score(npc, ending["tone"]) >= threshold][:max_replacements]
    if not selected:
        fallback = next(
            (
                npc
                for npc in ordered
                if npc.get("occupantStatus") in {"dead", "missing", "suspended"}
                or (npc.get("secretState") == "exposed" and npc.get("knownWeakness"))
            ),
            None,
        )
        if fallback:
            selected = [fallback]
    if not selected:
        return

    marks = list(campaign_state.get("worldMarks", []))
    for npc in selected:
        reason = _replacement_reason(npc, ending["tone"], int(ending["sessionNumber"]))
        if reason not in set(npc.get("replacementConditions", [])) | {"継承"}:
            continue
        _replace_role_slot_occupant(campaign_state, npc["roleSlotId"], reason, int(ending["sessionNumber"]))
        replacement = campaign_state["npcs"][npc["roleSlotId"]]["lastReplacement"]
        marks.append(
            f"{campaign_state['npcs'][npc['roleSlotId']]['roleLabel']}の座は{replacement['newOccupantName']}へ引き継がれた。"
        )
    campaign_state["worldMarks"] = marks[-8:]


def _ending_title(forecast: Dict[str, Any]) -> str:
    titles = {
        "steady": {
            "observe": "鐘脈を見切った薄明",
            "inspect": "帳簿に灯を残す夜",
            "speak": "停戦に声を残す夜",
            "intervene": "退路をこじ開けた夜",
        },
        "mixed": {
            "observe": "借り図を抱えた朝",
            "inspect": "薄明の裏帳面",
            "speak": "借り声の停戦",
            "intervene": "継ぎはぎの退路",
        },
        "grim": {
            "observe": "鐘音を抱えた夜営",
            "inspect": "焦げた目録の夜",
            "speak": "言い残しの停戦",
            "intervene": "崩落を越えた夜営",
        },
    }
    return titles.get(forecast["tone"], {}).get(forecast["dominantChoice"], "夜に残る余波")


def _latest_world_mark(campaign_state: Dict[str, Any]) -> str:
    marks = [mark for mark in campaign_state.get("worldMarks", []) if not str(mark).startswith("小結末:")]
    return marks[-1] if marks else "大きな傷はまだ定まっていない。"


def _free_action_entries(campaign_state: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    entries = [entry for entry in campaign_state.get("freeActionHistory", []) if isinstance(entry, dict)]
    return entries[-limit:]


def _archive_for_role_slot(campaign_state: Dict[str, Any], role_slot_id: str) -> Dict[str, Any] | None:
    for entry in _prioritized_archive_entries(campaign_state, limit=8):
        role_slot_ids = {
            *(str(raw_role_slot_id).strip() for raw_role_slot_id in entry.get("roleSlotEchoIds", [])),
            str(entry.get("keyRoleSlotId") or "").strip(),
        }
        if role_slot_id in role_slot_ids:
            return entry
    return None


def _role_slot_repercussion_mode(suspicion: float, distrust: float, retaliation: float) -> str:
    weighted = {
        "suspicion": suspicion,
        "distrust": distrust * 1.05,
        "retaliation": retaliation * 1.12,
    }
    return sorted(weighted, key=lambda key: (weighted[key], key), reverse=True)[0]


def _top_role_slot_repercussions(campaign_state: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    ensure_role_slot_repercussions(campaign_state)
    current_event = campaign_state["events"]["catalog"].get(campaign_state.get("currentEventId"), {})
    current_focus_slots = {
        str(role_slot_id)
        for branch in current_event.get("branches", [])
        for role_slot_id in branch.get("focusNpcIds", [])
    }
    ranked: List[Dict[str, Any]] = []
    for role_slot_id in NPC_ORDER:
        npc = campaign_state.get("npcs", {}).get(role_slot_id)
        if not isinstance(npc, dict):
            continue
        suspicion = _role_slot_repercussion_value(campaign_state, "roleSlotSuspicion", role_slot_id)
        distrust = _role_slot_repercussion_value(campaign_state, "roleSlotDistrust", role_slot_id)
        retaliation = _role_slot_repercussion_value(campaign_state, "roleSlotRetaliation", role_slot_id)
        base_total = round(suspicion + distrust * 1.08 + retaliation * 1.16, 1)
        if base_total < 7.5:
            continue
        archive_entry = _archive_for_role_slot(campaign_state, role_slot_id)
        relevance = 8.0 if role_slot_id in current_focus_slots else 0.0
        if archive_entry:
            relevance += min(8.0, float(archive_entry.get("_priority", {}).get("total", 0.0)) * 0.08)
        ranked.append(
            {
                "roleSlotId": role_slot_id,
                "roleLabel": str(npc.get("roleLabel") or "関係者"),
                "occupantLabel": str(npc.get("displayName") or npc.get("roleLabel") or "関係者"),
                "suspicion": suspicion,
                "distrust": distrust,
                "retaliation": retaliation,
                "mode": _role_slot_repercussion_mode(suspicion, distrust, retaliation),
                "archiveEntry": archive_entry,
                "score": round(base_total + relevance, 1),
            }
        )
    ranked.sort(
        key=lambda entry: (
            float(entry["score"]),
            float(entry["retaliation"]),
            float(entry["distrust"]),
            float(entry["suspicion"]),
        ),
        reverse=True,
    )
    return ranked[:limit]


def _vice_taboo_ending_penalty(campaign_state: Dict[str, Any]) -> float:
    history = _free_action_entries(campaign_state, limit=3)
    if not history:
        return 0.0
    penalty = 0.0
    penalty += float(campaign_state.get("publicInfamy", 0.0)) * 0.22
    penalty += float(campaign_state.get("hiddenCrimes", 0.0)) * 0.28
    penalty += max(0.0, float(campaign_state.get("ritualPollution", 0.0)) - 40.0) * 0.03
    penalty += max(0.0, float(campaign_state.get("publicShame", 0.0)) - 28.0) * 0.02
    penalty += len(list(campaign_state.get("viceTrace", []))[-3:]) * 0.7
    penalty += len(list(campaign_state.get("tabooTrace", []))[-3:]) * 1.0
    for entry in history[-2:]:
        adjudication = entry.get("adjudication", {})
        normalized = entry.get("normalizedIntent", {})
        penalty += {
            "success": 0.1,
            "partial_success": 0.5,
            "failure": 0.9,
            "exposed": 1.6,
            "concealed_success": 0.8,
            "backlash": 2.2,
        }.get(str(adjudication.get("outcome", "")), 0.3)
        penalty += {
            "unseen": 0.0,
            "suspected": 0.4,
            "contested": 0.7,
            "exposed": 1.3,
        }.get(str(adjudication.get("discovery_state", "")), 0.0)
        if normalized.get("vice_tags"):
            penalty += 0.3
        if normalized.get("taboo_tags"):
            penalty += 0.6
    return min(12.0, round(penalty, 1))


def _free_action_reverberation(campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    history = _free_action_entries(campaign_state, limit=2)
    empty = {
        "active": False,
        "scarText": "",
        "summaryClause": "",
        "legacyClause": "",
        "carryClause": "",
        "aftertasteClause": "",
        "eventCandidates": [],
        "pressureLines": [],
        "npcCarryOvers": [],
    }
    if not history:
        return empty

    last_entry = history[-1]
    summary = str(last_entry.get("summary") or "自由行動").strip()
    adjudication = last_entry.get("adjudication", {})
    normalized = last_entry.get("normalizedIntent", {})
    outcome = str(adjudication.get("outcome", "unknown"))
    discovery = str(adjudication.get("discovery_state", "unseen"))
    vice_tags = [str(tag) for tag in normalized.get("vice_tags", []) if str(tag).strip()]
    taboo_tags = [str(tag) for tag in normalized.get("taboo_tags", []) if str(tag).strip()]
    hidden_crimes = float(campaign_state.get("hiddenCrimes", 0.0))
    public_infamy = float(campaign_state.get("publicInfamy", 0.0))
    ritual_pollution = float(campaign_state.get("ritualPollution", 0.0))
    public_shame = float(campaign_state.get("publicShame", 0.0))

    targeted_slots = [
        campaign_state["npcs"][role_slot_id]
        for role_slot_id in normalized.get("target_role_slots", [])
        if role_slot_id in campaign_state.get("npcs", {})
    ]
    primary_slot = targeted_slots[0] if targeted_slots else None
    primary_role_label = primary_slot["roleLabel"] if primary_slot else "関係者"

    if discovery == "exposed":
        scar_text = f"「{summary}」がもう隠しきれないこと"
        summary_clause = f"「{summary}」の責任追及も始まっている"
    elif discovery == "contested":
        scar_text = f"「{summary}」を誰がやったかで見立てが割れていること"
        summary_clause = f"「{summary}」の犯人像が割れたままだ"
    elif discovery == "suspected":
        scar_text = f"「{summary}」を疑う視線"
        summary_clause = f"「{summary}」の痕をまだ疑われている"
    elif hidden_crimes >= 2.5 or outcome == "concealed_success":
        scar_text = f"「{summary}」の痕をまだ隠していること"
        summary_clause = f"「{summary}」の痕をまだ隠し切れていない"
    else:
        scar_text = f"「{summary}」の後ろ暗さ"
        summary_clause = f"「{summary}」の後ろ暗さが残った"

    if taboo_tags and ritual_pollution >= 35.0:
        scar_text = f"{scar_text}と、祈りと封印に残った濁り"
    elif vice_tags and public_infamy >= 3.0:
        scar_text = f"{scar_text}と、人づてに広がる悪評"

    legacy_parts: List[str] = []
    if taboo_tags and ritual_pollution >= 35.0:
        legacy_parts.append("禁じ手の濁りが祈りと封印に貼りつき、後始末が次節まで要る")
    if public_infamy >= 3.0 or public_shame >= 28.0:
        legacy_parts.append("悪評が人づてに広がり、関わらなかった座まで警戒し始める")
    if hidden_crimes >= 2.5 and discovery != "exposed":
        legacy_parts.append("まだ表に出ていない行いが残り、検分が入れば露見へ傾く")
    legacy_clause = "。".join(legacy_parts[:2])
    if legacy_clause:
        legacy_clause = f"{legacy_clause}。"

    carry_parts: List[str] = []
    if discovery == "exposed":
        carry_parts.append(f"「{summary}」の責任追及が始まり、{primary_role_label}の座ごと詮議と報復が続く")
    elif discovery == "contested":
        carry_parts.append(f"「{summary}」の犯人像が割れたままで、{primary_role_label}の座をめぐる疑い合いが続く")
    elif discovery == "suspected":
        carry_parts.append(f"「{summary}」を疑う視線が{primary_role_label}の座へ残り、出入りと判断が厳しくなる")
    elif hidden_crimes >= 2.5:
        carry_parts.append(f"「{summary}」の痕はまだ隠れており、帳簿合わせや検分ひとつで露見へ転ぶ")
    if taboo_tags and ritual_pollution >= 35.0:
        carry_parts.append("禁じ手の濁りを洗う検分が入り、祈りと封印の両方に負担が返ってくる")
    elif public_infamy >= 3.0:
        carry_parts.append("悪評が役目をまたいで広がり、無関係だった座にも不信が及ぶ")
    carry_clause = "。".join(carry_parts[:2])
    if carry_clause:
        carry_clause = f"{carry_clause}。"

    if primary_slot:
        if discovery == "exposed":
            aftertaste_clause = f"{primary_slot['displayName']}は「{summary}」の筋を掴み、静かに報いの機会をうかがっている。"
        elif discovery in {"suspected", "contested"}:
            aftertaste_clause = f"{primary_slot['displayName']}は「{summary}」の違和感を忘れず、同じ役目に近づく者を簡単には通さない。"
        elif taboo_tags and ritual_pollution >= 35.0:
            aftertaste_clause = f"{primary_slot['displayName']}は禁じ手の後始末を押しつけられたと感じ、祈りの言葉まで慎重になっている。"
        elif hidden_crimes >= 2.5:
            aftertaste_clause = f"{primary_slot['displayName']}は証拠を掴めないままでも、「{summary}」の痕を埋めた誰かがいると見ている。"
        else:
            aftertaste_clause = f"{primary_slot['displayName']}は「{summary}」の後ろ暗さを覚え、判断をひとつ分だけ慎重にしている。"
    else:
        aftertaste_clause = ""

    event_candidates: List[str] = []
    if discovery == "exposed":
        event_candidates.append(f"「{summary}」の責任追及: もう隠しきれない行いが、役職ごとの詮議へ転びやすい。")
    elif hidden_crimes >= 2.5:
        event_candidates.append(f"「{summary}」の痕の洗い出し: まだ表に出ていない不正が、検分ひとつで主事件へ育ちやすい。")
    if public_infamy >= 3.0 or public_shame >= 28.0:
        event_candidates.append(f"「{summary}」の悪評の拡散: 噂が別の座へ飛び火し、無関係だった役目まで巻き込みやすい。")
    if taboo_tags and ritual_pollution >= 35.0:
        event_candidates.append("禁じ手の検分: 祈りと封印に残った濁りを洗う動きが、次の主事件になりやすい。")
    if len(history) >= 2 and (vice_tags or taboo_tags):
        event_candidates.append("重なった後ろ暗い手の後始末: 同じ節で積み重なった不正が、ひとつの火種にまとまりかけている。")

    pressure_lines: List[str] = []
    if hidden_crimes >= 2.5:
        pressure_lines.append("まだ表に出ていない不正が残り、帳簿合わせや検分が入れば露見へ傾く。")
    if public_infamy >= 3.0 or public_shame >= 28.0:
        pressure_lines.append("悪評が人づてに広がり、同じ役目にいる者まで疑われやすい。")
    if taboo_tags and ritual_pollution >= 35.0:
        pressure_lines.append("禁じ手の濁りが残り、祈りと封印のどちらにも後始末が要る。")

    npc_lines: List[str] = []
    for npc in targeted_slots[:2]:
        if discovery == "exposed":
            line = f"{npc['roleLabel']}: {npc['displayName']}は「{summary}」の筋を掴み、関わった相手への詮議と報復を考えている。"
        elif discovery == "contested":
            line = f"{npc['roleLabel']}: {npc['displayName']}は「{summary}」の犯人像を絞れず、同じ座全体への不信を深めている。"
        elif discovery == "suspected":
            line = f"{npc['roleLabel']}: {npc['displayName']}は「{summary}」の違和感を覚え、出入りする者を厳しく見ている。"
        elif hidden_crimes >= 2.5 or outcome == "concealed_success":
            line = f"{npc['roleLabel']}: {npc['displayName']}は証拠を掴めないまま、「{summary}」の痕を埋めた誰かがいると見ている。"
        else:
            line = f"{npc['roleLabel']}: {npc['displayName']}は「{summary}」の後ろ暗さを忘れず、同じ役目への不信を残している。"
        if taboo_tags and outcome in {"failure", "exposed", "backlash"}:
            line = f"{line.rstrip('。')}。祈りや封印の後始末が、その座への不信をさらに強めている。"
        npc_lines.append(line)

    return {
        "active": True,
        "scarText": scar_text,
        "summaryClause": summary_clause,
        "legacyClause": legacy_clause,
        "carryClause": carry_clause,
        "aftertasteClause": aftertaste_clause,
        "eventCandidates": _dedupe_lines(event_candidates, limit=4),
        "pressureLines": _dedupe_lines(pressure_lines, limit=3),
        "npcCarryOvers": _dedupe_lines(npc_lines, limit=3),
    }


def _session_focus_scores(session_entries: List[Dict[str, Any]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for index, entry in enumerate(session_entries, start=1):
        base = 1.0 + index * 0.35
        if entry.get("outcome") == "failure":
            base += 0.5
        elif entry.get("outcome") == "partial_success":
            base += 0.2
        for npc_id in entry.get("focusNpcIds", []):
            scores[npc_id] = round(scores.get(npc_id, 0.0) + base, 2)
    return scores


def _session_key_npc(campaign_state: Dict[str, Any], session_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    focus_scores = _session_focus_scores(session_entries)
    npcs = campaign_state["npcs"]
    if focus_scores:
        return max(
            npcs.values(),
            key=lambda npc: (
                focus_scores.get(npc["npcId"], 0.0),
                float(npc["stress"]) * 0.08 + float(npc["trust"]) * 0.04,
                1.0 if npc.get("secretState") == "exposed" else 0.0,
                1.0 if npc.get("knownWeakness") else 0.0,
            ),
        )
    return max(npcs.values(), key=lambda npc: float(npc["trust"]) - float(npc["stress"]) * 0.5)


def _preserved_targets(campaign_state: Dict[str, Any]) -> list[str]:
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    npcs = list(campaign_state["npcs"].values())
    values: list[str] = []
    if float(hub["stability"]) >= 58:
        values.append(str(hub.get("protectedAsset") or hub["label"]))
    if float(hub["supply"]) >= 60:
        values.append(f"{hub['label']}へ届く補給線")
    if float(dungeon["sealIntegrity"]) >= 60:
        values.append(str(dungeon.get("protectedAsset") or dungeon["label"]))
    if sum(float(npc["trust"]) for npc in npcs) / max(1, len(npcs)) >= 54:
        values.append("まだ切れていない協力線")
    ordered = list(dict.fromkeys(values))
    return ordered or [f"{dungeon['label']}から戻る細い退路"]


def _lost_targets(campaign_state: Dict[str, Any]) -> list[str]:
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    current_event = max(campaign_state["events"]["catalog"].values(), key=lambda item: float(item["pressure"]))
    values: list[str] = []
    if float(hub["heat"]) >= 55:
        values.append(str(hub.get("lostAsset") or f"{hub['label']}の落ち着き"))
    if float(dungeon["threat"]) >= 58:
        values.append(str(dungeon.get("lostAsset") or f"{dungeon['label']}の安全"))
    if float(current_event["pressure"]) >= 68:
        values.append(f"{current_event['label']}の猶予")
    exposed = [npc["displayName"] for npc in campaign_state["npcs"].values() if npc.get("secretState") == "exposed"]
    if exposed:
        values.append(f"{exposed[0]}の隠し事")
    ordered = list(dict.fromkeys(values))
    return ordered or [f"{hub['label']}に残った小さな代償"]


def _protected_text(label: str, key_npc_label: str) -> str:
    mapping = {
        "まだ切れていない協力線": f"{key_npc_label}たちと辛うじて残した協力線",
    }
    return mapping.get(label, label)


def _lost_text(label: str, tone: str) -> str:
    if label.endswith("小さな代償"):
        return "小さくは済んだが残った代償"
    return label


def _main_wound_text(campaign_state: Dict[str, Any], session_entries: List[Dict[str, Any]]) -> str:
    if session_entries:
        last_entry = session_entries[-1]
        branch_label = last_entry["branchLabel"]
        outcome = last_entry.get("outcome")
        if outcome == "failure":
            return f"「{branch_label}」で広がった傷"
        if outcome == "partial_success":
            return f"「{branch_label}」で抱えた借り"
        return f"「{branch_label}」で背負った代償"
    mark = _latest_world_mark(campaign_state).rstrip("。")
    return f"{mark}こと"


def _carried_forward_text(
    campaign_state: Dict[str, Any],
    session_entries: List[Dict[str, Any]],
    tone: str,
    key_npc: Dict[str, Any],
    main_wound: str,
) -> str:
    reverberation = _free_action_reverberation(campaign_state)
    current_event = max(campaign_state["events"]["catalog"].values(), key=lambda item: float(item["pressure"]))
    conflict_label = key_npc.get("conflictsWithLabel", "相手")
    carry_hook = f"{key_npc['displayName']}と{conflict_label}の溝"
    if session_entries:
        last_branch = session_entries[-1]["branchLabel"]
        if tone == "steady":
            base = f"{current_event['label']}の圧は少し退いたが、{main_wound}と{carry_hook}は次節へ残る。"
            if reverberation["carryClause"]:
                return f"{base} {reverberation['carryClause']}"
            return base
        if tone == "mixed":
            base = f"{current_event['label']}の圧と「{last_branch}」の後腐れ、{carry_hook}が次のセッションの借りになる。"
            if reverberation["carryClause"]:
                return f"{base} {reverberation['carryClause']}"
            return base
        base = f"{current_event['label']}の圧に加え、「{last_branch}」の傷と{carry_hook}が次節を重くする。"
        if reverberation["carryClause"]:
            return f"{base} {reverberation['carryClause']}"
        return base
    if tone == "steady":
        base = f"{current_event['label']}の圧は少し退いたが、{main_wound}は次節へ残る。"
        if reverberation["carryClause"]:
            return f"{base} {reverberation['carryClause']}"
        return base
    if tone == "mixed":
        base = f"{current_event['label']}の圧と{main_wound}が次のセッションの借りになる。"
        if reverberation["carryClause"]:
            return f"{base} {reverberation['carryClause']}"
        return base
    base = f"{current_event['label']}の圧と{main_wound}が次節を重くする。"
    if reverberation["carryClause"]:
        return f"{base} {reverberation['carryClause']}"
    return base


def _ending_aftertaste(
    key_npc: Dict[str, Any],
    tone: str,
    protected: str,
    lost: str,
    campaign_state: Dict[str, Any],
) -> str:
    reverberation = _free_action_reverberation(campaign_state)
    reaction = str(key_npc.get("lastReaction", "まだ言葉にならない余波が残った。")).strip()
    reaction_head = reaction.split("。")[0].strip() or reaction.rstrip("。")
    if tone == "steady":
        base = f"{key_npc['displayName']}は{protected}が残ったことに口を閉ざしつつも、{reaction_head}。"
        if reverberation["aftertasteClause"]:
            return f"{base} {reverberation['aftertasteClause']}"
        return base
    if tone == "mixed":
        base = f"{key_npc['displayName']}は{protected}を繋いだ手応えも知っているが、{lost}にできた借りを忘れていない。"
        if reverberation["aftertasteClause"]:
            return f"{base} {reverberation['aftertasteClause']}"
        return base
    base = f"{key_npc['displayName']}は{lost}を抱えたまま、{reaction_head}。"
    if reverberation["aftertasteClause"]:
        return f"{base} {reverberation['aftertasteClause']}"
    return base


def _finalize_session(campaign_state: Dict[str, Any], session_number: int) -> Dict[str, Any]:
    session_entries = _session_entries(campaign_state, session_number)
    forecast = _ending_forecast(campaign_state)
    title = _ending_title(forecast)
    key_npc = _session_key_npc(campaign_state, session_entries)
    reverberation = _free_action_reverberation(campaign_state)
    preserved = _preserved_targets(campaign_state)
    lost = _lost_targets(campaign_state)
    protected_text = _protected_text(preserved[0], key_npc["displayName"])
    lost_text = _lost_text(lost[0], forecast["tone"])
    remained = _main_wound_text(campaign_state, session_entries)
    if reverberation["scarText"]:
        remained = f"{remained}と、{reverberation['scarText']}"
    carried_forward = _carried_forward_text(campaign_state, session_entries, forecast["tone"], key_npc, remained)
    if forecast["tone"] == "steady":
        summary = f"{key_npc['displayName']}が踏みとどまり、{protected_text}は守れた。{remained}は残ったが、{lost_text}はまだ手放していない。"
        legacy_text = f"{protected_text}はまだ残る。街道の熱は少し下がり、坑路の封印はひと息つく。"
    elif forecast["tone"] == "mixed":
        summary = f"{key_npc['displayName']}を軸に{protected_text}は繋いだ。だが、{lost_text}は削れ、{remained}が次の借りになった。"
        legacy_text = f"{protected_text}は残ったが、{lost_text}の穴埋めは次節へ回る。"
    else:
        summary = f"{key_npc['displayName']}でも{lost_text}は守り切れず、{remained}が重く残った。{protected_text}だけを拾って夜を越えた。"
        legacy_text = f"{lost_text}の傷は閉じず、拠点と坑路の両方に疲労が残る。"
    if reverberation["summaryClause"]:
        prefix = {"steady": "ただし", "mixed": "さらに", "grim": "そのうえ"}[forecast["tone"]]
        summary = f"{summary} {prefix}、{reverberation['summaryClause']}。"
    if reverberation["legacyClause"]:
        legacy_text = f"{legacy_text} {reverberation['legacyClause']}"
    legacy = _apply_session_legacy(campaign_state, forecast["tone"])
    ending = {
        "sessionNumber": session_number,
        "title": title,
        "tone": forecast["tone"],
        "dominantChoice": forecast["dominantChoice"],
        "keyNpcId": key_npc["npcId"],
        "keyRoleSlotId": key_npc["npcId"],
        "keyRoleLabel": key_npc["roleLabel"],
        "keyNpcLabel": key_npc["displayName"],
        "summary": summary,
        "legacyEffect": legacy_text,
        "whatRemained": remained,
        "protected": protected_text,
        "lost": lost_text,
        "carriedForward": carried_forward,
        "keyNpcAftertaste": _ending_aftertaste(key_npc, forecast["tone"], protected_text, lost_text, campaign_state),
        "score": forecast["score"],
        "recentBranches": [entry["branchLabel"] for entry in session_entries[-3:]],
    }
    return ending


def advance_campaign_state(
    world_state: Dict[str, Any],
    choice_id: str,
    intent: Dict[str, Any],
    resolution: Dict[str, Any],
) -> Dict[str, Any]:
    state = ensure_campaign_state(world_state)
    campaign = copy.deepcopy(state["campaign_state"])
    hub = campaign["hub"]
    dungeon = campaign["dungeon"]
    event = _current_event(campaign)
    session_before = campaign["session"]
    outcome = str(resolution.get("outcome", "unknown"))
    intent_type = str(intent.get("intent_type", choice_id))
    swing = _swing_for_outcome(outcome)
    branch = _pick_branch(event, intent_type, campaign)
    branch_note = branch["notes"][outcome]
    branch_fx = branch["fx"][outcome]

    event_pressure_before = float(event["pressure"])
    hub_stability_before = float(hub["stability"])
    hub_heat_before = float(hub["heat"])
    hub_supply_before = float(hub["supply"])
    dungeon_depth_before = int(dungeon["depth"])
    dungeon_seal_before = float(dungeon["sealIntegrity"])
    dungeon_threat_before = float(dungeon["threat"])

    if intent_type == "observe":
        hub["heat"] = _clamp(hub["heat"] - swing * 0.22)
        dungeon["sealIntegrity"] = _clamp(dungeon["sealIntegrity"] + swing * 0.34)
        dungeon["threat"] = _clamp(dungeon["threat"] - swing * 0.3)
        if dungeon["depth"] < dungeon["maxDepth"]:
            dungeon["depth"] = int(dungeon["depth"]) + 1
        event["pressure"] = _clamp(event["pressure"] - swing * 1.0)
    elif intent_type == "speak":
        hub["stability"] = _clamp(hub["stability"] + swing * 0.72)
        hub["heat"] = _clamp(hub["heat"] - swing * 0.28)
        event["pressure"] = _clamp(event["pressure"] - swing * 0.92)
    elif intent_type == "inspect":
        hub["supply"] = _clamp(hub["supply"] + swing * 0.66)
        hub["heat"] = _clamp(hub["heat"] - swing * 0.18)
        dungeon["sealIntegrity"] = _clamp(dungeon["sealIntegrity"] + swing * 0.24)
        event["pressure"] = _clamp(event["pressure"] - swing * 0.96)
    elif intent_type == "intervene":
        hub["stability"] = _clamp(hub["stability"] + swing * 0.44)
        hub["heat"] = _clamp(hub["heat"] - swing * 0.42)
        dungeon["sealIntegrity"] = _clamp(dungeon["sealIntegrity"] + swing * 0.64)
        dungeon["threat"] = _clamp(dungeon["threat"] - swing * 0.72)
        if dungeon["depth"] < dungeon["maxDepth"]:
            dungeon["depth"] = int(dungeon["depth"]) + 1
        event["pressure"] = _clamp(event["pressure"] - swing * 1.18)

    for npc_id, deltas in _npc_adjustments(intent_type, swing).items():
        npc = campaign["npcs"][npc_id]
        npc["trust"] = _clamp(npc["trust"] + deltas["trust"])
        npc["stress"] = _clamp(npc["stress"] + deltas["stress"])

    _apply_effect_bundle(campaign, branch_fx, intent_type, branch["label"], outcome, branch.get("focusNpcIds", []))

    campaign["choiceStats"][intent_type] = int(campaign["choiceStats"].get(intent_type, 0)) + 1
    event["lastBranchId"] = branch["branchId"]
    event["lastOutcome"] = outcome
    event["lastOutcomeText"] = branch_note

    choice_entry = {
        "turnCounter": session_before["turnCounter"],
        "sessionNumber": session_before["sessionNumber"],
        "turnInSession": session_before["turnInSession"],
        "choiceId": choice_id,
        "intentType": intent_type,
        "eventId": event["eventId"],
        "eventLabel": event["label"],
        "branchId": branch["branchId"],
        "branchLabel": branch["label"],
        "outcome": outcome,
        "outcomeText": branch_note,
        "pressureBefore": event_pressure_before,
        "pressureAfter": float(event["pressure"]),
        "focusNpcIds": list(branch.get("focusNpcIds", [])),
        "marksAdded": list(branch_fx.get("marks", [])),
    }
    choice_history = list(campaign.get("choiceHistory", []))
    choice_history.append(choice_entry)
    campaign["choiceHistory"] = choice_history[-24:]
    event_history = list(campaign["events"].get("history", []))
    event_history.append(choice_entry)
    campaign["events"]["history"] = event_history[-24:]

    next_session = _session_state(session_before["turnCounter"] + 1)
    ending = None
    if session_before["turnInSession"] == SESSION_TURNS:
        ending = _finalize_session(campaign, session_before["sessionNumber"])
        legacy = _apply_session_legacy(campaign, ending["tone"])
        hub["stability"] = _clamp(hub["stability"] + legacy.get("hub_stability", 0.0))
        hub["heat"] = _clamp(hub["heat"] + legacy.get("hub_heat", 0.0))
        hub["supply"] = _clamp(hub["supply"] + legacy.get("hub_supply", 0.0))
        dungeon["sealIntegrity"] = _clamp(dungeon["sealIntegrity"] + legacy.get("dungeon_seal", 0.0))
        dungeon["threat"] = _clamp(dungeon["threat"] + legacy.get("dungeon_threat", 0.0))
        for current in campaign["events"]["catalog"].values():
            current["pressure"] = _clamp(current["pressure"] + legacy["all_pressure"])
        for npc in campaign["npcs"].values():
            npc["trust"] = _clamp(npc["trust"] + legacy["npc_trust"])
            npc["stress"] = _clamp(npc["stress"] + legacy["npc_stress"])
            _append_memory(npc, f"小結末の余波: {ending['title']}")
        endings = list(campaign.get("sessionEndings", []))
        endings.append(ending)
        campaign["sessionEndings"] = endings[-6:]
        campaign["lastEnding"] = ending
        marks = list(campaign.get("worldMarks", []))
        marks.append(f"小結末: {ending['title']}")
        campaign["worldMarks"] = marks[-8:]

    campaign["lastTransition"] = {
        "choiceId": choice_id,
        "intentType": intent_type,
        "outcome": outcome,
        "turnBefore": session_before["turnInSession"],
        "turnAfter": next_session["turnInSession"],
        "eventId": event["eventId"],
        "eventLabel": event["label"],
        "branchId": branch["branchId"],
        "branchLabel": branch["label"],
        "branchOutcomeText": branch_note,
        "eventPressureBefore": event_pressure_before,
        "eventPressureAfter": float(event["pressure"]),
        "hubStabilityBefore": hub_stability_before,
        "hubStabilityAfter": float(hub["stability"]),
        "hubHeatBefore": hub_heat_before,
        "hubHeatAfter": float(hub["heat"]),
        "hubSupplyBefore": hub_supply_before,
        "hubSupplyAfter": float(hub["supply"]),
        "dungeonDepthBefore": dungeon_depth_before,
        "dungeonDepthAfter": int(dungeon["depth"]),
        "dungeonSealBefore": dungeon_seal_before,
        "dungeonSealAfter": float(dungeon["sealIntegrity"]),
        "dungeonThreatBefore": dungeon_threat_before,
        "dungeonThreatAfter": float(dungeon["threat"]),
        "endingTitle": ending["title"] if ending else None,
    }
    campaign["session"] = next_session
    campaign["currentEventId"] = next_session["eventId"]
    state["campaign_state"] = _refresh_campaign_state(state, campaign)
    return state


def current_event(world_state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_campaign_state(world_state)
    campaign = state["campaign_state"]
    event = copy.deepcopy(_current_event(campaign))
    archive_brief = _archive_scene_brief(campaign)
    composed = compose_event_copy(event)
    composed["summaryText"] = ensure_copy_quality(
        _compose_overlay_sentence(composed["summaryText"], archive_brief.get("eventSummaryText"), "状況を確認している。"),
        "explanation",
    )
    composed["importanceText"] = ensure_copy_quality(
        _compose_overlay_sentence(composed["importanceText"], archive_brief.get("eventImportanceText"), "この事件は放置できない。"),
        "explanation",
    )
    return composed


def current_session(world_state: Dict[str, Any]) -> Dict[str, Any]:
    return ensure_campaign_state(world_state)["campaign_state"]["session"]


def named_cast(world_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    campaign = ensure_campaign_state(world_state)["campaign_state"]
    return [_annotate_npc_with_archive_overlay(campaign, copy.deepcopy(campaign["npcs"][npc_id])) for npc_id in NPC_ORDER]


def current_hub(world_state: Dict[str, Any]) -> Dict[str, Any]:
    return compose_hub_copy(copy.deepcopy(ensure_campaign_state(world_state)["campaign_state"]["hub"]))


def current_dungeon(world_state: Dict[str, Any]) -> Dict[str, Any]:
    return compose_dungeon_copy(copy.deepcopy(ensure_campaign_state(world_state)["campaign_state"]["dungeon"]))


def build_player_trace(world_state: Dict[str, Any]) -> Dict[str, Any]:
    campaign = ensure_campaign_state(world_state)["campaign_state"]
    recent = campaign.get("choiceHistory", [])[-4:]
    dominant_choice = _dominant_choice(campaign.get("choiceStats", {}))
    return compose_player_trace(
        dominant_choice=dominant_choice,
        recent_entries=recent,
        npcs=campaign["npcs"].values(),
        world_marks=list(campaign.get("worldMarks", []))[-4:],
    )


def active_scene_npcs(world_state: Dict[str, Any], faction_ids: List[str]) -> List[Dict[str, Any]]:
    campaign = ensure_campaign_state(world_state)["campaign_state"]
    event = _current_event(campaign)
    branch = _branch_lookup(event, event.get("lastBranchId"))
    focus_ids = branch.get("focusNpcIds", []) if branch else []
    overlay_ids = [npc_id for npc_id in _archive_role_slot_overlays(campaign) if npc_id in campaign["npcs"]]
    theme_order = {
        "institution": [TRUCE_WARDEN_SLOT, LEDGER_CLERK_SLOT, QUARTERMASTER_SLOT, CANTOR_SLOT],
        "hub": [QUARTERMASTER_SLOT, LEDGER_CLERK_SLOT, TRUCE_WARDEN_SLOT, CANTOR_SLOT],
        "dungeon": [TUNNEL_GUIDE_SLOT, RELIC_KEEPER_SLOT, CANTOR_SLOT, TRUCE_WARDEN_SLOT],
    }.get(event["theme"], [TRUCE_WARDEN_SLOT, CANTOR_SLOT, LEDGER_CLERK_SLOT, QUARTERMASTER_SLOT])
    ordered = []
    seen: set[str] = set()
    for npc_id in overlay_ids + focus_ids + theme_order + NPC_ORDER:
        if npc_id in seen:
            continue
        npc = campaign["npcs"][npc_id]
        if npc["affiliationFactionId"] in faction_ids or npc["locationKey"] in {"hub", "dungeon", "world"}:
            ordered.append(_annotate_npc_with_archive_overlay(campaign, copy.deepcopy(npc)))
            seen.add(npc_id)
    return ordered[:3]


def relation_text(npc: Dict[str, Any]) -> str:
    return compose_npc_relation_line(npc)


def emotion_text(npc: Dict[str, Any]) -> str:
    return compose_npc_emotion_line(npc)


def role_text(npc: Dict[str, Any], event: Dict[str, Any]) -> str:
    return compose_npc_role_line(npc, event)


def build_story_guide(world_state: Dict[str, Any], scene_title: str) -> Dict[str, Any]:
    state = ensure_campaign_state(world_state)
    campaign = state["campaign_state"]
    event = current_event(state)
    session = campaign["session"]
    hub = current_hub(state)
    dungeon = current_dungeon(state)
    trace = build_player_trace(state)
    forecast = _ending_forecast(campaign)
    world_pulse = compose_world_pulse_copy(state.get("cycle_state", {}))
    guide = compose_story_guide_copy(scene_title, session, event, hub, dungeon, world_pulse, trace, forecast)
    archive_brief = _archive_scene_brief(campaign)
    guide["now"] = ensure_copy_quality(
        _compose_overlay_sentence(guide["now"], archive_brief.get("storyNowText"), "いまの局面を整理している。"),
        "explanation",
    )
    guide["stakes"] = ensure_copy_quality(
        _compose_overlay_sentence(guide["stakes"], archive_brief.get("storyStakesText"), "この局面の重要性を整理している。"),
        "explanation",
    )
    guide["worldState"] = ensure_copy_quality(
        _compose_overlay_sentence(guide["worldState"], archive_brief.get("worldStateText"), "世界の状態を整理している。"),
        "explanation",
    )
    return guide


def _trim_copy_text(text: object) -> str:
    return str(text or "").strip().rstrip("。！？").strip()


def _overlay_sentence_key(text: object) -> str:
    normalized = _trim_copy_text(text)
    for prefix in (
        "放置すると、",
        "このままでは、",
        "ここで誤ると、",
        "ここで見誤ると、",
        "いま強く戻ってきているのは、",
        "前のセッションの因果として、",
        "隠れた不正の痕として、",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    return normalized


def _compose_overlay_sentence(base: object, extra: object, fallback: str) -> str:
    parts = [_trim_copy_text(base), _trim_copy_text(extra)]
    deduped: List[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        key = _overlay_sentence_key(part)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(part)
    parts = deduped
    if not parts:
        return fallback if fallback.endswith("。") else f"{fallback}。"
    body = "。".join(parts)
    return body if body.endswith("。") else f"{body}。"


def _archive_scene_brief(campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    entries = _prioritized_archive_entries(campaign_state)
    tension_entries = _top_role_slot_repercussions(campaign_state, limit=1)
    if not entries:
        return {
            "headlineText": "",
            "openingLines": [],
            "storyNowText": "",
            "storyStakesText": "",
            "worldStateText": "",
            "eventSummaryText": "",
            "eventImportanceText": "",
        }

    latest_archive = list(campaign_state.get("sessionArchive", []))[-1]
    top = entries[0]
    hidden_wound = _archive_hidden_wound_text(top) or str(latest_archive.get("whatRemained") or "").strip()
    resurfacing = str(top.get("resurfacingRisk") or top.get("archivedCauseEcho") or "").strip()
    archived_echo = str(top.get("archivedCauseEcho") or "").strip()
    protected = str(latest_archive.get("protected") or "").strip()
    lost = str(latest_archive.get("lost") or "").strip()
    prefix = _archive_prefix(top)
    opening_lines: List[str] = []
    tension = tension_entries[0] if tension_entries else None

    if int(campaign_state["session"].get("turnInSession", 1)) == 1:
        if protected or lost:
            opening_lines.append(f"前のセッションでは{protected or '守るべきもの'}を残した一方で、{lost or '痛手'}を失った。")
        if resurfacing:
            opening_lines.append(f"いま強く戻ってきているのは、{_trim_copy_text(resurfacing)}。")
        if tension:
            if tension["mode"] == "retaliation":
                opening_lines.append(f"{tension['roleLabel']}の座では、報いを返そうとする空気がまだ強い。")
            elif tension["mode"] == "distrust":
                opening_lines.append(f"{tension['roleLabel']}の座では、役目そのものへの不信がまだ抜けていない。")
            else:
                opening_lines.append(f"{tension['roleLabel']}の座では、まだ疑いを解いていない。")
        if hidden_wound:
            opening_lines.append(f"まだ隠れている傷は、{_trim_copy_text(hidden_wound)}。")

    story_now = f"{prefix}の余波がまだこの場に残っている" if archived_echo else ""
    if tension:
        tone = {
            "retaliation": f"{tension['roleLabel']}の座では報いを返す気配も強い",
            "distrust": f"{tension['roleLabel']}の座では役目への不信も残っている",
            "suspicion": f"{tension['roleLabel']}の座では疑いも解けていない",
        }[tension["mode"]]
        story_now = _compose_overlay_sentence(story_now, tone, tone)
    story_stakes = (
        f"ここで見誤ると、{_trim_copy_text(resurfacing)}"
        if resurfacing
        else f"{prefix}からの傷が次の判断を鈍らせる"
    )
    if tension:
        stake_tail = {
            "retaliation": "報いに転べば、話し合いより先に関係が切れる",
            "distrust": "不信が続けば、協力の入口がさらに狭くなる",
            "suspicion": "疑いが続けば、些細な綻びでも再燃する",
        }[tension["mode"]]
        story_stakes = _compose_overlay_sentence(story_stakes, stake_tail, stake_tail)
    world_state = f"見えない傷として、{_trim_copy_text(hidden_wound)}" if hidden_wound else ""
    if tension:
        world_tail = {
            "retaliation": f"{tension['roleLabel']}の座には報いを返す気配が残っている",
            "distrust": f"{tension['roleLabel']}の座には不信が残っている",
            "suspicion": f"{tension['roleLabel']}の座には疑いが残っている",
        }[tension["mode"]]
        world_state = _compose_overlay_sentence(world_state, world_tail, world_tail)
    event_summary = (
        f"前のセッションの因果として、{_trim_copy_text(archived_echo or resurfacing)}"
        if (archived_echo or resurfacing)
        else ""
    )
    if tension:
        event_tail = {
            "retaliation": f"{tension['roleLabel']}の座では報いを返す構えが残っている",
            "distrust": f"{tension['roleLabel']}の座では先に不信が立つ",
            "suspicion": f"{tension['roleLabel']}の座ではまず疑いから始まる",
        }[tension["mode"]]
        event_summary = _compose_overlay_sentence(event_summary, event_tail, event_tail)
    event_importance = (
        f"放置すると、{_trim_copy_text(resurfacing)}"
        if resurfacing
        else f"{prefix}の傷が今の事件に重なる"
    )
    if tension:
        importance_tail = {
            "retaliation": "ここで誤ると、報いが別の火種を呼ぶ",
            "distrust": "ここで誤ると、不信が役目をまたいで広がる",
            "suspicion": "ここで誤ると、疑いが次の判断を縛る",
        }[tension["mode"]]
        event_importance = _compose_overlay_sentence(event_importance, importance_tail, importance_tail)
    headline_text = f"{prefix}から残る火種が、いまの場面にも影を落としている。"
    return {
        "headlineText": headline_text,
        "openingLines": opening_lines[:3],
        "storyNowText": story_now,
        "storyStakesText": story_stakes,
        "worldStateText": world_state,
        "eventSummaryText": event_summary,
        "eventImportanceText": event_importance,
    }


def scene_archive_brief(world_state: Dict[str, Any]) -> Dict[str, Any]:
    return _archive_scene_brief(ensure_campaign_state(world_state)["campaign_state"])


def _archive_reaction_mode(entry: Dict[str, Any]) -> str:
    if str(entry.get("unresolvedTaboo") or "").strip():
        return "retaliation"
    if str(entry.get("hiddenCrimeSummary") or "").strip():
        return "suspicion"
    if str(entry.get("publicInfamySummary") or "").strip():
        return "distrust"
    return "first_reaction"


def _archive_role_slot_overlays(campaign_state: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    current_event = campaign_state["events"]["catalog"].get(campaign_state.get("currentEventId"), {})
    current_focus_slots = {
        str(role_slot_id)
        for branch in current_event.get("branches", [])
        for role_slot_id in branch.get("focusNpcIds", [])
    }
    overlays: Dict[str, Dict[str, str]] = {}

    for entry in _prioritized_archive_entries(campaign_state):
        candidate_slot_ids = list(
            dict.fromkeys(
                [
                    *(str(role_slot_id) for role_slot_id in entry.get("roleSlotEchoIds", [])),
                    str(entry.get("keyRoleSlotId") or ""),
                ]
            )
        )
        candidate_slot_ids = [slot_id for slot_id in candidate_slot_ids if slot_id in campaign_state["npcs"]]
        candidate_slot_ids.sort(key=lambda slot_id: (slot_id not in current_focus_slots, slot_id))
        if not candidate_slot_ids:
            continue

        role_slot_id = candidate_slot_ids[0]
        if role_slot_id in overlays:
            continue

        prefix = _archive_prefix(entry)
        mode = _archive_reaction_mode(entry)
        if mode == "retaliation":
            overlays[role_slot_id] = {
                "archiveReactionMode": mode,
                "archiveReactionText": f"{prefix}の禁じ手以来、出入りと判断をかなり厳しく見ている。",
                "archiveRelationText": f"{prefix}の後始末を背負い、まずこちらを強く警戒している。",
                "archiveEmotionText": "静かな報いまで視野に入れて、言葉をかなり固くしている。",
                "archiveRoleText": "いまは本来の役目に加えて、禁じ手の検分と後始末を優先している。",
            }
            continue
        if mode == "suspicion":
            overlays[role_slot_id] = {
                "archiveReactionMode": mode,
                "archiveReactionText": f"{prefix}の不正の痕を洗い直すつもりで、細かな違和感を拾おうとしている。",
                "archiveRelationText": f"{prefix}の疑いが残り、まず痕跡から確かめようとしている。",
                "archiveEmotionText": "証拠はなくても違和感を捨てず、表情を少し固くしている。",
                "archiveRoleText": "いまは本来の役目と並行して、出入りと帳面の洗い直しへ意識を割いている。",
            }
            continue
        if mode == "distrust":
            overlays[role_slot_id] = {
                "archiveReactionMode": mode,
                "archiveReactionText": f"{prefix}で広がった悪評が残り、こちらとの距離を簡単には詰めない。",
                "archiveRelationText": f"{prefix}の悪評を受け、まず距離を置いて見ている。",
                "archiveEmotionText": "表向きは抑えているが、信用の切れ目を強く意識している。",
                "archiveRoleText": "いまは本来の役目より、座の信用を立て直す方へ意識が寄っている。",
            }
            continue
        overlays[role_slot_id] = {
            "archiveReactionMode": mode,
            "archiveReactionText": f"{prefix}の余波を踏まえ、先にこちらの出方を見極めようとしている。",
            "archiveRelationText": f"{prefix}の後ろ暗さを忘れず、ひとつ分だけ距離を取っている。",
            "archiveEmotionText": "まだ確信はないが、ひとつ分だけ慎重になっている。",
            "archiveRoleText": "いまは本来の役目に加えて、余波の見張りにも意識を割いている。",
        }
    for tension in _top_role_slot_repercussions(campaign_state):
        role_slot_id = tension["roleSlotId"]
        archive_entry = tension["archiveEntry"]
        prefix = _archive_prefix(archive_entry) if archive_entry else "前のセッションの余波"
        if role_slot_id in overlays:
            if tension["mode"] == "retaliation":
                overlays[role_slot_id]["archiveReactionMode"] = "retaliation"
                overlays[role_slot_id]["archiveReactionText"] = f"{prefix}以来、疑いを越えて報いまで視野に入れている。"
                overlays[role_slot_id]["archiveRelationText"] = f"{prefix}の後始末を背負い、まずこちらを強く牽制している。"
                overlays[role_slot_id]["archiveEmotionText"] = "表面は静かでも、返す気配をかなり深く抱えている。"
                overlays[role_slot_id]["archiveRoleText"] = "いまは本来の役目に加えて、後始末と報いの線引きを優先している。"
            elif tension["mode"] == "distrust" and overlays[role_slot_id]["archiveReactionMode"] != "retaliation":
                overlays[role_slot_id]["archiveReactionMode"] = "distrust"
                overlays[role_slot_id]["archiveReactionText"] = f"{prefix}以来、役目そのものを信じ切らず、まず距離を測っている。"
                overlays[role_slot_id]["archiveRelationText"] = f"{prefix}の余波で、こちらの言葉より先に不信が立っている。"
                overlays[role_slot_id]["archiveEmotionText"] = "露骨ではないが、信用の切れ目をかなり意識している。"
                overlays[role_slot_id]["archiveRoleText"] = "いまは本来の役目より、座の信用を崩さないことを優先している。"
            continue
        if tension["mode"] == "retaliation":
            overlays[role_slot_id] = {
                "archiveReactionMode": "retaliation",
                "archiveReactionText": f"{prefix}以来、疑いを越えて報いまで視野に入れている。",
                "archiveRelationText": f"{prefix}の後始末を背負い、まずこちらを強く牽制している。",
                "archiveEmotionText": "表面は静かでも、返す気配をかなり深く抱えている。",
                "archiveRoleText": "いまは本来の役目に加えて、後始末と報いの線引きを優先している。",
            }
            continue
        if tension["mode"] == "distrust":
            overlays[role_slot_id] = {
                "archiveReactionMode": "distrust",
                "archiveReactionText": f"{prefix}以来、役目そのものを信じ切らず、まず距離を測っている。",
                "archiveRelationText": f"{prefix}の余波で、こちらの言葉より先に不信が立っている。",
                "archiveEmotionText": "露骨ではないが、信用の切れ目をかなり意識している。",
                "archiveRoleText": "いまは本来の役目より、座の信用を崩さないことを優先している。",
            }
            continue
        overlays[role_slot_id] = {
            "archiveReactionMode": "suspicion",
            "archiveReactionText": f"{prefix}以来、まだ疑いを解かず、細かな違和感から先に拾おうとしている。",
            "archiveRelationText": f"{prefix}の痕が残り、まず事実関係から確かめようとしている。",
            "archiveEmotionText": "確証はなくても、違和感を捨てずに視線を細くしている。",
            "archiveRoleText": "いまは本来の役目と並行して、出入りや痕跡の洗い直しへ意識を割いている。",
        }
    if len(overlays) > 3:
        tension_scores = {entry["roleSlotId"]: float(entry["score"]) for entry in _top_role_slot_repercussions(campaign_state, limit=len(overlays))}
        archive_scores = {
            str(entry.get("keyRoleSlotId") or ""): float(entry.get("_priority", {}).get("total", 0.0))
            for entry in _prioritized_archive_entries(campaign_state, limit=len(overlays))
        }
        ordered_role_slot_ids = sorted(
            overlays,
            key=lambda role_slot_id: (
                role_slot_id in current_focus_slots,
                tension_scores.get(role_slot_id, 0.0),
                archive_scores.get(role_slot_id, 0.0),
                role_slot_id,
            ),
            reverse=True,
        )[:3]
        overlays = {role_slot_id: overlays[role_slot_id] for role_slot_id in ordered_role_slot_ids}
    return overlays


def _annotate_npc_with_archive_overlay(campaign_state: Dict[str, Any], npc: Dict[str, Any]) -> Dict[str, Any]:
    overlay = _archive_role_slot_overlays(campaign_state).get(str(npc.get("roleSlotId") or npc.get("npcId") or ""))
    if not overlay:
        return npc
    annotated = copy.deepcopy(npc)
    annotated.update(overlay)
    return annotated


def _dedupe_lines(lines: Iterable[str], limit: int = 3) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    for raw_line in lines:
        line = str(raw_line or "").strip()
        if not line or line in seen:
            continue
        seen.add(line)
        ordered.append(line)
        if len(ordered) >= limit:
            break
    return ordered


def _dedupe_tagged_lines(tagged_lines: Iterable[tuple[str, str]], limit: int = 3) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    for raw_key, raw_line in tagged_lines:
        key = str(raw_key or "").strip()
        line = str(raw_line or "").strip()
        if not line:
            continue
        unique_key = key or line
        if unique_key in seen:
            continue
        seen.add(unique_key)
        ordered.append(line)
        if len(ordered) >= limit:
            break
    return ordered


def _archive_reverberation_snapshot(campaign_state: Dict[str, Any], ending: Dict[str, Any]) -> Dict[str, Any]:
    last_action = campaign_state.get("lastFreeAction") or {}
    normalized = last_action.get("normalizedIntent", {})
    action_summary = str(
        last_action.get("freeActionSummary")
        or last_action.get("summary")
        or ""
    ).strip()
    residue_label = str(last_action.get("freeActionResidueLabel") or "").strip()
    role_slot_ids = list(
        dict.fromkeys(
            [
                *(str(role_slot_id).strip() for role_slot_id in normalized.get("target_role_slots", [])),
                str(ending.get("keyRoleSlotId") or "").strip(),
            ]
        )
    )
    role_slot_ids = [role_slot_id for role_slot_id in role_slot_ids if role_slot_id]
    institution_ids = [
        str(institution_id).strip()
        for institution_id in normalized.get("target_institutions", [])
        if str(institution_id).strip()
    ]
    public_infamy = float(campaign_state.get("publicInfamy", 0.0))
    hidden_crimes = float(campaign_state.get("hiddenCrimes", 0.0))
    ritual_pollution = float(campaign_state.get("ritualPollution", 0.0))
    role_slot_pressure_snapshot = {
        role_slot_id: {
            "suspicion": _role_slot_repercussion_value(campaign_state, "roleSlotSuspicion", role_slot_id),
            "distrust": _role_slot_repercussion_value(campaign_state, "roleSlotDistrust", role_slot_id),
            "retaliation": _role_slot_repercussion_value(campaign_state, "roleSlotRetaliation", role_slot_id),
        }
        for role_slot_id in role_slot_ids
    }
    lead_role_slot = role_slot_ids[0] if role_slot_ids else ""
    lead_pressure = role_slot_pressure_snapshot.get(lead_role_slot, {})
    role_slot_pressure_summary = ""
    if lead_role_slot:
        lead_role_label, lead_occupant_label = _archive_role_labels(
            {
                "keyRoleSlotId": lead_role_slot,
                "keyRoleLabel": campaign_state.get("npcs", {}).get(lead_role_slot, {}).get("roleLabel"),
                "keyOccupantLabel": campaign_state.get("npcs", {}).get(lead_role_slot, {}).get("displayName"),
            },
            campaign_state,
        )
        if float(lead_pressure.get("retaliation", 0.0)) >= 16.0:
            role_slot_pressure_summary = f"{lead_role_label}: {lead_occupant_label}の座では、報いを返そうとする空気が強く残った。"
        elif float(lead_pressure.get("distrust", 0.0)) >= 14.0:
            role_slot_pressure_summary = f"{lead_role_label}: {lead_occupant_label}の座では、役目そのものへの不信が強く残った。"
        elif float(lead_pressure.get("suspicion", 0.0)) >= 12.0:
            role_slot_pressure_summary = f"{lead_role_label}: {lead_occupant_label}の座では、まだ疑いを捨てていない。"

    vice_summary = ""
    if campaign_state.get("viceTrace") or public_infamy >= 3.0 or hidden_crimes >= 2.5:
        if action_summary:
            vice_summary = f"{action_summary}の余波で、悪徳の気配がまだ場に残っている。"
        else:
            vice_summary = "悪徳の気配がまだ場に残っている。"

    taboo_summary = ""
    if campaign_state.get("tabooTrace") or ritual_pollution >= 35.0:
        taboo_summary = "禁じ手の濁りが残り、祈りと封印の後始末が要る。"

    public_infamy_summary = ""
    if public_infamy >= 3.0:
        public_infamy_summary = "悪評が残り、関わらない座も警戒している。"

    hidden_crime_summary = ""
    if hidden_crimes >= 2.5:
        hidden_crime_summary = "表に出ていない不正が残り、検分が入れば露見へ傾く。"

    ritual_pollution_summary = ""
    if ritual_pollution >= 35.0:
        ritual_pollution_summary = "儀礼の汚れが残り、次の祈りや封印に重さが返る。"

    archived_cause_echo = ""
    if residue_label and action_summary:
        archived_cause_echo = f"{residue_label}として、{action_summary}の余波がまだ尾を引いている。"
    elif residue_label:
        archived_cause_echo = f"{residue_label}がまだ尾を引いている。"
    elif action_summary:
        archived_cause_echo = f"{action_summary}の余波がまだ尾を引いている。"

    resurfacing_risk = ""
    if hidden_crime_summary and taboo_summary:
        resurfacing_risk = "隠した不正を洗い直す動きが入り、禁じ手の痕まで一緒に表へ出るおそれがある。"
    elif hidden_crime_summary:
        resurfacing_risk = hidden_crime_summary
    elif taboo_summary:
        resurfacing_risk = "禁じ手の痕を洗う検分が入り、座や制度への疑いが広がるおそれがある。"
    elif public_infamy_summary:
        resurfacing_risk = public_infamy_summary

    unresolved_vice = ""
    if vice_summary:
        if hidden_crime_summary:
            unresolved_vice = f"{vice_summary.rstrip('。')}。{hidden_crime_summary}"
        elif public_infamy_summary:
            unresolved_vice = f"{vice_summary.rstrip('。')}。{public_infamy_summary}"
        else:
            unresolved_vice = vice_summary

    unresolved_taboo = ""
    if taboo_summary:
        if ritual_pollution_summary:
            unresolved_taboo = f"{taboo_summary.rstrip('。')}。{ritual_pollution_summary}"
        else:
            unresolved_taboo = taboo_summary

    return {
        "freeActionSummary": action_summary,
        "freeActionResidueLabel": residue_label,
        "viceSummary": vice_summary,
        "tabooSummary": taboo_summary,
        "publicInfamySummary": public_infamy_summary,
        "hiddenCrimeSummary": hidden_crime_summary,
        "ritualPollutionSummary": ritual_pollution_summary,
        "publicInfamyLevel": public_infamy,
        "hiddenCrimesLevel": hidden_crimes,
        "ritualPollutionLevel": ritual_pollution,
        "roleSlotEchoIds": role_slot_ids,
        "roleSlotPressureSnapshot": role_slot_pressure_snapshot,
        "roleSlotPressureSummary": role_slot_pressure_summary,
        "institutionIds": institution_ids,
        "archivedCauseEcho": archived_cause_echo,
        "resurfacingRisk": resurfacing_risk,
        "unresolvedVice": unresolved_vice,
        "unresolvedTaboo": unresolved_taboo,
    }


def _archive_entry(campaign_state: Dict[str, Any], ending: Dict[str, Any]) -> Dict[str, Any]:
    session = campaign_state["session"]
    reverberation = _archive_reverberation_snapshot(campaign_state, ending)
    opening_summary = str(
        campaign_state.get("sessionOpeningHooks", {}).get(str(ending["sessionNumber"]))
        or _initial_session_opening_summary()
    ).strip()
    return {
        "sessionNumber": ending["sessionNumber"],
        "openingSummary": opening_summary,
        "title": ending["title"],
        "tone": ending["tone"],
        "summary": ending["summary"],
        "whatRemained": ending["whatRemained"],
        "protected": ending["protected"],
        "lost": ending["lost"],
        "carriedForward": ending["carriedForward"],
        "keyRoleSlotId": ending.get("keyRoleSlotId") or ending.get("keyNpcId"),
        "keyRoleLabel": ending.get("keyRoleLabel"),
        "keyNpcLabel": ending["keyNpcLabel"],
        "keyOccupantLabel": ending["keyNpcLabel"],
        "archivedAtTurn": max(1, int(session["turnCounter"]) - 1),
        "eventId": campaign_state.get("currentEventId"),
        "eventLabel": campaign_state["events"]["catalog"].get(campaign_state.get("currentEventId"), {}).get("label"),
        "hubId": campaign_state.get("currentHubId"),
        "dungeonId": campaign_state.get("currentDungeonId"),
        **reverberation,
    }


def _new_game_genesis_surface(campaign_state: Dict[str, Any]) -> Dict[str, Any]:
    genesis = copy.deepcopy(campaign_state.get("newGameGenesis") or {})
    if not genesis:
        return {}
    loadout = genesis.get("sessionOneLoadout") or {}
    hub_catalog = campaign_state.get("hubCatalog") or {}
    dungeon_catalog = campaign_state.get("dungeonCatalog") or {}
    event_catalog = (campaign_state.get("events") or {}).get("catalog") or {}
    hub = copy.deepcopy(hub_catalog.get(loadout.get("hubId")) or {})
    dungeon = copy.deepcopy(dungeon_catalog.get(loadout.get("dungeonId")) or {})
    phase_event_labels = [
        str(event_catalog.get(event_id, {}).get("label") or event_id)
        for event_id in list(loadout.get("phaseEventIds") or [])
    ]
    cast_seed = []
    for slot_id in NPC_ORDER[:4]:
        npc = campaign_state.get("npcs", {}).get(slot_id)
        if not npc:
            continue
        cast_seed.append(
            {
                "roleSlotId": slot_id,
                "roleLabel": npc.get("roleLabel"),
                "displayName": npc.get("displayName"),
                "affiliationLabel": npc.get("affiliationLabel"),
                "agenda": npc.get("agenda"),
            }
        )
    return {
        "profileSurface": copy.deepcopy(genesis.get("profileSurface") or {}),
        "openingSummary": str(genesis.get("openingSummary") or ""),
        "phaseEventLabels": phase_event_labels,
        "hub": {
            "hubId": hub.get("hubId"),
            "label": hub.get("label"),
            "regionLabel": hub.get("regionLabel"),
            "pressureStyle": hub.get("pressureStyle"),
        },
        "dungeon": {
            "dungeonId": dungeon.get("dungeonId"),
            "label": dungeon.get("label"),
            "regionLabel": dungeon.get("regionLabel"),
            "pressureStyle": dungeon.get("pressureStyle"),
        },
        "incitingIncident": copy.deepcopy(genesis.get("incitingIncident") or {}),
        "storyAxes": [value for value in list(genesis.get("storyAxes") or []) if str(value).strip()],
        "preferredFactions": list(genesis.get("preferredFactions") or []),
        "castSeed": cast_seed,
    }


def _archived_entries(campaign_state: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    entries = [entry for entry in campaign_state.get("sessionArchive", []) if isinstance(entry, dict)]
    return entries[-limit:]


def _compress_session_archive(campaign_state: Dict[str, Any]) -> None:
    _archive_compression_defaults(campaign_state)
    archive = [entry for entry in campaign_state.get("sessionArchive", []) if isinstance(entry, dict)]
    if len(archive) <= SESSION_ARCHIVE_MAX:
        campaign_state["sessionArchive"] = archive
        return
    overflow = archive[:-SESSION_ARCHIVE_MAX]
    kept = archive[-SESSION_ARCHIVE_MAX:]
    compression = campaign_state["archiveCompression"]
    overflow_numbers = [int(entry.get("sessionNumber", -1)) for entry in overflow if int(entry.get("sessionNumber", -1)) > 0]
    compression["compressedCount"] = int(compression.get("compressedCount", 0)) + len(overflow)
    if overflow_numbers:
        current_oldest = compression.get("oldestSessionNumber")
        compression["oldestSessionNumber"] = min([*overflow_numbers, *( [int(current_oldest)] if current_oldest else [] )])
        compression["newestSessionNumber"] = max(
            [*overflow_numbers, *( [int(compression.get("newestSessionNumber"))] if compression.get("newestSessionNumber") else [] )]
        )
        latest_entry = overflow[-1]
        compression["latestSummary"] = (
            f"第{overflow_numbers[0]}セッションから第{overflow_numbers[-1]}セッションまでの古い記録は圧縮して保持している。"
            if len(overflow_numbers) > 1
            else f"第{overflow_numbers[0]}セッションの古い記録は圧縮して保持している。"
        )
    campaign_state["sessionArchive"] = kept


def _archive_priority_components(entry: Dict[str, Any], campaign_state: Dict[str, Any]) -> Dict[str, float]:
    current_event_id = str(campaign_state.get("currentEventId") or "")
    current_hub_id = str(campaign_state.get("currentHubId") or "")
    current_dungeon_id = str(campaign_state.get("currentDungeonId") or "")
    current_event = campaign_state["events"]["catalog"].get(current_event_id, {})
    current_focus_slots = {
        str(role_slot_id)
        for branch in current_event.get("branches", [])
        for role_slot_id in branch.get("focusNpcIds", [])
    }
    all_entries = _archived_entries(campaign_state, limit=8)
    newer_count = sum(
        1
        for other in all_entries
        if int(other.get("sessionNumber", -1)) > int(entry.get("sessionNumber", -1))
    )
    recency = max(0.0, 28.0 - newer_count * 6.0)

    severity = (
        float(entry.get("publicInfamyLevel", 0.0)) * 0.8
        + float(entry.get("hiddenCrimesLevel", 0.0)) * 1.0
        + float(entry.get("ritualPollutionLevel", 0.0)) * 0.32
        + sum(
            float(snapshot.get("suspicion", 0.0)) * 0.08
            + float(snapshot.get("distrust", 0.0)) * 0.1
            + float(snapshot.get("retaliation", 0.0)) * 0.12
            for snapshot in dict(entry.get("roleSlotPressureSnapshot") or {}).values()
        )
        + {"steady": 2.0, "mixed": 6.0, "grim": 11.0}.get(str(entry.get("tone", "")), 0.0)
    )

    visibility = float(entry.get("publicInfamyLevel", 0.0)) * 0.6
    residue_label = str(entry.get("freeActionResidueLabel") or "")
    if residue_label == "露見した不正":
        visibility += 12.0
    elif residue_label == "疑いを残した不正":
        visibility += 8.0
    elif residue_label:
        visibility += 4.0
    if str(entry.get("archivedCauseEcho") or "").strip():
        visibility += 3.0
    if str(entry.get("resurfacingRisk") or "").strip():
        visibility += 5.0

    role_slot_ids = {str(role_slot_id) for role_slot_id in entry.get("roleSlotEchoIds", []) if str(role_slot_id).strip()}
    role_overlap = len(role_slot_ids & current_focus_slots)
    role_relevance = role_overlap * 8.0
    if str(entry.get("keyRoleSlotId") or "") in current_focus_slots:
        role_relevance += 6.0
    if role_overlap:
        role_relevance += sum(
            float(snapshot.get("suspicion", 0.0)) * 0.04
            + float(snapshot.get("distrust", 0.0)) * 0.05
            + float(snapshot.get("retaliation", 0.0)) * 0.06
            for role_slot_id, snapshot in dict(entry.get("roleSlotPressureSnapshot") or {}).items()
            if role_slot_id in current_focus_slots
        )

    institution_relevance = 0.0
    if entry.get("institutionIds"):
        institution_relevance += 4.0
        if float(campaign_state["hub"].get("heat", 0.0)) >= 48.0 or float(campaign_state["hub"].get("stability", 0.0)) < 55.0:
            institution_relevance += 4.0

    current_event_relevance = 0.0
    if str(entry.get("eventId") or "") == current_event_id:
        current_event_relevance += 14.0
    if str(entry.get("hubId") or "") == current_hub_id:
        current_event_relevance += 5.0
    if str(entry.get("dungeonId") or "") == current_dungeon_id:
        current_event_relevance += 5.0
    if str(entry.get("unresolvedTaboo") or "").strip() and _is_ritual_event(current_event):
        current_event_relevance += 8.0
    if str(entry.get("unresolvedVice") or "").strip() and float(current_event.get("pressure", 0.0)) >= 65.0:
        current_event_relevance += 4.0

    total = round(
        recency + severity + visibility + role_relevance + institution_relevance + current_event_relevance,
        1,
    )
    return {
        "recency": round(recency, 1),
        "severity": round(severity, 1),
        "visibility": round(visibility, 1),
        "roleSlotRelevance": round(role_relevance, 1),
        "institutionRelevance": round(institution_relevance, 1),
        "currentEventRelevance": round(current_event_relevance, 1),
        "total": total,
    }


def _prioritized_archive_entries(campaign_state: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for entry in _archived_entries(campaign_state, limit=8):
        components = _archive_priority_components(entry, campaign_state)
        ranked.append({**entry, "_priority": components})
    ranked.sort(
        key=lambda entry: (
            float(entry["_priority"]["total"]),
            int(entry.get("sessionNumber", -1)),
            float(entry.get("ritualPollutionLevel", 0.0)),
            float(entry.get("hiddenCrimesLevel", 0.0)),
        ),
        reverse=True,
    )
    return ranked[:limit]


def _archive_prefix(entry: Dict[str, Any]) -> str:
    session_number = int(entry.get("sessionNumber", 0))
    title = str(entry.get("title") or "").strip()
    if title:
        return f"第{session_number}セッション「{title}」"
    return f"第{session_number}セッション"


def _archive_role_labels(entry: Dict[str, Any], campaign_state: Dict[str, Any]) -> tuple[str, str]:
    role_slot_id = str(entry.get("keyRoleSlotId") or "").strip()
    npc = campaign_state.get("npcs", {}).get(role_slot_id)
    if isinstance(npc, dict):
        return str(npc.get("roleLabel") or "関係者"), str(npc.get("displayName") or npc.get("roleLabel") or "関係者")
    return (
        str(entry.get("keyRoleLabel") or "関係者"),
        str(entry.get("keyOccupantLabel") or entry.get("keyNpcLabel") or entry.get("keyRoleLabel") or "関係者"),
    )


def _archive_hidden_wound_text(entry: Dict[str, Any]) -> str:
    hidden = str(entry.get("hiddenCrimeSummary") or "").strip()
    if hidden:
        return hidden
    if str(entry.get("freeActionResidueLabel") or "").strip() in {"隠れた不正の痕", "疑いを残した不正"}:
        return str(entry.get("archivedCauseEcho") or "").strip()
    taboo = str(entry.get("ritualPollutionSummary") or "").strip()
    if taboo:
        return taboo
    return ""


def _archive_event_candidates(campaign_state: Dict[str, Any]) -> List[str]:
    lines: List[tuple[str, str]] = []
    for entry in _prioritized_archive_entries(campaign_state):
        prefix = _archive_prefix(entry)
        action_summary = str(entry.get("freeActionSummary") or "").strip()
        taboo = str(entry.get("unresolvedTaboo") or "").strip()
        vice = str(entry.get("unresolvedVice") or "").strip()
        hidden = str(entry.get("hiddenCrimeSummary") or "").strip()
        public = str(entry.get("publicInfamySummary") or "").strip()
        if taboo:
            topic = f"「{action_summary}」の禁じ手の検分" if action_summary else f"{prefix}の禁じ手の検分"
            lines.append((f"taboo:{taboo}", f"{topic}: {taboo}"))
            continue
        if hidden:
            topic = f"「{action_summary}」の痕の洗い出し" if action_summary else f"{prefix}の不正の洗い出し"
            lines.append((f"hidden:{hidden}", f"{topic}: {hidden}"))
            continue
        if public:
            topic = f"「{action_summary}」の悪評の後始末" if action_summary else f"{prefix}の悪評の後始末"
            lines.append((f"public:{public}", f"{topic}: {public}"))
            continue
        if vice:
            topic = f"「{action_summary}」の後始末" if action_summary else f"{prefix}の後始末"
            lines.append((f"vice:{vice}", f"{topic}: {vice}"))
    return _dedupe_tagged_lines(lines, limit=3)


def _archive_npc_carry_overs(campaign_state: Dict[str, Any]) -> List[str]:
    lines: List[tuple[str, str]] = []
    for entry in _prioritized_archive_entries(campaign_state):
        prefix = _archive_prefix(entry)
        role_slot_id = str(entry.get("keyRoleSlotId") or "").strip()
        role_label, occupant_label = _archive_role_labels(entry, campaign_state)
        hidden = str(entry.get("hiddenCrimeSummary") or "").strip()
        public = str(entry.get("publicInfamySummary") or "").strip()
        taboo = str(entry.get("unresolvedTaboo") or "").strip()
        vice = str(entry.get("unresolvedVice") or "").strip()
        if taboo:
            lines.append((f"{role_slot_id}:taboo", f"{role_label}: {occupant_label}の座は、{prefix}で残った禁じ手の後始末と不信を背負っている。"))
            continue
        if hidden:
            lines.append((f"{role_slot_id}:hidden", f"{role_label}: {occupant_label}の座には、{prefix}で残った不正の疑いがまだ付きまとっている。"))
            continue
        if public:
            lines.append((f"{role_slot_id}:public", f"{role_label}: {occupant_label}の座は、{prefix}で広がった悪評の余波をまだ受けている。"))
            continue
        if vice:
            lines.append((f"{role_slot_id}:vice", f"{role_label}: {occupant_label}の座には、{prefix}で残った後ろ暗さがまだ抜けていない。"))
    for tension in _top_role_slot_repercussions(campaign_state):
        role_slot_id = tension["roleSlotId"]
        if tension["mode"] == "retaliation":
            lines.append(
                (
                    f"{role_slot_id}:retaliation:persistent",
                    f"{tension['roleLabel']}: {tension['occupantLabel']}の座では、報いを返す気配がまだ消えていない。",
                )
            )
            continue
        if tension["mode"] == "distrust":
            lines.append(
                (
                    f"{role_slot_id}:distrust:persistent",
                    f"{tension['roleLabel']}: {tension['occupantLabel']}の座では、役目そのものへの不信がまだ残っている。",
                )
            )
            continue
        lines.append(
            (
                f"{role_slot_id}:suspicion:persistent",
                f"{tension['roleLabel']}: {tension['occupantLabel']}の座では、まだ疑いを解いていない。",
            )
        )
    return _dedupe_tagged_lines(lines, limit=3)


def _archive_scars_remaining(campaign_state: Dict[str, Any]) -> List[str]:
    lines: List[tuple[str, str]] = []
    for entry in _prioritized_archive_entries(campaign_state):
        prefix = _archive_prefix(entry)
        hidden_wound = _archive_hidden_wound_text(entry)
        if hidden_wound:
            lines.append((hidden_wound, f"{prefix}: {hidden_wound}"))
            continue
        resurfacing = str(entry.get("resurfacingRisk") or "").strip()
        if resurfacing:
            lines.append((resurfacing, f"{prefix}: {resurfacing}"))
    return _dedupe_tagged_lines(lines, limit=2)


def _archived_cause_echoes(campaign_state: Dict[str, Any]) -> List[str]:
    lines = [
        (str(entry.get("archivedCauseEcho") or "").strip(), f"{_archive_prefix(entry)}: {entry['archivedCauseEcho']}")
        for entry in _prioritized_archive_entries(campaign_state)
        if str(entry.get("archivedCauseEcho") or "").strip()
    ]
    return _dedupe_tagged_lines(lines, limit=3)


def _resurfacing_risks(campaign_state: Dict[str, Any]) -> List[str]:
    lines = [
        (str(entry.get("resurfacingRisk") or "").strip(), f"{_archive_prefix(entry)}の余波: {entry['resurfacingRisk']}")
        for entry in _prioritized_archive_entries(campaign_state)
        if str(entry.get("resurfacingRisk") or "").strip()
    ]
    return _dedupe_tagged_lines(lines, limit=3)


def _unresolved_vice(campaign_state: Dict[str, Any]) -> List[str]:
    lines = [
        entry["unresolvedVice"]
        for entry in _prioritized_archive_entries(campaign_state)
        if str(entry.get("unresolvedVice") or "").strip()
    ]
    return _dedupe_lines(lines, limit=3)


def _unresolved_taboo(campaign_state: Dict[str, Any]) -> List[str]:
    lines = [
        entry["unresolvedTaboo"]
        for entry in _prioritized_archive_entries(campaign_state)
        if str(entry.get("unresolvedTaboo") or "").strip()
    ]
    return _dedupe_lines(lines, limit=3)


def _is_ritual_event(event: Dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(event.get("label") or ""),
            str(event.get("summary") or ""),
            str(event.get("theme") or ""),
        ]
    )
    return any(keyword in text for keyword in ("封", "祈", "遺物", "神託", "鐘", "聖", "儀礼"))


def _apply_archive_echoes_to_state(state: Dict[str, Any], campaign: Dict[str, Any]) -> None:
    applied = {int(session_number) for session_number in campaign.get("archiveEchoAppliedSessions", [])}
    new_entries = [
        entry
        for entry in _archived_entries(campaign, limit=4)
        if int(entry.get("sessionNumber", -1)) not in applied
    ]
    if not new_entries:
        return

    _age_role_slot_repercussions(campaign)
    institutions = state.get("resolved_world", {}).get("institutions", {})
    notes = list(campaign.get("nextSessionHookNotes", []))
    hub_catalog = campaign.get("hubCatalog", {})
    dungeon_catalog = campaign.get("dungeonCatalog", {})
    current_hub = hub_catalog.get(campaign.get("currentHubId"))
    current_dungeon = dungeon_catalog.get(campaign.get("currentDungeonId"))

    for entry in new_entries:
        session_number = int(entry.get("sessionNumber", -1))
        public_infamy = float(entry.get("publicInfamyLevel", 0.0))
        hidden_crimes = float(entry.get("hiddenCrimesLevel", 0.0))
        ritual_pollution = float(entry.get("ritualPollutionLevel", 0.0))
        has_taboo_residue = any(
            str(entry.get(key) or "").strip()
            for key in ("unresolvedTaboo", "tabooSummary", "ritualPollutionSummary")
        )
        role_slot_ids = [
            role_slot_id
            for role_slot_id in entry.get("roleSlotEchoIds", [])
            if role_slot_id in campaign.get("npcs", {})
        ]
        if not role_slot_ids:
            fallback_role = str(entry.get("keyRoleSlotId") or "").strip()
            if fallback_role in campaign.get("npcs", {}):
                role_slot_ids = [fallback_role]

        trust_drop = public_infamy * 0.08 + hidden_crimes * 0.12
        stress_rise = public_infamy * 0.1 + hidden_crimes * 0.14
        apply_role_slot_repercussions(
            campaign,
            role_slot_ids,
            suspicion_delta=hidden_crimes * 0.2 + public_infamy * 0.05,
            distrust_delta=public_infamy * 0.26 + hidden_crimes * 0.08,
            retaliation_delta=(ritual_pollution * 0.08 + 2.0) if has_taboo_residue else 0.0,
        )
        for role_slot_id in role_slot_ids:
            npc = campaign["npcs"][role_slot_id]
            if trust_drop > 0.0:
                npc["trust"] = _clamp(float(npc.get("trust", 50.0)) - trust_drop)
            if stress_rise > 0.0:
                npc["stress"] = _clamp(float(npc.get("stress", 50.0)) + stress_rise)
            if str(entry.get("resurfacingRisk") or "").strip():
                _append_memory(npc, str(entry["resurfacingRisk"]))
                npc["lastReaction"] = str(entry["resurfacingRisk"])

        if current_hub and public_infamy > 0.0:
            current_hub["heat"] = _clamp(float(current_hub.get("heat", 0.0)) + public_infamy * 0.14)
            current_hub["stability"] = _clamp(float(current_hub.get("stability", 0.0)) - public_infamy * 0.08)

        if current_dungeon and has_taboo_residue and ritual_pollution >= 35.0:
            current_dungeon["sealIntegrity"] = _clamp(float(current_dungeon.get("sealIntegrity", 0.0)) - min(2.6, 0.8 + ritual_pollution * 0.018))
            current_dungeon["threat"] = _clamp(float(current_dungeon.get("threat", 0.0)) + min(2.6, 0.6 + ritual_pollution * 0.014))

        for institution_id in entry.get("institutionIds", []):
            institution = institutions.get(institution_id)
            if not institution:
                continue
            if public_infamy > 0.0:
                institution["support"] = _clamp(float(institution.get("support", 50.0)) - public_infamy * 0.12)
            if hidden_crimes > 0.0:
                institution["breach_risk"] = _clamp(float(institution.get("breach_risk", 0.0)) + hidden_crimes * 0.14)

        if has_taboo_residue and ritual_pollution >= 35.0:
            for event in campaign["events"]["catalog"].values():
                if _is_ritual_event(event):
                    event["pressure"] = _clamp(float(event.get("pressure", 0.0)) + 1.4)
                    event["status"] = _event_status(float(event["pressure"]))

        if str(entry.get("archivedCauseEcho") or "").strip():
            notes.append(f"第{session_number}セッションの余波: {entry['archivedCauseEcho']}")
        if str(entry.get("resurfacingRisk") or "").strip():
            notes.append(f"第{session_number}セッションの再浮上: {entry['resurfacingRisk']}")
        role_slot_pressure_summary = str(entry.get("roleSlotPressureSummary") or "").strip()
        if role_slot_pressure_summary:
            notes.append(f"第{session_number}セッションの座のこじれ: {role_slot_pressure_summary}")
        applied.add(session_number)

    campaign["archiveEchoAppliedSessions"] = sorted(applied)[-12:]
    campaign["nextSessionHookNotes"] = _dedupe_lines(notes, limit=12)


def _archive_review(campaign_state: Dict[str, Any], hook: Dict[str, Any] | None) -> Dict[str, str] | None:
    archive = _archived_entries(campaign_state, limit=1)
    if not archive:
        return None
    latest = archive[-1]
    prioritized = _prioritized_archive_entries(campaign_state)
    resurfacing = list((hook or {}).get("resurfacingRisks", []))
    spark_entry = prioritized[0] if prioritized else latest
    hidden_entry = next(
        (entry for entry in prioritized if _archive_hidden_wound_text(entry)),
        spark_entry,
    )
    latest_summary = f"{_archive_prefix(latest)}: {latest['summary']}"
    resurfacing_text = resurfacing[0] if resurfacing else str(
        spark_entry.get("resurfacingRisk") or spark_entry.get("archivedCauseEcho") or "まだ古い因果は強く浮いていない。"
    )
    hidden_text = _archive_hidden_wound_text(hidden_entry) or str(
        hidden_entry.get("whatRemained")
        or hidden_entry.get("carriedForward")
        or hidden_entry.get("lost")
        or "まだ隠れた傷は大きく残っていない。"
    )
    hidden_line = f"{_archive_prefix(hidden_entry)}: {hidden_text}"
    return {
        "latestArchiveSummary": latest_summary,
        "resurfacingSpark": resurfacing_text,
        "hiddenWound": hidden_line,
        "previousSessionScar": str(latest.get("whatRemained") or latest.get("carriedForward") or latest.get("lost") or "まだ大きな傷は整理されていない。"),
        "resurfacingRisk": resurfacing_text,
    }


def _archive_hook_connections(entry: Dict[str, Any], hook: Dict[str, Any] | None) -> List[str]:
    if not isinstance(hook, dict):
        return []
    prefix = _archive_prefix(entry)
    archived_cause_echo = str(entry.get("archivedCauseEcho") or "").strip()
    resurfacing_risk = str(entry.get("resurfacingRisk") or "").strip()
    lines: List[str] = []
    if archived_cause_echo and f"{prefix}: {archived_cause_echo}" in list(hook.get("archivedCauseEchoes", [])):
        lines.append(f"強く戻ってきている因果: {archived_cause_echo}")
    if resurfacing_risk and f"{prefix}の余波: {resurfacing_risk}" in list(hook.get("resurfacingRisks", [])):
        lines.append(f"再燃している火種: {resurfacing_risk}")
    unresolved_vice = str(entry.get("unresolvedVice") or "").strip()
    if unresolved_vice and unresolved_vice in list(hook.get("unresolvedVice", [])):
        lines.append(f"残っている悪徳: {unresolved_vice}")
    unresolved_taboo = str(entry.get("unresolvedTaboo") or "").strip()
    if unresolved_taboo and unresolved_taboo in list(hook.get("unresolvedTaboo", [])):
        lines.append(f"残っている禁忌: {unresolved_taboo}")
    action_summary = str(entry.get("freeActionSummary") or "").strip()
    if action_summary:
        event_line = next(
            (line for line in list(hook.get("nextMainEventCandidates", [])) if action_summary in str(line)),
            "",
        )
        if event_line:
            lines.append(f"次の主事件候補: {event_line}")
    return _dedupe_lines(lines, limit=4)


def _archive_filter_tags(entry: Dict[str, Any], hook_connections: List[str]) -> List[str]:
    tags = ["all", f"role:{entry.get('keyRoleSlotId') or ''}".rstrip(":")]
    if str(entry.get("unresolvedVice") or "").strip() or str(entry.get("viceSummary") or "").strip():
        tags.append("vice")
    if str(entry.get("unresolvedTaboo") or "").strip() or str(entry.get("tabooSummary") or "").strip():
        tags.append("taboo")
    if str(entry.get("hiddenCrimeSummary") or "").strip():
        tags.append("hidden")
    if hook_connections:
        tags.append("hook")
    if str(entry.get("resurfacingRisk") or "").strip():
        tags.append("resurfacing")
    return [tag for tag in tags if tag]


def _archive_inspector(campaign_state: Dict[str, Any], hook: Dict[str, Any] | None) -> Dict[str, Any] | None:
    archive = [entry for entry in campaign_state.get("sessionArchive", []) if isinstance(entry, dict)]
    if not archive:
        return None
    ranked = _prioritized_archive_entries(campaign_state, limit=len(archive))
    rank_map = {int(entry.get("sessionNumber", -1)): index + 1 for index, entry in enumerate(ranked)}
    priority_map = {int(entry.get("sessionNumber", -1)): entry.get("_priority", {}) for entry in ranked}
    entries: List[Dict[str, Any]] = []
    for entry in reversed(archive):
        session_number = int(entry.get("sessionNumber", -1))
        hook_connections = _archive_hook_connections(entry, hook)
        priority = priority_map.get(session_number, {})
        entries.append(
            {
                "sessionNumber": session_number,
                "openingSummary": str(entry.get("openingSummary") or "セッションの始まりの記録はまだまとまっていない。"),
                "title": entry.get("title"),
                "tone": entry.get("tone"),
                "keyRoleSlotId": entry.get("keyRoleSlotId"),
                "keyRoleLabel": entry.get("keyRoleLabel"),
                "keyOccupantLabel": entry.get("keyOccupantLabel"),
                "protected": entry.get("protected"),
                "lost": entry.get("lost"),
                "carriedForward": entry.get("carriedForward"),
                "summary": entry.get("summary"),
                "whatRemained": entry.get("whatRemained"),
                "viceSummary": entry.get("viceSummary"),
                "tabooSummary": entry.get("tabooSummary"),
                "hiddenCrimeSummary": entry.get("hiddenCrimeSummary"),
                "ritualPollutionSummary": entry.get("ritualPollutionSummary"),
                "archivedCauseEcho": entry.get("archivedCauseEcho"),
                "resurfacingRisk": entry.get("resurfacingRisk"),
                "unresolvedVice": entry.get("unresolvedVice"),
                "unresolvedTaboo": entry.get("unresolvedTaboo"),
                "priorityRank": rank_map.get(session_number),
                "priorityDebug": {
                    "recency": round(float(priority.get("recency", 0.0)), 1),
                    "severity": round(float(priority.get("severity", 0.0)), 1),
                    "visibility": round(float(priority.get("visibility", 0.0)), 1),
                    "relevance": round(
                        float(priority.get("roleSlotRelevance", 0.0))
                        + float(priority.get("institutionRelevance", 0.0))
                        + float(priority.get("currentEventRelevance", 0.0)),
                        1,
                    ),
                    "total": round(float(priority.get("total", 0.0)), 1),
                },
                "hookConnections": hook_connections,
                "filterTags": _archive_filter_tags(entry, hook_connections),
            }
        )

    role_filters = []
    seen_roles: set[str] = set()
    for entry in entries:
        role_slot_id = str(entry.get("keyRoleSlotId") or "").strip()
        role_label = str(entry.get("keyRoleLabel") or "").strip()
        if not role_slot_id or not role_label or role_slot_id in seen_roles:
            continue
        seen_roles.add(role_slot_id)
        role_filters.append({"roleSlotId": role_slot_id, "roleLabel": role_label})

    return {
        "entries": entries,
        "roleFilters": role_filters,
        "archiveCompression": copy.deepcopy(campaign_state.get("archiveCompression")),
    }


def _next_main_event_candidates(campaign_state: Dict[str, Any]) -> List[str]:
    catalog = campaign_state["events"]["catalog"]
    current_event_id = campaign_state["currentEventId"]
    reverberation = _free_action_reverberation(campaign_state)
    archive_candidates = _archive_event_candidates(campaign_state)
    ordered = sorted(
        catalog.values(),
        key=lambda event: (-float(event["pressure"]), EVENT_ORDER.index(event["eventId"])),
    )
    lines = [*archive_candidates, *reverberation["eventCandidates"]]
    for event in ordered[:3]:
        if event["eventId"] == current_event_id:
            lines.append(f"{event['label']}: 圧が{float(event['pressure']):.1f}/100まで残り、次の主事件になりやすい。")
        else:
            lines.append(f"{event['label']}: 余圧が{float(event['pressure']):.1f}/100残っている。")
    return _dedupe_lines(lines, limit=3)


def _carried_pressures(campaign_state: Dict[str, Any]) -> List[str]:
    event = _current_event(campaign_state)
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    reverberation = _free_action_reverberation(campaign_state)
    lines: List[str] = []
    if float(event["pressure"]) >= 45:
        lines.append(f"{event['label']}の余波が続き、次の判断を急がせる。")
    if float(hub["heat"]) >= 45 or float(hub["stability"]) < 55:
        lines.append(f"{hub['label']}では不信と緊張が残り、場の空気がまだ落ち着いていない。")
    if float(dungeon["threat"]) >= 45 or float(dungeon["sealIntegrity"]) < 65:
        lines.append(f"{dungeon['label']}では封印の負担が残り、奥ほど危うい。")
    if float(campaign_state.get("vicePressure", 0.0)) >= 45:
        lines.append("ごまかしや横流しの余圧が残り、次の判断にも濁りが差している。")
    if float(campaign_state.get("tabooPressure", 0.0)) >= 45 or float(campaign_state.get("ritualPollution", 0.0)) >= 35:
        lines.append("禁忌の痕が薄く残り、祈りと封印のどちらにも負担がかかっている。")
    for tension in _top_role_slot_repercussions(campaign_state, limit=2):
        if tension["mode"] == "retaliation":
            lines.append(f"{tension['roleLabel']}の座では報いを返す気配が強く、次の接触も荒れやすい。")
        elif tension["mode"] == "distrust":
            lines.append(f"{tension['roleLabel']}の座では役目そのものへの不信が残り、話が通りにくい。")
        else:
            lines.append(f"{tension['roleLabel']}の座では疑いが残り、細かな確認が増えやすい。")
    lines.extend(reverberation["pressureLines"])
    if not lines:
        lines.append("大きな圧は少し引いたが、傷はまだ消えていない。")
    return _dedupe_lines(lines, limit=3)


def _npc_carry_overs(campaign_state: Dict[str, Any]) -> List[str]:
    reverberation = _free_action_reverberation(campaign_state)
    archive_lines = _archive_npc_carry_overs(campaign_state)
    tension_lines: List[str] = []
    for tension in _top_role_slot_repercussions(campaign_state, limit=2):
        if tension["mode"] == "retaliation":
            tension_lines.append(
                f"{tension['occupantLabel']}: いまは疑いを越えて、報いを返す機会まで測っている。"
            )
        elif tension["mode"] == "distrust":
            tension_lines.append(
                f"{tension['occupantLabel']}: 役目ごと信用を崩されたと見て、まず距離を取っている。"
            )
        else:
            tension_lines.append(
                f"{tension['occupantLabel']}: まだ疑いを解いておらず、細かな違和感から確かめようとしている。"
            )

    def score(npc: Dict[str, Any]) -> float:
        secret_state = str(npc.get("secretState", "hidden"))
        secret_score = {"hidden": 0.0, "hinted": 30.0, "exposed": 55.0}.get(secret_state, 0.0)
        weakness_score = 20.0 if npc.get("knownWeakness") else 0.0
        return secret_score + weakness_score + float(npc.get("stress", 0.0)) - float(npc.get("trust", 0.0)) * 0.2

    lines = []
    ordered = sorted(campaign_state["npcs"].values(), key=score, reverse=True)
    replacements = [npc for npc in campaign_state["npcs"].values() if npc.get("lastReplacement")]
    for npc in replacements:
        replacement = npc.get("lastReplacement")
        lines.append(
            f"{npc['roleLabel']}: {replacement['previousOccupantName']}は{replacement['reason']}で退き、"
            f"{replacement['newOccupantName']}が座に就いた。{npc['conflictsWithRoleLabel']}との利害はそのまま残る。"
        )
    for npc in ordered:
        if npc.get("lastReplacement"):
            continue
        parts = [f"{npc['conflictsWithLabel']}との利害対立が続く"]
        if npc.get("secretState") == "exposed":
            parts.append("秘密がすでに表へ出ている")
        elif npc.get("secretState") == "hinted":
            parts.append("秘密の気配がまだ尾を引く")
        if npc.get("knownWeakness"):
            parts.append("弱みも見られている")
        if len(parts) == 1 and float(npc.get("stress", 0.0)) >= 55:
            parts.append("緊張が高いままだ")
        lines.append(f"{npc['displayName']}: {'。'.join(parts)}。")
        if len(lines) >= 3:
            break
    lines = [*archive_lines, *tension_lines, *reverberation["npcCarryOvers"], *lines]
    return _dedupe_lines(lines, limit=3)


def _scars_remaining(campaign_state: Dict[str, Any], ending: Dict[str, Any]) -> List[str]:
    lines = [ending["whatRemained"], f"失ったもの: {ending['lost']}。", *_archive_scars_remaining(campaign_state)]
    for tension in _top_role_slot_repercussions(campaign_state, limit=2):
        if tension["mode"] == "retaliation":
            lines.append(f"{tension['roleLabel']}の座では報いを返す気配が残り、関係のこじれがまだ深い。")
        elif tension["mode"] == "distrust":
            lines.append(f"{tension['roleLabel']}の座では不信が残り、役目どうしの橋が細っている。")
        else:
            lines.append(f"{tension['roleLabel']}の座では疑いが残り、些細な綻びでも再燃しかねない。")
    if float(campaign_state.get("hiddenCrimes", 0.0)) >= 2.5:
        lines.append("まだ表に出ていない不正が残り、次の検分で露見へ転ぶおそれがある。")
    if float(campaign_state.get("publicInfamy", 0.0)) >= 3.0 or float(campaign_state.get("publicShame", 0.0)) >= 28.0:
        lines.append("悪評が残り、関わっていない座にも疑いがにじんでいる。")
    if float(campaign_state.get("ritualPollution", 0.0)) >= 35.0 and campaign_state.get("tabooTrace"):
        lines.append("禁じ手の濁りが祈りと封印に残り、簡単には洗えない。")
    for trace in reversed(list(campaign_state.get("viceTrace", []))[-2:]):
        lines.append(trace)
    for trace in reversed(list(campaign_state.get("tabooTrace", []))[-2:]):
        lines.append(trace)
    world_marks = list(campaign_state.get("worldMarks", []))
    for mark in reversed(world_marks):
        if mark == f"小結末: {ending['title']}":
            continue
        lines.append(mark if str(mark).endswith("。") else f"{mark}。")
    return _dedupe_lines(lines, limit=3)


def _protected_assets(campaign_state: Dict[str, Any], ending: Dict[str, Any]) -> List[str]:
    hub = campaign_state["hub"]
    dungeon = campaign_state["dungeon"]
    lines = [ending["protected"]]
    if float(hub["supply"]) >= 50:
        lines.append(f"{hub['label']}へ届く補給はまだ途切れていない。")
    if float(dungeon["sealIntegrity"]) >= 55:
        lines.append(f"{dungeon['label']}の封印はまだ持ちこたえている。")
    if float(campaign_state.get("collectiveEfficacy", 0.0)) >= 55:
        lines.append("まだ人の連携は切れていない。")
    return _dedupe_lines(lines, limit=3)


def build_next_session_hook(world_state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_campaign_state(world_state)
    campaign = state["campaign_state"]
    ending = campaign.get("lastEnding")
    if not isinstance(ending, dict):
        raise WorldStateError("今のセッションはまだ終了していません。次のセッションへ進めるのは 6 手目の後です。")
    hook = {
        "nextMainEventCandidates": _next_main_event_candidates(campaign),
        "carriedPressures": _carried_pressures(campaign),
        "npcCarryOvers": _npc_carry_overs(campaign),
        "scarsRemaining": _scars_remaining(campaign, ending),
        "protectedAssets": _protected_assets(campaign, ending),
        "archivedCauseEchoes": _archived_cause_echoes(campaign),
        "resurfacingRisks": _resurfacing_risks(campaign),
        "unresolvedVice": _unresolved_vice(campaign),
        "unresolvedTaboo": _unresolved_taboo(campaign),
    }
    if campaign.get("nextSessionHookNotes"):
        hook["carriedPressures"] = _dedupe_lines([*hook["carriedPressures"], *campaign["nextSessionHookNotes"]], limit=3)
    return hook


def prepare_next_session(world_state: Dict[str, Any]) -> Dict[str, Any]:
    state = ensure_campaign_state(world_state)
    campaign = copy.deepcopy(state["campaign_state"])
    ending = campaign.get("lastEnding")
    if not isinstance(ending, dict):
        raise WorldStateError("今のセッションはまだ終了していません。次のセッションへ進めるのは 6 手目の後です。")

    archive = list(campaign.get("sessionArchive", []))
    session_number = int(ending["sessionNumber"])
    already_archived = any(int(entry.get("sessionNumber", -1)) == session_number for entry in archive)
    if not already_archived:
        archive.append(_archive_entry(campaign, ending))
        campaign["sessionArchive"] = archive
        _compress_session_archive(campaign)
        _advance_role_slot_occupants(campaign, ending)
    _apply_archive_echoes_to_state(state, campaign)
    campaign["nextSessionHook"] = build_next_session_hook({**state, "campaign_state": campaign})
    next_session_number = int(ending["sessionNumber"]) + 1
    campaign.setdefault("sessionOpeningHooks", {})[str(next_session_number)] = _session_opening_summary_from_hook(campaign["nextSessionHook"])
    state["campaign_state"] = _refresh_campaign_state(state, campaign)
    return state


def build_campaign_display(world_state: Dict[str, Any], scene_title: str) -> Dict[str, Any]:
    state = ensure_campaign_state(world_state)
    campaign = state["campaign_state"]
    event = current_event(state)
    hub = current_hub(state)
    dungeon = current_dungeon(state)
    trace = build_player_trace(state)
    world_pulse = compose_world_pulse_copy(state.get("cycle_state", {}))
    hook = copy.deepcopy(campaign.get("nextSessionHook"))
    return {
        "playCycle": copy.deepcopy(campaign["session"]),
        "storyGuide": build_story_guide(state, scene_title),
        "currentEvent": event,
        "hub": hub,
        "dungeon": dungeon,
        "worldPulseGuide": world_pulse,
        "namedCast": [compose_npc_copy(_annotate_npc_with_archive_overlay(campaign, copy.deepcopy(campaign["npcs"][npc_id]))) for npc_id in NPC_ORDER],
        "playerTrace": trace,
        "endingForecast": _ending_forecast(campaign),
        "newGameGenesis": _new_game_genesis_surface(campaign),
        "sessionEnding": copy.deepcopy(campaign.get("lastEnding")),
        "lastTransition": copy.deepcopy(campaign.get("lastTransition")),
        "nextSessionHook": hook,
        "archiveReview": _archive_review(campaign, hook),
        "archiveInspector": _archive_inspector(campaign, hook),
        "saveMeta": copy.deepcopy(campaign.get("saveMeta")),
        "viceTaboo": {
            "vicePressure": campaign.get("vicePressure"),
            "tabooPressure": campaign.get("tabooPressure"),
            "moralCorrosion": campaign.get("moralCorrosion"),
            "publicInfamy": campaign.get("publicInfamy"),
            "hiddenCrimes": campaign.get("hiddenCrimes"),
            "ritualPollution": campaign.get("ritualPollution"),
            "publicLegitimacy": campaign.get("publicLegitimacy"),
            "collectiveEfficacy": campaign.get("collectiveEfficacy"),
            "viceSources": copy.deepcopy(campaign.get("viceSources", [])),
            "tabooSources": copy.deepcopy(campaign.get("tabooSources", [])),
            "viceTrace": list(campaign.get("viceTrace", []))[-3:],
            "tabooTrace": list(campaign.get("tabooTrace", []))[-3:],
        },
        "lastFreeAction": copy.deepcopy(campaign.get("lastFreeAction")),
    }
