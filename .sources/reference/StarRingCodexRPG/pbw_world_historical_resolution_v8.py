
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBW World Historical Node Resolution Layer v8

v7 の世界史事件ノードを、鎮圧・和解・神罰化・再編・再燃まで進める層。
standalone で動作し、sample seed を生成する。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import importlib.util
import sys
import json
import copy


def load_v7():
    here = Path(__file__).resolve().parent
    target = here / "pbw_world_historical_nodes_v7.py"
    spec = importlib.util.spec_from_file_location("pbw_v7", target)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


v7 = load_v7()


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def title_from_points(points: float) -> str:
    if points < 120:
        return "名もなき介入者"
    if points < 320:
        return "名を覚えられる者"
    if points < 620:
        return "都市を動かす者"
    if points < 980:
        return "時代の継ぎ手"
    return "神話に触れる者"


@dataclass
class ProtagonistProfile:
    protagonist_id: str
    label_ja: str
    race: str
    archetype: str
    skills: Dict[str, float]
    tendencies: Dict[str, float]
    vessel_points: float = 40.0
    existence_title: str = "名もなき介入者"

    def refresh_title(self) -> None:
        self.existence_title = title_from_points(self.vessel_points)


@dataclass
class HistoricalResolution:
    season: int
    year: int
    node_id: str
    node_title: str
    event_family: str
    approach: str
    outcome: str
    intervention: bool
    capability: float
    difficulty: float
    delta: float
    resulting_status: str
    vessel_gain: float
    realized_media: List[str] = field(default_factory=list)
    region_deltas: Dict[str, Dict[str, float]] = field(default_factory=dict)
    faction_deltas: Dict[str, Dict[str, float]] = field(default_factory=dict)
    institution_patch: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


@dataclass
class RealizedLegacy:
    season: int
    year: int
    node_id: str
    node_title: str
    medium: str
    tone: str
    regions: List[str]
    factions: List[str]
    magnitude: float


@dataclass
class ResolutionWorldState:
    base_world: Any
    protagonist: ProtagonistProfile
    resolution_history: List[HistoricalResolution] = field(default_factory=list)
    archived_nodes: Dict[str, Any] = field(default_factory=dict)
    realized_legacies: List[RealizedLegacy] = field(default_factory=list)


ARCHETYPE_LIBRARY: Dict[str, Dict[str, Any]] = {
    "balanced": {
        "label_ja": "均衡者",
        "skills": {"combat": 60, "diplomacy": 62, "ritual": 58, "stewardship": 60, "stealth": 54, "authority": 59},
        "tendencies": {"mercy": 60, "zeal": 48, "ambition": 56, "prudence": 58},
    },
    "marshal": {
        "label_ja": "鎮圧者",
        "skills": {"combat": 76, "diplomacy": 44, "ritual": 40, "stewardship": 54, "stealth": 48, "authority": 69},
        "tendencies": {"mercy": 36, "zeal": 45, "ambition": 67, "prudence": 51},
    },
    "mediator": {
        "label_ja": "仲裁者",
        "skills": {"combat": 48, "diplomacy": 78, "ritual": 58, "stewardship": 66, "stealth": 52, "authority": 63},
        "tendencies": {"mercy": 75, "zeal": 42, "ambition": 48, "prudence": 70},
    },
    "hierophant": {
        "label_ja": "神託司",
        "skills": {"combat": 46, "diplomacy": 56, "ritual": 82, "stewardship": 52, "stealth": 42, "authority": 66},
        "tendencies": {"mercy": 49, "zeal": 77, "ambition": 46, "prudence": 57},
    },
    "chancellor": {
        "label_ja": "再編卿",
        "skills": {"combat": 44, "diplomacy": 67, "ritual": 50, "stewardship": 80, "stealth": 43, "authority": 71},
        "tendencies": {"mercy": 55, "zeal": 44, "ambition": 63, "prudence": 76},
    },
}

APPROACH_SKILLS: Dict[str, Dict[str, float]] = {
    "suppress": {"combat": 0.50, "authority": 0.25, "stewardship": 0.15, "diplomacy": 0.10},
    "reconcile": {"diplomacy": 0.45, "authority": 0.20, "stewardship": 0.20, "ritual": 0.15},
    "divine_judgement": {"ritual": 0.45, "authority": 0.20, "combat": 0.15, "diplomacy": 0.10, "stewardship": 0.10},
    "restructure": {"stewardship": 0.35, "authority": 0.20, "diplomacy": 0.25, "ritual": 0.10, "combat": 0.10},
}

FAMILY_APPROACH_AFFINITY: Dict[str, Dict[str, float]] = {
    "food_crisis": {"restructure": 1.00, "reconcile": 0.85, "suppress": 0.35, "divine_judgement": 0.45},
    "pilgrimage_conflict": {"reconcile": 1.00, "divine_judgement": 0.82, "restructure": 0.45, "suppress": 0.40},
    "mining_conflict": {"restructure": 0.88, "suppress": 0.74, "reconcile": 0.60, "divine_judgement": 0.20},
    "deep_delving_conflict": {"restructure": 0.76, "suppress": 0.74, "divine_judgement": 0.58, "reconcile": 0.40},
    "succession_conflict": {"restructure": 1.00, "reconcile": 0.84, "divine_judgement": 0.60, "suppress": 0.46},
    "frontier_militarization": {"suppress": 1.00, "reconcile": 0.62, "restructure": 0.48, "divine_judgement": 0.36},
    "religious_schism": {"reconcile": 0.92, "divine_judgement": 0.92, "restructure": 0.50, "suppress": 0.28},
    "tributary_revolt": {"suppress": 0.80, "reconcile": 0.74, "restructure": 0.62, "divine_judgement": 0.28},
    "hostage_breakdown": {"reconcile": 0.96, "restructure": 0.56, "suppress": 0.48, "divine_judgement": 0.22},
    "relic_dispute": {"divine_judgement": 0.92, "reconcile": 0.70, "suppress": 0.50, "restructure": 0.40},
    "institutional_breakdown": {"restructure": 1.00, "reconcile": 0.70, "divine_judgement": 0.52, "suppress": 0.42},
}

