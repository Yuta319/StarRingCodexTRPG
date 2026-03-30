"""PBW diplomacy + quest generation v3

Extends pbw_world_bootstrap_ai_v2.py by directly connecting:
- faction actions -> diplomacy drift
- faction actions + race micro_conflict_vectors -> quest generation
- world era / regional pressure -> macro and meta stakes on quests

The goal is not to script a fixed narrative, but to keep the world self-running
while exposing locally actionable quest hooks that can feed a player-facing loop.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_V2_PATH = BASE_DIR / "pbw_world_bootstrap_ai_v2.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v2 = _load_module(DEFAULT_V2_PATH, "pbw_world_bootstrap_ai_v2_ext")

WorldState = v2.WorldState
GeneratedFaction = v2.GeneratedFaction
RegionState = v2.RegionState
clamp = v2.clamp
compute_pressures = v2.compute_pressures
export_world_base = v2.export_world


TERRITORIAL_TYPES = {"state", "tribe", "demon_domain"}
STRUCTURAL_TYPES = {"state", "religion", "guild", "tribe", "demon_domain"}
COOPERATIVE_ACTIONS = {"grain_distribution", "migration_convoy", "pilgrimage", "purify_miasma", "seal_rift", "smuggle_relief", "awaken_hero_cult"}
ORDER_ACTIONS = {"rationing", "fortify_borders", "inquisition", "enforce_contracts", "seal_rift", "purify_miasma"}
AGGRESSIVE_ACTIONS = {"raid_caravans", "colonize_frontier", "spread_miasma", "inquisition"}
ECONOMIC_ACTIONS = {"grain_distribution", "rationing", "sponsor_delvers", "enforce_contracts", "smuggle_relief", "raid_caravans"}
RIFT_ACTIONS = {"seal_rift", "purify_miasma", "spread_miasma", "sponsor_delvers"}

STATUS_THRESHOLDS = [
    (70, "盟約"),
    (40, "協調"),
    (15, "友好"),
    (-14, "中立"),
    (-39, "緊張"),
    (-69, "敵対"),
    (-101, "戦争前夜"),
]


@dataclass
class DiplomacyRelation:
    relation_id: str
    faction_a: str
    faction_b: str
    score: float
    status: str
    axes: Dict[str, float]
    tags: List[str] = field(default_factory=list)
    shared_regions: List[str] = field(default_factory=list)
    border_regions: List[str] = field(default_factory=list)
    last_delta: float = 0.0
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class QuestOffer:
    quest_id: str
    season_key: str
    source_kind: str
    quest_type: str
    title_ja: str
    summary_ja: str
    issuer_faction_id: str
    issuer_faction_name: str
    issuer_race: str
    region_id: str
    region_name_ja: str
    counterparty_faction_id: Optional[str] = None
    counterparty_faction_name: Optional[str] = None
    counterparty_race: Optional[str] = None
    urgency: float = 50.0
    difficulty: float = 50.0
    objective_tags: List[str] = field(default_factory=list)
    race_hooks: List[str] = field(default_factory=list)
    pressure_hooks: List[str] = field(default_factory=list)
    dialogue_mood: List[str] = field(default_factory=list)
    impact_projection: Dict[str, Any] = field(default_factory=dict)
    potential_success_effects: Dict[str, float] = field(default_factory=dict)
    potential_failure_effects: Dict[str, float] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtendedWorldState:
    world: WorldState
    diplomacy: Dict[str, DiplomacyRelation]
    active_quests: List[QuestOffer] = field(default_factory=list)
    diplomacy_history: List[Dict[str, Any]] = field(default_factory=list)
    quest_history: List[Dict[str, Any]] = field(default_factory=list)


TYPE_RELATION_BASE: Dict[Tuple[str, str], float] = {
    ("state", "state"): -6.0,
    ("state", "religion"): 10.0,
    ("state", "guild"): 9.0,
    ("state", "tribe"): -8.0,
    ("state", "demon_domain"): -42.0,
    ("religion", "religion"): -2.0,
    ("religion", "guild"): 3.0,
    ("religion", "tribe"): -4.0,
    ("religion", "demon_domain"): -38.0,
    ("guild", "guild"): -4.0,
    ("guild", "tribe"): 2.0,
    ("guild", "demon_domain"): -16.0,
    ("tribe", "tribe"): -3.0,
    ("tribe", "demon_domain"): -18.0,
    ("demon_domain", "demon_domain"): -8.0,
}


ACTION_RELATION_RULES: Dict[str, Dict[str, Any]] = {
    "grain_distribution": {
        "base_nearby": {"state": 4.0, "religion": 4.0, "guild": 3.0, "tribe": 4.0, "demon_domain": -5.0},
        "region_bonus": "food_stress",
        "notes": ["救済", "配給"],
    },
    "rationing": {
        "base_nearby": {"state": 2.0, "religion": 1.0, "guild": -2.0, "tribe": -3.0, "demon_domain": 0.0},
        "region_bonus": "food_stress",
        "notes": ["配給統制", "不満"],
    },
    "migration_convoy": {
        "base_nearby": {"state": 1.0, "religion": 4.0, "guild": 3.0, "tribe": 3.0, "demon_domain": -4.0},
        "region_bonus": "housing_stress",
        "notes": ["避難", "移民"],
    },
    "fortify_borders": {
        "base_nearby": {"state": 4.0, "religion": 2.0, "guild": -1.0, "tribe": -4.0, "demon_domain": -6.0},
        "region_bonus": "demon_lord_pressure",
        "notes": ["国境強化", "封鎖"],
    },
    "inquisition": {
        "base_nearby": {"state": 4.0, "religion": 5.0, "guild": -3.0, "tribe": -6.0, "demon_domain": -8.0},
        "region_bonus": "faith_schism",
        "notes": ["異端審問", "粛清"],
    },
    "pilgrimage": {
        "base_nearby": {"state": 2.0, "religion": 6.0, "guild": 3.0, "tribe": 1.0, "demon_domain": -4.0},
        "region_bonus": "faith_schism",
        "notes": ["巡礼", "聖路"],
    },
    "purify_miasma": {
        "base_nearby": {"state": 4.0, "religion": 5.0, "guild": 3.0, "tribe": 4.0, "demon_domain": -10.0},
        "region_bonus": "miasma_bloom",
        "notes": ["浄化", "瘴気"],
    },
    "sponsor_delvers": {
        "base_nearby": {"state": 2.0, "religion": -2.0, "guild": 6.0, "tribe": -1.0, "demon_domain": -3.0},
        "region_bonus": "dungeon_fixation",
        "notes": ["探索支援", "深層"],
    },
    "seal_rift": {
        "base_nearby": {"state": 4.0, "religion": 5.0, "guild": -2.0, "tribe": 1.0, "demon_domain": -9.0},
        "region_bonus": "interworld_bleed",
        "notes": ["裂け目封鎖", "封印"],
    },
    "colonize_frontier": {
        "base_nearby": {"state": 3.0, "religion": 0.0, "guild": 2.0, "tribe": -8.0, "demon_domain": -2.0},
        "region_bonus": "housing_stress",
        "notes": ["開拓", "境界侵犯"],
    },
    "raid_caravans": {
        "base_nearby": {"state": -8.0, "religion": -3.0, "guild": -10.0, "tribe": -2.0, "demon_domain": 2.0},
        "region_bonus": "food_stress",
        "notes": ["略奪", "商路襲撃"],
    },
    "enforce_contracts": {
        "base_nearby": {"state": 3.0, "religion": -1.0, "guild": 4.0, "tribe": -4.0, "demon_domain": 2.0},
        "region_bonus": "legitimacy_crisis",
        "notes": ["契約執行", "記録"],
    },
    "smuggle_relief": {
        "base_nearby": {"state": -4.0, "religion": 2.0, "guild": 4.0, "tribe": 4.0, "demon_domain": -1.0},
        "region_bonus": "food_stress",
        "notes": ["密輸救済", "闇市"],
    },
    "awaken_hero_cult": {
        "base_nearby": {"state": 2.0, "religion": 4.0, "guild": 0.0, "tribe": 2.0, "demon_domain": -4.0},
        "region_bonus": "faith_schism",
        "notes": ["英雄崇拝", "奇跡"],
    },
    "spread_miasma": {
        "base_nearby": {"state": -10.0, "religion": -10.0, "guild": -7.0, "tribe": -6.0, "demon_domain": 4.0},
        "region_bonus": "miasma_bloom",
        "notes": ["瘴気拡散", "侵蝕"],
    },
}

ACTION_TO_QUEST = {
    "grain_distribution": ("護送", ["配給", "護衛", "帳簿"], ["飢え", "切迫", "不正の匂い"]),
    "rationing": ("監査", ["配給統制", "帳簿", "群衆管理"], ["緊張", "焦燥", "猜疑"]),
    "migration_convoy": ("避難", ["護送", "失踪者", "越境"], ["喪失", "保護", "混乱"]),
    "fortify_borders": ("警戒", ["斥候", "封鎖", "偽装"], ["警戒", "敵意", "息苦しさ"]),
    "inquisition": ("糾明", ["異端", "証言", "保護か告発"], ["信仰", "恐怖", "断罪"]),
    "pilgrimage": ("巡礼", ["護衛", "聖遺物", "道程"], ["敬虔", "疲労", "希望"]),
    "purify_miasma": ("浄化", ["浄化", "救出", "祭具"], ["腐敗", "祈り", "急務"]),
    "sponsor_delvers": ("探索", ["深層", "遺物", "救助"], ["欲望", "好奇心", "不穏"]),
    "seal_rift": ("封印", ["裂け目", "儀式", "素材収集"], ["切迫", "畏れ", "厳粛"]),
    "colonize_frontier": ("境界", ["測量", "交渉", "報復回避"], ["野心", "反発", "不安"]),
    "raid_caravans": ("奪還", ["追跡", "奪還", "捕虜"], ["怒り", "飢え", "報復"]),
    "enforce_contracts": ("契約", ["偽印", "徴収", "証文"], ["圧迫", "理詰め", "不服"]),
    "smuggle_relief": ("密輸", ["抜け道", "密輸", "内通者"], ["背徳", "慈悲", "焦燥"]),
    "awaken_hero_cult": ("聖跡", ["奇跡", "偽遺物", "巡礼"], ["熱狂", "崇拝", "疑念"]),
    "spread_miasma": ("汚染源", ["瘴気核", "破壊", "感染"], ["絶望", "嫌悪", "執念"]),
}

VECTOR_TAG_KEYWORDS = {
    "forgery": ["偽造", "改竄", "偽装", "偽印", "偽"] ,
    "inheritance": ["継承", "家督", "戴冠", "血統", "隠し子"],
    "disappearance": ["失踪", "誘拐", "連れ去り"],
    "heresy": ["異端", "聖名", "神託", "密告", "断罪"],
    "resource": ["狩場", "伐採", "鉱", "真珠", "種子", "遺物", "税", "航路", "漁"],
    "contract": ["契約", "真名", "証文", "封印"],
    "rescue": ["奪還", "救出", "捕縛"],
    "coverup": ["隠蔽", "転嫁", "処遇", "是非"],
    "rite": ["通過儀礼", "巡礼", "沈黙儀礼", "花季婚"],
}

QUEST_TYPE_BY_VECTOR = {
    "forgery": "偽証暴き",
    "inheritance": "継承争い",
    "disappearance": "失踪追跡",
    "heresy": "信仰裁定",
    "resource": "資源争奪",
    "contract": "契約解決",
    "rescue": "奪還",
    "coverup": "真相隠し",
    "rite": "儀礼支援",
}

SUCCESS_MEDIA_BY_ACTION = {
    "grain_distribution": {"制度": 0.4, "伝承": 0.2},
    "rationing": {"制度": 0.5, "正史": 0.1},
    "migration_convoy": {"伝承": 0.3, "制度": 0.2},
    "fortify_borders": {"建築": 0.4, "正史": 0.1},
    "inquisition": {"正史": 0.3, "異端文書": 0.3},
    "pilgrimage": {"信仰": 0.5, "伝承": 0.2},
    "purify_miasma": {"信仰": 0.2, "建築": 0.2, "魂": 0.2},
    "sponsor_delvers": {"建築": 0.1, "伝承": 0.2, "制度": 0.1},
    "seal_rift": {"信仰": 0.2, "魂": 0.4, "建築": 0.2},
    "colonize_frontier": {"制度": 0.3, "建築": 0.2},
    "raid_caravans": {"伝承": 0.2, "魂": 0.1},
    "enforce_contracts": {"制度": 0.5, "正史": 0.1},
    "smuggle_relief": {"伝承": 0.4, "異端文書": 0.2},
    "awaken_hero_cult": {"信仰": 0.6, "伝承": 0.2},
    "spread_miasma": {"魂": 0.3, "建築": 0.1, "異端文書": 0.2},
}


def avg(values: Iterable[float], default: float = 0.0) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else default


def pair_key(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a < b else (b, a)


def relation_status(score: float) -> str:
    for threshold, label in STATUS_THRESHOLDS:
        if score >= threshold:
            return label
    return "戦争前夜"


def round_obj(obj: Any, digits: int = 3) -> Any:
    if isinstance(obj, float):
        return round(obj, digits)
    if isinstance(obj, list):
        return [round_obj(v, digits) for v in obj]
    if isinstance(obj, dict):
        return {k: round_obj(v, digits) for k, v in obj.items()}
    return obj


def build_extended_world(seed: int, regions: int, schema_path: Path = v2.DEFAULT_SCHEMA_PATH) -> ExtendedWorldState:
    world = v2.generate_initial_world(seed, schema_path, regions)
    diplomacy = initialize_diplomacy(world)
    return ExtendedWorldState(world=world, diplomacy=diplomacy)


def region_lookup(world: WorldState) -> Dict[str, RegionState]:
    return {r.region_id: r for r in world.regions}


def faction_lookup(world: WorldState) -> Dict[str, GeneratedFaction]:
    return {f.faction_id: f for f in world.factions}


def relation_base_for_types(type_a: str, type_b: str) -> float:
    key = pair_key(type_a, type_b)
    return TYPE_RELATION_BASE.get(key, 0.0)


def shared_border_regions(world: WorldState, a: GeneratedFaction, b: GeneratedFaction) -> List[str]:
    reg = region_lookup(world)
    b_regions = set(b.regions)
    out: List[str] = []
    for rid in a.regions:
        for adj in reg[rid].adjacent:
            if adj in b_regions and rid not in out:
                out.append(rid)
    return out


def doctrine_overlap(a: GeneratedFaction, b: GeneratedFaction) -> float:
    ta = set(a.doctrine_tags)
    tb = set(b.doctrine_tags)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta | tb), 1)


def compute_relation_axes(world: WorldState, a: GeneratedFaction, b: GeneratedFaction) -> Tuple[Dict[str, float], List[str], List[str], List[str]]:
    reg = region_lookup(world)
    runtime = world.runtime_profiles
    shared = sorted(set(a.regions) & set(b.regions))
    borders = shared_border_regions(world, a, b)
    overlap = doctrine_overlap(a, b)
    a_drive = runtime[a.dominant_race]["drives"]
    b_drive = runtime[b.dominant_race]["drives"]
    a_num = runtime[a.dominant_race]["numeric"]
    b_num = runtime[b.dominant_race]["numeric"]

    territory = 0.0
    if a.faction_type in TERRITORIAL_TYPES and b.faction_type in TERRITORIAL_TYPES:
        territory += 0.28
    territory += 0.18 * len(shared)
    territory += 0.08 * len(borders)
    if a.faction_type == b.faction_type == "guild":
        territory += 0.08 * len(shared)

    trade = 0.12 + 0.36 * avg([a_drive["trade"], b_drive["trade"]], 0.4)
    if "guild" in {a.faction_type, b.faction_type}:
        trade += 0.12
    trade += 0.05 * len(shared)
    if a.faction_type == b.faction_type == "guild":
        trade -= 0.06 * len(shared)

    theology = 0.0
    if "religion" in {a.faction_type, b.faction_type}:
        theology += 0.20
        theology += 0.30 * (1.0 - overlap)
        theology += 0.12 * avg([a_num["heresy_risk"], b_num["heresy_risk"]], 0.5)
    if a.faction_type == b.faction_type == "religion":
        theology += 0.08
    if "主神奉戴" in a.doctrine_tags and "主神奉戴" in b.doctrine_tags:
        theology -= 0.18
    if "異界浸潤" in a.doctrine_tags or "異界浸潤" in b.doctrine_tags:
        theology += 0.18

    security = 0.08
    def avg_region_value(ids: Sequence[str], key: str) -> float:
        return avg([reg[rid].values[key] for rid in ids], 50.0)

    a_miasma = avg_region_value(a.regions, "miasma_level")
    b_miasma = avg_region_value(b.regions, "miasma_level")
    security += abs(a_miasma - b_miasma) / 220.0
    security += abs(a.legitimacy - b.legitimacy) / 250.0
    if "demon_domain" in {a.faction_type, b.faction_type}:
        security += 0.22
    if a.faction_type == b.faction_type == "tribe":
        security += 0.05 * len(borders)

    legitimacy_alignment = 0.20
    legitimacy_alignment += 0.25 * (1.0 - abs(a.legitimacy - b.legitimacy) / 100.0)
    legitimacy_alignment += 0.18 * overlap
    if a.dominant_race == b.dominant_race:
        legitimacy_alignment += 0.12
    if a.faction_type == "state" and b.faction_type == "religion":
        legitimacy_alignment += 0.08

    tags: List[str] = []
    if shared:
        tags.append("shared_region")
    if borders:
        tags.append("border_contact")
    if a.dominant_race == b.dominant_race:
        tags.append("same_race")
    if overlap >= 0.25:
        tags.append("doctrine_overlap")
    if "guild" in {a.faction_type, b.faction_type} and trade >= 0.4:
        tags.append("trade_channel")
    if "religion" in {a.faction_type, b.faction_type} and theology >= 0.35:
        tags.append("theological_tension")
    if "demon_domain" in {a.faction_type, b.faction_type}:
        tags.append("miasma_hostility")

    axes = {
        "territory": clamp(territory),
        "trade": clamp(trade),
        "theology": clamp(theology),
        "security": clamp(security),
        "legitimacy": clamp(legitimacy_alignment),
    }
    return axes, tags, shared, borders


def compute_relation_score(world: WorldState, a: GeneratedFaction, b: GeneratedFaction, axes: Dict[str, float]) -> float:
    runtime = world.runtime_profiles
    a_drive = runtime[a.dominant_race]["drives"]
    b_drive = runtime[b.dominant_race]["drives"]

    score = relation_base_for_types(a.faction_type, b.faction_type)
    score += 24.0 * axes["trade"]
    score += 20.0 * axes["legitimacy"]
    score -= 28.0 * axes["territory"]
    score -= 22.0 * axes["theology"]
    score -= 18.0 * axes["security"]
    score += 10.0 * avg([a_drive["order"], b_drive["order"]], 0.5)
    score += 8.0 * avg([a_drive["relief"], b_drive["relief"]], 0.5)
    score -= 8.0 * avg([a_drive["corruption"], b_drive["corruption"]], 0.5)
    if a.dominant_race == b.dominant_race:
        score += 8.0
    if "主神奉戴" in a.doctrine_tags and "主神奉戴" in b.doctrine_tags:
        score += 6.0
    if "異界浸潤" in a.doctrine_tags or "異界浸潤" in b.doctrine_tags:
        score -= 10.0
    return round(max(-100.0, min(100.0, score)), 2)


def initialize_diplomacy(world: WorldState) -> Dict[str, DiplomacyRelation]:
    factions = world.factions
    out: Dict[str, DiplomacyRelation] = {}
    for i, a in enumerate(factions):
        for b in factions[i + 1:]:
            axes, tags, shared, borders = compute_relation_axes(world, a, b)
            score = compute_relation_score(world, a, b, axes)
            rid = f"{a.faction_id}__{b.faction_id}" if a.faction_id < b.faction_id else f"{b.faction_id}__{a.faction_id}"
            out[rid] = DiplomacyRelation(
                relation_id=rid,
                faction_a=min(a.faction_id, b.faction_id),
                faction_b=max(a.faction_id, b.faction_id),
                score=score,
                status=relation_status(score),
                axes=axes,
                tags=tags,
                shared_regions=shared,
                border_regions=borders,
            )
    return out


def apply_baseline_diplomacy_drift(ext: ExtendedWorldState) -> List[Dict[str, Any]]:
    world = ext.world
    fl = faction_lookup(world)
    events: List[Dict[str, Any]] = []
    for rel in ext.diplomacy.values():
        a = fl[rel.faction_a]
        b = fl[rel.faction_b]
        old_score = rel.score
        old_status = rel.status
        axes, tags, shared, borders = compute_relation_axes(world, a, b)
        baseline = compute_relation_score(world, a, b, axes)
        rel.score = round(old_score * 0.78 + baseline * 0.22, 2)
        rel.axes = axes
        rel.tags = tags
        rel.shared_regions = shared
        rel.border_regions = borders
        rel.last_delta = round(rel.score - old_score, 2)
        rel.status = relation_status(rel.score)
        if rel.status != old_status:
            events.append({
                "kind": "status_shift",
                "relation_id": rel.relation_id,
                "from": old_status,
                "to": rel.status,
                "delta": rel.last_delta,
            })
        rel.history.append({
            "calendar_year": world.calendar_year,
            "season_index": world.season_index,
            "score": rel.score,
            "status": rel.status,
            "kind": "baseline",
        })
    return events


def reaction_bonus_from_race(world: WorldState, other: GeneratedFaction, action_id: str) -> float:
    runtime = world.runtime_profiles[other.dominant_race]
    num = runtime["numeric"]
    primary = runtime["primary_attribute"]
    bonus = 0.0
    if action_id == "inquisition":
        bonus -= 6.0 * num["heresy_risk"]
        if primary in {"dark", "mind", "explosion"}:
            bonus -= 3.0
    elif action_id == "purify_miasma":
        if primary in {"healing", "light", "water"}:
            bonus += 2.5
        if other.faction_type == "demon_domain":
            bonus -= 5.0
    elif action_id == "sponsor_delvers":
        if primary in {"earth", "metal", "dark"}:
            bonus += 3.0
    elif action_id == "seal_rift":
        if primary in {"mind", "dark"} and other.faction_type in {"guild", "tribe"}:
            bonus -= 2.0
        if primary in {"light", "healing", "thunder"}:
            bonus += 2.0
    elif action_id == "colonize_frontier":
        if other.dominant_race in {"werebeast", "plantfolk", "fey"}:
            bonus -= 4.0
    elif action_id == "spread_miasma":
        if other.dominant_race in {"demonian", "fallen"}:
            bonus += 3.0
        if primary in {"healing", "light"}:
            bonus -= 4.0
    return bonus


def relation_for_pair(ext: ExtendedWorldState, a_id: str, b_id: str) -> DiplomacyRelation:
    low, high = pair_key(a_id, b_id)
    rel_id = f"{low}__{high}"
    return ext.diplomacy[rel_id]


def affected_factions_for_action(world: WorldState, actor: GeneratedFaction, target_region: str) -> List[GeneratedFaction]:
    reg = region_lookup(world)
    target_neighbors = set([target_region] + reg[target_region].adjacent)
    out: List[GeneratedFaction] = []
    for other in world.factions:
        if other.faction_id == actor.faction_id:
            continue
        if target_neighbors & set(other.regions):
            out.append(other)
    return out


def apply_action_diplomacy(ext: ExtendedWorldState, decisions: List[Dict[str, Any]], pressures: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    world = ext.world
    fl = faction_lookup(world)
    events: List[Dict[str, Any]] = []
    for decision in decisions:
        actor = fl[decision["faction_id"]]
        action_id = decision["action_id"]
        action_rule = ACTION_RELATION_RULES[action_id]
        region_id = decision["target_region"]
        regional_pressure = pressures.get(region_id, {})
        nearby = affected_factions_for_action(world, actor, region_id)
        for other in nearby:
            rel = relation_for_pair(ext, actor.faction_id, other.faction_id)
            old_score = rel.score
            old_status = rel.status
            base_delta = action_rule["base_nearby"].get(other.faction_type, 0.0)
            pressure_factor = regional_pressure.get(action_rule["region_bonus"], 0.0)
            delta = base_delta + pressure_factor * 6.0
            delta += reaction_bonus_from_race(world, other, action_id)
            # same-side synergy or mirrored hostility
            if action_id in COOPERATIVE_ACTIONS and other.last_action and other.last_action.get("target_region") == region_id:
                if other.last_action.get("action_id") in COOPERATIVE_ACTIONS:
                    delta += 3.0
            if action_id in AGGRESSIVE_ACTIONS and other.last_action and other.last_action.get("target_region") == region_id:
                if other.last_action.get("action_id") in ORDER_ACTIONS | COOPERATIVE_ACTIONS:
                    delta -= 4.0
            rel.score = round(max(-100.0, min(100.0, rel.score + delta)), 2)
            rel.last_delta = round(rel.score - old_score, 2)
            rel.status = relation_status(rel.score)
            rel.history.append({
                "calendar_year": world.calendar_year,
                "season_index": world.season_index,
                "score": rel.score,
                "status": rel.status,
                "kind": "action",
                "by": actor.faction_id,
                "action_id": action_id,
                "target_region": region_id,
                "delta": rel.last_delta,
            })
            if abs(rel.last_delta) >= 4.0 or rel.status != old_status:
                events.append({
                    "kind": "action_shift",
                    "relation_id": rel.relation_id,
                    "actor": actor.faction_id,
                    "other": other.faction_id,
                    "action_id": action_id,
                    "region_id": region_id,
                    "delta": rel.last_delta,
                    "from": old_status,
                    "to": rel.status,
                })
    return events


def infer_vector_tags(vector: str) -> List[str]:
    tags: List[str] = []
    for tag, keywords in VECTOR_TAG_KEYWORDS.items():
        if any(word in vector for word in keywords):
            tags.append(tag)
    return tags or ["resource"]


def score_vector_for_context(vector: str, action_id: str, region: RegionState, pressures: Dict[str, float]) -> float:
    score = 0.0
    tags = infer_vector_tags(vector)
    if action_id in {"grain_distribution", "rationing", "smuggle_relief", "raid_caravans"} and ("resource" in tags or "forgery" in tags):
        score += 2.0
    if action_id in {"inquisition", "pilgrimage", "awaken_hero_cult"} and ("heresy" in tags or "rite" in tags):
        score += 2.0
    if action_id in {"sponsor_delvers", "seal_rift", "spread_miasma"} and ("contract" in tags or "coverup" in tags or "disappearance" in tags):
        score += 2.0
    if action_id in {"colonize_frontier", "migration_convoy", "fortify_borders"} and ("resource" in tags or "rescue" in tags or "inheritance" in tags):
        score += 1.5
    score += pressures.get("food_stress", 0.0) if "resource" in tags else 0.0
    score += pressures.get("faith_schism", 0.0) if "heresy" in tags else 0.0
    score += pressures.get("legitimacy_crisis", 0.0) if "inheritance" in tags or "forgery" in tags else 0.0
    score += pressures.get("interworld_bleed", 0.0) if "contract" in tags or "disappearance" in tags else 0.0
    if region.values["trade_routes"] >= 60 and "resource" in tags:
        score += 0.6
    if region.values["law_order"] <= 40 and "coverup" in tags:
        score += 0.8
    return score


def choose_micro_vector(world: WorldState, race_id: str, action_id: str, region: RegionState, pressures: Dict[str, float], rng: random.Random) -> str:
    vectors = world.runtime_profiles[race_id]["original_tags"]["micro_conflict_vectors"]
    scored = [(v, score_vector_for_context(v, action_id, region, pressures) + rng.random() * 0.4) for v in vectors]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def quest_type_for_vector(vector: str, action_id: str) -> str:
    for tag in infer_vector_tags(vector):
        if tag in QUEST_TYPE_BY_VECTOR:
            return QUEST_TYPE_BY_VECTOR[tag]
    return ACTION_TO_QUEST[action_id][0]


def top_pressure_tags(pressures: Dict[str, float], k: int = 2) -> List[str]:
    return [name for name, _ in sorted(pressures.items(), key=lambda kv: kv[1], reverse=True)[:k] if _ > 0.2]


def region_name(world: WorldState, rid: str) -> str:
    return world.region_meta[rid]["name_ja"]


def build_action_quest_title(action_id: str, vector: str, region_name_ja: str, counterparty_name: Optional[str], rng: random.Random) -> str:
    base_type, _, _ = ACTION_TO_QUEST[action_id]
    if action_id == "grain_distribution":
        choices = [f"{region_name_ja}の配給路", f"{region_name_ja}の欠けた倉札", f"{region_name_ja}の飢えぬ荷車"]
    elif action_id == "inquisition":
        choices = [f"{region_name_ja}の沈黙証言", f"{region_name_ja}の偽りの神託", f"{region_name_ja}の断罪前夜"]
    elif action_id == "sponsor_delvers":
        choices = [f"{region_name_ja}の下層図", f"{region_name_ja}の戻らぬ探索隊", f"{region_name_ja}の封鎖坑道"]
    elif action_id == "seal_rift":
        choices = [f"{region_name_ja}の裂け目祭具", f"{region_name_ja}の境界縫い", f"{region_name_ja}の最後の楔"]
    elif action_id == "spread_miasma":
        choices = [f"{region_name_ja}の瘴核", f"{region_name_ja}の黒い胞子舟", f"{region_name_ja}の汚染鐘"]
    else:
        choices = [f"{region_name_ja}の{vector}", f"{region_name_ja}の{base_type}", f"{region_name_ja}の{vector}事件"]
    if counterparty_name and rng.random() < 0.4:
        choices.append(f"{counterparty_name}と{region_name_ja}の{base_type}")
    return rng.choice(choices)


def build_action_quest_summary(world: WorldState, issuer: GeneratedFaction, decision: Dict[str, Any], region: RegionState, vector: str, counterparty: Optional[GeneratedFaction], pressures: Dict[str, float]) -> str:
    era_name = None
    if world.world_era and world.world_era.get("names"):
        era_name = world.world_era["names"].get("common")
    action_id = decision["action_id"]
    templates = {
        "grain_distribution": "{era}の余波で配給が乱れ、{region}では{vector}が倉札の裏で進んでいる。{issuer}は荷と帳面を守る手を必要としている。",
        "rationing": "{region}では統制配給が始まったが、{vector}が列と帳簿を歪めている。{issuer}は暴動を避けつつ真相を押さえたい。",
        "migration_convoy": "避難列が{region}を抜ける最中、{vector}が行路を裂いた。{issuer}は人々を欠けさせず送り届けたい。",
        "fortify_borders": "{region}の境界が閉ざされるなか、{vector}が見張りを攪乱している。{issuer}は封鎖の穴を塞ぎたい。",
        "inquisition": "{region}では異端審問が始まり、{vector}が証言の底に沈んでいる。{issuer}は断罪か保護かの分岐に立っている。",
        "pilgrimage": "{region}へ向かう巡礼路で{vector}が聖路を濁している。{issuer}は祈りを途切れさせたくない。",
        "purify_miasma": "{region}では瘴気浄化が進むが、{vector}が汚染源への道を隠している。{issuer}は人命と儀式の両方を守りたい。",
        "sponsor_delvers": "{region}の深層探索は利益を呼ぶ一方、{vector}が帰還率を削っている。{issuer}は深層の成果と生還を両立させたい。",
        "seal_rift": "{region}の裂け目封鎖には時間がない。{vector}が術式の継ぎ目を乱し、{issuer}は最後の楔を求めている。",
        "colonize_frontier": "{region}の開拓は進むが、{vector}が古い境界と新しい地図を衝突させている。{issuer}は流血なしの拡張を望む。",
        "raid_caravans": "{region}を通る隊商が襲われ、{vector}が奪われた荷の行方をさらに曇らせている。{issuer}は損害を取り戻したい。",
        "enforce_contracts": "{region}では契約執行が強まり、{vector}が証文の信頼を揺らしている。{issuer}は名と印の秩序を回復したい。",
        "smuggle_relief": "{region}の飢えを前に、非合法の救援路が走り始めた。だが{vector}が善意と利権を絡ませている。{issuer}は誰を生かし誰を裏切るか迫られている。",
        "awaken_hero_cult": "{region}では英雄崇拝が燃え上がる一方、{vector}が奇跡の真贋を曖昧にしている。{issuer}は熱狂を信仰へ変えたい。",
        "spread_miasma": "{region}に瘴気が広がり、{vector}が汚染の核を守っている。{issuer}は恐怖を支配へ変えようとしている。",
    }
    era = era_name or f"{world.main_god_name}暦{world.calendar_year}年"
    text = templates[action_id].format(era=era, region=world.region_meta[region.region_id]["name_ja"], vector=vector, issuer=issuer.label_ja)
    if counterparty:
        text += f" 対立先としては {counterparty.label_ja} の影が濃い。"
    top = top_pressure_tags(pressures)
    if top:
        text += f" 現地では {', '.join(top)} が強く、放置すると状況は一段悪化する。"
    return text


def estimate_impact_projection(world: WorldState, region: RegionState, action_id: str, urgency: float, counterparty: Optional[GeneratedFaction]) -> Dict[str, Any]:
    affected = int(region.values["population"] * (18 + urgency / 8.0))
    systems = 2
    if action_id in {"seal_rift", "spread_miasma", "awaken_hero_cult", "inquisition"}:
        systems += 1
    if counterparty is not None:
        systems += 1
    tier = "local"
    if affected >= 1700 or systems >= 4:
        tier = "regional"
    if action_id in {"seal_rift", "spread_miasma", "awaken_hero_cult"} and urgency >= 75:
        tier = "macro"
    if world.world_era and world.world_era.get("coverage_ratio", 0) >= 0.55 and tier == "macro":
        tier = "meta"
    media = SUCCESS_MEDIA_BY_ACTION.get(action_id, {"伝承": 0.2})
    return {
        "affected_population_estimate": affected,
        "systems_affected_count": systems,
        "impact_tier": tier,
        "possible_media": media,
        "existence_grade_hint": round(0.18 + affected / 2400.0 + systems * 0.08 + (0.2 if tier in {"macro", "meta"} else 0.0), 3),
    }


def build_success_failure_effects(action_id: str, region: RegionState, pressures: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    base_effects = dict(v2.ACTION_DEFINITIONS[action_id]["effects"])
    success = {k: round(v * 1.25, 2) for k, v in base_effects.items()}
    failure = {k: round(-v * 0.65, 2) for k, v in base_effects.items()}
    # targeted systemic failures
    if action_id in {"grain_distribution", "smuggle_relief", "rationing"}:
        failure["food"] = round(failure.get("food", 0.0) - 4.0 - pressures.get("food_stress", 0.0) * 4.0, 2)
    if action_id in {"purify_miasma", "seal_rift"}:
        failure["miasma_level"] = round(failure.get("miasma_level", 0.0) + 3.0, 2)
    if action_id == "spread_miasma":
        success["miasma_level"] = round(success.get("miasma_level", 0.0) + 3.0, 2)
    return success, failure


def build_action_quest(world: WorldState, decision: Dict[str, Any], season_key: str, rng: random.Random, quest_index: int, ext: ExtendedWorldState) -> QuestOffer:
    fl = faction_lookup(world)
    issuer = fl[decision["faction_id"]]
    region = region_lookup(world)[decision["target_region"]]
    pressures = compute_pressures(region)
    counterpart = None
    nearby = affected_factions_for_action(world, issuer, region.region_id)
    if nearby:
        # choose strongest relation movement target or nearest hostile/cooperative counterpart
        candidates = []
        for other in nearby:
            rel = relation_for_pair(ext, issuer.faction_id, other.faction_id)
            proximity = 1.0 if region.region_id in other.regions else 0.7
            score = abs(rel.last_delta) + abs(rel.score) / 40.0 + proximity
            candidates.append((score, other))
        counterpart = sorted(candidates, key=lambda x: x[0], reverse=True)[0][1]

    vector = choose_micro_vector(world, issuer.dominant_race, decision["action_id"], region, pressures, rng)
    base_type, objective_tags, mood = ACTION_TO_QUEST[decision["action_id"]]
    quest_type = quest_type_for_vector(vector, decision["action_id"])
    title = build_action_quest_title(decision["action_id"], vector, region_name(world, region.region_id), counterpart.label_ja if counterpart else None, rng)
    summary = build_action_quest_summary(world, issuer, decision, region, vector, counterpart, pressures)
    top_pressure = max(pressures.values()) if pressures else 0.0
    urgency = round(clamp(40 + decision["score"] * 12 + top_pressure * 28, 0, 100), 2)
    difficulty = round(clamp(30 + len(objective_tags) * 5 + top_pressure * 30 + (12 if counterpart else 0), 0, 100), 2)
    success, failure = build_success_failure_effects(decision["action_id"], region, pressures)
    impact = estimate_impact_projection(world, region, decision["action_id"], urgency, counterpart)
    pressure_hooks = top_pressure_tags(pressures, k=3)
    vector_tags = infer_vector_tags(vector)
    combined_objectives = list(dict.fromkeys(objective_tags + vector_tags + [decision["action_id"], base_type, quest_type]))
    return QuestOffer(
        quest_id=f"q_{season_key}_{quest_index:03d}",
        season_key=season_key,
        source_kind="action",
        quest_type=quest_type,
        title_ja=title,
        summary_ja=summary,
        issuer_faction_id=issuer.faction_id,
        issuer_faction_name=issuer.label_ja,
        issuer_race=issuer.dominant_race,
        region_id=region.region_id,
        region_name_ja=region_name(world, region.region_id),
        counterparty_faction_id=counterpart.faction_id if counterpart else None,
        counterparty_faction_name=counterpart.label_ja if counterpart else None,
        counterparty_race=counterpart.dominant_race if counterpart else None,
        urgency=urgency,
        difficulty=difficulty,
        objective_tags=combined_objectives,
        race_hooks=[vector],
        pressure_hooks=pressure_hooks,
        dialogue_mood=mood + (["敵意"] if counterpart and relation_for_pair(ext, issuer.faction_id, counterpart.faction_id).score < -25 else []),
        impact_projection=impact,
        potential_success_effects=success,
        potential_failure_effects=failure,
        provenance={
            "action_id": decision["action_id"],
            "decision_score": decision["score"],
            "vector_tags": vector_tags,
        },
    )


def build_diplomacy_event_label(rel: DiplomacyRelation, a: GeneratedFaction, b: GeneratedFaction) -> str:
    if rel.status in {"盟約", "協調"} and "trade_channel" in rel.tags:
        return "交易盟約"
    if rel.status in {"盟約", "協調"} and "doctrine_overlap" in rel.tags:
        return "共同巡礼協定"
    if rel.status in {"敵対", "戦争前夜"} and "theological_tension" in rel.tags:
        return "宗派抗争"
    if rel.status in {"敵対", "戦争前夜"} and "border_contact" in rel.tags:
        return "境界衝突"
    if "demon_domain" in {a.faction_type, b.faction_type}:
        return "浄化戦線"
    return "勢力均衡の変化"


def build_diplomacy_quest(world: WorldState, rel: DiplomacyRelation, season_key: str, rng: random.Random, quest_index: int) -> QuestOffer:
    fl = faction_lookup(world)
    a = fl[rel.faction_a]
    b = fl[rel.faction_b]
    host = a if a.legitimacy >= b.legitimacy else b
    other = b if host is a else a
    region_candidates = rel.shared_regions or rel.border_regions or host.regions or other.regions
    rid = region_candidates[0]
    region = region_lookup(world)[rid]
    pressures = compute_pressures(region)

    hostile = rel.score <= -35
    vector_source_race = host.dominant_race if hostile else other.dominant_race
    vector = choose_micro_vector(world, vector_source_race, "inquisition" if rel.axes["theology"] >= rel.axes["trade"] else "grain_distribution", region, pressures, rng)

    if hostile:
        quest_type = "仲裁" if rel.axes["theology"] < 0.45 else "停戦交渉"
        title = rng.choice([
            f"{region_name(world, rid)}の停戦書",
            f"{region_name(world, rid)}の裂けた盟札",
            f"{a.label_ja}と{b.label_ja}の境界火種",
        ])
        summary = (
            f"{build_diplomacy_event_label(rel, a, b)}が {region_name(world, rid)} で現実化しつつある。"
            f" 発端には {vector} があり、{host.label_ja} と {other.label_ja} の双方が譲歩の代償を計っている。"
            f" 放置すれば、局地争いは季節のうちに制度や信仰へ燃え移る。"
        )
        success = {"legitimacy": 4.0, "law_order": 3.0, "racial_tension": -4.0, "trade_routes": 2.0}
        failure = {"legitimacy": -4.0, "law_order": -3.0, "racial_tension": 5.0, "miasma_level": 2.0}
        mood = ["緊迫", "不信", "疲弊"]
    else:
        quest_type = "共同事業"
        title = rng.choice([
            f"{region_name(world, rid)}の共同勅許",
            f"{a.label_ja}と{b.label_ja}の合同行",
            f"{region_name(world, rid)}の二重印章",
        ])
        summary = (
            f"{build_diplomacy_event_label(rel, a, b)}が {region_name(world, rid)} で形を取り始めた。"
            f" だが裏では {vector} が約定の隙を探している。"
            f" 成功すれば {a.label_ja} と {b.label_ja} の関係は一段深まり、失敗すれば相互不信が残る。"
        )
        success = {"trade_routes": 4.0, "faith_density": 2.0, "law_order": 2.0}
        failure = {"legitimacy": -2.0, "trade_routes": -3.0, "faith_density": -1.0}
        mood = ["慎重", "期待", "駆け引き"]

    urgency = round(clamp(38 + abs(rel.score) * 0.45 + max(rel.axes.values()) * 26, 0, 100), 2)
    difficulty = round(clamp(35 + len(region_candidates) * 4 + rel.axes["territory"] * 26 + rel.axes["theology"] * 18, 0, 100), 2)
    impact = {
        "affected_population_estimate": int(region.values["population"] * (10 + urgency / 10.0)),
        "systems_affected_count": 3,
        "impact_tier": "regional" if urgency >= 65 else "local",
        "possible_media": {"制度": 0.3, "伝承": 0.3, "正史": 0.2},
        "existence_grade_hint": round(0.22 + urgency / 120.0 + (0.15 if hostile else 0.08), 3),
    }

    return QuestOffer(
        quest_id=f"q_{season_key}_{quest_index:03d}",
        season_key=season_key,
        source_kind="diplomacy",
        quest_type=quest_type,
        title_ja=title,
        summary_ja=summary,
        issuer_faction_id=host.faction_id,
        issuer_faction_name=host.label_ja,
        issuer_race=host.dominant_race,
        region_id=rid,
        region_name_ja=region_name(world, rid),
        counterparty_faction_id=other.faction_id,
        counterparty_faction_name=other.label_ja,
        counterparty_race=other.dominant_race,
        urgency=urgency,
        difficulty=difficulty,
        objective_tags=[quest_type, build_diplomacy_event_label(rel, a, b), *infer_vector_tags(vector)],
        race_hooks=[vector],
        pressure_hooks=top_pressure_tags(pressures, 2),
        dialogue_mood=mood,
        impact_projection=impact,
        potential_success_effects=success,
        potential_failure_effects=failure,
        provenance={
            "relation_id": rel.relation_id,
            "relation_status": rel.status,
            "relation_score": rel.score,
        },
    )


def build_era_quest(world: WorldState, season_key: str, quest_index: int, rng: random.Random) -> Optional[QuestOffer]:
    if not world.world_era:
        return None
    driver = world.world_era["driver"]
    coverage = world.world_era.get("coverage_ratio", 0.0)
    if coverage < 0.35:
        return None
    var, op = driver
    candidate_regions = []
    for region in world.regions:
        pressures = compute_pressures(region)
        relevant = {
            ("food", "scarcity"): pressures.get("food_stress", 0.0),
            ("mana_level", "surplus"): pressures.get("mana_surge", 0.0),
            ("mana_level", "scarcity"): pressures.get("mana_crisis", 0.0),
            ("miasma_level", "surplus"): pressures.get("miasma_bloom", 0.0),
            ("dungeon_density", "fixation"): pressures.get("dungeon_fixation", 0.0),
            ("interworld_intrusion", "runaway"): pressures.get("interworld_bleed", 0.0),
            ("legitimacy", "collapse"): pressures.get("legitimacy_crisis", 0.0),
            ("faith_density", "runaway"): pressures.get("faith_schism", 0.0),
        }
        candidate_regions.append((relevant.get((var, op), 0.0), region))
    candidate_regions.sort(key=lambda x: x[0], reverse=True)
    pressure, region = candidate_regions[0]
    if pressure < 0.35:
        return None

    title_map = {
        ("food", "scarcity"): [f"{region_name(world, region.region_id)}の最後の種子", f"{region_name(world, region.region_id)}の灰麦台帳"],
        ("mana_level", "surplus"): [f"{region_name(world, region.region_id)}の溢れた星脈", f"{region_name(world, region.region_id)}の夢潮防壁"],
        ("mana_level", "scarcity"): [f"{region_name(world, region.region_id)}の枯れた灯", f"{region_name(world, region.region_id)}の失われた術路"],
        ("miasma_level", "surplus"): [f"{region_name(world, region.region_id)}の胞子炉", f"{region_name(world, region.region_id)}の黒潮井"],
        ("dungeon_density", "fixation"): [f"{region_name(world, region.region_id)}の閉じない深層", f"{region_name(world, region.region_id)}の穴守り"] ,
        ("interworld_intrusion", "runaway"): [f"{region_name(world, region.region_id)}の薄い境", f"{region_name(world, region.region_id)}の帰らぬ門"] ,
        ("legitimacy", "collapse"): [f"{region_name(world, region.region_id)}の空位詔", f"{region_name(world, region.region_id)}の裂けた冠"] ,
        ("faith_density", "runaway"): [f"{region_name(world, region.region_id)}の逆光巡礼", f"{region_name(world, region.region_id)}の二つの祭壇"] ,
    }
    summary_map = {
        ("food", "scarcity"): "飢えは一地方の問題ではなくなった。倉は空き、数季先の播種すら脅かされている。いま手を打てば制度が残り、遅れれば民は神話化された飢えだけを覚える。",
        ("mana_level", "surplus"): "星脈が膨らみ、祝福と事故の境が薄れている。術師も神官も恩恵を語るが、過剰は必ず裂け目を呼ぶ。",
        ("mana_level", "scarcity"): "術路は痩せ、癒しも灯も値を上げた。文明の骨組みそのものが摩耗し、古い炉や井戸の価値が跳ね上がっている。",
        ("miasma_level", "surplus"): "瘴気は風景ではなく制度を侵し始めた。人は住居を捨て、税と軍制は感染に合わせて書き換わる。",
        ("dungeon_density", "fixation"): "深層はもはや局地的な危険ではない。戻らぬ探索と遺物流通が、政治と信仰の両方に口を出し始めている。",
        ("interworld_intrusion", "runaway"): "境界が薄れ、異界由来のものが交易品と災厄の両方として流れ込む。封鎖も開放も、どちらも代償が大きい。",
        ("legitimacy", "collapse"): "冠と法が軽くなり、声の大きい者ほど真実を名乗る。いま必要なのは勝者ではなく、次の季節を受け止める形式だ。",
        ("faith_density", "runaway"): "祈りは秩序にも刃にもなる。相反する神託が都市を二分し、正統と異端の線は日ごとに引き直されている。",
    }
    common_name = None
    if world.world_era.get("names"):
        common_name = world.world_era["names"].get("common")
    title = rng.choice(title_map.get((var, op), [f"{region_name(world, region.region_id)}の時代傷"]))
    summary = f"{common_name or world.main_god_name + '暦'}の只中で、{summary_map.get((var, op), '世界そのものが軋んでいる。')}"
    urgency = round(clamp(55 + coverage * 30 + pressure * 20, 0, 100), 2)
    difficulty = round(clamp(60 + coverage * 20 + pressure * 20, 0, 100), 2)
    return QuestOffer(
        quest_id=f"q_{season_key}_{quest_index:03d}",
        season_key=season_key,
        source_kind="era",
        quest_type="時代介入",
        title_ja=title,
        summary_ja=summary,
        issuer_faction_id="world",
        issuer_faction_name="世界そのもの",
        issuer_race="none",
        region_id=region.region_id,
        region_name_ja=region_name(world, region.region_id),
        urgency=urgency,
        difficulty=difficulty,
        objective_tags=["Era", var, op, world.world_era.get("names", {}).get("official", "時代")],
        race_hooks=[],
        pressure_hooks=[var, op],
        dialogue_mood=["宿命", "巨視", "不吉"],
        impact_projection={
            "affected_population_estimate": int(avg([r.values["population"] for r in world.regions], 50.0) * len(world.regions) * (8 + coverage * 6)),
            "systems_affected_count": 5,
            "impact_tier": "meta",
            "possible_media": {"正史": 0.5, "制度": 0.4, "信仰": 0.4, "魂": 0.2},
            "existence_grade_hint": round(0.55 + coverage * 0.4, 3),
        },
        potential_success_effects={var: 6.0 if op in {"scarcity", "collapse"} else -6.0, "cycle_stability": 4.0},
        potential_failure_effects={var: -6.0 if op in {"scarcity", "collapse"} else 6.0, "legitimacy": -4.0, "faith_density": 3.0 if var == "faith_density" else 0.0},
        provenance={"world_era": world.world_era},
    )


def sort_and_trim_quests(quests: List[QuestOffer], limit: int) -> List[QuestOffer]:
    quests.sort(key=lambda q: (q.urgency * 0.65 + q.difficulty * 0.25 + q.impact_projection.get("existence_grade_hint", 0.0) * 40.0), reverse=True)
    return quests[:limit]


def generate_quests(ext: ExtendedWorldState, season_result: Dict[str, Any], budget: int = 12) -> List[QuestOffer]:
    world = ext.world
    rng = random.Random(world.seed * 1009 + world.calendar_year * 37 + world.season_index * 7 + len(world.history))
    season_key = f"{world.calendar_year:04d}_s{world.season_index}"
    quests: List[QuestOffer] = []
    qidx = 1

    for decision in season_result["decisions"]:
        quests.append(build_action_quest(world, decision, season_key, rng, qidx, ext))
        qidx += 1

    # diplomacy quests from strongest shifts / strongest tensions
    prominent_relations = sorted(
        ext.diplomacy.values(),
        key=lambda rel: (abs(rel.last_delta) * 1.5 + abs(rel.score) / 25.0 + max(rel.axes.values())),
        reverse=True,
    )
    for rel in prominent_relations[: max(3, budget // 3)]:
        if abs(rel.last_delta) < 2.5 and abs(rel.score) < 32:
            continue
        quests.append(build_diplomacy_quest(world, rel, season_key, rng, qidx))
        qidx += 1

    era_quest = build_era_quest(world, season_key, qidx, rng)
    if era_quest is not None:
        quests.append(era_quest)

    return sort_and_trim_quests(quests, budget)


def advance_extended_world_one_season(ext: ExtendedWorldState, quest_budget: int = 12) -> Dict[str, Any]:
    # let the base world act first
    season_result = v2.advance_world_one_season(ext.world)

    # diplomacy baseline from new state, then action drift from recorded decisions
    baseline_events = apply_baseline_diplomacy_drift(ext)
    action_events = apply_action_diplomacy(ext, season_result["decisions"], season_result["pressures"])
    quests = generate_quests(ext, season_result, budget=quest_budget)
    ext.active_quests = quests

    season_record = {
        "calendar_year": ext.world.calendar_year,
        "season_index": ext.world.season_index,
        "world_era": ext.world.world_era,
        "baseline_events": baseline_events,
        "action_events": action_events,
        "quest_ids": [q.quest_id for q in quests],
        "top_relations": [
            {
                "relation_id": r.relation_id,
                "score": r.score,
                "status": r.status,
                "last_delta": r.last_delta,
                "factions": [r.faction_a, r.faction_b],
            }
            for r in sorted(ext.diplomacy.values(), key=lambda x: abs(x.score), reverse=True)[:10]
        ],
    }
    ext.diplomacy_history.append(season_record)
    ext.quest_history.append({
        "calendar_year": ext.world.calendar_year,
        "season_index": ext.world.season_index,
        "quests": [asdict(q) for q in quests],
    })
    return {
        **season_result,
        "diplomacy_events": baseline_events + action_events,
        "quests": [asdict(q) for q in quests],
    }


def export_diplomacy(ext: ExtendedWorldState) -> Dict[str, Any]:
    out = {}
    for rel_id, rel in ext.diplomacy.items():
        out[rel_id] = round_obj(asdict(rel), 3)
    return out


def export_extended_world(ext: ExtendedWorldState) -> Dict[str, Any]:
    return {
        "base_world": export_world_base(ext.world),
        "diplomacy": export_diplomacy(ext),
        "active_quests": [round_obj(asdict(q), 3) for q in ext.active_quests],
        "diplomacy_history": round_obj(ext.diplomacy_history, 3),
        "quest_history": round_obj(ext.quest_history, 3),
    }


def summarize_extended_world(ext: ExtendedWorldState) -> str:
    world = ext.world
    lines: List[str] = []
    lines.append(f"# PBW Diplomacy + Quest Summary")
    lines.append("")
    lines.append(f"- 世界名: **{world.world_name}**")
    lines.append(f"- 暦: **{world.calendar_name} {world.calendar_year}年**")
    if world.world_era and world.world_era.get("names"):
        lines.append(f"- 現在Era: **{world.world_era['names'].get('official','無名時代')}** / 民間名 **{world.world_era['names'].get('common','呼称なし')}**")
    else:
        lines.append(f"- 現在Era: **未成立**")
    lines.append(f"- 勢力数: **{len(world.factions)}**")
    lines.append(f"- 外交関係数: **{len(ext.diplomacy)}**")
    lines.append(f"- 現在クエスト件数: **{len(ext.active_quests)}**")
    lines.append("")
    lines.append("## 緊張の高い関係")
    lines.append("")
    for rel in sorted(ext.diplomacy.values(), key=lambda r: r.score)[:8]:
        fl = faction_lookup(world)
        a = fl[rel.faction_a]
        b = fl[rel.faction_b]
        lines.append(f"- {a.label_ja} ↔ {b.label_ja}: score={rel.score:.1f} / {rel.status} / tags={', '.join(rel.tags[:3])}")
    lines.append("")
    lines.append("## 協調の強い関係")
    lines.append("")
    for rel in sorted(ext.diplomacy.values(), key=lambda r: r.score, reverse=True)[:8]:
        fl = faction_lookup(world)
        a = fl[rel.faction_a]
        b = fl[rel.faction_b]
        lines.append(f"- {a.label_ja} ↔ {b.label_ja}: score={rel.score:.1f} / {rel.status} / tags={', '.join(rel.tags[:3])}")
    lines.append("")
    lines.append("## 現在クエスト上位")
    lines.append("")
    for q in ext.active_quests[:10]:
        lines.append(f"- **{q.title_ja}** ({q.source_kind}/{q.quest_type}) @ {q.region_name_ja} | issuer={q.issuer_faction_name} | urgency={q.urgency:.1f} | diff={q.difficulty:.1f}")
        lines.append(f"  - {q.summary_ja}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="PBW diplomacy + quest generator v3")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--regions", type=int, default=20)
    parser.add_argument("--seasons", type=int, default=6)
    parser.add_argument("--quests", type=int, default=12)
    parser.add_argument("--schema", type=Path, default=v2.DEFAULT_SCHEMA_PATH)
    parser.add_argument("--out", type=Path, default=BASE_DIR / "pbw_generated_world_seed1729_v2_diplomacy_quests.json")
    parser.add_argument("--summary-out", type=Path, default=BASE_DIR / "pbw_generated_world_seed1729_v2_diplomacy_quests_summary.md")
    args = parser.parse_args()

    ext = build_extended_world(args.seed, args.regions, args.schema)
    for _ in range(args.seasons):
        advance_extended_world_one_season(ext, quest_budget=args.quests)

    args.out.write_text(json.dumps(export_extended_world(ext), ensure_ascii=False, indent=2), encoding="utf-8")
    args.summary_out.write_text(summarize_extended_world(ext), encoding="utf-8")


if __name__ == "__main__":
    main()
