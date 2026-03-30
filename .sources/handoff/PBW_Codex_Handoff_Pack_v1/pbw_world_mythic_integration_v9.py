
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PBW World Divine / Cycle Integration Layer v9

v8 の世界史事件解決層に、
- 神々
- 主神暦
- 昇神
- 輪廻歪み
- 主神交代
- 神代戦争
- 主人公の最終分岐
を接続する最終統合層。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import importlib.util
import sys
import json


def load_v8():
    here = Path(__file__).resolve().parent
    target = here / "pbw_world_historical_resolution_v8.py"
    spec = importlib.util.spec_from_file_location("pbw_v8", target)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


v8 = load_v8()
v7 = v8.v7


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass
class DivineEntity:
    god_id: str
    label_ja: str
    rank: str  # main / major / minor
    origin: str  # created / ascended / protagonist
    domains: List[str]
    authority: float
    attention: float
    favorability: float
    volatility: float
    status: str = "active"
    linked_factions: List[str] = field(default_factory=list)
    linked_regions: List[str] = field(default_factory=list)


@dataclass
class ReincarnationCycleState:
    distortion: float
    apotheosis_flux: float
    succession_pressure: float
    cycle_stoppage_risk: float
    divine_war_pressure: float
    notes: List[str] = field(default_factory=list)


@dataclass
class DivineIntervention:
    season: int
    year: int
    god_id: str
    god_name: str
    intervention_kind: str
    regions: List[str]
    factions: List[str]
    region_deltas: Dict[str, Dict[str, float]]
    faction_deltas: Dict[str, Dict[str, float]]
    notes: List[str] = field(default_factory=list)


@dataclass
class ApotheosisRecord:
    season: int
    year: int
    candidate_name: str
    promoted_god_id: str
    promoted_name: str
    source: str
    domains: List[str]
    score: float
    became_main: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class DivineWarFront:
    front_id: str
    label_ja: str
    attacker_god_id: str
    defender_god_id: str
    doctrine_axis: str
    regions: List[str]
    factions: List[str]
    intensity: float
    exhaustion: float
    devastation: float
    status: str = "active"  # active / cooling / resolved


@dataclass
class SuccessionRecord:
    season: int
    old_main: str
    new_main: str
    old_calendar: str
    new_calendar: str
    reason: str
    distortion: float
    divine_war_pressure: float


@dataclass
class FinalBranchAssessment:
    season: int
    year: int
    scores: Dict[str, float]
    available: List[str]
    dominant_branch: str
    notes: List[str] = field(default_factory=list)


@dataclass
class DivineWorldState:
    base_resolution_world: Any
    pantheon: Dict[str, DivineEntity]
    cycle_state: ReincarnationCycleState
    interventions: List[DivineIntervention] = field(default_factory=list)
    apotheosis_history: List[ApotheosisRecord] = field(default_factory=list)
    divine_wars: Dict[str, DivineWarFront] = field(default_factory=dict)
    succession_history: List[SuccessionRecord] = field(default_factory=list)
    final_branch_history: List[FinalBranchAssessment] = field(default_factory=list)


DOMAIN_NAME_LIBRARY: Dict[str, List[str]] = {
    "crown": ["ラレイナ", "オルシェル", "セディオン"],
    "harvest": ["エルミラ", "サラフィ", "メルディア"],
    "contract": ["カディル", "ヴェルクト", "ネルサム"],
    "seal": ["シオルカ", "テリオス", "封華シィラ"],
    "grave": ["モルネア", "ガレム", "屍灯マルダ"],
    "tide": ["ネレシア", "ハルウェル", "潮姫ユルナ"],
    "forge": ["ドラム", "金炉オルダ", "カルグナ"],
    "hunt": ["ヴァルグ", "セイラハ", "狩冠リーヴ"],
    "dream": ["イゼルナ", "ミラセア", "夢紗ルネ"],
    "shadow": ["ナクサ", "ヴェスラ", "黒環サディア"],
    "relic": ["アレノン", "祠冠アシュラ", "レイフィス"],
    "cycle": ["エイラト", "輪紡ネミア", "サーリュ"],
}


DOMAIN_FALLBACK_PREFIX = {
    "crown": "王冠",
    "harvest": "穀環",
    "contract": "契環",
    "seal": "封継",
    "grave": "墓灯",
    "tide": "潮環",
    "forge": "炉鋳",
    "hunt": "狩冠",
    "dream": "夢綾",
    "shadow": "影環",
    "relic": "祠継",
    "cycle": "輪紡",
}
FALLBACK_SUFFIX = ["ノア", "イリス", "セル", "アウラ", "リオン", "エル", "シア", "ヴェル"]
DOMAIN_OPPOSITION = {
    ("crown", "shadow"): "王冠と奈落",
    ("seal", "shadow"): "封印と深淵",
    ("relic", "grave"): "聖遺と埋葬",
    ("harvest", "grave"): "収穫と死",
    ("contract", "dream"): "契約と夢",
    ("cycle", "shadow"): "輪廻と断絶",
}

DOMAIN_FROM_FAMILY = {
    "food_crisis": ["harvest", "crown"],
    "pilgrimage_conflict": ["relic", "seal"],
    "mining_conflict": ["forge", "contract"],
    "deep_delving_conflict": ["seal", "grave", "shadow"],
    "succession_conflict": ["crown", "cycle"],
    "frontier_militarization": ["hunt", "crown"],
    "religious_schism": ["relic", "dream", "seal"],
    "tributary_revolt": ["crown", "contract"],
    "hostage_breakdown": ["contract", "crown"],
    "relic_dispute": ["relic", "seal", "dream"],
    "institutional_breakdown": ["contract", "shadow", "cycle"],
}