FAMILY_POSITIVE_REGION_DELTAS: Dict[str, Dict[str, float]] = {
    "food_crisis": {"food": 10, "trade_routes": 4, "law_order": 3, "racial_tension": -3},
    "pilgrimage_conflict": {"law_order": 5, "faith_density": 3, "trade_routes": 2, "racial_tension": -4},
    "mining_conflict": {"trade_routes": 4, "housing": 4, "law_order": 2, "food": 1},
    "deep_delving_conflict": {"miasma_level": -7, "law_order": 3, "trade_routes": 2, "housing": 2},
    "succession_conflict": {"legitimacy": 7, "succession_stability": 10, "law_order": 3},
    "frontier_militarization": {"law_order": 6, "racial_tension": -7, "housing": 1},
    "religious_schism": {"faith_density": 2, "legitimacy": 5, "law_order": 4, "miasma_level": -2, "racial_tension": -5},
    "tributary_revolt": {"legitimacy": 4, "law_order": 4, "food": 2, "racial_tension": -3},
    "hostage_breakdown": {"legitimacy": 5, "law_order": 3, "trade_routes": 1},
    "relic_dispute": {"faith_density": 4, "legitimacy": 3, "miasma_level": -3},
    "institutional_breakdown": {"legitimacy": 7, "law_order": 6, "trade_routes": 3, "succession_stability": 2},
}

FAMILY_NEGATIVE_REGION_DELTAS: Dict[str, Dict[str, float]] = {
    "food_crisis": {"food": -7, "law_order": -5, "trade_routes": -4, "racial_tension": 5, "legitimacy": -3},
    "pilgrimage_conflict": {"law_order": -5, "faith_density": 2, "racial_tension": 4, "legitimacy": -3},
    "mining_conflict": {"housing": -4, "law_order": -4, "miasma_level": 3, "trade_routes": -3},
    "deep_delving_conflict": {"miasma_level": 8, "law_order": -4, "housing": -3, "trade_routes": -2},
    "succession_conflict": {"legitimacy": -7, "succession_stability": -9, "law_order": -3, "racial_tension": 4},
    "frontier_militarization": {"law_order": -6, "racial_tension": 7, "housing": -3, "food": -2},
    "religious_schism": {"legitimacy": -5, "law_order": -4, "racial_tension": 6, "miasma_level": 2},
    "tributary_revolt": {"legitimacy": -6, "law_order": -5, "trade_routes": -2, "racial_tension": 5},
    "hostage_breakdown": {"legitimacy": -5, "law_order": -4, "racial_tension": 5},
    "relic_dispute": {"law_order": -3, "faith_density": 5, "miasma_level": 4, "racial_tension": 3},
    "institutional_breakdown": {"legitimacy": -6, "law_order": -6, "trade_routes": -4, "succession_stability": -3},
}

FAMILY_REFORM_CLAUSE: Dict[str, str] = {
    "food_crisis": "grain_quota",
    "pilgrimage_conflict": "pilgrimage_route_protection",
    "mining_conflict": "joint_mining_rights",
    "deep_delving_conflict": "joint_delving_recovery",
    "succession_conflict": "dynastic_marriage",
    "frontier_militarization": "demilitarized_border",
    "religious_schism": "joint_sealing_duty",
    "tributary_revolt": "tribute_delivery",
    "hostage_breakdown": "hostage_exchange",
    "relic_dispute": "sacred_relic_custody",
    "institutional_breakdown": "refugee_corridor",
}


def deterministic_noise(seed: int, *parts: object, span: float = 6.0) -> float:
    return v7.deterministic_noise(seed, *parts, span=span)


def build_protagonist(seed: int = 1729, archetype: str = "balanced", race: str = "human") -> ProtagonistProfile:
    ar = ARCHETYPE_LIBRARY[archetype]
    skills = {k: clamp(v + deterministic_noise(seed, archetype, "skill", k, span=5.5)) for k, v in ar["skills"].items()}
    tendencies = {k: clamp(v + deterministic_noise(seed, archetype, "tendency", k, span=5.0)) for k, v in ar["tendencies"].items()}
    p = ProtagonistProfile(
        protagonist_id="protagonist_001",
        label_ja=f"{ar['label_ja']}の旅人",
        race=race,
        archetype=archetype,
        skills=skills,
        tendencies=tendencies,
    )
    p.refresh_title()
    return p


def build_resolution_world(seed: int = 1729, archetype: str = "balanced") -> ResolutionWorldState:
    world = v7.build_sample_world(seed)
    protagonist = build_protagonist(seed=seed, archetype=archetype)
    return ResolutionWorldState(base_world=world, protagonist=protagonist)


