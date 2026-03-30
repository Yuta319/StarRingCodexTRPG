
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBW World Historical Node Layer v7

条項違反・制度破綻を、専用の世界史事件ノードへ昇格させる層。
standalone で動くサンプル実装。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
import json
import math
import random
import hashlib


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def deterministic_noise(seed: int, *parts: object, span: float = 6.0) -> float:
    raw = "::".join([str(seed)] + [str(p) for p in parts]).encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return (n - 0.5) * 2 * span


@dataclass
class RegionState:
    region_id: str
    label_ja: str
    biome: str
    dominant_race: str
    values: Dict[str, float]
    adjacency: List[str] = field(default_factory=list)
    local_tags: List[str] = field(default_factory=list)


@dataclass
class FactionState:
    faction_id: str
    label_ja: str
    faction_type: str
    dominant_race: str
    regions: List[str]
    legitimacy: float
    militarization: float
    treasury: float
    zeal: float
    doctrine_tags: List[str] = field(default_factory=list)


@dataclass
class TreatyClause:
    clause_id: str
    clause_kind: str
    label_ja: str
    support: float = 60.0
    strain: float = 0.0
    intensity: float = 50.0
    status: str = "active"  # active / strained / violated / collapsed
    last_tension: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass
class InstitutionState:
    institution_id: str
    institution_kind: str
    label_ja: str
    party_a: str
    party_b: str
    support: float
    breach_risk: float
    age_seasons: int = 0
    status: str = "active"  # active / strained / broken
    clauses: List[TreatyClause] = field(default_factory=list)
    terms: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestOffer:
    quest_id: str
    title: str
    source_kind: str
    issuer_faction_id: Optional[str]
    counterparty_faction_id: Optional[str]
    region_id: Optional[str]
    node_id: str
    urgency: float
    difficulty: float
    recommended_vectors: List[str]
    race_hooks: List[str]
    pressure_hooks: List[str]
    dialogue_mood: str
    success_effects: Dict[str, float]
    failure_effects: Dict[str, float]
    projected_media: List[str]


@dataclass
class HistoricalEventNode:
    node_id: str
    node_type: str
    event_family: str
    title: str
    description: str
    severity: float
    urgency: float
    source_institution_id: Optional[str]
    source_clause_id: Optional[str]
    factions: List[str]
    regions: List[str]
    promoted_from: str
    chain_id: Optional[str] = None
    stage: int = 1
    status: str = "active"  # active / cooling / merged / resolved
    era_impetus: Dict[str, float] = field(default_factory=dict)
    quest_offers: List[QuestOffer] = field(default_factory=list)
    projected_legacies: List[str] = field(default_factory=list)


@dataclass
class EventChain:
    chain_id: str
    family: str
    label_ja: str
    factions: List[str]
    regions: List[str]
    stage: int = 1
    cumulative_severity: float = 0.0
    active_nodes: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)


@dataclass
class WorldState:
    seed: int
    world_name: str
    calendar_name: str
    calendar_year: int
    season_index: int
    main_god_name: str
    current_world_era: str
    regions: Dict[str, RegionState]
    factions: Dict[str, FactionState]
    institutions: Dict[str, InstitutionState]
    active_nodes: Dict[str, HistoricalEventNode] = field(default_factory=dict)
    chains: Dict[str, EventChain] = field(default_factory=dict)
    history_log: List[Dict[str, Any]] = field(default_factory=list)


RACES = [
    "human", "elf", "dwarf", "werebeast", "birdfolk", "fishfolk",
    "dragonewt", "fey", "demonian", "fallen", "plantfolk", "gemfolk"
]

CLAUSE_LABELS = {
    "grain_tariff_relief": "穀物関税軽減",
    "grain_quota": "主食供給割当",
    "pilgrimage_route_protection": "巡礼路保護",
    "joint_mining_rights": "共同採掘権",
    "joint_delving_recovery": "共同深層回収",
    "river_passage_rights": "河川通行権",
    "dynastic_marriage": "婚姻同盟",
    "demilitarized_border": "非武装境界",
    "war_reparation": "戦後賠償",
    "prisoner_exchange": "捕虜交換",
    "refugee_corridor": "難民回廊",
    "joint_sealing_duty": "共同封印義務",
    "sacred_relic_custody": "聖遺物保管",
    "hostage_exchange": "人質交換",
    "tribute_delivery": "朝貢納付"
}

INSTITUTION_LABELS = {
    "trade_compact": "通商盟約",
    "religious_concord": "宗教同盟",
    "non_aggression_pact": "相互不可侵条約",
    "defense_alliance": "防衛同盟",
    "truce": "停戦条約",
    "war": "戦争状態",
    "holy_war": "聖戦布告",
    "blockade": "封鎖令",
    "tributary_compact": "属国化盟約"
}

EVENT_FAMILY_LABELS = {
    "food_crisis": "食糧危機連鎖",
    "pilgrimage_conflict": "巡礼路紛争連鎖",
    "mining_conflict": "採掘利権紛争",
    "deep_delving_conflict": "深層利権紛争",
    "succession_conflict": "継承連鎖",
    "frontier_militarization": "境界軍事化連鎖",
    "religious_schism": "宗教分裂連鎖",
    "tributary_revolt": "属国反乱連鎖",
    "hostage_breakdown": "人質外交破綻連鎖",
    "relic_dispute": "聖遺物争奪連鎖",
    "institutional_breakdown": "制度崩落連鎖"
}