RACE_DOMAIN_AFFINITY = {
    "human": ["crown", "contract", "harvest"],
    "elf": ["dream", "tide", "cycle"],
    "dwarf": ["forge", "contract", "seal"],
    "werebeast": ["hunt", "harvest", "grave"],
    "birdfolk": ["crown", "relic", "seal"],
    "fishfolk": ["tide", "harvest", "cycle"],
    "dragonewt": ["crown", "forge", "relic"],
    "fey": ["dream", "cycle", "relic"],
    "demonian": ["shadow", "contract", "grave"],
    "fallen": ["seal", "shadow", "relic"],
    "plantfolk": ["harvest", "cycle", "tide"],
    "gemfolk": ["forge", "relic", "contract"],
}

FINAL_BRANCH_LABELS = {
    "administrator_shard": "管理者の端",
    "successor_attendant": "代替わりの介添え",
    "cycle_breaker": "断輪の終神者",
    "apotheosis_path": "新たな神格",
}


def deterministic_noise(seed: int, *parts: object, span: float = 6.0) -> float:
    return v7.deterministic_noise(seed, *parts, span=span)


def pick_name(seed: int, domain: str, used: List[str]) -> str:
    candidates = DOMAIN_NAME_LIBRARY[domain]
    ranked = sorted(
        candidates,
        key=lambda n: deterministic_noise(seed, domain, n, span=99.0),
        reverse=True,
    )
    for name in ranked:
        if name not in used:
            return name
    suffix_idx = int(abs(deterministic_noise(seed, domain, "fallback", span=100.0))) % len(FALLBACK_SUFFIX)
    return f"{DOMAIN_FALLBACK_PREFIX.get(domain, domain)}{FALLBACK_SUFFIX[suffix_idx]}"


def regions_for_faction(world: Any, faction_id: str) -> List[Any]:
    if faction_id not in world.factions:
        return []
    faction = world.factions[faction_id]
    return [world.regions[rid] for rid in faction.regions if rid in world.regions]


def main_god_id(dw: DivineWorldState) -> str:
    for gid, g in dw.pantheon.items():
        if g.rank == "main" and g.status == "active":
            return gid
    # fallback
    return sorted(dw.pantheon.keys())[0]


def count_institution_kinds(world: Any, kind: str) -> int:
    return len([i for i in world.institutions.values() if i.institution_kind == kind])


def active_nodes_by_family(world: Any, family: str) -> List[Any]:
    return [n for n in world.active_nodes.values() if n.status == "active" and n.event_family == family]


def avg_region_value(world: Any, key: str) -> float:
    vals = [r.values.get(key, 50.0) for r in world.regions.values()]
    return mean(vals)


def build_initial_pantheon(world: Any) -> Dict[str, DivineEntity]:
    seed = world.seed
    used: List[str] = [world.main_god_name]
    pantheon: Dict[str, DivineEntity] = {}

    pantheon["god_main"] = DivineEntity(
        god_id="god_main",
        label_ja=world.main_god_name,
        rank="main",
        origin="created",
        domains=["crown", "cycle", "relic"],
        authority=82.0,
        attention=58.0,
        favorability=53.0,
        volatility=34.0,
        linked_factions=list(world.factions.keys())[:2],
        linked_regions=list(world.regions.keys())[:2],
    )

    base_domains = ["harvest", "contract", "seal", "grave", "tide", "forge", "hunt", "dream", "shadow", "relic"]
    # choose a world-sensible subset
    selected = []
    domain_scores = {
        "harvest": 100 - avg_region_value(world, "food"),
        "contract": (100 - avg_region_value(world, "law_order")) + count_institution_kinds(world, "trade_compact") * 4,
        "seal": avg_region_value(world, "miasma_level") + len(active_nodes_by_family(world, "deep_delving_conflict")) * 7,
        "grave": avg_region_value(world, "miasma_level") + len(active_nodes_by_family(world, "institutional_breakdown")) * 4,
        "tide": 100 - avg_region_value(world, "trade_routes"),
        "forge": len(active_nodes_by_family(world, "mining_conflict")) * 8 + avg_region_value(world, "trade_routes") * 0.2,
        "hunt": avg_region_value(world, "racial_tension"),
        "dream": len(active_nodes_by_family(world, "religious_schism")) * 6 + avg_region_value(world, "faith_density") * 0.3,
        "shadow": count_institution_kinds(world, "holy_war") * 14 + count_institution_kinds(world, "blockade") * 8 + avg_region_value(world, "miasma_level") * 0.4,
        "relic": len(active_nodes_by_family(world, "relic_dispute")) * 12 + avg_region_value(world, "faith_density") * 0.2,
    }
    selected = [k for k, _ in sorted(domain_scores.items(), key=lambda kv: kv[1], reverse=True)[:6]]

    for idx, domain in enumerate(selected, start=1):
        name = pick_name(seed + idx * 17, domain, used)
        used.append(name)
        rank = "major" if idx <= 3 else "minor"
        pantheon[f"god_{domain}"] = DivineEntity(
            god_id=f"god_{domain}",
            label_ja=name,
            rank=rank,
            origin="created",
            domains=[domain],
            authority=64.0 - idx * 2 + deterministic_noise(seed, domain, "authority", span=5.0),
            attention=48.0 + deterministic_noise(seed, domain, "attention", span=9.0),
            favorability=52.0 + deterministic_noise(seed, domain, "favor", span=10.0),
            volatility=42.0 + deterministic_noise(seed, domain, "volatility", span=14.0),
        )
    return pantheon


def build_divine_world(seed: int = 1729, archetype: str = "balanced") -> DivineWorldState:
    rw = v8.build_resolution_world(seed=seed, archetype=archetype)
    pantheon = build_initial_pantheon(rw.base_world)
    cycle_state = ReincarnationCycleState(
        distortion=24.0,
        apotheosis_flux=18.0,
        succession_pressure=12.0,
        cycle_stoppage_risk=10.0,
        divine_war_pressure=8.0,
        notes=[],
    )
    return DivineWorldState(base_resolution_world=rw, pantheon=pantheon, cycle_state=cycle_state)


