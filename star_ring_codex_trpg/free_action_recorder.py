from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping
import copy

from .free_action_adjudicator import derived_intent_type, validate_structured_result
from .gameplay_experience import advance_campaign_state, apply_role_slot_repercussions


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, float(value))), 1)


def _append_limited(existing: Iterable[str], additions: Iterable[str], limit: int) -> List[str]:
    lines: List[str] = []
    seen: set[str] = set()
    for raw_line in list(existing) + list(additions):
        line = str(raw_line or "").strip()
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines[-limit:]


def _resolution_outcome(outcome: str) -> str:
    if outcome == "success":
        return "success"
    if outcome == "partial_success":
        return "partial_success"
    if outcome == "concealed_success":
        return "failure"
    return "failure"


def _free_action_residue_label(structured_result: Mapping[str, Any]) -> str:
    normalized = structured_result.get("normalized_intent", {})
    adjudication = structured_result.get("adjudication", {})
    world_patch = structured_result.get("consequence", {}).get("world_patch", {})
    discovery = str(adjudication.get("discovery_state", "unseen"))
    outcome = str(adjudication.get("outcome", "unknown"))
    if normalized.get("taboo_tags") and float(world_patch.get("ritual_pollution_delta", 0.0)) > 0.0:
        return "禁じ手の濁り"
    if discovery == "exposed":
        return "露見した不正"
    if discovery in {"suspected", "contested"}:
        return "疑いを残した不正"
    if float(world_patch.get("hidden_crimes_delta", 0.0)) > 0.0 or outcome == "concealed_success":
        return "隠れた不正の痕"
    return "後ろ暗い余波"


def _node_container(resolved_world: Dict[str, Any], node_id: str) -> Dict[str, Any] | None:
    active_nodes = resolved_world.get("active_nodes", {})
    if node_id in active_nodes:
        return active_nodes[node_id]
    archived_nodes = resolved_world.get("archived_nodes", {})
    if node_id in archived_nodes:
        return archived_nodes[node_id]
    return None


def _apply_node_patch(world_state: Dict[str, Any], scene_context: Any, node_patch: Mapping[str, Any]) -> None:
    node_id = scene_context.focus_node["node_id"]
    node = _node_container(world_state["resolved_world"], node_id)
    if not node:
        return
    node["severity"] = _clamp(float(node.get("severity", 0.0)) + float(node_patch.get("severity_delta", 0.0)))
    node["urgency"] = _clamp(float(node.get("urgency", 0.0)) + float(node_patch.get("urgency_delta", 0.0)))
    node["status"] = str(node_patch.get("status_after") or node.get("status") or "active")


def _institution_status(breach_risk: float) -> str:
    if breach_risk >= 85:
        return "broken"
    if breach_risk >= 50:
        return "strained"
    return "active"


def _apply_institution_patches(world_state: Dict[str, Any], institution_patch: Iterable[Mapping[str, Any]]) -> None:
    institutions = world_state["resolved_world"].get("institutions", {})
    for patch in institution_patch:
        institution_id = str(patch.get("institution_id") or "").strip()
        if not institution_id or institution_id not in institutions:
            continue
        institution = institutions[institution_id]
        institution["breach_risk"] = _clamp(float(institution.get("breach_risk", 0.0)) + float(patch.get("breach_risk_delta", 0.0)))
        institution["support"] = _clamp(float(institution.get("support", 0.0)) + float(patch.get("support_delta", 0.0)))
        institution["status"] = str(patch.get("status_after") or _institution_status(float(institution["breach_risk"])))


def _apply_region_world_patch(world_state: Dict[str, Any], scene_context: Any, world_patch: Mapping[str, Any], target_regions: Iterable[str]) -> None:
    resolved_world = world_state["resolved_world"]
    regions = resolved_world.get("regions", {})
    region_ids = list(dict.fromkeys([*scene_context.focus_node.get("regions", []), *list(target_regions)]))
    for region_id in region_ids:
        region = regions.get(region_id)
        if not region:
            continue
        values = region.setdefault("values", {})
        values["law_order"] = _clamp(float(values.get("law_order", 50.0)) + float(world_patch.get("law_order_delta", 0.0)))
        values["legitimacy"] = _clamp(float(values.get("legitimacy", 50.0)) + float(world_patch.get("legitimacy_delta", 0.0)))