def build_sample_world(seed: int = 1729) -> WorldState:
    rng = random.Random(seed)

    regions = {
        "north_granary": RegionState(
            "north_granary", "北穀州", "plains", "human",
            {
                "food": 72, "housing": 58, "law_order": 49, "legitimacy": 52,
                "faith_density": 41, "trade_routes": 63, "mana_level": 46, "miasma_level": 22,
                "succession_stability": 38, "racial_tension": 31
            },
            adjacency=["river_gate", "ash_frontier"], local_tags=["granary", "borderland"]
        ),
        "river_gate": RegionState(
            "river_gate", "川門州", "river", "fishfolk",
            {
                "food": 57, "housing": 61, "law_order": 54, "legitimacy": 59,
                "faith_density": 48, "trade_routes": 78, "mana_level": 50, "miasma_level": 18,
                "succession_stability": 56, "racial_tension": 28
            },
            adjacency=["north_granary", "white_shrine", "deep_mouth"], local_tags=["port", "river"]
        ),
        "white_shrine": RegionState(
            "white_shrine", "白祠圏", "highland", "birdfolk",
            {
                "food": 46, "housing": 53, "law_order": 57, "legitimacy": 63,
                "faith_density": 74, "trade_routes": 45, "mana_level": 55, "miasma_level": 16,
                "succession_stability": 60, "racial_tension": 24
            },
            adjacency=["river_gate", "seal_marsh"], local_tags=["shrine", "pilgrimage"]
        ),
        "deep_mouth": RegionState(
            "deep_mouth", "深口盆地", "cavern", "dwarf",
            {
                "food": 38, "housing": 47, "law_order": 43, "legitimacy": 46,
                "faith_density": 29, "trade_routes": 51, "mana_level": 42, "miasma_level": 58,
                "succession_stability": 44, "racial_tension": 39
            },
            adjacency=["river_gate", "ash_frontier"], local_tags=["mine", "dungeon"]
        ),
        "ash_frontier": RegionState(
            "ash_frontier", "灰縁辺州", "ashlands", "dragonewt",
            {
                "food": 32, "housing": 35, "law_order": 33, "legitimacy": 41,
                "faith_density": 37, "trade_routes": 29, "mana_level": 48, "miasma_level": 66,
                "succession_stability": 34, "racial_tension": 52
            },
            adjacency=["north_granary", "deep_mouth", "seal_marsh"], local_tags=["frontier", "warzone"]
        ),
        "seal_marsh": RegionState(
            "seal_marsh", "封泥湿域", "marsh", "plantfolk",
            {
                "food": 44, "housing": 41, "law_order": 39, "legitimacy": 36,
                "faith_density": 58, "trade_routes": 22, "mana_level": 62, "miasma_level": 61,
                "succession_stability": 47, "racial_tension": 36
            },
            adjacency=["white_shrine", "ash_frontier"], local_tags=["rift", "sealing", "marsh"]
        ),
    }

    factions = {
        "kingdom": FactionState("kingdom", "穀冠王国", "state", "human", ["north_granary", "river_gate"], 58, 47, 54, 42, ["order", "grain", "law"]),
        "shrine_synod": FactionState("shrine_synod", "白祠宗務会", "religion", "birdfolk", ["white_shrine"], 65, 34, 36, 77, ["light", "pilgrimage", "purity"]),
        "miners_compact": FactionState("miners_compact", "黒鎚採鉱盟", "guild", "dwarf", ["deep_mouth"], 43, 29, 57, 22, ["mining", "delve", "metal"]),
        "march_clans": FactionState("march_clans", "灰縁侯族", "state", "dragonewt", ["ash_frontier"], 41, 63, 33, 49, ["frontier", "martial", "blood"]),
        "mire_circle": FactionState("mire_circle", "封泥環", "religion", "plantfolk", ["seal_marsh"], 39, 25, 28, 69, ["sealing", "healing", "marsh"]),
        "demon_domain": FactionState("demon_domain", "瘴冠魔域", "demon_domain", "demonian", ["ash_frontier", "seal_marsh"], 26, 68, 41, 61, ["miasma", "dark", "infiltration"]),
    }

    institutions = {}

    def mk_clause(kind: str, support: float, strain: float = 0.0, intensity: float = 50.0) -> TreatyClause:
        clause_id = f"cl_{kind}_{abs(hash((kind, support, intensity))) % 99999:05d}"
        return TreatyClause(clause_id, kind, CLAUSE_LABELS[kind], support=support, strain=strain, intensity=intensity)

    institutions["inst_trade_01"] = InstitutionState(
        "inst_trade_01", "trade_compact", "穀冠王国＝黒鎚採鉱盟通商盟約", "kingdom", "miners_compact", 61, 25, clauses=[
            mk_clause("grain_tariff_relief", 58, 8, 62),
            mk_clause("joint_mining_rights", 55, 12, 56),
            mk_clause("river_passage_rights", 64, 5, 54),
            mk_clause("joint_delving_recovery", 46, 18, 59),
        ]
    )
    institutions["inst_pilgrim_01"] = InstitutionState(
        "inst_pilgrim_01", "religious_concord", "白祠宗務会＝封泥環宗教同盟", "shrine_synod", "mire_circle", 66, 19, clauses=[
            mk_clause("pilgrimage_route_protection", 62, 7, 71),
            mk_clause("joint_sealing_duty", 57, 11, 68),
            mk_clause("sacred_relic_custody", 53, 12, 65),
        ]
    )
    institutions["inst_border_01"] = InstitutionState(
        "inst_border_01", "non_aggression_pact", "穀冠王国＝灰縁侯族不可侵条約", "kingdom", "march_clans", 49, 31, clauses=[
            mk_clause("demilitarized_border", 44, 21, 67),
            mk_clause("hostage_exchange", 57, 11, 54),
            mk_clause("dynastic_marriage", 42, 16, 52),
        ]
    )
    institutions["inst_tributary_01"] = InstitutionState(
        "inst_tributary_01", "tributary_compact", "灰縁侯族＝瘴冠魔域属国化盟約", "march_clans", "demon_domain", 43, 37, clauses=[
            mk_clause("tribute_delivery", 37, 23, 63),
            mk_clause("hostage_exchange", 41, 20, 58),
        ]
    )
    institutions["inst_blockade_01"] = InstitutionState(
        "inst_blockade_01", "blockade", "白祠宗務会＝瘴冠魔域封鎖令", "shrine_synod", "demon_domain", 55, 27, clauses=[
            mk_clause("refugee_corridor", 39, 22, 55),
            mk_clause("war_reparation", 0, 0, 0),
        ]
    )
    institutions["inst_holywar_01"] = InstitutionState(
        "inst_holywar_01", "holy_war", "白祠宗務会＝瘴冠魔域聖戦布告", "shrine_synod", "demon_domain", 52, 35, clauses=[
            mk_clause("prisoner_exchange", 33, 20, 48),
            mk_clause("sacred_relic_custody", 29, 26, 66),
        ]
    )

    world = WorldState(
        seed=seed,
        world_name="霧環連界",
        calendar_name="ラレイナ暦",
        calendar_year=168,
        season_index=0,
        main_god_name="ラレイナ",
        current_world_era="瘴潮期",
        regions=regions,
        factions=factions,
        institutions=institutions,
    )
    world.history_log.append({
        "season": 0,
        "year": world.calendar_year,
        "entry": "seed world initialized"
    })
    return world