def choose_top_regions(world: Any, domain: str, limit: int = 3) -> List[str]:
    scores: List[Tuple[float, str]] = []
    for rid, r in world.regions.items():
        if domain == "harvest":
            score = (100 - r.values["food"]) + (100 - r.values["trade_routes"]) * 0.4
        elif domain == "contract":
            score = (100 - r.values["law_order"]) + (100 - r.values["legitimacy"]) * 0.4
        elif domain == "seal":
            score = r.values["miasma_level"] + (100 - r.values["law_order"]) * 0.2
        elif domain == "grave":
            score = r.values["miasma_level"] + r.values["racial_tension"] * 0.15
        elif domain == "tide":
            score = (100 - r.values["trade_routes"]) + (100 - r.values["food"]) * 0.2
        elif domain == "forge":
            score = (100 - r.values["housing"]) * 0.3 + len([n for n in world.active_nodes.values() if rid in n.regions and n.event_family in ["mining_conflict", "deep_delving_conflict"]]) * 18
        elif domain == "hunt":
            score = r.values["racial_tension"] + (100 - r.values["law_order"]) * 0.25
        elif domain == "dream":
            score = r.values["faith_density"] + len([n for n in world.active_nodes.values() if rid in n.regions and n.event_family == "religious_schism"]) * 16
        elif domain == "shadow":
            score = r.values["miasma_level"] + len([n for n in world.active_nodes.values() if rid in n.regions and n.event_family in ["institutional_breakdown", "relic_dispute"]]) * 12
        elif domain == "relic":
            score = r.values["faith_density"] + len([n for n in world.active_nodes.values() if rid in n.regions and n.event_family == "relic_dispute"]) * 22
        elif domain == "crown":
            score = (100 - r.values["succession_stability"]) + (100 - r.values["legitimacy"]) * 0.5
        elif domain == "cycle":
            score = r.values["miasma_level"] + (100 - r.values["faith_density"]) * 0.2
        else:
            score = 50.0
        scores.append((score, rid))
    return [rid for _, rid in sorted(scores, reverse=True)[:limit]]


def god_faction_targets(world: Any, domain: str, limit: int = 2) -> List[str]:
    scores: List[Tuple[float, str]] = []
    for fid, f in world.factions.items():
        score = 0.0
        race_domains = RACE_DOMAIN_AFFINITY.get(f.dominant_race, [])
        if domain in race_domains:
            score += 18.0
        if domain == "crown":
            score += f.legitimacy * 0.4
        if domain == "contract":
            score += f.treasury * 0.25
        if domain == "seal":
            score += f.zeal * 0.2
        if domain == "shadow" and f.faction_type == "demon_domain":
            score += 25.0
        if domain == "relic" and "shrine" in f.faction_id:
            score += 22.0
        if domain == "hunt" and f.faction_type in ["tribe", "march_clans"]:
            score += 15.0
        if domain == "forge" and "mining" in f.faction_id:
            score += 18.0
        scores.append((score, fid))
    return [fid for _, fid in sorted(scores, reverse=True)[:limit] if _ > 0]


def update_cycle_state(dw: DivineWorldState) -> None:
    world = dw.base_resolution_world.base_world
    unresolved = [n for n in world.active_nodes.values() if n.status == "active"]
    broken_insts = [i for i in world.institutions.values() if i.status == "broken"]
    holy_wars = [i for i in world.institutions.values() if i.institution_kind == "holy_war"]
    soul_legacies = [x for x in dw.base_resolution_world.realized_legacies if x.medium == "魂"]
    distortion = (
        avg_region_value(world, "miasma_level") * 0.38
        + mean([n.severity for n in unresolved]) * 0.16
        + len(broken_insts) * 2.8
        + len(soul_legacies) * 3.4
        + len(holy_wars) * 5.0
    )
    distortion = clamp(distortion)

    faith = avg_region_value(world, "faith_density")
    protagonist = dw.base_resolution_world.protagonist
    apotheosis_flux = clamp(
        faith * 0.28
        + protagonist.vessel_points * 0.045
        + len(dw.base_resolution_world.archived_nodes) * 2.4
        + distortion * 0.22
    )
    succession_pressure = clamp(
        (100 - avg_region_value(world, "legitimacy")) * 0.45
        + (100 - avg_region_value(world, "succession_stability")) * 0.35
        + len(holy_wars) * 5.0
        + len([n for n in unresolved if n.event_family in ["succession_conflict", "religious_schism", "relic_dispute"]]) * 3.5
        + distortion * 0.18
    )
    divine_war_pressure = clamp(
        len(holy_wars) * 11.0
        + len([n for n in unresolved if n.event_family in ["religious_schism", "relic_dispute", "institutional_breakdown"]]) * 4.8
        + distortion * 0.22
    )
    cycle_stoppage_risk = clamp(
        distortion * 0.45
        + divine_war_pressure * 0.22
        + len(soul_legacies) * 2.0
    )

    notes = []
    if distortion > 65:
        notes.append("輪廻路に歪みが定着しつつある")
    if apotheosis_flux > 70:
        notes.append("新たな神格が立ち上がる条件が熟している")
    if succession_pressure > 72:
        notes.append("主神権威が揺らぎ、暦の交代圧が高い")
    if divine_war_pressure > 70:
        notes.append("神々の代理戦争が神代戦争へ近づいている")

    dw.cycle_state = ReincarnationCycleState(
        distortion=round(distortion, 1),
        apotheosis_flux=round(apotheosis_flux, 1),
        succession_pressure=round(succession_pressure, 1),
        cycle_stoppage_risk=round(cycle_stoppage_risk, 1),
        divine_war_pressure=round(divine_war_pressure, 1),
        notes=notes,
    )


