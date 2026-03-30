from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple
import copy

from .intent import PlayerIntent
from .scene_builder import SceneContext


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def title_from_vessel_points(points: float) -> str:
    if points < 120:
        return "名もなき介入者"
    if points < 320:
        return "名を覚えられる者"
    if points < 620:
        return "都市を動かす者"
    if points < 980:
        return "時代の継ぎ手"
    return "神話に触れる者"


@dataclass(frozen=True)
class ResolutionResult:
    intent_type: str
    outcome: str
    capability: float
    difficulty: float
    delta: float
    vessel_gain: float
    status_after: str
    node_patch: Dict[str, Any]
    institution_patch: Dict[str, Any]
    world_pulse_patch: Dict[str, Any]
    note: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _intent_capability(protagonist: Dict[str, Any], intent: PlayerIntent, recommended_vectors: List[str]) -> float:
    skills = protagonist.get("skills", {})
    tendencies = protagonist.get("tendencies", {})
    skill_score = sum(float(skills.get(key, 45.0)) for key in intent.skill_keys) / max(len(intent.skill_keys), 1)
    tendency_score = sum(float(tendencies.get(key, 50.0)) for key in intent.tendency_keys) / max(len(intent.tendency_keys), 1)
    recommendation_bonus = 5.0 if any(key in recommended_vectors for key in intent.skill_keys) else 0.0
    return round(skill_score * 0.78 + tendency_score * 0.22 + recommendation_bonus, 1)


def _difficulty(node: Dict[str, Any], intent: PlayerIntent) -> float:
    severity = float(node.get("severity", 0.0))
    urgency = float(node.get("urgency", 0.0))
    stage = float(node.get("stage", 1))
    return round(severity * 0.6 + urgency * 0.4 + stage * 2.5 + intent.pressure_bias, 1)


def resolve_intent(world_state: Dict[str, Any], context: SceneContext, intent: PlayerIntent) -> ResolutionResult:
    protagonist = world_state["resolved_world"]["protagonist"]
    node = context.focus_node
    recommended_vectors = ((node.get("quest_offers") or [{}])[0].get("recommended_vectors") or [])
    capability = _intent_capability(protagonist, intent, recommended_vectors)
    difficulty = _difficulty(node, intent)
    delta = round(capability - difficulty, 1)

    if delta >= 10:
        outcome = "success"
        vessel_gain = round(22.0 * intent.impact_scale, 1)
        status_after = "resolved" if float(node.get("stage", 1)) >= 2 or float(node.get("severity", 0.0)) <= 72.0 else "cooling"
        node_patch = {"severity": -24.0 * intent.impact_scale, "urgency": -16.0 * intent.impact_scale, "stage": 0}
        institution_patch = {"breach_risk": -10.0 * intent.impact_scale, "support": 6.0 * intent.impact_scale}
        world_pulse_patch = {"distortion": -3.2 * intent.impact_scale, "divine_war_pressure": -1.8 * intent.impact_scale}
        note = "介入が事件の熱を押し下げた。"
    elif delta >= -12:
        outcome = "partial_success"
        vessel_gain = round(12.0 * intent.impact_scale, 1)
        status_after = "cooling"
        node_patch = {"severity": -11.0 * intent.impact_scale, "urgency": -7.0 * intent.impact_scale, "stage": 0}
        institution_patch = {"breach_risk": -4.5 * intent.impact_scale, "support": 2.5 * intent.impact_scale}
        world_pulse_patch = {"distortion": -1.2 * intent.impact_scale, "divine_war_pressure": -0.8 * intent.impact_scale}
        note = "火種は残るが、局地は一度引いた。"
    else:
        outcome = "failure"
        vessel_gain = round(4.0 * intent.impact_scale, 1)
        status_after = "active"
        node_patch = {"severity": 8.0 * intent.impact_scale, "urgency": 10.0 * intent.impact_scale, "stage": 1}
        institution_patch = {"breach_risk": 6.0 * intent.impact_scale, "support": -3.0 * intent.impact_scale}
        world_pulse_patch = {"distortion": 2.4 * intent.impact_scale, "divine_war_pressure": 1.4 * intent.impact_scale}
        note = "介入は逆目に出て、圧力が一段上がった。"

    return ResolutionResult(
        intent_type=intent.intent_type,
        outcome=outcome,
        capability=capability,
        difficulty=difficulty,
        delta=delta,
        vessel_gain=vessel_gain,
        status_after=status_after,
        node_patch=node_patch,
        institution_patch=institution_patch,
        world_pulse_patch=world_pulse_patch,
        note=note,
    )


def _institution_status(breach_risk: float) -> str:
    if breach_risk >= 85:
        return "broken"
    if breach_risk >= 50:
        return "strained"
    return "active"


def _region_delta(resolution: ResolutionResult) -> Dict[str, float]:
    if resolution.outcome == "failure":
        return {"law_order": -2.0, "legitimacy": -1.0, "racial_tension": 2.0}
    if resolution.outcome == "partial_success":
        return {"law_order": 1.0, "legitimacy": 1.0, "racial_tension": -1.0}
    return {"law_order": 2.5, "legitimacy": 1.5, "racial_tension": -2.0}