def region_pressure_snapshot(region: RegionState) -> Dict[str, float]:
    v = region.values
    food_stress = clamp(100 - v["food"])
    law_break = clamp(100 - v["law_order"])
    faith_schism = clamp(v["faith_density"] * 0.6 + v["racial_tension"] * 0.4 - v["legitimacy"] * 0.2)
    succession_crisis = clamp(100 - v["succession_stability"])
    frontier_violence = clamp(v["racial_tension"] * 0.45 + (100 - v["law_order"]) * 0.35 + v["miasma_level"] * 0.25)
    miasma_pressure = clamp(v["miasma_level"] * 0.9 - v["mana_level"] * 0.15)
    trade_distress = clamp(100 - v["trade_routes"])
    return {
        "food_stress": food_stress,
        "law_break": law_break,
        "faith_schism": faith_schism,
        "succession_crisis": succession_crisis,
        "frontier_violence": frontier_violence,
        "miasma_pressure": miasma_pressure,
        "trade_distress": trade_distress,
    }


def faction_pair_context(world: WorldState, inst: InstitutionState) -> Dict[str, float]:
    fa = world.factions[inst.party_a]
    fb = world.factions[inst.party_b]
    regions = [world.regions[rid] for rid in set(fa.regions + fb.regions)]
    pressures = [region_pressure_snapshot(r) for r in regions]
    return {
        "mean_food_stress": mean([p["food_stress"] for p in pressures]),
        "mean_law_break": mean([p["law_break"] for p in pressures]),
        "mean_faith_schism": mean([p["faith_schism"] for p in pressures]),
        "mean_trade_distress": mean([p["trade_distress"] for p in pressures]),
        "mean_frontier_violence": mean([p["frontier_violence"] for p in pressures]),
        "mean_miasma_pressure": mean([p["miasma_pressure"] for p in pressures]),
        "mean_succession_crisis": mean([p["succession_crisis"] for p in pressures]),
        "mean_legitimacy": mean([fa.legitimacy, fb.legitimacy]),
        "power_gap": abs((fa.militarization + fa.treasury) - (fb.militarization + fb.treasury)),
        "zeal_mean": mean([fa.zeal, fb.zeal]),
    }


def seasonal_drift(world: WorldState) -> None:
    """簡易な世界側自走。"""
    s = world.season_index
    for region in world.regions.values():
        p = region_pressure_snapshot(region)
        # 飢えと瘴気の世界
        region.values["food"] = clamp(region.values["food"] - 2 + deterministic_noise(world.seed, region.region_id, s, "food", span=2.5))
        region.values["trade_routes"] = clamp(region.values["trade_routes"] - 1 + deterministic_noise(world.seed, region.region_id, s, "trade", span=2.2))
        region.values["miasma_level"] = clamp(region.values["miasma_level"] + 1.4 + deterministic_noise(world.seed, region.region_id, s, "miasma", span=2.0))
        region.values["law_order"] = clamp(region.values["law_order"] - 0.8 + deterministic_noise(world.seed, region.region_id, s, "law", span=2.0))
        if "pilgrimage" in region.local_tags:
            region.values["faith_density"] = clamp(region.values["faith_density"] + 0.5)
        if "rift" in region.local_tags:
            region.values["miasma_level"] = clamp(region.values["miasma_level"] + 1.2)
        if "mine" in region.local_tags and p["miasma_pressure"] > 50:
            region.values["housing"] = clamp(region.values["housing"] - 1.3)

    for faction in world.factions.values():
        faction.legitimacy = clamp(faction.legitimacy + deterministic_noise(world.seed, faction.faction_id, s, "legitimacy", span=3.5))
        faction.treasury = clamp(faction.treasury + deterministic_noise(world.seed, faction.faction_id, s, "treasury", span=4.0))
        faction.militarization = clamp(faction.militarization + deterministic_noise(world.seed, faction.faction_id, s, "mil", span=3.5))
        if faction.faction_type == "demon_domain":
            faction.militarization = clamp(faction.militarization + 1.8)
            faction.zeal = clamp(faction.zeal + 1.0)
        if faction.faction_type == "religion":
            faction.zeal = clamp(faction.zeal + 0.7)

    world.calendar_year += 1
    world.season_index += 1