def intervention_profile(domain: str, severity: float, seed: int, season: int) -> Tuple[str, Dict[str, float], Dict[str, float], List[str]]:
    tone = deterministic_noise(seed, domain, season, "tone", span=100.0)
    benevolent = tone >= 0
    region_deltas: Dict[str, float] = {}
    faction_deltas: Dict[str, float] = {}
    notes: List[str] = []
    kind = "oracle"

    if domain == "harvest":
        kind = "豊穣加護" if benevolent else "収穫徴発"
        region_deltas = {"food": 8 if benevolent else -5, "trade_routes": 2 if benevolent else -2, "faith_density": 2}
        notes.append("穀倉と配給秩序へ干渉")
    elif domain == "contract":
        kind = "誓約修復" if benevolent else "契約硬化"
        region_deltas = {"law_order": 6 if benevolent else -3, "trade_routes": 3 if benevolent else 1, "legitimacy": 3 if benevolent else -2}
        notes.append("制度と交易へ干渉")
    elif domain == "seal":
        kind = "封印補修" if benevolent else "封鎖断行"
        region_deltas = {"miasma_level": -8 if benevolent else -2, "law_order": 3 if benevolent else -3, "faith_density": 2}
        notes.append("裂け目と深層への干渉")
    elif domain == "grave":
        kind = "鎮魂" if benevolent else "死霧降し"
        region_deltas = {"miasma_level": -5 if benevolent else 7, "faith_density": 1 if benevolent else 2, "law_order": 1 if benevolent else -3}
        notes.append("魂残滓と葬送へ干渉")
    elif domain == "tide":
        kind = "潮路開放" if benevolent else "潮路阻絶"
        region_deltas = {"trade_routes": 7 if benevolent else -6, "food": 3 if benevolent else -2}
        notes.append("河川・潮路・港の流通へ干渉")
    elif domain == "forge":
        kind = "炉脈共鳴" if benevolent else "鍛火の独占"
        region_deltas = {"housing": 4 if benevolent else -3, "trade_routes": 3 if benevolent else -2, "miasma_level": -2 if benevolent else 3}
        notes.append("工房・採掘・回収に干渉")
    elif domain == "hunt":
        kind = "辺境守り" if benevolent else "狩軍化"
        region_deltas = {"law_order": 4 if benevolent else -2, "racial_tension": -5 if benevolent else 6}
        notes.append("辺境と狩猟共同体へ干渉")
    elif domain == "dream":
        kind = "夢告" if benevolent else "幻潮"
        region_deltas = {"faith_density": 6, "law_order": 1 if benevolent else -5, "miasma_level": -1 if benevolent else 4}
        notes.append("夢と教義の解釈へ干渉")
    elif domain == "shadow":
        kind = "深淵の徴" if benevolent else "奈落侵蝕"
        region_deltas = {"miasma_level": 6 if benevolent else 10, "law_order": -4, "faith_density": 2}
        notes.append("奈落と呪詛に干渉")
    elif domain == "relic":
        kind = "聖遺裁定" if benevolent else "遺物争奪煽動"
        region_deltas = {"faith_density": 6, "legitimacy": 3 if benevolent else -3, "law_order": 2 if benevolent else -3}
        notes.append("聖遺物と巡礼権へ干渉")
    elif domain == "crown":
        kind = "戴冠承認" if benevolent else "王権試練"
        region_deltas = {"legitimacy": 8 if benevolent else -6, "succession_stability": 7 if benevolent else -5}
        notes.append("継承と戴冠へ干渉")
    elif domain == "cycle":
        kind = "輪紡保全" if benevolent else "再誕偏流"
        region_deltas = {"miasma_level": -4 if benevolent else 4, "faith_density": 3, "law_order": 2 if benevolent else -2}
        notes.append("輪廻路そのものへ干渉")

    scale = clamp(severity / 100.0, 0.3, 1.0)
    region_deltas = {k: round(v * scale, 1) for k, v in region_deltas.items()}
    faction_deltas = {"legitimacy": round((2.5 if benevolent else -2.0) * scale, 1)}
    return kind, region_deltas, faction_deltas, notes


def apply_region_deltas(world: Any, region_delta_map: Dict[str, Dict[str, float]]) -> None:
    for rid, deltas in region_delta_map.items():
        if rid not in world.regions:
            continue
        region = world.regions[rid]
        for k, v in deltas.items():
            if k in region.values:
                region.values[k] = clamp(region.values[k] + v)


def apply_faction_deltas(world: Any, faction_delta_map: Dict[str, Dict[str, float]]) -> None:
    for fid, deltas in faction_delta_map.items():
        if fid not in world.factions:
            continue
        fac = world.factions[fid]
        if "legitimacy" in deltas:
            fac.legitimacy = clamp(fac.legitimacy + deltas["legitimacy"])
        if "militarization" in deltas:
            fac.militarization = clamp(fac.militarization + deltas["militarization"])
        if "treasury" in deltas:
            fac.treasury = clamp(fac.treasury + deltas["treasury"])