def _apply_cycle_patch(world_state: Dict[str, Any], campaign_state: Dict[str, Any], world_patch: Mapping[str, Any]) -> None:
    cycle_state = world_state.setdefault("cycle_state", {})
    distortion_delta = float(world_patch.get("taboo_pressure_delta", 0.0)) * 0.08 + float(world_patch.get("ritual_pollution_delta", 0.0)) * 0.06
    divine_delta = float(world_patch.get("taboo_pressure_delta", 0.0)) * 0.04 + float(world_patch.get("public_infamy_delta", 0.0)) * 0.02
    succession_delta = float(world_patch.get("moral_corrosion_delta", 0.0)) * 0.05 + float(world_patch.get("legitimacy_delta", 0.0)) * -0.04
    cycle_state["distortion"] = _clamp(float(cycle_state.get("distortion", 0.0)) + distortion_delta)
    cycle_state["divine_war_pressure"] = _clamp(float(cycle_state.get("divine_war_pressure", 0.0)) + divine_delta)
    cycle_state["succession_pressure"] = _clamp(float(cycle_state.get("succession_pressure", 0.0)) + succession_delta)
    notes = list(cycle_state.get("notes") or [])
    notes.insert(0, "自由行動の余波が世界に残った。")
    cycle_state["notes"] = notes[:4]

    campaign_state["vicePressure"] = _clamp(float(campaign_state.get("vicePressure", 0.0)) + float(world_patch.get("vice_pressure_delta", 0.0)))
    campaign_state["tabooPressure"] = _clamp(float(campaign_state.get("tabooPressure", 0.0)) + float(world_patch.get("taboo_pressure_delta", 0.0)))
    campaign_state["moralCorrosion"] = _clamp(float(campaign_state.get("moralCorrosion", 0.0)) + float(world_patch.get("moral_corrosion_delta", 0.0)))
    campaign_state["ritualPollution"] = _clamp(float(campaign_state.get("ritualPollution", 0.0)) + float(world_patch.get("ritual_pollution_delta", 0.0)))
    campaign_state["publicInfamy"] = _clamp(float(campaign_state.get("publicInfamy", 0.0)) + float(world_patch.get("public_infamy_delta", 0.0)))
    campaign_state["hiddenCrimes"] = _clamp(float(campaign_state.get("hiddenCrimes", 0.0)) + float(world_patch.get("hidden_crimes_delta", 0.0)))


def _apply_npc_patch(campaign_state: Dict[str, Any], npc_patch: Iterable[Mapping[str, Any]]) -> None:
    npcs = campaign_state.get("npcs", {})
    for patch in npc_patch:
        role_slot_id = str(patch.get("role_slot_id") or "").strip()
        if role_slot_id not in npcs:
            continue
        npc = npcs[role_slot_id]
        npc["trust"] = _clamp(float(npc.get("trust", 50.0)) + float(patch.get("trust_delta", 0.0)))
        npc["stress"] = _clamp(float(npc.get("stress", 50.0)) + float(patch.get("stress_delta", 0.0)))
        if "secret_state_after" in patch:
            npc["secretState"] = str(patch["secret_state_after"])
            npc["lastSecretTrigger"] = "自由行動の余波"
        if bool(patch.get("weakness_revealed")):
            npc["knownWeakness"] = npc.get("weakness")
            npc["lastWeaknessTrigger"] = "自由行動の余波"
        if patch.get("occupant_status_after"):
            npc["occupantStatus"] = str(patch["occupant_status_after"])
        memory = list(npc.get("memory", []))
        memory.append("自由行動の余波がこの座に残った。")
        npc["memory"] = memory[-6:]


def _free_action_repercussion_deltas(structured_result: Mapping[str, Any]) -> tuple[float, float, float]:
    normalized = structured_result.get("normalized_intent", {})
    adjudication = structured_result.get("adjudication", {})
    world_patch = structured_result.get("consequence", {}).get("world_patch", {})
    discovery = str(adjudication.get("discovery_state", "unseen"))
    outcome = str(adjudication.get("outcome", "unknown"))

    suspicion = float(world_patch.get("hidden_crimes_delta", 0.0)) * 3.6
    distrust = float(world_patch.get("public_infamy_delta", 0.0)) * 4.2
    retaliation = float(world_patch.get("ritual_pollution_delta", 0.0)) * 0.18

    suspicion += {
        "unseen": 1.0,
        "suspected": 6.0,
        "contested": 8.0,
        "exposed": 4.0,
    }.get(discovery, 3.0)
    distrust += {
        "unseen": 0.0,
        "suspected": 3.0,
        "contested": 5.0,
        "exposed": 11.0,
    }.get(discovery, 1.5)
    retaliation += {
        "success": 0.0,
        "partial_success": 1.8,
        "failure": 3.5,
        "concealed_success": 1.0,
        "exposed": 6.0,
        "backlash": 14.0,
    }.get(outcome, 1.5)

    if normalized.get("vice_tags"):
        suspicion += 1.8
        distrust += 3.5
    if normalized.get("taboo_tags"):
        retaliation += 7.0
        suspicion += 1.5
    return round(suspicion, 1), round(distrust, 1), round(retaliation, 1)