def clause_tension(world: WorldState, inst: InstitutionState, clause: TreatyClause) -> Tuple[float, List[str]]:
    ctx = faction_pair_context(world, inst)
    reasons: List[str] = []
    tension = 0.0

    if clause.clause_kind == "grain_tariff_relief":
        tension += ctx["mean_food_stress"] * 0.55 + ctx["mean_trade_distress"] * 0.25
        if ctx["mean_food_stress"] > 50:
            reasons.append("食糧圧迫が関税軽減の履行を難化")
    elif clause.clause_kind == "grain_quota":
        tension += ctx["mean_food_stress"] * 0.60 + ctx["power_gap"] * 0.15
        reasons.append("配給不足が供給割当を侵食")
    elif clause.clause_kind == "pilgrimage_route_protection":
        tension += ctx["mean_frontier_violence"] * 0.45 + ctx["mean_faith_schism"] * 0.35
        reasons.append("巡礼路で信仰摩擦と襲撃圧が増大")
    elif clause.clause_kind == "joint_mining_rights":
        tension += ctx["mean_trade_distress"] * 0.30 + ctx["mean_miasma_pressure"] * 0.35 + ctx["power_gap"] * 0.20
        reasons.append("鉱区利権と瘴気で共同採掘が不安定化")
    elif clause.clause_kind == "joint_delving_recovery":
        tension += ctx["mean_miasma_pressure"] * 0.45 + ctx["mean_frontier_violence"] * 0.25 + ctx["mean_trade_distress"] * 0.15
        reasons.append("深層回収で損耗と利権摩擦")
    elif clause.clause_kind == "river_passage_rights":
        tension += ctx["mean_trade_distress"] * 0.45 + ctx["mean_law_break"] * 0.20
        reasons.append("河川通行が交易不安と検問強化で詰まる")
    elif clause.clause_kind == "dynastic_marriage":
        tension += ctx["mean_succession_crisis"] * 0.50 + (100 - ctx["mean_legitimacy"]) * 0.20
        reasons.append("継承危機が婚姻同盟を不安定化")
    elif clause.clause_kind == "demilitarized_border":
        tension += ctx["mean_frontier_violence"] * 0.55 + ctx["power_gap"] * 0.20
        reasons.append("境界の軍事化が非武装条項を侵害")
    elif clause.clause_kind == "war_reparation":
        tension += (100 - ctx["mean_legitimacy"]) * 0.20 + ctx["mean_trade_distress"] * 0.35
        reasons.append("賠償負担が財政と民心を圧迫")
    elif clause.clause_kind == "prisoner_exchange":
        tension += ctx["mean_frontier_violence"] * 0.35 + ctx["mean_law_break"] * 0.25
        reasons.append("戦時不信が捕虜交換を遅延")
    elif clause.clause_kind == "refugee_corridor":
        tension += ctx["mean_frontier_violence"] * 0.35 + ctx["mean_food_stress"] * 0.25 + ctx["mean_law_break"] * 0.20
        reasons.append("難民回廊が襲撃・飢え・治安悪化で逼迫")
    elif clause.clause_kind == "joint_sealing_duty":
        tension += ctx["mean_miasma_pressure"] * 0.45 + ctx["mean_faith_schism"] * 0.20 + ctx["mean_trade_distress"] * 0.10
        reasons.append("封印義務が瘴気増大で過負荷")
    elif clause.clause_kind == "sacred_relic_custody":
        tension += ctx["mean_faith_schism"] * 0.50 + ctx["zeal_mean"] * 0.20
        reasons.append("聖遺物をめぐる信仰競合が先鋭化")
    elif clause.clause_kind == "hostage_exchange":
        tension += ctx["mean_succession_crisis"] * 0.30 + ctx["power_gap"] * 0.20 + ctx["mean_legitimacy"] * -0.1 + 18
        reasons.append("人質外交が継承不安と不信で軋む")
    elif clause.clause_kind == "tribute_delivery":
        tension += ctx["power_gap"] * 0.15 + ctx["mean_food_stress"] * 0.20 + ctx["mean_trade_distress"] * 0.25 + ctx["mean_law_break"] * 0.15 + 15
        reasons.append("朝貢履行が疲弊と密輸で崩れ始める")

    # clauseの状態で増幅
    tension += clause.strain * 0.55
    tension += (100 - clause.support) * 0.25
    tension += deterministic_noise(world.seed, world.calendar_year, inst.institution_id, clause.clause_id, span=4.0)
    tension = clamp(tension)

    return tension, reasons


def update_clause_states(world: WorldState) -> List[Tuple[str, str, float, List[str]]]:
    reports: List[Tuple[str, str, float, List[str]]] = []
    for inst in world.institutions.values():
        inst.age_seasons += 1
        clause_tensions: List[float] = []
        for clause in inst.clauses:
            tension, reasons = clause_tension(world, inst, clause)
            clause.last_tension = tension
            clause_tensions.append(tension)

            if tension >= 70:
                clause.status = "violated"
                clause.strain = clamp(clause.strain + 16)
                clause.support = clamp(clause.support - 12)
            elif tension >= 45:
                clause.status = "strained"
                clause.strain = clamp(clause.strain + 9)
                clause.support = clamp(clause.support - 4)
            else:
                clause.status = "active"
                clause.strain = clamp(clause.strain - 5)
                clause.support = clamp(clause.support + 2)

            if reasons:
                clause.notes = reasons[:3]
            reports.append((inst.institution_id, clause.clause_id, tension, reasons))

        if clause_tensions:
            inst.breach_risk = clamp(mean(clause_tensions) * 0.75 + len([c for c in inst.clauses if c.status == "violated"]) * 7)
            inst.support = clamp(mean([c.support for c in inst.clauses]))
            if inst.breach_risk >= 68:
                inst.status = "broken"
            elif inst.breach_risk >= 42:
                inst.status = "strained"
            else:
                inst.status = "active"

    return reports