def world_response_capacity(world: Any, node: Any) -> float:
    region_scores = []
    for rid in node.regions:
        if rid in world.regions:
            r = world.regions[rid]
            region_scores.append(mean([r.values["law_order"], r.values["legitimacy"], 100 - r.values["miasma_level"]]))
    inst_support = 50.0
    if node.source_institution_id and node.source_institution_id in world.institutions:
        inst = world.institutions[node.source_institution_id]
        inst_support = mean([inst.support, 100 - inst.breach_risk])
    faction_leg = []
    for fid in node.factions:
        if fid in world.factions:
            faction_leg.append(world.factions[fid].legitimacy)
    return mean(region_scores + [inst_support] + faction_leg)


def recommended_vector_weights(node: Any) -> Dict[str, float]:
    if node.quest_offers:
        vectors = node.quest_offers[0].recommended_vectors
    else:
        vectors = ["combat", "diplomacy", "ritual"]
    weights: Dict[str, float] = {}
    if not vectors:
        return {"combat": 0.2, "diplomacy": 0.2, "ritual": 0.2, "stewardship": 0.2, "stealth": 0.1, "authority": 0.1}
    primary = 0.46
    secondary = 0.31
    tertiary = 0.23
    parts = [primary, secondary, tertiary]
    for vec, w in zip(vectors[:3], parts):
        weights[vec] = w
    # normalize in case fewer than 3
    s = sum(weights.values()) or 1.0
    return {k: v / s for k, v in weights.items()}


def protagonist_skill_score(protagonist: ProtagonistProfile, weights: Dict[str, float]) -> float:
    return sum(protagonist.skills.get(k, 50.0) * w for k, w in weights.items())


def race_affinity_bonus(world: Any, protagonist: ProtagonistProfile, node: Any) -> float:
    bonus = 0.0
    for rid in node.regions:
        if rid in world.regions and world.regions[rid].dominant_race == protagonist.race:
            bonus += 2.0
    for fid in node.factions:
        if fid in world.factions and world.factions[fid].dominant_race == protagonist.race:
            bonus += 1.5
    return min(7.0, bonus)


def approach_fit_score(world: Any, protagonist: ProtagonistProfile, node: Any, approach: str) -> float:
    skill_mix = APPROACH_SKILLS[approach]
    weights = recommended_vector_weights(node)
    vector_alignment = 0.0
    for vec, w in weights.items():
        vector_alignment += skill_mix.get(vec, 0.0) * w
    family_aff = FAMILY_APPROACH_AFFINITY.get(node.event_family, {}).get(approach, 0.5)
    skill_score = sum(protagonist.skills.get(k, 50.0) * w for k, w in skill_mix.items())
    tendency_bonus = 0.0
    if approach == "suppress":
        tendency_bonus += protagonist.tendencies["ambition"] * 0.06
        tendency_bonus -= protagonist.tendencies["mercy"] * 0.03
    elif approach == "reconcile":
        tendency_bonus += protagonist.tendencies["mercy"] * 0.07
        tendency_bonus += protagonist.tendencies["prudence"] * 0.04
    elif approach == "divine_judgement":
        tendency_bonus += protagonist.tendencies["zeal"] * 0.08
    elif approach == "restructure":
        tendency_bonus += protagonist.tendencies["prudence"] * 0.08
        tendency_bonus += protagonist.tendencies["ambition"] * 0.03
    return skill_score * 0.58 + vector_alignment * 18 + family_aff * 14 + tendency_bonus


def choose_approach(world: Any, protagonist: ProtagonistProfile, node: Any) -> str:
    candidates = {a: approach_fit_score(world, protagonist, node, a) for a in APPROACH_SKILLS}
    return max(candidates.items(), key=lambda x: x[1])[0]


def target_capacity(protagonist: ProtagonistProfile) -> int:
    if protagonist.vessel_points >= 800:
        return 4
    if protagonist.vessel_points >= 320:
        return 3
    return 2


def node_priority(world: Any, protagonist: ProtagonistProfile, node: Any) -> float:
    approach = choose_approach(world, protagonist, node)
    fit = approach_fit_score(world, protagonist, node, approach)
    capacity = world_response_capacity(world, node)
    family_pressure = sum(node.era_impetus.values()) * 0.12
    return node.severity * 0.48 + node.urgency * 0.34 + fit * 0.18 - capacity * 0.12 + family_pressure


def select_targets(rw: ResolutionWorldState) -> List[str]:
    world = rw.base_world
    active = [n for n in world.active_nodes.values() if n.status == "active"]
    ranked = sorted(active, key=lambda n: (-node_priority(world, rw.protagonist, n), n.node_id))
    return [n.node_id for n in ranked[: target_capacity(rw.protagonist)]]


def difficulty_score(world: Any, node: Any) -> float:
    inst_penalty = 0.0
    if node.source_institution_id and node.source_institution_id in world.institutions:
        inst = world.institutions[node.source_institution_id]
        inst_penalty += inst.breach_risk * 0.05
        if inst.status == "broken":
            inst_penalty += 4.0
    chain_penalty = 0.0
    if node.chain_id and node.chain_id in world.chains:
        chain_penalty += world.chains[node.chain_id].stage * 1.8
    return 16.0 + node.severity * 0.26 + node.urgency * 0.12 + node.stage * 2.8 + inst_penalty + chain_penalty