def apply_divine_interventions(dw: DivineWorldState) -> None:
    world = dw.base_resolution_world.base_world
    update_cycle_state(dw)
    seed = world.seed
    season = world.season_index
    interventions: List[DivineIntervention] = []

    for god in dw.pantheon.values():
        if god.status != "active":
            continue
        domain = god.domains[0]
        severity_map = {
            "harvest": 100 - avg_region_value(world, "food"),
            "contract": 100 - avg_region_value(world, "law_order") + count_institution_kinds(world, "trade_compact") * 2,
            "seal": avg_region_value(world, "miasma_level") + len(active_nodes_by_family(world, "deep_delving_conflict")) * 8,
            "grave": dw.cycle_state.distortion,
            "tide": 100 - avg_region_value(world, "trade_routes"),
            "forge": len(active_nodes_by_family(world, "mining_conflict")) * 12 + len(active_nodes_by_family(world, "deep_delving_conflict")) * 8,
            "hunt": avg_region_value(world, "racial_tension"),
            "dream": len(active_nodes_by_family(world, "religious_schism")) * 10 + avg_region_value(world, "faith_density") * 0.4,
            "shadow": dw.cycle_state.divine_war_pressure + count_institution_kinds(world, "holy_war") * 8,
            "relic": len(active_nodes_by_family(world, "relic_dispute")) * 12 + avg_region_value(world, "faith_density") * 0.4,
            "crown": dw.cycle_state.succession_pressure,
            "cycle": dw.cycle_state.distortion,
        }
        severity = clamp(severity_map.get(domain, 0.0))
        threshold = 54.0 if god.rank == "main" else 61.0
        if severity < threshold:
            god.attention = clamp(god.attention - 1.2)
            continue

        region_ids = choose_top_regions(world, domain, limit=3 if god.rank == "main" else 2)
        faction_ids = god_faction_targets(world, domain, limit=2)
        kind, base_region_deltas, base_faction_deltas, notes = intervention_profile(domain, severity, seed, season)
        region_delta_map = {rid: dict(base_region_deltas) for rid in region_ids}
        faction_delta_map = {fid: dict(base_faction_deltas) for fid in faction_ids}
        apply_region_deltas(world, region_delta_map)
        apply_faction_deltas(world, faction_delta_map)

        god.attention = clamp(god.attention + severity * 0.04)
        god.authority = clamp(god.authority + (2.2 if god.rank == "main" else 1.1) - god.volatility * 0.01)
        interventions.append(
            DivineIntervention(
                season=world.season_index,
                year=world.calendar_year,
                god_id=god.god_id,
                god_name=god.label_ja,
                intervention_kind=kind,
                regions=region_ids,
                factions=faction_ids,
                region_deltas=region_delta_map,
                faction_deltas=faction_delta_map,
                notes=notes,
            )
        )
    dw.interventions.extend(interventions)


def evaluate_apotheosis(dw: DivineWorldState) -> None:
    world = dw.base_resolution_world.base_world
    seed = world.seed
    protagonist = dw.base_resolution_world.protagonist
    faith = avg_region_value(world, "faith_density")
    season = world.season_index

    existing_names = [g.label_ja for g in dw.pantheon.values()]
    protagonist_score = clamp(
        protagonist.vessel_points * 0.095
        + dw.cycle_state.apotheosis_flux * 0.42
        + len(dw.base_resolution_world.realized_legacies) * 1.7
        + faith * 0.22
    )

    if protagonist_score > 112 and not any(x.source == "protagonist" for x in dw.apotheosis_history):
        domains = ["cycle", "relic"] if protagonist.skills["ritual"] >= protagonist.skills["combat"] else ["crown", "seal"]
        new_name = pick_name(seed + 701, domains[0], existing_names)
        new_god = DivineEntity(
            god_id="god_protagonist",
            label_ja=new_name,
            rank="major",
            origin="protagonist",
            domains=domains,
            authority=78.0,
            attention=72.0,
            favorability=58.0,
            volatility=28.0,
            linked_factions=[],
            linked_regions=list(world.regions.keys())[:3],
        )
        dw.pantheon[new_god.god_id] = new_god
        dw.apotheosis_history.append(
            ApotheosisRecord(
                season=season,
                year=world.calendar_year,
                candidate_name=protagonist.label_ja,
                promoted_god_id=new_god.god_id,
                promoted_name=new_god.label_ja,
                source="protagonist",
                domains=domains,
                score=round(protagonist_score, 1),
                notes=["主人公の因果足跡が神格閾値を越えた"],
            )
        )

    # faction based candidates
    existing_sources = {(x.source, x.candidate_name) for x in dw.apotheosis_history}
    for fid, faction in world.factions.items():
        regions = regions_for_faction(world, fid)
        avg_faith = mean([r.values["faith_density"] for r in regions]) if regions else faith
        avg_leg = mean([r.values["legitimacy"] for r in regions]) if regions else faction.legitimacy
        archived_for_faction = len([r for r in dw.base_resolution_world.resolution_history if fid in r.faction_deltas])
        candidate_score = clamp(
            avg_faith * 0.42
            + avg_leg * 0.18
            + faction.zeal * 0.25
            + archived_for_faction * 8.0
            + dw.cycle_state.apotheosis_flux * 0.18
        )
        if candidate_score < 96:
            continue
        candidate_name = faction.label_ja
        if ("faction", candidate_name) in existing_sources:
            continue
        domains = RACE_DOMAIN_AFFINITY.get(faction.dominant_race, ["crown", "contract"])[:2]
        new_name = pick_name(seed + len(dw.apotheosis_history) * 41 + len(fid), domains[0], existing_names)
        existing_names.append(new_name)
        new_id = f"god_{fid}"
        dw.pantheon[new_id] = DivineEntity(
            god_id=new_id,
            label_ja=new_name,
            rank="minor",
            origin="ascended",
            domains=domains,
            authority=69.0 + deterministic_noise(seed, fid, "apotheosis", span=6.0),
            attention=55.0,
            favorability=50.0 + deterministic_noise(seed, fid, "favor", span=8.0),
            volatility=41.0,
            linked_factions=[fid],
            linked_regions=[r.region_id for r in regions[:2]],
        )
        dw.apotheosis_history.append(
            ApotheosisRecord(
                season=season,
                year=world.calendar_year,
                candidate_name=candidate_name,
                promoted_god_id=new_id,
                promoted_name=new_name,
                source="faction",
                domains=domains,
                score=round(candidate_score, 1),
                notes=[f"{faction.label_ja} の歴史残滓が地方信仰から昇神化した"],
            )
        )