def overlapping_regions(world: WorldState, inst: InstitutionState) -> List[str]:
    fa = world.factions[inst.party_a]
    fb = world.factions[inst.party_b]
    region_ids = list(dict.fromkeys(fa.regions + fb.regions))
    return region_ids


def node_title_for_clause(clause_kind: str, inst_kind: str) -> Tuple[str, str, str]:
    if clause_kind == "grain_tariff_relief":
        return "food_crisis", "穀価盟約違反", "穀物流通の約定違反が市場と配給を揺らしている。"
    if clause_kind == "grain_quota":
        return "food_crisis", "供給割当破綻", "主食割当が守られず、配給と徴発が衝突している。"
    if clause_kind == "pilgrimage_route_protection":
        return "pilgrimage_conflict", "巡礼路襲撃事件", "巡礼路保護条項が破れ、信徒と武装勢力が対立している。"
    if clause_kind == "joint_mining_rights":
        return "mining_conflict", "共同採掘権侵害", "共同採掘権が侵害され、鉱区と鍛工権をめぐる争いが始まった。"
    if clause_kind == "joint_delving_recovery":
        return "deep_delving_conflict", "共同深層回収破綻", "深層回収の取り分と死者処理をめぐり提携が崩れ始めている。"
    if clause_kind == "river_passage_rights":
        return "food_crisis", "河川通行権争議", "河川通行権の制限が輸送と検問の衝突を生んでいる。"
    if clause_kind == "dynastic_marriage":
        return "succession_conflict", "婚姻条約継承危機", "婚姻同盟が継承危機と正統性争いに巻き込まれている。"
    if clause_kind == "demilitarized_border":
        return "frontier_militarization", "非武装境界破り", "境界の軍事化により相互不可侵の根幹が崩れている。"
    if clause_kind == "war_reparation":
        return "institutional_breakdown", "賠償履行争議", "戦後賠償をめぐり再び封鎖と略奪が起こり始めた。"
    if clause_kind == "prisoner_exchange":
        return "institutional_breakdown", "捕虜交換破綻", "捕虜交換の停滞が停戦や聖戦の再燃を招いている。"
    if clause_kind == "refugee_corridor":
        return "food_crisis", "難民回廊封鎖", "難民回廊が襲撃と配給破綻で崩れかけている。"
    if clause_kind == "joint_sealing_duty":
        return "religious_schism", "共同封印義務逸脱", "封印義務の不履行が神官団と境界守の対立を激化させている。"
    if clause_kind == "sacred_relic_custody":
        return "relic_dispute", "聖遺物保管争奪", "聖遺物の保管権が信仰圏の境界そのものを揺らしている。"
    if clause_kind == "hostage_exchange":
        return "hostage_breakdown", "人質交換破綻", "人質外交の破断が報復と疑心を急速に広げている。"
    if clause_kind == "tribute_delivery":
        return "tributary_revolt", "朝貢納付拒絶", "朝貢停止が属国反乱と討伐動員の口実になりつつある。"
    # fallback
    return "institutional_breakdown", f"{CLAUSE_LABELS.get(clause_kind, clause_kind)}破綻", "条項の不履行が制度全体へ波及している。"


def era_impetus_from_family(family: str) -> Dict[str, float]:
    if family == "food_crisis":
        return {"food_shortage": 18, "trade_rupture": 12, "migration": 8}
    if family == "pilgrimage_conflict":
        return {"faith_violence": 16, "law_rupture": 8, "legitimacy": 6}
    if family == "mining_conflict":
        return {"resource_war": 14, "guild_friction": 10, "law_rupture": 6}
    if family == "deep_delving_conflict":
        return {"dungeon_activation": 16, "miasma_growth": 10, "guild_friction": 8}
    if family == "succession_conflict":
        return {"succession_crisis": 18, "legitimacy": 10}
    if family == "frontier_militarization":
        return {"border_war": 20, "racial_tension": 8}
    if family == "religious_schism":
        return {"faith_schism": 20, "divine_interference": 10}
    if family == "tributary_revolt":
        return {"state_collapse": 12, "border_war": 12, "class_conflict": 10}
    if family == "hostage_breakdown":
        return {"diplomatic_rupture": 18, "retaliation": 10}
    if family == "relic_dispute":
        return {"holy_war": 16, "faith_schism": 12}
    return {"institutional_breakdown": 18}


def projected_legacies_for_family(family: str) -> List[str]:
    mapping = {
        "food_crisis": ["制度", "伝承", "正史"],
        "pilgrimage_conflict": ["信仰", "伝承", "異端文書"],
        "mining_conflict": ["制度", "建築", "正史"],
        "deep_delving_conflict": ["魂", "伝承", "正史"],
        "succession_conflict": ["制度", "正史", "信仰"],
        "frontier_militarization": ["建築", "制度", "伝承"],
        "religious_schism": ["信仰", "異端文書", "伝承"],
        "tributary_revolt": ["制度", "正史", "伝承"],
        "hostage_breakdown": ["正史", "伝承"],
        "relic_dispute": ["信仰", "正史", "魂"],
        "institutional_breakdown": ["制度", "正史", "伝承"],
    }
    return mapping.get(family, ["制度", "伝承"])