def apply_free_action_result(
    world_state: Dict[str, Any],
    scene_context: Any,
    structured_result: Mapping[str, Any],
) -> Dict[str, Any]:
    validate_structured_result(structured_result)
    normalized = structured_result["normalized_intent"]
    intent_type = derived_intent_type({"normalized_intent": normalized})
    adjudication = structured_result["adjudication"]
    progressed = advance_campaign_state(
        world_state,
        choice_id="custom_action",
        intent={"intent_type": intent_type},
        resolution={"outcome": _resolution_outcome(str(adjudication["outcome"]))},
    )
    updated = copy.deepcopy(progressed)
    campaign_state = updated["campaign_state"]
    consequence = structured_result["consequence"]

    _apply_node_patch(updated, scene_context, consequence["node_patch"])
    _apply_institution_patches(updated, consequence["institution_patch"])
    _apply_region_world_patch(updated, scene_context, consequence["world_patch"], normalized.get("target_regions", []))
    _apply_cycle_patch(updated, campaign_state, consequence["world_patch"])
    _apply_npc_patch(campaign_state, consequence["npc_patch"])

    campaign_state["worldMarks"] = _append_limited(
        campaign_state.get("worldMarks", []),
        consequence["campaign_patch"].get("world_marks_append", []),
        12,
    )
    campaign_state["viceTrace"] = _append_limited(
        campaign_state.get("viceTrace", []),
        consequence["campaign_patch"].get("vice_trace_append", []),
        16,
    )
    campaign_state["tabooTrace"] = _append_limited(
        campaign_state.get("tabooTrace", []),
        consequence["campaign_patch"].get("taboo_trace_append", []),
        16,
    )
    campaign_state["nextSessionHookNotes"] = _append_limited(
        campaign_state.get("nextSessionHookNotes", []),
        consequence["campaign_patch"].get("next_session_hook_append", []),
        12,
    )

    free_action_entry = {
        "actionId": structured_result["action_id"],
        "sessionNumber": structured_result["session"]["session_number"],
        "turnCounter": structured_result["session"]["turn_counter"],
        "phaseLabel": structured_result["session"]["phase_label"],
        "summary": structured_result["source"]["player_summary"],
        "freeActionSummary": structured_result["source"]["player_summary"],
        "freeActionResidueLabel": _free_action_residue_label(structured_result),
        "normalizedIntent": normalized,
        "adjudication": structured_result["adjudication"],
        "logs": structured_result["consequence"]["logs"],
    }
    history = list(campaign_state.get("freeActionHistory", []))
    history.append(free_action_entry)
    campaign_state["freeActionHistory"] = history[-24:]
    campaign_state["lastFreeAction"] = free_action_entry

    targeted_role_slot_ids = [
        role_slot_id
        for role_slot_id in normalized.get("target_role_slots", [])
        if role_slot_id in campaign_state.get("npcs", {})
    ]
    if not targeted_role_slot_ids:
        targeted_role_slot_ids = [
            str(patch.get("role_slot_id")).strip()
            for patch in consequence.get("npc_patch", [])
            if str(patch.get("role_slot_id")).strip() in campaign_state.get("npcs", {})
        ]
    suspicion_delta, distrust_delta, retaliation_delta = _free_action_repercussion_deltas(structured_result)
    apply_role_slot_repercussions(
        campaign_state,
        targeted_role_slot_ids,
        suspicion_delta=suspicion_delta,
        distrust_delta=distrust_delta,
        retaliation_delta=retaliation_delta,
    )

    transition = dict(campaign_state.get("lastTransition") or {})
    transition["customActionId"] = structured_result["action_id"]
    transition["customActionSummary"] = structured_result["source"]["player_summary"]
    transition["customActionResidueLabel"] = _free_action_residue_label(structured_result)
    transition["customActionOutcome"] = structured_result["adjudication"]["outcome"]
    transition["customActionNote"] = structured_result["adjudication"]["note"]
    transition["customActionAfterglow"] = structured_result["consequence"]["logs"]["afterglow"]
    campaign_state["lastTransition"] = transition
    return updated