def pair_opposition_score(a: DivineEntity, b: DivineEntity) -> Tuple[float, str]:
    axis = ""
    score = 0.0
    for da in a.domains:
        for db in b.domains:
            if da == db:
                continue
            key = (da, db) if (da, db) in DOMAIN_OPPOSITION else (db, da)
            if key in DOMAIN_OPPOSITION:
                axis = DOMAIN_OPPOSITION[key]
                score = 34.0
            if da == "shadow" and db in ["seal", "crown", "cycle", "relic"]:
                axis = "奈落と秩序"
                score = max(score, 40.0)
            if db == "shadow" and da in ["seal", "crown", "cycle", "relic"]:
                axis = "奈落と秩序"
                score = max(score, 40.0)
    score += abs(a.authority - b.authority) * 0.08
    score += abs(a.favorability - b.favorability) * 0.05
    return score, axis or "神統争い"


def update_divine_wars(dw: DivineWorldState) -> None:
    world = dw.base_resolution_world.base_world
    gods = [g for g in dw.pantheon.values() if g.status == "active" and g.rank in ["main", "major"]]
    if len(gods) < 2:
        return

    # update existing
    for front in dw.divine_wars.values():
        if front.status != "active":
            continue
        front.exhaustion = clamp(front.exhaustion + 4.0 + deterministic_noise(world.seed, front.front_id, world.calendar_year, span=4.0))
        front.devastation = clamp(front.devastation + front.intensity * 0.06)
        front.intensity = clamp(front.intensity + dw.cycle_state.divine_war_pressure * 0.08 - front.exhaustion * 0.03)
        if front.intensity < 18 or front.exhaustion > 96:
            front.status = "cooling"

    # maybe create a new front
    best = (0.0, None, None, "")
    for i, a in enumerate(gods):
        for b in gods[i + 1:]:
            score, axis = pair_opposition_score(a, b)
            score += dw.cycle_state.divine_war_pressure * 0.55
            score += count_institution_kinds(world, "holy_war") * 6.0
            if "shadow" in a.domains or "shadow" in b.domains:
                score += 10.0
            if a.god_id == main_god_id(dw) or b.god_id == main_god_id(dw):
                score += 8.0
            if score > best[0]:
                best = (score, a, b, axis)

    if best[0] > 58 or dw.cycle_state.divine_war_pressure > 60:
        _, a, b, axis = best
        assert a and b
        front_id = f"divine_front_{a.god_id}_{b.god_id}"
        if front_id not in dw.divine_wars or dw.divine_wars[front_id].status != "active":
            # pick contested regions from nodes + faction domains
            region_ids: List[str] = []
            faction_ids: List[str] = []
            for node in world.active_nodes.values():
                node_domains = DOMAIN_FROM_FAMILY.get(node.event_family, [])
                if any(d in a.domains for d in node_domains) or any(d in b.domains for d in node_domains):
                    region_ids.extend(node.regions)
                    faction_ids.extend(node.factions)
            if not region_ids:
                region_ids = choose_top_regions(world, a.domains[0], limit=2) + choose_top_regions(world, b.domains[0], limit=2)
            if not faction_ids:
                faction_ids = god_faction_targets(world, a.domains[0], limit=1) + god_faction_targets(world, b.domains[0], limit=1)
            front = DivineWarFront(
                front_id=front_id,
                label_ja=f"{a.label_ja}＝{b.label_ja}神統戦",
                attacker_god_id=a.god_id,
                defender_god_id=b.god_id,
                doctrine_axis=axis,
                regions=sorted(set(region_ids))[:4],
                factions=sorted(set(faction_ids))[:4],
                intensity=clamp(best[0] * 0.72),
                exhaustion=18.0,
                devastation=12.0,
                status="active",
            )
            dw.divine_wars[front_id] = front

    # apply war damage
    for front in dw.divine_wars.values():
        if front.status != "active":
            continue
        region_delta_map = {}
        for rid in front.regions:
            region_delta_map[rid] = {
                "law_order": round(-4.0 - front.intensity * 0.04, 1),
                "faith_density": round(2.0 + front.intensity * 0.03, 1),
                "miasma_level": round(1.5 + front.devastation * 0.04, 1),
                "legitimacy": round(-2.0 - front.intensity * 0.03, 1),
            }
        apply_region_deltas(world, region_delta_map)



def maybe_succeed_main_god(dw: DivineWorldState) -> None:
    world = dw.base_resolution_world.base_world
    gid = main_god_id(dw)
    main_god = dw.pantheon[gid]

    legitimacy = avg_region_value(world, "legitimacy")
    succession = avg_region_value(world, "succession_stability")
    faith = avg_region_value(world, "faith_density")
    instability = clamp(
        (100 - legitimacy) * 0.42
        + (100 - succession) * 0.26
        + dw.cycle_state.distortion * 0.22
        + dw.cycle_state.divine_war_pressure * 0.18
        + count_institution_kinds(world, "holy_war") * 4.0
    )

    main_god.authority = clamp(main_god.authority - instability * 0.05 + faith * 0.012)
    main_god.attention = clamp(main_god.attention + instability * 0.05)

    # allow only one explicit succession in the sample engine to avoid rapid oscillation
    if dw.succession_history:
        return

    challengers = [g for g in dw.pantheon.values() if g.god_id != gid and g.status == "active"]
    if not challengers:
        return
    best = max(challengers, key=lambda g: g.authority + (14 if g.origin in ["ascended", "protagonist"] else 0))
    pressure = dw.cycle_state.succession_pressure + dw.cycle_state.divine_war_pressure * 0.45 + (100 - main_god.authority) * 0.4

    if pressure > 56 and best.authority > main_god.authority - 6:
        old_name = world.main_god_name
        old_calendar = world.calendar_name
        main_god.rank = "major"
        best.rank = "main"
        world.main_god_name = best.label_ja
        world.calendar_name = f"{best.label_ja}暦"
        world.calendar_year = 1
        dw.succession_history.append(
            SuccessionRecord(
                season=world.season_index,
                old_main=old_name,
                new_main=best.label_ja,
                old_calendar=old_calendar,
                new_calendar=world.calendar_name,
                reason="主神権威の失墜と昇神勢力の台頭",
                distortion=dw.cycle_state.distortion,
                divine_war_pressure=dw.cycle_state.divine_war_pressure,
            )
        )
        for rec in reversed(dw.apotheosis_history):
            if rec.promoted_name == best.label_ja and not rec.became_main:
                rec.became_main = True
                rec.notes.append("主神交代により新暦を開いた")
                break