def build_event_quest(node: HistoricalEventNode, world: WorldState) -> QuestOffer:
    family_vectors = {
        "food_crisis": ["stewardship", "diplomacy", "combat"],
        "pilgrimage_conflict": ["diplomacy", "ritual", "combat"],
        "mining_conflict": ["authority", "combat", "stewardship"],
        "deep_delving_conflict": ["combat", "ritual", "stealth"],
        "succession_conflict": ["authority", "diplomacy", "stealth"],
        "frontier_militarization": ["combat", "authority", "diplomacy"],
        "religious_schism": ["ritual", "diplomacy", "authority"],
        "tributary_revolt": ["combat", "diplomacy", "stewardship"],
        "hostage_breakdown": ["stealth", "diplomacy", "combat"],
        "relic_dispute": ["ritual", "stealth", "combat"],
        "institutional_breakdown": ["diplomacy", "stewardship", "authority"],
    }
    pressure_hooks = list(node.era_impetus.keys())
    race_hooks = [world.factions[fid].dominant_race for fid in node.factions if fid in world.factions]
    dialogue_mood = {
        "food_crisis": "切迫・疲弊・計算",
        "pilgrimage_conflict": "敬虔・疑念・抑えた怒気",
        "mining_conflict": "利害・不信・職人気質",
        "deep_delving_conflict": "利権・恐怖・秘匿",
        "succession_conflict": "儀礼・血統・不安",
        "frontier_militarization": "警戒・短気・命令",
        "religious_schism": "静かな断絶・反復・禁忌",
        "tributary_revolt": "屈辱・挑発・動員",
        "hostage_breakdown": "硬い沈黙・取引・焦り",
        "relic_dispute": "敬意・執着・冒涜恐怖",
        "institutional_breakdown": "冷えた実務・責任転嫁・保身",
    }[node.event_family]

    difficulty = clamp(node.severity * 0.82 + node.urgency * 0.28)
    success_effects = {
        "severity_drop": round(node.severity * 0.30, 1),
        "institution_breach_risk_drop": 8.0,
        "legitimacy_gain": 4.0
    }
    failure_effects = {
        "severity_rise": round(node.severity * 0.18, 1),
        "institution_breach_risk_rise": 9.0,
        "law_order_drop": 5.0
    }

    return QuestOffer(
        quest_id=f"hq_{node.node_id}",
        title=f"{node.title}への介入",
        source_kind="historical_node",
        issuer_faction_id=node.factions[0] if node.factions else None,
        counterparty_faction_id=node.factions[1] if len(node.factions) > 1 else None,
        region_id=node.regions[0] if node.regions else None,
        node_id=node.node_id,
        urgency=round(node.urgency, 1),
        difficulty=round(difficulty, 1),
        recommended_vectors=family_vectors[node.event_family],
        race_hooks=sorted(set(race_hooks)),
        pressure_hooks=pressure_hooks,
        dialogue_mood=dialogue_mood,
        success_effects=success_effects,
        failure_effects=failure_effects,
        projected_media=node.projected_legacies[:],
    )



def find_live_node_for_source(world: WorldState, source_institution_id: Optional[str], source_clause_id: Optional[str], family: str) -> Optional[HistoricalEventNode]:
    for node in world.active_nodes.values():
        if node.source_institution_id == source_institution_id and node.source_clause_id == source_clause_id and node.event_family == family and node.status in {"active", "cooling"}:
            return node
    return None


def maybe_promote_nodes(world: WorldState) -> List[HistoricalEventNode]:
    new_nodes: List[HistoricalEventNode] = []
    for inst in world.institutions.values():
        related_regions = overlapping_regions(world, inst)
        region_pressures = [region_pressure_snapshot(world.regions[rid]) for rid in related_regions]
        regional_scale = clamp(mean([
            p["food_stress"] * 0.15 + p["faith_schism"] * 0.15 + p["frontier_violence"] * 0.20 +
            p["trade_distress"] * 0.15 + p["miasma_pressure"] * 0.20 + p["succession_crisis"] * 0.15
            for p in region_pressures
        ]))
        for clause in inst.clauses:
            if clause.status != "violated":
                continue
            family, title, desc = node_title_for_clause(clause.clause_kind, inst.institution_kind)
            severity = clamp(clause.last_tension * 0.65 + inst.breach_risk * 0.30 + regional_scale * 0.35)
            urgency = clamp(clause.last_tension * 0.75 + inst.breach_risk * 0.20)
            existing = find_live_node_for_source(world, inst.institution_id, clause.clause_id, family)
            if existing is not None:
                existing.severity = round(clamp(existing.severity * 0.78 + severity * 0.42), 1)
                existing.urgency = round(clamp(existing.urgency * 0.70 + urgency * 0.45), 1)
                existing.regions = sorted(set(existing.regions + related_regions))
                existing.factions = sorted(set(existing.factions + [inst.party_a, inst.party_b]))
                existing.description = desc
                existing.status = "active"
                if existing.quest_offers:
                    existing.quest_offers[0] = build_event_quest(existing, world)
                else:
                    existing.quest_offers.append(build_event_quest(existing, world))
            else:
                node_id = f"node_{inst.institution_id}_{clause.clause_id}_{world.season_index}"
                node = HistoricalEventNode(
                    node_id=node_id,
                    node_type="historical_event",
                    event_family=family,
                    title=title,
                    description=desc,
                    severity=round(severity, 1),
                    urgency=round(urgency, 1),
                    source_institution_id=inst.institution_id,
                    source_clause_id=clause.clause_id,
                    factions=[inst.party_a, inst.party_b],
                    regions=related_regions,
                    promoted_from=clause.clause_kind,
                    era_impetus=era_impetus_from_family(family),
                    projected_legacies=projected_legacies_for_family(family),
                )
                node.quest_offers.append(build_event_quest(node, world))
                new_nodes.append(node)

        if inst.status == "broken" and inst.breach_risk >= 70:
            family = "institutional_breakdown"
            title = f"{inst.label_ja}崩壊"
            desc = "条項違反が累積し、制度そのものが歴史事件として崩壊局面に入った。"
            severity = clamp(inst.breach_risk * 0.82 + regional_scale * 0.28)
            existing = find_live_node_for_source(world, inst.institution_id, None, family)
            if existing is not None:
                existing.severity = round(clamp(existing.severity * 0.74 + severity * 0.46), 1)
                existing.urgency = round(clamp(existing.urgency * 0.74 + inst.breach_risk * 0.26), 1)
                existing.regions = sorted(set(existing.regions + related_regions))
                existing.factions = sorted(set(existing.factions + [inst.party_a, inst.party_b]))
                existing.status = "active"
                if existing.quest_offers:
                    existing.quest_offers[0] = build_event_quest(existing, world)
                else:
                    existing.quest_offers.append(build_event_quest(existing, world))
            else:
                node_id = f"collapse_{inst.institution_id}_{world.season_index}"
                node = HistoricalEventNode(
                    node_id=node_id,
                    node_type="institutional_collapse",
                    event_family=family,
                    title=title,
                    description=desc,
                    severity=round(severity, 1),
                    urgency=round(clamp(inst.breach_risk * 0.92), 1),
                    source_institution_id=inst.institution_id,
                    source_clause_id=None,
                    factions=[inst.party_a, inst.party_b],
                    regions=related_regions,
                    promoted_from=inst.institution_kind,
                    era_impetus=era_impetus_from_family(family),
                    projected_legacies=projected_legacies_for_family(family),
                )
                node.quest_offers.append(build_event_quest(node, world))
                new_nodes.append(node)

    for node in new_nodes:
        world.active_nodes[node.node_id] = node
        world.history_log.append({
            "season": world.season_index,
            "year": world.calendar_year,
            "entry": f"historical node promoted: {node.title}",
            "node_id": node.node_id,
        })

    return new_nodes