def capability_score(world: Any, protagonist: ProtagonistProfile, node: Any, approach: str) -> float:
    weights = recommended_vector_weights(node)
    base = protagonist_skill_score(protagonist, weights)
    approach_gain = approach_fit_score(world, protagonist, node, approach) * 0.46
    race_bonus = race_affinity_bonus(world, protagonist, node)
    era_bonus = 0.0
    if world.current_world_era in ["瘴潮期", "聖罰期"] and approach in ["divine_judgement", "restructure"]:
        era_bonus += 3.5
    return base * 0.72 + approach_gain + race_bonus + era_bonus


def outcome_from_delta(delta: float) -> str:
    if delta >= 22:
        return "great_success"
    if delta >= 6:
        return "success"
    if delta >= -10:
        return "partial_success"
    if delta >= -26:
        return "failure"
    return "catastrophe"


def scale_for_outcome(outcome: str) -> float:
    return {
        "great_success": 1.20,
        "success": 1.00,
        "partial_success": 0.55,
        "failure": -0.75,
        "catastrophe": -1.18,
    }[outcome]


def add_or_update(region_delta_map: Dict[str, Dict[str, float]], region_ids: List[str], deltas: Dict[str, float], scale: float) -> None:
    for rid in region_ids:
        bucket = region_delta_map.setdefault(rid, {})
        for k, v in deltas.items():
            bucket[k] = bucket.get(k, 0.0) + v * scale


def add_or_update_faction(faction_delta_map: Dict[str, Dict[str, float]], faction_ids: List[str], deltas: Dict[str, float]) -> None:
    for fid in faction_ids:
        bucket = faction_delta_map.setdefault(fid, {})
        for k, v in deltas.items():
            bucket[k] = bucket.get(k, 0.0) + v


def patch_source_institution(world: Any, node: Any, approach: str, outcome: str) -> Dict[str, float]:
    if not node.source_institution_id or node.source_institution_id not in world.institutions:
        return {}
    inst = world.institutions[node.source_institution_id]
    clause = None
    if node.source_clause_id:
        for c in inst.clauses:
            if c.clause_id == node.source_clause_id:
                clause = c
                break

    patch: Dict[str, float] = {}
    if outcome in ["great_success", "success"]:
        inst.breach_risk = clamp(inst.breach_risk - (20 if outcome == "great_success" else 13))
        inst.support = clamp(inst.support + (15 if outcome == "great_success" else 8))
        patch["institution_breach_risk"] = round(inst.breach_risk, 1)
        patch["institution_support"] = round(inst.support, 1)
        if clause:
            clause.support = clamp(clause.support + (25 if outcome == "great_success" else 16))
            clause.strain = clamp(clause.strain - (24 if outcome == "great_success" else 16))
            clause.last_tension = clamp(clause.last_tension - (22 if outcome == "great_success" else 14))
            clause.status = "active" if clause.last_tension < 45 else "strained"
            patch["clause_support"] = round(clause.support, 1)
            patch["clause_strain"] = round(clause.strain, 1)

        if approach == "restructure":
            reform_kind = FAMILY_REFORM_CLAUSE.get(node.event_family)
            if reform_kind and all(c.clause_kind != reform_kind for c in inst.clauses):
                new_clause = v7.TreatyClause(
                    clause_id=f"cl_reform_{reform_kind}_{world.season_index:03d}",
                    clause_kind=reform_kind,
                    label_ja=v7.CLAUSE_LABELS.get(reform_kind, reform_kind),
                    support=58.0,
                    strain=4.0,
                    intensity=62.0,
                    status="active",
                    last_tension=24.0,
                    notes=["介入後の再編条項として追加"]
                )
                inst.clauses.append(new_clause)
                patch["reform_clause_added"] = 1.0

        inst.status = "active" if inst.breach_risk < 40 else "strained"
    elif outcome == "partial_success":
        inst.breach_risk = clamp(inst.breach_risk - 7)
        inst.support = clamp(inst.support + 4)
        patch["institution_breach_risk"] = round(inst.breach_risk, 1)
        if clause:
            clause.support = clamp(clause.support + 7)
            clause.strain = clamp(clause.strain - 5)
            clause.last_tension = clamp(clause.last_tension - 7)
            clause.status = "strained" if clause.last_tension >= 45 else "active"
        if inst.breach_risk < 50:
            inst.status = "strained"
    else:
        inst.breach_risk = clamp(inst.breach_risk + (10 if outcome == "failure" else 18))
        inst.support = clamp(inst.support - (5 if outcome == "failure" else 12))
        patch["institution_breach_risk"] = round(inst.breach_risk, 1)
        if clause:
            clause.support = clamp(clause.support - (8 if outcome == "failure" else 14))
            clause.strain = clamp(clause.strain + (10 if outcome == "failure" else 18))
            clause.last_tension = clamp(clause.last_tension + (8 if outcome == "failure" else 15))
            clause.status = "violated"
        inst.status = "broken" if inst.breach_risk >= 68 else "strained"
    return patch