def apply_divine_era(world: Any, dw: DivineWorldState) -> None:
    base_era = world.current_world_era
    active_fronts = [f for f in dw.divine_wars.values() if f.status == "active"]
    apotheosis_recent = len([a for a in dw.apotheosis_history if a.year >= world.calendar_year - 1])
    scores = {
        base_era: 64.0,
        "神墜期": mean([f.intensity for f in active_fronts]) if active_fronts else 0.0 + dw.cycle_state.divine_war_pressure * 0.55,
        "昇神期": dw.cycle_state.apotheosis_flux * 0.82 + apotheosis_recent * 18.0,
        "継冠期": dw.cycle_state.succession_pressure * 0.92 + len(dw.succession_history) * 14.0,
        "断輪期": dw.cycle_state.distortion * 0.92 + dw.cycle_state.cycle_stoppage_risk * 0.35,
    }
    winner, score = max(scores.items(), key=lambda kv: kv[1])
    if winner != base_era and score > 74:
        world.current_world_era = winner


def evaluate_final_branches(dw: DivineWorldState) -> None:
    rw = dw.base_resolution_world
    p = rw.protagonist
    world = rw.base_world
    reform_count = len([r for r in rw.resolution_history if r.approach == "restructure" and r.outcome in ["success", "great_success"]])
    judgement_count = len([r for r in rw.resolution_history if r.approach == "divine_judgement" and r.outcome in ["success", "great_success"]])
    succession_touch = len(dw.succession_history)
    apotheosis_touch = len([x for x in dw.apotheosis_history if x.source in ["protagonist", "faction"]])
    mercy = p.tendencies["mercy"]
    ambition = p.tendencies["ambition"]
    prudence = p.tendencies["prudence"]

    scores = {
        "administrator_shard": (
            p.vessel_points * 0.54
            + p.skills["stewardship"] * 2.8
            + p.skills["authority"] * 2.0
            + reform_count * 14.0
            + (100 - avg_region_value(world, "law_order")) * -0.3
            + len(rw.archived_nodes) * 2.6
        ),
        "successor_attendant": (
            p.vessel_points * 0.47
            + p.skills["ritual"] * 2.2
            + p.skills["diplomacy"] * 1.9
            + succession_touch * 26.0
            + prudence * 0.9
            + mercy * 0.7
            + dw.cycle_state.succession_pressure * 0.6
        ),
        "cycle_breaker": (
            p.vessel_points * 0.45
            + p.skills["combat"] * 1.8
            + p.skills["authority"] * 1.5
            + dw.cycle_state.distortion * 1.2
            + dw.cycle_state.cycle_stoppage_risk * 0.9
            + (100 - mercy) * 0.8
            + ambition * 0.7
        ),
        "apotheosis_path": (
            p.vessel_points * 0.52
            + p.skills["ritual"] * 2.1
            + p.skills["authority"] * 1.1
            + apotheosis_touch * 18.0
            + judgement_count * 12.0
            + avg_region_value(world, "faith_density") * 0.55
        ),
    }
    scores = {k: round(v, 1) for k, v in scores.items()}
    available = [FINAL_BRANCH_LABELS[k] for k, v in scores.items() if v >= 620]
    dom_key = max(scores.items(), key=lambda kv: kv[1])[0]
    notes = []
    if dw.cycle_state.distortion > 70:
        notes.append("輪廻歪みが強く、断輪の分岐が現実味を帯びる")
    if dw.succession_history:
        notes.append("主神交代に立ち会ったため、代替わりの介添え分岐が開いている")
    if any(x.source == "protagonist" for x in dw.apotheosis_history):
        notes.append("主人公自身の昇神路が開通している")

    dw.final_branch_history.append(
        FinalBranchAssessment(
            season=world.season_index,
            year=world.calendar_year,
            scores=scores,
            available=available,
            dominant_branch=FINAL_BRANCH_LABELS[dom_key],
            notes=notes,
        )
    )


def advance_divine_world_one_season(dw: DivineWorldState) -> Dict[str, Any]:
    world = dw.base_resolution_world.base_world
    apply_divine_interventions(dw)
    season_report = v8.advance_resolution_world_one_season(dw.base_resolution_world)
    update_cycle_state(dw)
    evaluate_apotheosis(dw)
    update_divine_wars(dw)
    maybe_succeed_main_god(dw)
    apply_divine_era(world, dw)
    evaluate_final_branches(dw)

    latest_branch = dw.final_branch_history[-1]
    return {
        "season": world.season_index,
        "year": world.calendar_year,
        "calendar": world.calendar_name,
        "main_god": world.main_god_name,
        "era": world.current_world_era,
        "cycle_state": asdict(dw.cycle_state),
        "apotheosis_count": len(dw.apotheosis_history),
        "divine_wars": len([f for f in dw.divine_wars.values() if f.status == "active"]),
        "available_branches": latest_branch.available,
        "dominant_branch": latest_branch.dominant_branch,
        "base_report": season_report,
    }


def simulate(seed: int = 1729, seasons: int = 10, archetype: str = "balanced") -> DivineWorldState:
    dw = build_divine_world(seed=seed, archetype=archetype)
    for _ in range(seasons):
        advance_divine_world_one_season(dw)
    return dw