def nodes_overlap(a: HistoricalEventNode, b: HistoricalEventNode) -> bool:
    if a.event_family != b.event_family:
        return False
    if set(a.factions) & set(b.factions):
        return True
    if set(a.regions) & set(b.regions):
        return True
    return False


def link_event_chains(world: WorldState, nodes: List[HistoricalEventNode]) -> None:
    for node in nodes:
        linked = None
        for chain in world.chains.values():
            if chain.family == node.event_family and (set(chain.factions) & set(node.factions) or set(chain.regions) & set(node.regions)):
                linked = chain
                break

        if linked is None:
            chain_id = f"chain_{node.event_family}_{len(world.chains)+1:03d}"
            linked = EventChain(
                chain_id=chain_id,
                family=node.event_family,
                label_ja=EVENT_FAMILY_LABELS[node.event_family],
                factions=node.factions[:],
                regions=node.regions[:],
                stage=1,
                cumulative_severity=node.severity,
                active_nodes=[node.node_id],
                history=[node.title],
            )
            world.chains[chain_id] = linked
        else:
            linked.cumulative_severity = round(linked.cumulative_severity + node.severity * 0.72, 1)
            linked.active_nodes.append(node.node_id)
            linked.history.append(node.title)
            linked.factions = sorted(set(linked.factions + node.factions))
            linked.regions = sorted(set(linked.regions + node.regions))
            linked.stage = 1 + len(linked.active_nodes) // 2

        node.chain_id = linked.chain_id
        node.stage = linked.stage


def cool_or_decay_nodes(world: WorldState) -> None:
    for node in world.active_nodes.values():
        if node.status != "active":
            continue
        # 同一制度の breach risk が下がれば鎮静化
        if node.source_institution_id and node.source_institution_id in world.institutions:
            inst = world.institutions[node.source_institution_id]
            if inst.breach_risk < 38:
                node.status = "cooling"
                node.urgency = clamp(node.urgency - 16)
                node.severity = clamp(node.severity - 12)


def one_season(world: WorldState) -> Dict[str, Any]:
    seasonal_drift(world)
    clause_reports = update_clause_states(world)
    new_nodes = maybe_promote_nodes(world)
    link_event_chains(world, new_nodes)
    cool_or_decay_nodes(world)
    return {
        "year": world.calendar_year,
        "season": world.season_index,
        "new_nodes": len(new_nodes),
        "violated_clauses": len([r for r in clause_reports if r[2] >= 70]),
        "strained_clauses": len([r for r in clause_reports if 45 <= r[2] < 70]),
    }


def simulate(seed: int = 1729, seasons: int = 6) -> WorldState:
    world = build_sample_world(seed)
    for _ in range(seasons):
        one_season(world)
    return world


