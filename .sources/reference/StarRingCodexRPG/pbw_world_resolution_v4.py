"""PBW quest resolution + causal legacy v4

Extends diplomacy + quest generation v3 by adding a resolution layer that:
- selects protagonist interventions from generated quests
- resolves engaged / unattended quests into outcomes
- applies consequences to region state, faction legitimacy/treasury, diplomacy
- writes legacy media back into regions so future seasons are history-sensitive
- converts quest impact into protagonist vessel / existence-grade growth

Design stance:
- do not replace v3 generation; consume its active quests as world-side outputs
- treat quests as seasonal historical knots, not isolated errands
- keep outcomes finite and inspectable rather than narratively handwaved
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_V3_PATH = BASE_DIR / "pbw_world_diplomacy_quests_v3.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v3 = _load_module(DEFAULT_V3_PATH, "pbw_world_diplomacy_quests_v3_ext")
v2 = v3.v2
v1 = v2.v1

QuestOffer = v3.QuestOffer
ExtendedWorldState = v3.ExtendedWorldState
WorldState = v3.WorldState
GeneratedFaction = v3.GeneratedFaction
RegionState = v3.RegionState
DiplomacyRelation = v3.DiplomacyRelation
LegacyMedium = v2.LegacyMedium
clamp = v2.clamp
compute_pressures = v2.compute_pressures
evaluate_protagonist_gain = v1.evaluate_protagonist_gain
ProtagonistImpact = v1.ProtagonistImpact
pair_key = v3.pair_key
region_lookup = v3.region_lookup
faction_lookup = v3.faction_lookup
relation_for_pair = v3.relation_for_pair
export_extended_world_base = v3.export_extended_world
round_obj = v3.round_obj

POSITIVE_OUTCOMES = {"大成", "成功", "自力解決"}
NEGATIVE_OUTCOMES = {"失敗", "放置悪化", "惨敗"}
MIXED_OUTCOMES = {"部分成功", "継続小康", "収奪的成功"}

TIER_ORDER = ["micro", "local", "regional", "macro", "meta", "mythic"]
TIER_BASE_PERSISTENCE = {
    "micro": 0.8,
    "local": 2.0,
    "regional": 6.0,
    "macro": 18.0,
    "meta": 45.0,
    "mythic": 90.0,
}
TIER_IMPACT_WEIGHT = {
    "micro": 0.5,
    "local": 1.0,
    "regional": 1.45,
    "macro": 2.1,
    "meta": 3.0,
    "mythic": 4.4,
}

OUTCOME_SCALES: Dict[str, Dict[str, float]] = {
    "大成": {"success": 1.35, "failure": 0.0, "legacy": 1.20, "gain": 1.25, "diplomacy": 1.20, "legitimacy": 1.15, "population_factor": 1.10},
    "成功": {"success": 1.00, "failure": 0.0, "legacy": 1.00, "gain": 1.00, "diplomacy": 1.00, "legitimacy": 1.00, "population_factor": 1.00},
    "部分成功": {"success": 0.55, "failure": 0.22, "legacy": 0.78, "gain": 0.70, "diplomacy": 0.60, "legitimacy": 0.45, "population_factor": 0.72},
    "失敗": {"success": 0.0, "failure": 1.00, "legacy": 0.88, "gain": 0.22, "diplomacy": -0.90, "legitimacy": -1.00, "population_factor": 0.36},
    "惨敗": {"success": 0.0, "failure": 1.30, "legacy": 1.05, "gain": 0.12, "diplomacy": -1.20, "legitimacy": -1.20, "population_factor": 0.24},
    "自力解決": {"success": 0.62, "failure": 0.0, "legacy": 0.56, "gain": 0.0, "diplomacy": 0.45, "legitimacy": 0.55, "population_factor": 0.70},
    "継続小康": {"success": 0.34, "failure": 0.26, "legacy": 0.45, "gain": 0.0, "diplomacy": 0.05, "legitimacy": 0.08, "population_factor": 0.52},
    "放置悪化": {"success": 0.0, "failure": 0.86, "legacy": 0.72, "gain": 0.0, "diplomacy": -0.55, "legitimacy": -0.55, "population_factor": 0.50},
    "収奪的成功": {"success": 0.78, "failure": 0.28, "legacy": 1.05, "gain": 0.86, "diplomacy": -0.85, "legitimacy": -0.42, "population_factor": 0.84},
}

EXISTENCE_TITLES = [
    (0.0, 0, "人"),
    (250.0, 1, "名を残す者"),
    (900.0, 2, "地方英雄"),
    (2200.0, 3, "国史の楔"),
    (4200.0, 4, "時代攪乱者"),
    (7600.0, 5, "半神の器"),
    (12000.0, 6, "神座の候補"),
    (18000.0, 7, "管理者の端"),
]

RESOLUTION_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "balanced": {
        "aptitudes": {"combat": 0.63, "diplomacy": 0.62, "ritual": 0.60, "stealth": 0.52, "stewardship": 0.66, "authority": 0.58},
        "source_bias": {"action": 0.10, "diplomacy": 0.12, "era": 0.15},
        "tag_bias": {"護衛": 0.06, "仲裁": 0.10, "封印": 0.10, "Era": 0.12, "配給": 0.08, "浄化": 0.08},
        "risk": 0.52,
        "opportunism": 0.22,
        "mercy": 0.72,
    },
    "diplomat": {
        "aptitudes": {"combat": 0.44, "diplomacy": 0.86, "ritual": 0.60, "stealth": 0.56, "stewardship": 0.68, "authority": 0.74},
        "source_bias": {"action": 0.03, "diplomacy": 0.22, "era": 0.10},
        "tag_bias": {"仲裁": 0.16, "停戦交渉": 0.18, "共同事業": 0.14, "契約": 0.12, "信仰裁定": 0.10},
        "risk": 0.42,
        "opportunism": 0.16,
        "mercy": 0.76,
    },
    "delver": {
        "aptitudes": {"combat": 0.72, "diplomacy": 0.42, "ritual": 0.64, "stealth": 0.63, "stewardship": 0.40, "authority": 0.34},
        "source_bias": {"action": 0.18, "diplomacy": -0.04, "era": 0.08},
        "tag_bias": {"探索": 0.18, "深層": 0.16, "封印": 0.14, "裂け目": 0.12, "奪還": 0.10},
        "risk": 0.68,
        "opportunism": 0.34,
        "mercy": 0.48,
    },
    "devout": {
        "aptitudes": {"combat": 0.54, "diplomacy": 0.60, "ritual": 0.88, "stealth": 0.36, "stewardship": 0.56, "authority": 0.66},
        "source_bias": {"action": 0.04, "diplomacy": 0.10, "era": 0.22},
        "tag_bias": {"浄化": 0.15, "巡礼": 0.18, "聖跡": 0.16, "信仰裁定": 0.14, "Era": 0.16},
        "risk": 0.50,
        "opportunism": 0.10,
        "mercy": 0.82,
    },
    "shadow": {
        "aptitudes": {"combat": 0.50, "diplomacy": 0.56, "ritual": 0.48, "stealth": 0.88, "stewardship": 0.42, "authority": 0.34},
        "source_bias": {"action": 0.10, "diplomacy": 0.06, "era": -0.06},
        "tag_bias": {"密輸": 0.18, "真相隠し": 0.16, "偽証暴き": 0.12, "契約": 0.10, "失踪追跡": 0.12},
        "risk": 0.60,
        "opportunism": 0.82,
        "mercy": 0.26,
    },
}

ACTION_SKILL_WEIGHTS: Dict[str, Dict[str, float]] = {
    "grain_distribution": {"stewardship": 0.45, "diplomacy": 0.18, "authority": 0.15, "combat": 0.10, "stealth": 0.04, "ritual": 0.08},
    "rationing": {"stewardship": 0.36, "authority": 0.28, "diplomacy": 0.14, "combat": 0.08, "stealth": 0.06, "ritual": 0.08},
    "migration_convoy": {"stewardship": 0.28, "combat": 0.22, "diplomacy": 0.18, "authority": 0.12, "stealth": 0.10, "ritual": 0.10},
    "fortify_borders": {"combat": 0.30, "authority": 0.20, "stewardship": 0.16, "diplomacy": 0.10, "stealth": 0.08, "ritual": 0.16},
    "inquisition": {"authority": 0.28, "ritual": 0.26, "diplomacy": 0.18, "combat": 0.10, "stealth": 0.10, "stewardship": 0.08},
    "pilgrimage": {"ritual": 0.38, "diplomacy": 0.18, "stewardship": 0.16, "combat": 0.10, "authority": 0.10, "stealth": 0.08},
    "purify_miasma": {"ritual": 0.30, "combat": 0.24, "stewardship": 0.14, "authority": 0.08, "stealth": 0.06, "diplomacy": 0.18},
    "sponsor_delvers": {"combat": 0.28, "stealth": 0.18, "ritual": 0.20, "stewardship": 0.12, "diplomacy": 0.08, "authority": 0.14},
    "seal_rift": {"ritual": 0.40, "combat": 0.18, "authority": 0.12, "diplomacy": 0.10, "stealth": 0.08, "stewardship": 0.12},
    "colonize_frontier": {"combat": 0.20, "diplomacy": 0.18, "authority": 0.22, "stewardship": 0.18, "stealth": 0.08, "ritual": 0.14},
    "raid_caravans": {"combat": 0.34, "stealth": 0.18, "authority": 0.10, "diplomacy": 0.08, "ritual": 0.06, "stewardship": 0.24},
    "enforce_contracts": {"authority": 0.24, "diplomacy": 0.20, "stealth": 0.12, "stewardship": 0.14, "ritual": 0.10, "combat": 0.20},
    "smuggle_relief": {"stealth": 0.26, "stewardship": 0.24, "diplomacy": 0.16, "combat": 0.10, "authority": 0.08, "ritual": 0.16},
    "awaken_hero_cult": {"ritual": 0.30, "authority": 0.18, "diplomacy": 0.20, "combat": 0.08, "stealth": 0.06, "stewardship": 0.18},
    "spread_miasma": {"combat": 0.24, "ritual": 0.24, "stealth": 0.18, "authority": 0.08, "diplomacy": 0.08, "stewardship": 0.18},
}

QUESTTYPE_SKILL_WEIGHTS: Dict[str, Dict[str, float]] = {
    "仲裁": {"diplomacy": 0.45, "authority": 0.20, "stewardship": 0.12, "ritual": 0.10, "combat": 0.08, "stealth": 0.05},
    "停戦交渉": {"diplomacy": 0.42, "authority": 0.22, "combat": 0.12, "stewardship": 0.10, "ritual": 0.09, "stealth": 0.05},
    "共同事業": {"diplomacy": 0.36, "stewardship": 0.22, "authority": 0.16, "ritual": 0.10, "combat": 0.08, "stealth": 0.08},
    "時代介入": {"ritual": 0.28, "authority": 0.18, "stewardship": 0.16, "combat": 0.12, "diplomacy": 0.14, "stealth": 0.12},
    "信仰裁定": {"ritual": 0.28, "diplomacy": 0.22, "authority": 0.18, "stealth": 0.10, "combat": 0.08, "stewardship": 0.14},
    "契約解決": {"diplomacy": 0.24, "authority": 0.20, "stealth": 0.18, "ritual": 0.12, "stewardship": 0.12, "combat": 0.14},
    "偽証暴き": {"stealth": 0.30, "diplomacy": 0.20, "authority": 0.16, "stewardship": 0.12, "combat": 0.12, "ritual": 0.10},
    "失踪追跡": {"stealth": 0.24, "combat": 0.20, "diplomacy": 0.16, "ritual": 0.14, "stewardship": 0.12, "authority": 0.14},
    "奪還": {"combat": 0.34, "stealth": 0.16, "authority": 0.12, "diplomacy": 0.10, "ritual": 0.10, "stewardship": 0.18},
    "資源争奪": {"combat": 0.22, "stewardship": 0.24, "diplomacy": 0.14, "authority": 0.14, "stealth": 0.10, "ritual": 0.16},
    "儀礼支援": {"ritual": 0.36, "stewardship": 0.18, "diplomacy": 0.16, "authority": 0.12, "stealth": 0.06, "combat": 0.12},
}

ERA_DRIVER_SKILL_WEIGHTS: Dict[Tuple[str, str], Dict[str, float]] = {
    ("food", "scarcity"): {"stewardship": 0.38, "authority": 0.20, "diplomacy": 0.16, "ritual": 0.08, "combat": 0.10, "stealth": 0.08},
    ("mana_level", "surplus"): {"ritual": 0.34, "authority": 0.14, "diplomacy": 0.12, "stealth": 0.12, "combat": 0.12, "stewardship": 0.16},
    ("mana_level", "scarcity"): {"ritual": 0.26, "stewardship": 0.20, "authority": 0.18, "diplomacy": 0.14, "combat": 0.10, "stealth": 0.12},
    ("miasma_level", "surplus"): {"ritual": 0.28, "combat": 0.26, "stewardship": 0.12, "diplomacy": 0.08, "authority": 0.10, "stealth": 0.16},
    ("dungeon_density", "fixation"): {"combat": 0.28, "ritual": 0.22, "stealth": 0.18, "authority": 0.10, "diplomacy": 0.08, "stewardship": 0.14},
    ("interworld_intrusion", "runaway"): {"ritual": 0.34, "stealth": 0.14, "combat": 0.16, "diplomacy": 0.12, "authority": 0.10, "stewardship": 0.14},
    ("legitimacy", "collapse"): {"authority": 0.32, "diplomacy": 0.20, "stewardship": 0.16, "combat": 0.14, "ritual": 0.08, "stealth": 0.10},
    ("faith_density", "runaway"): {"ritual": 0.32, "diplomacy": 0.18, "authority": 0.16, "stewardship": 0.12, "stealth": 0.10, "combat": 0.12},
}

OUTCOME_NEGATIVE_MEDIA = {
    "default": {"伝承": 0.18, "魂": 0.08},
    "diplomacy": {"伝承": 0.24, "異端文書": 0.18},
    "era": {"伝承": 0.26, "魂": 0.12, "異端文書": 0.18},
}


@dataclass
class ProtagonistState:
    strategy_id: str
    aptitudes: Dict[str, float]
    vessel_points: float = 0.0
    existence_grade: int = 0
    existence_title: str = "人"
    total_affected_population: int = 0
    total_systems_affected: int = 0
    interventions: int = 0
    media_totals: Dict[str, float] = field(default_factory=dict)
    gain_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class QuestResolution:
    quest_id: str
    season_key: str
    quest_title_ja: str
    quest_type: str
    source_kind: str
    region_id: str
    region_name_ja: str
    outcome: str
    resolution_mode: str
    actor: str
    score: float
    success_scale: float
    failure_scale: float
    applied_effects: Dict[str, float]
    diplomacy_delta: Dict[str, float] = field(default_factory=dict)
    faction_delta: Dict[str, Dict[str, float]] = field(default_factory=dict)
    legacies_created: List[Dict[str, Any]] = field(default_factory=list)
    protagonist_gain: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass
class ResolvedWorldState:
    ext: ExtendedWorldState
    protagonist: ProtagonistState
    last_generated_quests: List[QuestOffer] = field(default_factory=list)
    last_resolutions: List[QuestResolution] = field(default_factory=list)
    resolution_history: List[Dict[str, Any]] = field(default_factory=list)
    season_reports: List[Dict[str, Any]] = field(default_factory=list)


# --------------------------- helpers ---------------------------

def dedupe(seq: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def relation_id_for(a: str, b: str) -> str:
    low, high = pair_key(a, b)
    return f"{low}__{high}"


def initialize_protagonist(strategy_id: str = "balanced") -> ProtagonistState:
    strategy = RESOLUTION_STRATEGIES[strategy_id]
    return ProtagonistState(strategy_id=strategy_id, aptitudes=dict(strategy["aptitudes"]))


def update_existence_title(protagonist: ProtagonistState) -> None:
    title = protagonist.existence_title
    grade = protagonist.existence_grade
    for threshold, g, t in EXISTENCE_TITLES:
        if protagonist.vessel_points >= threshold:
            title = t
            grade = g
    protagonist.existence_title = title
    protagonist.existence_grade = grade


def downgrade_tier(tier: str) -> str:
    idx = max(0, TIER_ORDER.index(tier) - 1) if tier in TIER_ORDER else 1
    return TIER_ORDER[idx]


def upgrade_tier(tier: str) -> str:
    idx = min(len(TIER_ORDER) - 1, TIER_ORDER.index(tier) + 1) if tier in TIER_ORDER else 1
    return TIER_ORDER[idx]


def strategy_profile(state: ResolvedWorldState) -> Dict[str, Any]:
    return RESOLUTION_STRATEGIES[state.protagonist.strategy_id]


def quest_action_id(quest: QuestOffer) -> Optional[str]:
    return quest.provenance.get("action_id") if quest.provenance else None


def tier_of_quest(quest: QuestOffer) -> str:
    return quest.impact_projection.get("impact_tier", "local")


def quest_skill_weights(quest: QuestOffer) -> Dict[str, float]:
    weights = {k: 1.0 / 6.0 for k in ["combat", "diplomacy", "ritual", "stealth", "stewardship", "authority"]}
    if quest.source_kind == "action":
        action_id = quest_action_id(quest)
        if action_id and action_id in ACTION_SKILL_WEIGHTS:
            return dict(ACTION_SKILL_WEIGHTS[action_id])
    if quest.source_kind == "era" and quest.provenance and quest.provenance.get("world_era"):
        driver = tuple(quest.provenance["world_era"].get("driver", (None, None)))
        if driver in ERA_DRIVER_SKILL_WEIGHTS:
            return dict(ERA_DRIVER_SKILL_WEIGHTS[driver])
    return dict(QUESTTYPE_SKILL_WEIGHTS.get(quest.quest_type, weights))


def weighted_skill_match(protagonist: ProtagonistState, weights: Dict[str, float]) -> float:
    total = 0.0
    weight_sum = 0.0
    for skill, weight in weights.items():
        total += protagonist.aptitudes.get(skill, 0.5) * weight
        weight_sum += weight
    return total / weight_sum if weight_sum > 0 else 0.5


def strategy_quest_bias(state: ResolvedWorldState, quest: QuestOffer) -> float:
    prof = strategy_profile(state)
    bias = prof["source_bias"].get(quest.source_kind, 0.0)
    for tag in quest.objective_tags + quest.race_hooks + quest.pressure_hooks:
        bias += prof["tag_bias"].get(tag, 0.0)
    return bias


def intervention_priority(state: ResolvedWorldState, quest: QuestOffer) -> float:
    skill = weighted_skill_match(state.protagonist, quest_skill_weights(quest))
    bias = strategy_quest_bias(state, quest)
    existence = quest.impact_projection.get("existence_grade_hint", 0.0)
    era_bonus = 0.0
    if quest.source_kind == "era":
        era_bonus = 10.0
    return (
        quest.urgency * 0.55
        + quest.difficulty * 0.15
        + existence * 38.0
        + skill * 20.0
        + bias * 40.0
        + era_bonus
    )


def select_intervention_targets(state: ResolvedWorldState, budget: int) -> List[QuestOffer]:
    ranked = sorted(state.last_generated_quests, key=lambda q: intervention_priority(state, q), reverse=True)
    return ranked[: max(0, min(budget, len(ranked)))]


def local_pressure_scalar(world: WorldState, region_id: str, quest: QuestOffer) -> float:
    region = region_lookup(world)[region_id]
    pressures = compute_pressures(region)
    if not pressures:
        return 0.0
    tops = [pressures.get(h, 0.0) for h in quest.pressure_hooks if h in pressures]
    if tops:
        return sum(tops) / len(tops)
    return max(pressures.values()) * 0.6


def hostile_pair_present(world: WorldState, quest: QuestOffer, ext: ExtendedWorldState) -> bool:
    if not quest.counterparty_faction_id:
        return False
    rel = relation_for_pair(ext, quest.issuer_faction_id, quest.counterparty_faction_id)
    return rel.score <= -30 or rel.status in {"敵対", "戦争前夜"}


def protagonist_resolution_score(state: ResolvedWorldState, quest: QuestOffer, rng: random.Random) -> float:
    skill = weighted_skill_match(state.protagonist, quest_skill_weights(quest))
    prof = strategy_profile(state)
    bias = strategy_quest_bias(state, quest)
    rank_bonus = min(0.18, state.protagonist.existence_grade * 0.025)
    challenge = 0.48 * (quest.difficulty / 100.0) + 0.12 * (quest.urgency / 100.0)
    pressure = 0.12 * local_pressure_scalar(state.ext.world, quest.region_id, quest)
    hostility = 0.05 if hostile_pair_present(state.ext.world, quest, state.ext) else 0.0
    volatility = rng.uniform(-0.08, 0.08) * (0.8 + prof["risk"])
    return 0.44 + 0.56 * skill + bias + rank_bonus - challenge - pressure - hostility + volatility


def can_exploit(state: ResolvedWorldState, quest: QuestOffer) -> bool:
    prof = strategy_profile(state)
    if prof["opportunism"] < 0.65:
        return False
    if quest.source_kind == "era":
        return False
    tags = set(quest.objective_tags + quest.race_hooks)
    return bool(tags & {"契約", "偽証暴き", "真相隠し", "密輸", "契約解決"}) or any(
        key in tags for key in ["forgery", "coverup", "contract"]
    )


def resolve_protagonist_outcome(state: ResolvedWorldState, quest: QuestOffer, rng: random.Random) -> Tuple[str, float, List[str]]:
    score = protagonist_resolution_score(state, quest, rng)
    notes: List[str] = []
    if can_exploit(state, quest) and 0.46 <= score <= 0.82 and quest.counterparty_faction_id and rng.random() < strategy_profile(state)["opportunism"] * 0.55:
        notes.append("機会主義的転用")
        return "収奪的成功", score, notes
    if score >= 0.88:
        return "大成", score, notes
    if score >= 0.68:
        return "成功", score, notes
    if score >= 0.50:
        return "部分成功", score, notes
    if score >= 0.30:
        return "失敗", score, notes
    return "惨敗", score, notes


def neighboring_support_score(world: WorldState, ext: ExtendedWorldState, issuer: GeneratedFaction, region_id: str) -> float:
    neighbors = v3.affected_factions_for_action(world, issuer, region_id)
    if not neighbors:
        return 0.0
    vals = []
    for other in neighbors:
        rel = relation_for_pair(ext, issuer.faction_id, other.faction_id)
        vals.append(rel.score / 100.0)
    return sum(vals) / len(vals)


def resolve_background_outcome(state: ResolvedWorldState, quest: QuestOffer, rng: random.Random) -> Tuple[str, float, List[str]]:
    world = state.ext.world
    fl = faction_lookup(world)
    issuer = fl[quest.issuer_faction_id]
    support = neighboring_support_score(world, state.ext, issuer, quest.region_id)
    power = (issuer.legitimacy + issuer.treasury + issuer.militarization) / 300.0
    pressure = local_pressure_scalar(world, quest.region_id, quest)
    score = 0.22 + 0.55 * power + 0.18 * support - 0.42 * (quest.difficulty / 100.0) - 0.12 * pressure + rng.uniform(-0.07, 0.07)
    notes: List[str] = []
    if score >= 0.56:
        return "自力解決", score, notes
    if score >= 0.34:
        return "継続小康", score, notes
    return "放置悪化", score, notes


def combine_effects(quest: QuestOffer, outcome: str) -> Dict[str, float]:
    scale = OUTCOME_SCALES[outcome]
    combined: Dict[str, float] = {}
    for key, value in quest.potential_success_effects.items():
        combined[key] = combined.get(key, 0.0) + value * scale["success"]
    for key, value in quest.potential_failure_effects.items():
        combined[key] = combined.get(key, 0.0) + value * scale["failure"]
    # exploit should leave a darker residue in the local order
    if outcome == "収奪的成功":
        combined["class_gap"] = combined.get("class_gap", 0.0) + 2.2
        combined["law_order"] = combined.get("law_order", 0.0) - 1.8
        combined["slavery_rate"] = combined.get("slavery_rate", 0.0) + 1.4
    if outcome in {"失敗", "惨敗", "放置悪化"} and quest.source_kind == "era":
        combined["cycle_stability"] = combined.get("cycle_stability", 0.0) - 1.5
    return {k: round(v, 2) for k, v in combined.items() if abs(v) >= 0.01}


def apply_region_effects(world: WorldState, region_id: str, effects: Dict[str, float]) -> Dict[str, float]:
    region = region_lookup(world)[region_id]
    applied: Dict[str, float] = {}
    for key, delta in effects.items():
        if key in region.values:
            old = region.values[key]
            region.values[key] = round(clamp(old + delta), 2)
            applied[key] = round(region.values[key] - old, 2)
    return applied


def adjust_relation_score(ext: ExtendedWorldState, a_id: str, b_id: str, delta: float, reason: str, resolution: QuestResolution) -> None:
    rel = relation_for_pair(ext, a_id, b_id)
    old = rel.score
    rel.score = round(max(-100.0, min(100.0, rel.score + delta)), 2)
    rel.last_delta = round(rel.score - old, 2)
    rel.status = v3.relation_status(rel.score)
    rel.history.append({
        "calendar_year": ext.world.calendar_year,
        "season_index": ext.world.season_index,
        "score": rel.score,
        "status": rel.status,
        "kind": "quest_resolution",
        "reason": reason,
        "delta": rel.last_delta,
        "quest_id": resolution.quest_id,
    })
    resolution.diplomacy_delta[rel.relation_id] = rel.last_delta


def relation_delta_from_resolution(state: ResolvedWorldState, quest: QuestOffer, outcome: str) -> float:
    if not quest.counterparty_faction_id:
        return 0.0
    tier_weight = TIER_IMPACT_WEIGHT.get(tier_of_quest(quest), 1.0)
    scale = OUTCOME_SCALES[outcome]["diplomacy"]
    if scale == 0.0:
        return 0.0
    base = 5.0 * tier_weight
    action_id = quest_action_id(quest)
    if quest.source_kind == "diplomacy":
        return round(base * scale, 2)
    if action_id in v3.COOPERATIVE_ACTIONS:
        return round(base * 0.70 * scale, 2)
    if action_id in v3.AGGRESSIVE_ACTIONS:
        return round(-base * 0.78 * abs(scale), 2)
    if action_id in v3.ORDER_ACTIONS:
        # order quests soothe aligned powers but aggravate noncompliant ones less directly
        return round(base * 0.18 * scale, 2)
    return round(base * 0.10 * scale, 2)


def update_factions_from_resolution(state: ResolvedWorldState, quest: QuestOffer, outcome: str) -> Dict[str, Dict[str, float]]:
    world = state.ext.world
    fl = faction_lookup(world)
    tier_weight = TIER_IMPACT_WEIGHT.get(tier_of_quest(quest), 1.0)
    legitimacy_scale = OUTCOME_SCALES[outcome]["legitimacy"]
    delta_map: Dict[str, Dict[str, float]] = {}

    issuer = fl.get(quest.issuer_faction_id)
    if issuer and quest.issuer_faction_id != "world":
        lg_delta = round(2.2 * tier_weight * legitimacy_scale, 2)
        if quest.source_kind == "era":
            lg_delta *= 0.7
        old_legit = issuer.legitimacy
        issuer.legitimacy = round(clamp(issuer.legitimacy + lg_delta), 2)
        treasury_delta = 0.0
        if outcome in POSITIVE_OUTCOMES:
            treasury_delta = round((0.8 if quest.source_kind != "era" else -0.6) * tier_weight, 2)
        elif outcome in NEGATIVE_OUTCOMES:
            treasury_delta = round((-1.0) * tier_weight, 2)
        elif outcome == "収奪的成功":
            treasury_delta = round(1.4 * tier_weight, 2)
        old_t = issuer.treasury
        issuer.treasury = round(clamp(issuer.treasury + treasury_delta), 2)
        delta_map[issuer.faction_id] = {
            "legitimacy": round(issuer.legitimacy - old_legit, 2),
            "treasury": round(issuer.treasury - old_t, 2),
        }

    if quest.counterparty_faction_id:
        cp = fl.get(quest.counterparty_faction_id)
        if cp:
            cp_delta = 0.0
            if relation_delta_from_resolution(state, quest, outcome) < 0:
                cp_delta = round(-1.4 * tier_weight * legitimacy_scale, 2)
            elif quest.source_kind == "diplomacy" and outcome in POSITIVE_OUTCOMES | {"部分成功", "自力解決"}:
                cp_delta = round(0.8 * tier_weight * max(0.0, legitimacy_scale), 2)
            if cp_delta != 0.0:
                old_legit = cp.legitimacy
                cp.legitimacy = round(clamp(cp.legitimacy + cp_delta), 2)
                delta_map.setdefault(cp.faction_id, {})["legitimacy"] = round(cp.legitimacy - old_legit, 2)
    return delta_map


def overlap_ratio(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def merge_legacy(region: RegionState, medium: str, tags: List[str], intensity: float) -> Dict[str, Any]:
    intensity = max(0.05, min(1.0, intensity))
    best_idx = None
    best_overlap = 0.0
    for idx, legacy in enumerate(region.legacies):
        if legacy.medium != medium:
            continue
        ov = overlap_ratio(legacy.tags, tags)
        if ov > best_overlap:
            best_overlap = ov
            best_idx = idx
    if best_idx is not None and best_overlap >= 0.25:
        legacy = region.legacies[best_idx]
        old_intensity = legacy.intensity
        legacy.intensity = round(min(1.0, legacy.intensity + intensity * (0.65 + 0.35 * best_overlap)), 3)
        legacy.tags = dedupe(list(legacy.tags) + list(tags))[:12]
        return {"medium": medium, "tags": legacy.tags, "intensity_delta": round(legacy.intensity - old_intensity, 3), "merged": True}
    region.legacies.append(LegacyMedium(medium=medium, tags=tags[:12], intensity=round(intensity, 3)))
    if len(region.legacies) > 28:
        region.legacies.sort(key=lambda lg: lg.intensity, reverse=True)
        region.legacies = region.legacies[:28]
    return {"medium": medium, "tags": tags[:12], "intensity_delta": round(intensity, 3), "merged": False}


def legacy_region_spread(state: ResolvedWorldState, quest: QuestOffer) -> Dict[str, float]:
    world = state.ext.world
    reg = region_lookup(world)
    issuer_regions = []
    if quest.issuer_faction_id != "world":
        fl = faction_lookup(world)
        issuer = fl.get(quest.issuer_faction_id)
        if issuer:
            issuer_regions = list(issuer.regions)
    out = {quest.region_id: 1.0}
    tier = tier_of_quest(quest)
    if tier == "regional":
        for rid in reg[quest.region_id].adjacent[:2]:
            out[rid] = max(out.get(rid, 0.0), 0.55)
    elif tier == "macro":
        for rid in reg[quest.region_id].adjacent:
            out[rid] = max(out.get(rid, 0.0), 0.65)
        for rid in issuer_regions[:3]:
            out[rid] = max(out.get(rid, 0.0), 0.55)
    elif tier in {"meta", "mythic"}:
        for region in world.regions:
            out[region.region_id] = max(out.get(region.region_id, 0.0), 0.40 if region.region_id != quest.region_id else 1.0)
    return out


def media_map_for_outcome(quest: QuestOffer, outcome: str) -> Dict[str, float]:
    base_media = dict(quest.impact_projection.get("possible_media", {}))
    if outcome in NEGATIVE_OUTCOMES:
        negative = OUTCOME_NEGATIVE_MEDIA.get(quest.source_kind, OUTCOME_NEGATIVE_MEDIA["default"])
        for medium, weight in negative.items():
            base_media[medium] = max(base_media.get(medium, 0.0), weight)
    if outcome == "収奪的成功":
        base_media["異端文書"] = max(base_media.get("異端文書", 0.0), 0.26)
        base_media["伝承"] = max(base_media.get("伝承", 0.0), 0.24)
    return base_media


def create_legacies_from_resolution(state: ResolvedWorldState, quest: QuestOffer, outcome: str) -> List[Dict[str, Any]]:
    world = state.ext.world
    scale = OUTCOME_SCALES[outcome]["legacy"]
    tier_weight = TIER_IMPACT_WEIGHT.get(tier_of_quest(quest), 1.0)
    spread = legacy_region_spread(state, quest)
    media_map = media_map_for_outcome(quest, outcome)
    tags = dedupe(
        list(quest.objective_tags[:5])
        + list(quest.race_hooks[:2])
        + list(quest.pressure_hooks[:3])
        + [quest.quest_type, quest.source_kind, outcome]
    )
    created: List[Dict[str, Any]] = []
    reg = region_lookup(world)
    for rid, region_factor in spread.items():
        region = reg[rid]
        for medium, weight in media_map.items():
            intensity = min(1.0, max(0.05, weight * scale * (0.35 + 0.35 * tier_weight) * region_factor))
            created_info = merge_legacy(region, medium, tags, intensity)
            created.append({"region_id": rid, "region_name_ja": world.region_meta[rid]["name_ja"], **created_info})
    return created


def protagonist_impact_from_resolution(quest: QuestOffer, outcome: str, legacies_created: List[Dict[str, Any]]) -> Optional[ProtagonistImpact]:
    if OUTCOME_SCALES[outcome]["gain"] <= 0.0:
        return None
    population_est = int(quest.impact_projection.get("affected_population_estimate", 200) * OUTCOME_SCALES[outcome]["population_factor"])
    systems = int(max(1, round(quest.impact_projection.get("systems_affected_count", 1) * (0.65 if outcome == "部分成功" else 1.0))))
    tier = tier_of_quest(quest)
    if outcome in {"失敗", "惨敗"}:
        tier = downgrade_tier(tier)
    elif outcome == "大成":
        tier = upgrade_tier(tier)
    persistence = TIER_BASE_PERSISTENCE.get(tier, 3.0) * (1.15 if outcome == "大成" else 1.0)
    tags = set(quest.objective_tags + quest.race_hooks + quest.pressure_hooks)
    sacrifice = clamp((quest.difficulty / 100.0) * 0.45 + (quest.urgency / 100.0) * 0.18 + (0.12 if quest.counterparty_faction_id else 0.0))
    law_deformation = 0.08
    if quest.source_kind == "diplomacy":
        law_deformation += 0.24
    if quest.source_kind == "era":
        law_deformation += 0.32
    if tags & {"契約", "契約解決", "継承争い", "信仰裁定", "停戦交渉", "共同事業", "Era"}:
        law_deformation += 0.18
    media_outputs: Dict[str, float] = {}
    for entry in legacies_created:
        media_outputs[entry["medium"]] = max(media_outputs.get(entry["medium"], 0.0), min(1.0, entry["intensity_delta"]))
    return ProtagonistImpact(
        affected_population=max(25, population_est),
        systems_affected_count=max(1, systems),
        impact_tier=tier,
        persistence_years=persistence,
        sacrifice_cost=sacrifice,
        law_deformation=min(1.0, law_deformation),
        media_outputs=media_outputs or {"伝承": 0.1},
    )


def apply_protagonist_gain(state: ResolvedWorldState, quest: QuestOffer, outcome: str, legacies_created: List[Dict[str, Any]]) -> float:
    impact = protagonist_impact_from_resolution(quest, outcome, legacies_created)
    if impact is None:
        return 0.0
    gain = evaluate_protagonist_gain(impact) * OUTCOME_SCALES[outcome]["gain"]
    protagonist = state.protagonist
    protagonist.vessel_points = round(protagonist.vessel_points + gain, 3)
    protagonist.total_affected_population += impact.affected_population
    protagonist.total_systems_affected += impact.systems_affected_count
    protagonist.interventions += 1
    for medium, intensity in impact.media_outputs.items():
        protagonist.media_totals[medium] = round(protagonist.media_totals.get(medium, 0.0) + intensity, 3)
    update_existence_title(protagonist)
    protagonist.gain_history.append({
        "quest_id": quest.quest_id,
        "title": quest.title_ja,
        "outcome": outcome,
        "gain": round(gain, 3),
        "impact_tier": impact.impact_tier,
        "media_outputs": impact.media_outputs,
        "existence_title": protagonist.existence_title,
        "vessel_points": protagonist.vessel_points,
    })
    return round(gain, 3)


def resolve_one_quest(state: ResolvedWorldState, quest: QuestOffer, mode: str, rng: random.Random) -> QuestResolution:
    if mode == "protagonist":
        outcome, score, notes = resolve_protagonist_outcome(state, quest, rng)
        actor = "主人公"
    else:
        outcome, score, notes = resolve_background_outcome(state, quest, rng)
        actor = "世界側"
    scale = OUTCOME_SCALES[outcome]
    effects = combine_effects(quest, outcome)
    applied = apply_region_effects(state.ext.world, quest.region_id, effects)
    resolution = QuestResolution(
        quest_id=quest.quest_id,
        season_key=quest.season_key,
        quest_title_ja=quest.title_ja,
        quest_type=quest.quest_type,
        source_kind=quest.source_kind,
        region_id=quest.region_id,
        region_name_ja=quest.region_name_ja,
        outcome=outcome,
        resolution_mode=mode,
        actor=actor,
        score=round(score, 4),
        success_scale=scale["success"],
        failure_scale=scale["failure"],
        applied_effects=applied,
        notes=notes,
    )

    # diplomacy
    if quest.counterparty_faction_id:
        delta = relation_delta_from_resolution(state, quest, outcome)
        if abs(delta) >= 0.01:
            adjust_relation_score(state.ext, quest.issuer_faction_id, quest.counterparty_faction_id, delta, f"quest:{outcome}", resolution)

    # faction legitimacy / treasury
    resolution.faction_delta = update_factions_from_resolution(state, quest, outcome)

    # legacies and protagonist gain
    resolution.legacies_created = create_legacies_from_resolution(state, quest, outcome)
    if mode == "protagonist":
        resolution.protagonist_gain = apply_protagonist_gain(state, quest, outcome, resolution.legacies_created)

    # write into base world history for downstream visibility
    state.ext.world.history.append({
        "calendar_year": state.ext.world.calendar_year,
        "season_index": state.ext.world.season_index,
        "kind": "quest_resolution",
        "quest_id": quest.quest_id,
        "quest_title_ja": quest.title_ja,
        "region_id": quest.region_id,
        "outcome": outcome,
        "mode": mode,
        "applied_effects": applied,
    })
    return resolution


def advance_resolved_world_one_season(state: ResolvedWorldState, quest_budget: int = 12, intervention_budget: int = 4) -> Dict[str, Any]:
    season_result = v3.advance_extended_world_one_season(state.ext, quest_budget=quest_budget)
    state.last_generated_quests = list(state.ext.active_quests)

    engaged = {q.quest_id for q in select_intervention_targets(state, intervention_budget)}
    rng = random.Random(state.ext.world.seed * 104729 + state.ext.world.calendar_year * 101 + state.ext.world.season_index * 13 + len(state.resolution_history) * 17)
    resolutions: List[QuestResolution] = []
    for quest in state.last_generated_quests:
        mode = "protagonist" if quest.quest_id in engaged else "background"
        resolutions.append(resolve_one_quest(state, quest, mode, rng))

    state.last_resolutions = resolutions
    state.resolution_history.append({
        "calendar_year": state.ext.world.calendar_year,
        "season_index": state.ext.world.season_index,
        "resolutions": [round_obj(asdict(r), 3) for r in resolutions],
    })

    era_name = None
    if state.ext.world.world_era and state.ext.world.world_era.get("names"):
        era_name = state.ext.world.world_era["names"].get("official")
    state.season_reports.append({
        "calendar_year": state.ext.world.calendar_year,
        "season_index": state.ext.world.season_index,
        "era": era_name,
        "generated_quests": len(state.last_generated_quests),
        "resolved_by_protagonist": sum(1 for r in resolutions if r.resolution_mode == "protagonist"),
        "positive_outcomes": sum(1 for r in resolutions if r.outcome in POSITIVE_OUTCOMES),
        "negative_outcomes": sum(1 for r in resolutions if r.outcome in NEGATIVE_OUTCOMES),
        "vessel_points": state.protagonist.vessel_points,
        "existence_title": state.protagonist.existence_title,
    })

    return {
        **season_result,
        "generated_quests": [round_obj(asdict(q), 3) for q in state.last_generated_quests],
        "quest_resolutions": [round_obj(asdict(r), 3) for r in resolutions],
        "protagonist": round_obj(asdict(state.protagonist), 3),
    }


def build_resolved_world(seed: int, regions: int, strategy: str = "balanced", schema_path: Path = v2.DEFAULT_SCHEMA_PATH) -> ResolvedWorldState:
    ext = v3.build_extended_world(seed=seed, regions=regions, schema_path=schema_path)
    protagonist = initialize_protagonist(strategy)
    return ResolvedWorldState(ext=ext, protagonist=protagonist)


def export_resolved_world(state: ResolvedWorldState) -> Dict[str, Any]:
    return {
        "resolved_world_version": "4.0",
        "strategy": state.protagonist.strategy_id,
        "protagonist": round_obj(asdict(state.protagonist), 3),
        "base_extended_world": export_extended_world_base(state.ext),
        "last_generated_quests": [round_obj(asdict(q), 3) for q in state.last_generated_quests],
        "last_resolutions": [round_obj(asdict(r), 3) for r in state.last_resolutions],
        "resolution_history": round_obj(state.resolution_history, 3),
        "season_reports": round_obj(state.season_reports, 3),
    }


def summarize_resolved_world(state: ResolvedWorldState) -> str:
    world = state.ext.world
    protagonist = state.protagonist
    lines: List[str] = []
    lines.append("# PBW Resolution + Legacy Summary")
    lines.append("")
    lines.append(f"- 世界名: **{world.world_name}**")
    lines.append(f"- 暦: **{world.calendar_name} {world.calendar_year}年**")
    if world.world_era and world.world_era.get("names"):
        lines.append(f"- 現在Era: **{world.world_era['names'].get('official','無名時代')}** / 民間名 **{world.world_era['names'].get('common','呼称なし')}**")
    else:
        lines.append("- 現在Era: **未成立**")
    lines.append(f"- 主人公方針: **{protagonist.strategy_id}**")
    lines.append(f"- 存在級位: **{protagonist.existence_title}** (grade={protagonist.existence_grade}, vessel={protagonist.vessel_points:.1f})")
    lines.append(f"- 総介入回数: **{protagonist.interventions}**")
    lines.append("")
    lines.append("## 直近の解決結果")
    lines.append("")
    for res in state.last_resolutions[:10]:
        lines.append(f"- **{res.quest_title_ja}** [{res.source_kind}/{res.quest_type}] @ {res.region_name_ja}")
        lines.append(f"  - outcome={res.outcome} / mode={res.resolution_mode} / gain={res.protagonist_gain:.1f}")
        if res.applied_effects:
            eff = ", ".join(f"{k}:{v:+.1f}" for k, v in list(res.applied_effects.items())[:6])
            lines.append(f"  - effects: {eff}")
        if res.diplomacy_delta:
            dd = ", ".join(f"{k}:{v:+.1f}" for k, v in list(res.diplomacy_delta.items())[:3])
            lines.append(f"  - diplomacy: {dd}")
    lines.append("")
    lines.append("## 主人公に残った媒体")
    lines.append("")
    for medium, value in sorted(protagonist.media_totals.items(), key=lambda kv: kv[1], reverse=True)[:8]:
        lines.append(f"- {medium}: {value:.2f}")
    lines.append("")
    lines.append("## 直近季節の上位残滓")
    lines.append("")
    reg = region_lookup(world)
    legacy_rows = []
    for region in world.regions:
        for legacy in region.legacies:
            legacy_rows.append((legacy.intensity, world.region_meta[region.region_id]["name_ja"], legacy.medium, ", ".join(legacy.tags[:4])))
    for intensity, region_name_ja, medium, tags in sorted(legacy_rows, reverse=True)[:12]:
        lines.append(f"- {region_name_ja}: {medium} ({intensity:.2f}) / {tags}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="PBW quest resolution + legacy v4")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--regions", type=int, default=20)
    parser.add_argument("--seasons", type=int, default=6)
    parser.add_argument("--quests", type=int, default=12)
    parser.add_argument("--budget", type=int, default=4, help="protagonist interventions per season")
    parser.add_argument("--strategy", type=str, default="balanced", choices=sorted(RESOLUTION_STRATEGIES.keys()))
    parser.add_argument("--schema", type=Path, default=v2.DEFAULT_SCHEMA_PATH)
    parser.add_argument("--out", type=Path, default=BASE_DIR / "pbw_generated_world_seed1729_v3_resolution.json")
    parser.add_argument("--summary-out", type=Path, default=BASE_DIR / "pbw_generated_world_seed1729_v3_resolution_summary.md")
    args = parser.parse_args()

    state = build_resolved_world(seed=args.seed, regions=args.regions, strategy=args.strategy, schema_path=args.schema)
    for _ in range(args.seasons):
        advance_resolved_world_one_season(state, quest_budget=args.quests, intervention_budget=args.budget)

    args.out.write_text(json.dumps(export_resolved_world(state), ensure_ascii=False, indent=2), encoding="utf-8")
    args.summary_out.write_text(summarize_resolved_world(state), encoding="utf-8")
    print(f"Wrote resolved world to {args.out}")
    print(f"Wrote summary to {args.summary_out}")
    print(f"Existence: {state.protagonist.existence_title} / {state.protagonist.vessel_points:.1f}")


if __name__ == "__main__":
    main()