def export_world(dw: DivineWorldState) -> Dict[str, Any]:
    data = {
        "schema_version": "9.0",
        "resolved_world": v8.export_world(dw.base_resolution_world),
        "pantheon": [asdict(g) for g in dw.pantheon.values()],
        "cycle_state": asdict(dw.cycle_state),
        "interventions": [asdict(i) for i in dw.interventions],
        "apotheosis_history": [asdict(a) for a in dw.apotheosis_history],
        "divine_wars": [asdict(f) for f in dw.divine_wars.values()],
        "succession_history": [asdict(s) for s in dw.succession_history],
        "final_branch_history": [asdict(f) for f in dw.final_branch_history],
    }
    return data


def summary_markdown(dw: DivineWorldState) -> str:
    world = dw.base_resolution_world.base_world
    p = dw.base_resolution_world.protagonist
    lines: List[str] = []
    lines.append(f"# {world.world_name} 神話統合層要約")
    lines.append("")
    lines.append(f"- seed: **{world.seed}**")
    lines.append(f"- 暦: **{world.calendar_name} {world.calendar_year}年**")
    lines.append(f"- 現在Era: **{world.current_world_era}**")
    lines.append(f"- 主神: **{world.main_god_name}**")
    lines.append(f"- 主人公: **{p.label_ja}** / archetype={p.archetype} / race={p.race}")
    lines.append(f"- 存在級位: **{p.existence_title}**")
    lines.append(f"- vessel points: **{p.vessel_points:.1f}**")
    lines.append(f"- 輪廻歪み: **{dw.cycle_state.distortion:.1f}**")
    lines.append(f"- 昇神流束: **{dw.cycle_state.apotheosis_flux:.1f}**")
    lines.append(f"- 主神交代圧: **{dw.cycle_state.succession_pressure:.1f}**")
    lines.append(f"- 神代戦争圧: **{dw.cycle_state.divine_war_pressure:.1f}**")
    lines.append("")

    if dw.cycle_state.notes:
        lines.append("## 輪廻 / 神格圧の所見")
        lines.append("")
        for note in dw.cycle_state.notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.append("## 現在の神々")
    lines.append("")
    for god in sorted(dw.pantheon.values(), key=lambda g: (g.rank != "main", -g.authority, g.label_ja))[:8]:
        lines.append(
            f"- **{god.label_ja}** / rank={god.rank} / origin={god.origin} / domains={', '.join(god.domains)} / authority={god.authority:.1f}"
        )

    if dw.apotheosis_history:
        lines.append("")
        lines.append("## 昇神履歴")
        lines.append("")
        for rec in dw.apotheosis_history[-6:]:
            lines.append(
                f"- **{rec.candidate_name}** → **{rec.promoted_name}** / source={rec.source} / domains={', '.join(rec.domains)} / score={rec.score:.1f}"
            )
            if rec.notes:
                lines.append(f"  - {' / '.join(rec.notes)}")

    if dw.succession_history:
        lines.append("")
        lines.append("## 主神交代")
        lines.append("")
        for rec in dw.succession_history[-4:]:
            lines.append(
                f"- **{rec.old_main}** → **{rec.new_main}** / {rec.old_calendar} → {rec.new_calendar} / distortion={rec.distortion:.1f} / war_pressure={rec.divine_war_pressure:.1f}"
            )
            lines.append(f"  - {rec.reason}")

    active_fronts = [f for f in dw.divine_wars.values() if f.status == "active"]
    if active_fronts:
        lines.append("")
        lines.append("## 神代戦争前線")
        lines.append("")
        for front in sorted(active_fronts, key=lambda x: -x.intensity)[:6]:
            a = dw.pantheon[front.attacker_god_id].label_ja if front.attacker_god_id in dw.pantheon else front.attacker_god_id
            b = dw.pantheon[front.defender_god_id].label_ja if front.defender_god_id in dw.pantheon else front.defender_god_id
            lines.append(
                f"- **{front.label_ja}** / {a} vs {b} / intensity={front.intensity:.1f} / exhaustion={front.exhaustion:.1f} / devastation={front.devastation:.1f}"
            )
            lines.append(f"  - axis: {front.doctrine_axis}")
            lines.append(f"  - regions: {', '.join(front.regions)}")
            if front.factions:
                lines.append(f"  - factions: {', '.join(front.factions)}")

    if dw.interventions:
        lines.append("")
        lines.append("## 直近の神意介入")
        lines.append("")
        for iv in dw.interventions[-8:]:
            lines.append(f"- **{iv.god_name}** / {iv.intervention_kind} / regions={', '.join(iv.regions)}")
            if iv.notes:
                lines.append(f"  - {' / '.join(iv.notes)}")

    if dw.final_branch_history:
        fb = dw.final_branch_history[-1]
        lines.append("")
        lines.append("## 最終分岐評価")
        lines.append("")
        lines.append(f"- dominant: **{fb.dominant_branch}**")
        if fb.available:
            lines.append(f"- available: **{', '.join(fb.available)}**")
        else:
            lines.append("- available: まだ最終分岐は開いていない")
        lines.append("- scores:")
        for k, v in sorted(fb.scores.items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {FINAL_BRANCH_LABELS[k]}: {v:.1f}")
        if fb.notes:
            lines.append("- notes:")
            for note in fb.notes:
                lines.append(f"  - {note}")

    return "\n".join(lines)


def save_outputs(base_dir: str = "/mnt/data", seed: int = 1729, seasons: int = 10, archetype: str = "balanced") -> Tuple[str, str, str]:
    dw = simulate(seed=seed, seasons=seasons, archetype=archetype)

    base = Path(base_dir)
    py_path = base / "pbw_world_mythic_integration_v9.py"
    json_path = base / f"pbw_generated_world_seed{seed}_v9_mythic_integration.json"
    summary_path = base / f"pbw_generated_world_seed{seed}_v9_mythic_integration_summary.md"

    if not py_path.exists():
        py_path.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
    json_path.write_text(json.dumps(export_world(dw), ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(summary_markdown(dw), encoding="utf-8")
    return str(py_path), str(json_path), str(summary_path)


if __name__ == "__main__":
    paths = save_outputs()
    print("\n".join(paths))