def export_world(world: WorldState) -> Dict[str, Any]:
    def clause_to_dict(c: TreatyClause) -> Dict[str, Any]:
        d = asdict(c)
        d["support"] = round(d["support"], 1)
        d["strain"] = round(d["strain"], 1)
        d["intensity"] = round(d["intensity"], 1)
        d["last_tension"] = round(d["last_tension"], 1)
        return d

    def inst_to_dict(inst: InstitutionState) -> Dict[str, Any]:
        return {
            "institution_id": inst.institution_id,
            "institution_kind": inst.institution_kind,
            "label_ja": inst.label_ja,
            "party_a": inst.party_a,
            "party_b": inst.party_b,
            "support": round(inst.support, 1),
            "breach_risk": round(inst.breach_risk, 1),
            "age_seasons": inst.age_seasons,
            "status": inst.status,
            "clauses": [clause_to_dict(c) for c in inst.clauses],
        }

    def node_to_dict(node: HistoricalEventNode) -> Dict[str, Any]:
        return {
            "node_id": node.node_id,
            "node_type": node.node_type,
            "event_family": node.event_family,
            "title": node.title,
            "description": node.description,
            "severity": round(node.severity, 1),
            "urgency": round(node.urgency, 1),
            "source_institution_id": node.source_institution_id,
            "source_clause_id": node.source_clause_id,
            "factions": node.factions,
            "regions": node.regions,
            "promoted_from": node.promoted_from,
            "chain_id": node.chain_id,
            "stage": node.stage,
            "status": node.status,
            "era_impetus": node.era_impetus,
            "projected_legacies": node.projected_legacies,
            "quest_offers": [asdict(q) for q in node.quest_offers],
        }

    return {
        "world": {
            "seed": world.seed,
            "world_name": world.world_name,
            "calendar_name": world.calendar_name,
            "calendar_year": world.calendar_year,
            "season_index": world.season_index,
            "main_god_name": world.main_god_name,
            "current_world_era": world.current_world_era,
        },
        "regions": {
            rid: {
                "label_ja": r.label_ja,
                "biome": r.biome,
                "dominant_race": r.dominant_race,
                "values": {k: round(v, 1) for k, v in r.values.items()},
                "adjacency": r.adjacency,
                "local_tags": r.local_tags,
            }
            for rid, r in world.regions.items()
        },
        "factions": {
            fid: {
                "label_ja": f.label_ja,
                "faction_type": f.faction_type,
                "dominant_race": f.dominant_race,
                "regions": f.regions,
                "legitimacy": round(f.legitimacy, 1),
                "militarization": round(f.militarization, 1),
                "treasury": round(f.treasury, 1),
                "zeal": round(f.zeal, 1),
                "doctrine_tags": f.doctrine_tags,
            }
            for fid, f in world.factions.items()
        },
        "institutions": {iid: inst_to_dict(inst) for iid, inst in world.institutions.items()},
        "active_nodes": {nid: node_to_dict(node) for nid, node in world.active_nodes.items()},
        "chains": {cid: asdict(chain) for cid, chain in world.chains.items()},
        "history_log": world.history_log,
    }


def summary_markdown(world: WorldState) -> str:
    lines: List[str] = []
    lines.append(f"# {world.world_name} 世界史事件ノード要約")
    lines.append("")
    lines.append(f"- seed: **{world.seed}**")
    lines.append(f"- 暦: **{world.calendar_name} {world.calendar_year}年**")
    lines.append(f"- 現在Era: **{world.current_world_era}**")
    lines.append(f"- active institutions: **{len(world.institutions)}**")
    lines.append(f"- active event nodes: **{len(world.active_nodes)}**")
    lines.append(f"- event chains: **{len(world.chains)}**")
    lines.append("")
    lines.append("## 破綻が強い制度")
    lines.append("")
    ranked_inst = sorted(world.institutions.values(), key=lambda x: (-x.breach_risk, x.institution_id))[:6]
    for inst in ranked_inst:
        lines.append(f"- **{inst.label_ja}** / breach_risk={inst.breach_risk:.1f} / status={inst.status}")
        for clause in sorted(inst.clauses, key=lambda c: (-c.last_tension, c.clause_kind))[:3]:
            lines.append(f"  - {clause.label_ja}: tension={clause.last_tension:.1f} / status={clause.status}")

    lines.append("")
    lines.append("## 昇格した世界史事件ノード")
    lines.append("")
    ranked_nodes = sorted(world.active_nodes.values(), key=lambda x: (-x.severity, -x.urgency, x.title))[:10]
    for node in ranked_nodes:
        lines.append(f"- **{node.title}** ({EVENT_FAMILY_LABELS.get(node.event_family, node.event_family)})")
        lines.append(f"  - severity={node.severity:.1f}, urgency={node.urgency:.1f}, stage={node.stage}, status={node.status}")
        lines.append(f"  - source: {node.source_institution_id} / {node.promoted_from}")
        lines.append(f"  - factions: {', '.join(node.factions)}")
        lines.append(f"  - regions: {', '.join(node.regions)}")
        if node.quest_offers:
            q = node.quest_offers[0]
            lines.append(f"  - quest: {q.title} / vectors={', '.join(q.recommended_vectors)}")

    lines.append("")
    lines.append("## 事件連鎖")
    lines.append("")
    ranked_chains = sorted(world.chains.values(), key=lambda c: (-c.cumulative_severity, c.chain_id))
    for chain in ranked_chains[:8]:
        lines.append(f"- **{chain.label_ja}** / stage={chain.stage} / cumulative={chain.cumulative_severity:.1f}")
        lines.append(f"  - factions: {', '.join(chain.factions)}")
        lines.append(f"  - regions: {', '.join(chain.regions)}")
        lines.append(f"  - nodes: {', '.join(chain.active_nodes[:4])}")

    return "\n".join(lines)


def save_outputs(base_dir: str = "/mnt/data", seed: int = 1729, seasons: int = 6) -> Tuple[str, str, str]:
    world = simulate(seed, seasons)
    data = export_world(world)
    json_path = f"{base_dir}/pbw_generated_world_seed{seed}_v7_historical_nodes.json"
    md_path = f"{base_dir}/pbw_generated_world_seed{seed}_v7_historical_nodes_summary.md"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(summary_markdown(world))
    return json_path, md_path, world.world_name


if __name__ == "__main__":
    json_path, md_path, world_name = save_outputs()
    print(f"generated: {world_name}")
    print(json_path)
    print(md_path)