def _faction_delta(resolution: ResolutionResult) -> Dict[str, float]:
    if resolution.outcome == "failure":
        return {"legitimacy": -1.5, "treasury": -0.5}
    if resolution.outcome == "partial_success":
        return {"legitimacy": 1.5, "treasury": 0.6}
    return {"legitimacy": 3.0, "treasury": 1.2}


def apply_resolution(world_state: Dict[str, Any], context: SceneContext, intent: PlayerIntent, resolution: ResolutionResult) -> Dict[str, Any]:
    updated = copy.deepcopy(world_state)
    resolved_world = updated["resolved_world"]
    node_id = context.focus_node["node_id"]
    active_nodes = resolved_world.get("active_nodes", {})
    if node_id not in active_nodes:
        raise RuntimeError(f"Focus node is no longer active: {node_id}")
    node = active_nodes[node_id]

    node["severity"] = round(clamp(float(node.get("severity", 0.0)) + float(resolution.node_patch["severity"])), 1)
    node["urgency"] = round(clamp(float(node.get("urgency", 0.0)) + float(resolution.node_patch["urgency"])), 1)
    node["stage"] = max(1, min(4, int(node.get("stage", 1)) + int(resolution.node_patch["stage"])))
    node["status"] = resolution.status_after

    institution_patch_record: Dict[str, float] = {}
    institution = context.focus_institution
    if institution is not None:
        updated_institution = resolved_world["institutions"][institution["institution_id"]]
        updated_institution["breach_risk"] = round(
            clamp(float(updated_institution.get("breach_risk", 0.0)) + float(resolution.institution_patch["breach_risk"])),
            1,
        )
        updated_institution["support"] = round(
            clamp(float(updated_institution.get("support", 0.0)) + float(resolution.institution_patch["support"])),
            1,
        )
        updated_institution["status"] = _institution_status(float(updated_institution["breach_risk"]))
        institution_patch_record = {
            "institution_breach_risk": updated_institution["breach_risk"],
            "institution_support": updated_institution["support"],
        }

    cycle_state = updated.setdefault("cycle_state", {})
    cycle_state["distortion"] = round(
        clamp(float(cycle_state.get("distortion", 0.0)) + float(resolution.world_pulse_patch["distortion"])),
        1,
    )
    cycle_state["divine_war_pressure"] = round(
        clamp(float(cycle_state.get("divine_war_pressure", 0.0)) + float(resolution.world_pulse_patch["divine_war_pressure"])),
        1,
    )
    notes = list(cycle_state.get("notes") or [])
    notes.insert(0, resolution.note)
    cycle_state["notes"] = notes[:3]

    protagonist = resolved_world["protagonist"]
    protagonist["vessel_points"] = round(float(protagonist.get("vessel_points", 0.0)) + resolution.vessel_gain, 1)
    protagonist["existence_title"] = title_from_vessel_points(float(protagonist["vessel_points"]))

    region_deltas = {}
    region_delta = _region_delta(resolution)
    for region_id in node.get("regions", []):
        region = resolved_world["regions"].get(region_id)
        if not region:
            continue
        region_deltas[region_id] = {}
        for key, delta_value in region_delta.items():
            current = float(region["values"].get(key, 50.0))
            region["values"][key] = round(clamp(current + delta_value), 1)
            region_deltas[region_id][key] = delta_value

    faction_deltas = {}
    faction_delta = _faction_delta(resolution)
    for faction_id in node.get("factions", []):
        faction = resolved_world["factions"].get(faction_id)
        if not faction:
            continue
        faction_deltas[faction_id] = {}
        for key, delta_value in faction_delta.items():
            current = float(faction.get(key, 50.0))
            faction[key] = round(clamp(current + delta_value), 1)
            faction_deltas[faction_id][key] = delta_value

    if resolution.status_after == "resolved":
        node["status"] = "resolved"
        resolved_world.setdefault("archived_nodes", {})[node_id] = copy.deepcopy(node)
        del active_nodes[node_id]

    history_entry = {
        "season": int(context.world["season_index"]),
        "year": int(context.world["calendar_year"]),
        "node_id": node_id,
        "node_title": context.focus_node.get("title", node_id),
        "event_family": context.focus_node.get("event_family", "local_event"),
        "approach": intent.intent_type,
        "outcome": resolution.outcome,
        "intervention": True,
        "capability": resolution.capability,
        "difficulty": resolution.difficulty,
        "delta": resolution.delta,
        "resulting_status": resolution.status_after,
        "vessel_gain": resolution.vessel_gain,
        "realized_media": (context.focus_node.get("projected_legacies") or ["伝承"])[: (2 if resolution.outcome != "failure" else 1)],
        "region_deltas": region_deltas,
        "faction_deltas": faction_deltas,
        "institution_patch": institution_patch_record,
        "notes": [resolution.note],
    }
    resolved_world.setdefault("resolution_history", []).append(history_entry)
    return updated