def approach_region_and_faction_modifiers(node: Any, approach: str, outcome: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    pos = FAMILY_POSITIVE_REGION_DELTAS.get(node.event_family, {"law_order": 4, "legitimacy": 4})
    neg = FAMILY_NEGATIVE_REGION_DELTAS.get(node.event_family, {"law_order": -4, "legitimacy": -4})
    scale = scale_for_outcome(outcome)
    if scale >= 0:
        region = dict(pos)
        faction = {"legitimacy": 3.0 if outcome == "success" else 5.0, "treasury": 1.5}
    else:
        region = dict(neg)
        faction = {"legitimacy": -3.0 if outcome == "failure" else -6.0, "treasury": -1.5}

    if approach == "suppress":
        region["law_order"] = region.get("law_order", 0.0) + (3 if scale >= 0 else -2)
        region["racial_tension"] = region.get("racial_tension", 0.0) + (1 if scale >= 0 else 2)
        faction["militarization"] = faction.get("militarization", 0.0) + (4.0 if scale >= 0 else 2.0)
    elif approach == "reconcile":
        region["racial_tension"] = region.get("racial_tension", 0.0) + (-3 if scale >= 0 else 1)
        region["legitimacy"] = region.get("legitimacy", 0.0) + (2 if scale >= 0 else -1)
        faction["legitimacy"] = faction.get("legitimacy", 0.0) + (2.0 if scale >= 0 else -1.0)
    elif approach == "divine_judgement":
        region["faith_density"] = region.get("faith_density", 0.0) + (4 if scale >= 0 else 2)
        region["miasma_level"] = region.get("miasma_level", 0.0) + (-4 if scale >= 0 else 2)
        faction["zeal"] = faction.get("zeal", 0.0) + (4.0 if scale >= 0 else 3.0)
    elif approach == "restructure":
        region["trade_routes"] = region.get("trade_routes", 0.0) + (4 if scale >= 0 else -2)
        region["food"] = region.get("food", 0.0) + (3 if scale >= 0 else -1)
        region["housing"] = region.get("housing", 0.0) + (2 if scale >= 0 else -1)
        faction["treasury"] = faction.get("treasury", 0.0) + (3.5 if scale >= 0 else -1.5)

    return region, faction


def apply_region_deltas(world: Any, region_deltas: Dict[str, Dict[str, float]]) -> None:
    for rid, delta_map in region_deltas.items():
        if rid not in world.regions:
            continue
        region = world.regions[rid]
        for key, delta in delta_map.items():
            if key in region.values:
                region.values[key] = clamp(region.values[key] + delta)


def apply_faction_deltas(world: Any, faction_deltas: Dict[str, Dict[str, float]]) -> None:
    for fid, delta_map in faction_deltas.items():
        if fid not in world.factions:
            continue
        faction = world.factions[fid]
        for key, delta in delta_map.items():
            if hasattr(faction, key):
                setattr(faction, key, clamp(getattr(faction, key) + delta))


def mark_node_archived(rw: ResolutionWorldState, node: Any) -> None:
    if node.node_id in rw.base_world.active_nodes:
        rw.archived_nodes[node.node_id] = rw.base_world.active_nodes.pop(node.node_id)


def update_chain_after_resolution(world: Any, node: Any, outcome: str) -> None:
    if not node.chain_id or node.chain_id not in world.chains:
        return
    chain = world.chains[node.chain_id]
    if node.node_id in chain.active_nodes and outcome in ["great_success", "success"]:
        chain.active_nodes.remove(node.node_id)
        chain.cumulative_severity = max(0.0, chain.cumulative_severity - node.severity * 0.65)
    elif outcome == "partial_success":
        chain.cumulative_severity = max(0.0, chain.cumulative_severity - node.severity * 0.25)
    else:
        chain.cumulative_severity += node.severity * (0.18 if outcome == "failure" else 0.32)

    chain.stage = max(1, 1 + len(chain.active_nodes) // 2)
    chain.history.append(f"{world.calendar_year}年:{node.title}:{outcome}")


def vessel_gain_for_resolution(node: Any, outcome: str, realized_media: List[str]) -> float:
    outcome_factor = {
        "great_success": 1.05,
        "success": 0.82,
        "partial_success": 0.40,
        "failure": 0.08,
        "catastrophe": 0.00,
    }[outcome]
    media_bonus = len(realized_media) * 7.0
    base = node.severity * 0.38 + node.urgency * 0.20 + node.stage * 11.0 + media_bonus
    return round(base * outcome_factor, 1)


def realize_legacies(rw: ResolutionWorldState, node: Any, outcome: str, approach: str) -> List[str]:
    if outcome == "catastrophe":
        media = node.projected_legacies[:2] + ["伝承"]
        tone = "破局"
    elif outcome == "failure":
        media = node.projected_legacies[:1] + ["伝承"]
        tone = "失敗"
    elif outcome == "partial_success":
        media = node.projected_legacies[:2]
        tone = "暫定"
    elif outcome == "great_success":
        media = node.projected_legacies[:]
        tone = {"suppress": "鎮圧", "reconcile": "和解", "divine_judgement": "神罰", "restructure": "再編"}[approach]
    else:
        media = node.projected_legacies[:2]
        tone = {"suppress": "鎮圧", "reconcile": "和解", "divine_judgement": "神罰", "restructure": "再編"}[approach]

    magnitude = max(12.0, node.severity * (0.55 if outcome in ["great_success", "success"] else 0.28))
    for medium in media:
        rw.realized_legacies.append(
            RealizedLegacy(
                season=rw.base_world.season_index,
                year=rw.base_world.calendar_year,
                node_id=node.node_id,
                node_title=node.title,
                medium=medium,
                tone=tone,
                regions=node.regions[:],
                factions=node.factions[:],
                magnitude=round(magnitude, 1),
            )
        )
    return media


def passive_world_response(rw: ResolutionWorldState, untreated_ids: List[str]) -> None:
    world = rw.base_world
    for node_id in untreated_ids:
        if node_id not in world.active_nodes:
            continue
        node = world.active_nodes[node_id]
        if node.status != "active":
            continue
        capacity = world_response_capacity(world, node)
        drift = capacity - (node.severity * 0.45 + node.urgency * 0.22) + deterministic_noise(world.seed, world.calendar_year, node_id, "passive", span=6.0)
        if drift >= 18:
            node.status = "cooling"
            node.severity = clamp(node.severity - 10)
            node.urgency = clamp(node.urgency - 8)
            if node.source_institution_id and node.source_institution_id in world.institutions:
                inst = world.institutions[node.source_institution_id]
                inst.breach_risk = clamp(inst.breach_risk - 4)
        elif drift <= -18:
            node.severity = clamp(node.severity + 7)
            node.urgency = clamp(node.urgency + 6)
            node.stage += 1
            if node.source_institution_id and node.source_institution_id in world.institutions:
                inst = world.institutions[node.source_institution_id]
                inst.breach_risk = clamp(inst.breach_risk + 5)
                inst.status = "broken" if inst.breach_risk >= 68 else "strained"
            if node.chain_id and node.chain_id in world.chains:
                world.chains[node.chain_id].cumulative_severity += 8.0
                world.chains[node.chain_id].stage = max(world.chains[node.chain_id].stage, node.stage)
        world.history_log.append({
            "season": world.season_index,
            "year": world.calendar_year,
            "entry": f"passive node response: {node.title}",
            "node_id": node.node_id,
            "status": node.status,
        })


def resolve_node(rw: ResolutionWorldState, node_id: str) -> HistoricalResolution:
    world = rw.base_world
    protagonist = rw.protagonist
    node = world.active_nodes[node_id]

    approach = choose_approach(world, protagonist, node)
    capability = capability_score(world, protagonist, node, approach)
    difficulty = difficulty_score(world, node)
    delta = capability - difficulty + deterministic_noise(world.seed, world.calendar_year, node_id, protagonist.archetype, "resolve", span=10.0)
    outcome = outcome_from_delta(delta)

    region_mods, faction_mods = approach_region_and_faction_modifiers(node, approach, outcome)
    region_deltas: Dict[str, Dict[str, float]] = {}
    faction_deltas: Dict[str, Dict[str, float]] = {}
    scale = abs(scale_for_outcome(outcome))
    add_or_update(region_deltas, node.regions, region_mods, scale)
    add_or_update_faction(faction_deltas, node.factions, {k: v * scale for k, v in faction_mods.items()})

    # divine_judgement は demon_domain に非対称
    if approach == "divine_judgement" and any(fid in world.factions and world.factions[fid].faction_type == "demon_domain" for fid in node.factions):
        for fid in node.factions:
            if fid in world.factions and world.factions[fid].faction_type == "demon_domain":
                faction_deltas.setdefault(fid, {})
                faction_deltas[fid]["legitimacy"] = faction_deltas[fid].get("legitimacy", 0.0) - (5.0 if outcome in ["great_success", "success"] else 0.0)

    if outcome in ["great_success", "success"]:
        node.status = "resolved"
        node.severity = clamp(node.severity - (35 if outcome == "great_success" else 26))
        node.urgency = clamp(node.urgency - (32 if outcome == "great_success" else 24))
    elif outcome == "partial_success":
        node.status = "cooling"
        node.severity = clamp(node.severity - 14)
        node.urgency = clamp(node.urgency - 12)
    elif outcome == "failure":
        node.status = "active"
        node.severity = clamp(node.severity + 6)
        node.urgency = clamp(node.urgency + 5)
        node.stage += 1
    else:
        node.status = "active"
        node.severity = clamp(node.severity + 12)
        node.urgency = clamp(node.urgency + 9)
        node.stage += 1

    patch = patch_source_institution(world, node, approach, outcome)
    apply_region_deltas(world, region_deltas)
    apply_faction_deltas(world, faction_deltas)
    update_chain_after_resolution(world, node, outcome)
    media = realize_legacies(rw, node, outcome, approach)
    vessel_gain = vessel_gain_for_resolution(node, outcome, media)
    protagonist.vessel_points = round(protagonist.vessel_points + vessel_gain, 1)
    protagonist.refresh_title()

    notes: List[str] = []
    if approach == "restructure" and patch.get("reform_clause_added"):
        notes.append("再編条項を追加")
    if outcome == "catastrophe":
        notes.append("事件は再燃し、制度破綻をさらに悪化させた")
    elif outcome == "partial_success":
        notes.append("一時鎮静化したが、火種は残っている")
    elif outcome in ["great_success", "success"]:
        notes.append("事件は決着し、残滓として固定化された")

    resolution = HistoricalResolution(
        season=world.season_index,
        year=world.calendar_year,
        node_id=node.node_id,
        node_title=node.title,
        event_family=node.event_family,
        approach=approach,
        outcome=outcome,
        intervention=True,
        capability=round(capability, 1),
        difficulty=round(difficulty, 1),
        delta=round(delta, 1),
        resulting_status=node.status,
        vessel_gain=vessel_gain,
        realized_media=media,
        region_deltas={rid: {k: round(v, 1) for k, v in d.items()} for rid, d in region_deltas.items()},
        faction_deltas={fid: {k: round(v, 1) for k, v in d.items()} for fid, d in faction_deltas.items()},
        institution_patch=patch,
        notes=notes,
    )
    rw.resolution_history.append(resolution)

    world.history_log.append({
        "season": world.season_index,
        "year": world.calendar_year,
        "entry": f"historical node resolved: {node.title}",
        "node_id": node.node_id,
        "approach": approach,
        "outcome": outcome,
    })

    if node.status == "resolved":
        mark_node_archived(rw, node)
    return resolution


def recompute_world_era(world: Any) -> None:
    impetus_totals: Dict[str, float] = {}
    for node in world.active_nodes.values():
        if node.status not in ["active", "cooling"]:
            continue
        for k, v in node.era_impetus.items():
            impetus_totals[k] = impetus_totals.get(k, 0.0) + v * (1.0 if node.status == "active" else 0.55)

    # regional base pressure
    food = mean([100 - r.values["food"] for r in world.regions.values()])
    miasma = mean([r.values["miasma_level"] for r in world.regions.values()])
    faith = mean([r.values["faith_density"] for r in world.regions.values()])
    law = mean([100 - r.values["law_order"] for r in world.regions.values()])
    succession = mean([100 - r.values["succession_stability"] for r in world.regions.values()])
    racial = mean([r.values["racial_tension"] for r in world.regions.values()])
    trade = mean([100 - r.values["trade_routes"] for r in world.regions.values()])

    era_scores = {
        "瘴潮期": impetus_totals.get("miasma_growth", 0.0) + impetus_totals.get("dungeon_activation", 0.0) + miasma * 0.9,
        "囲麦期": impetus_totals.get("food_shortage", 0.0) + impetus_totals.get("migration", 0.0) + food * 0.9 + trade * 0.25,
        "聖罰期": impetus_totals.get("faith_schism", 0.0) + impetus_totals.get("holy_war", 0.0) + impetus_totals.get("divine_interference", 0.0) + faith * 0.55,
        "境火期": impetus_totals.get("border_war", 0.0) + impetus_totals.get("racial_tension", 0.0) + racial * 0.75,
        "断契期": impetus_totals.get("diplomatic_rupture", 0.0) + impetus_totals.get("institutional_breakdown", 0.0) + impetus_totals.get("state_collapse", 0.0) + law * 0.55 + trade * 0.45,
        "裂冠期": impetus_totals.get("succession_crisis", 0.0) + impetus_totals.get("legitimacy", 0.0) + succession * 0.65,
        "鉱争期": impetus_totals.get("resource_war", 0.0) + impetus_totals.get("guild_friction", 0.0) + trade * 0.28 + miasma * 0.18,
    }
    world.current_world_era = max(era_scores.items(), key=lambda x: x[1])[0]


def advance_resolution_world_one_season(rw: ResolutionWorldState) -> Dict[str, Any]:
    season_report = v7.one_season(rw.base_world)

    targets = select_targets(rw)
    target_set = set(targets)
    outcomes = [resolve_node(rw, node_id) for node_id in targets if node_id in rw.base_world.active_nodes]

    untreated = [nid for nid, node in rw.base_world.active_nodes.items() if node.status == "active" and nid not in target_set]
    passive_world_response(rw, untreated)
    recompute_world_era(rw.base_world)

    return {
        "season": rw.base_world.season_index,
        "year": rw.base_world.calendar_year,
        "generated": season_report,
        "intervened_nodes": targets,
        "outcomes": [asdict(o) for o in outcomes],
        "current_era": rw.base_world.current_world_era,
        "vessel_points": rw.protagonist.vessel_points,
        "existence_title": rw.protagonist.existence_title,
    }


def simulate(seed: int = 1729, seasons: int = 6, archetype: str = "balanced") -> ResolutionWorldState:
    rw = build_resolution_world(seed=seed, archetype=archetype)
    for _ in range(seasons):
        advance_resolution_world_one_season(rw)
    return rw


def export_world(rw: ResolutionWorldState) -> Dict[str, Any]:
    data = v7.export_world(rw.base_world)
    data["protagonist"] = {
        "label_ja": rw.protagonist.label_ja,
        "race": rw.protagonist.race,
        "archetype": rw.protagonist.archetype,
        "skills": {k: round(v, 1) for k, v in rw.protagonist.skills.items()},
        "tendencies": {k: round(v, 1) for k, v in rw.protagonist.tendencies.items()},
        "vessel_points": round(rw.protagonist.vessel_points, 1),
        "existence_title": rw.protagonist.existence_title,
    }
    data["resolution_history"] = [asdict(r) for r in rw.resolution_history]
    data["archived_nodes"] = {
        nid: {
            "title": node.title,
            "event_family": node.event_family,
            "status": node.status,
            "stage": node.stage,
            "chain_id": node.chain_id,
        }
        for nid, node in rw.archived_nodes.items()
    }
    data["realized_legacies"] = [asdict(x) for x in rw.realized_legacies]
    return data


def summary_markdown(rw: ResolutionWorldState) -> str:
    world = rw.base_world
    p = rw.protagonist
    lines: List[str] = []
    lines.append(f"# {world.world_name} 世界史事件解決層要約")
    lines.append("")
    lines.append(f"- seed: **{world.seed}**")
    lines.append(f"- 暦: **{world.calendar_name} {world.calendar_year}年**")
    lines.append(f"- 現在Era: **{world.current_world_era}**")
    lines.append(f"- 主神: **{world.main_god_name}**")
    lines.append(f"- 主人公: **{p.label_ja}** / archetype={p.archetype} / race={p.race}")
    lines.append(f"- 存在級位: **{p.existence_title}**")
    lines.append(f"- vessel points: **{p.vessel_points:.1f}**")
    lines.append(f"- 残存active nodes: **{len([n for n in world.active_nodes.values() if n.status == 'active'])}**")
    lines.append(f"- resolved nodes: **{len(rw.archived_nodes)}**")
    lines.append("")

    lines.append("## 最近の解決")
    lines.append("")
    for res in sorted(rw.resolution_history[-8:], key=lambda r: (r.year, r.season)):
        lines.append(f"- **{res.node_title}** / {res.outcome} / approach={res.approach} / vessel+{res.vessel_gain:.1f}")
        lines.append(f"  - capability={res.capability:.1f} / difficulty={res.difficulty:.1f} / delta={res.delta:.1f}")
        if res.notes:
            lines.append(f"  - notes: {' / '.join(res.notes)}")
        if res.realized_media:
            lines.append(f"  - media: {', '.join(res.realized_media)}")

    lines.append("")
    lines.append("## まだ危険なactive nodes")
    lines.append("")
    ranked = sorted(
        [n for n in world.active_nodes.values() if n.status == "active"],
        key=lambda n: (-n.severity, -n.urgency, n.title)
    )
    for node in ranked[:10]:
        lines.append(f"- **{node.title}** ({v7.EVENT_FAMILY_LABELS.get(node.event_family, node.event_family)})")
        lines.append(f"  - severity={node.severity:.1f}, urgency={node.urgency:.1f}, stage={node.stage}")
        lines.append(f"  - factions: {', '.join(node.factions)}")
        lines.append(f"  - regions: {', '.join(node.regions)}")
        if node.quest_offers:
            q = node.quest_offers[0]
            lines.append(f"  - vectors: {', '.join(q.recommended_vectors)}")

    lines.append("")
    lines.append("## 壊れかけの制度")
    lines.append("")
    risky = sorted(world.institutions.values(), key=lambda x: (-x.breach_risk, x.institution_id))
    for inst in risky[:8]:
        lines.append(f"- **{inst.label_ja}** / status={inst.status} / breach_risk={inst.breach_risk:.1f} / support={inst.support:.1f}")
        hot = sorted(inst.clauses, key=lambda c: (-c.last_tension, c.clause_kind))[:3]
        for cl in hot:
            lines.append(f"  - {cl.label_ja}: tension={cl.last_tension:.1f}, status={cl.status}, support={cl.support:.1f}, strain={cl.strain:.1f}")

    lines.append("")
    lines.append("## 実現した残滓")
    lines.append("")
    recent_legacies = rw.realized_legacies[-10:]
    for lg in recent_legacies:
        lines.append(f"- **{lg.node_title}** → {lg.medium} / tone={lg.tone} / magnitude={lg.magnitude:.1f}")
        lines.append(f"  - regions: {', '.join(lg.regions)}")

    return "\n".join(lines)


def save_outputs(base_dir: str = "/mnt/data", seed: int = 1729, seasons: int = 6, archetype: str = "balanced") -> Tuple[str, str, str]:
    rw = simulate(seed=seed, seasons=seasons, archetype=archetype)
    data = export_world(rw)
    json_path = f"{base_dir}/pbw_generated_world_seed{seed}_v8_historical_resolution.json"
    md_path = f"{base_dir}/pbw_generated_world_seed{seed}_v8_historical_resolution_summary.md"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(summary_markdown(rw))
    return json_path, md_path, rw.base_world.world_name


README = """# PBW World Historical Resolution v8

この層は v7 の **HistoricalEventNode** を、実際に

- 鎮圧 (`suppress`)
- 和解 (`reconcile`)
- 神罰化 (`divine_judgement`)
- 再編 (`restructure`)

で処理し、その結果を

- 地域値
- 勢力値
- 条項 / 制度
- 事件連鎖
- Era
- 残滓媒体
- 主人公の存在級位

へ返す層です。

## 何が増えたか

- 主人公介入の選定
- 事件ごとの介入方針選択
- 成否判定
- untreated node の受動的悪化 / 鎮静
- 条項修復
- 制度の breach_risk 更新
- 事件連鎖の縮退 / 再燃
- 実現した残滓媒体
- vessel points / 存在級位上昇
- active node 再集計後の Era 再判定

## ここでの意味

v7 までは「事件ノードが立つ」までだった。
v8 では、その事件が

- 解ける
- 抑え込まれる
- 宗教的裁断を受ける
- 制度再編で縫い直される
- 失敗して連鎖が深くなる

まで世界の中で動く。

つまりここで初めて、  
**条項違反 → 事件化 → 介入 → 歴史媒体化** が閉じる。
"""


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    readme_path = base / "pbw_world_historical_resolution_v8_README.md"
    readme_path.write_text(README, encoding="utf-8")
    json_path, md_path, world_name = save_outputs(base_dir=str(base))
    print(f"generated: {world_name}")
    print(json_path)
    print(md_path)
    print(readme_path)
