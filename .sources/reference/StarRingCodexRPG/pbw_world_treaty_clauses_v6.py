"""PBW treaty clauses v6

Extends institutional diplomacy v5 by decomposing diplomacy into clause bundles.
Institutions remain the durable relationship layer (trade compact, truce, war,
etc.), while clauses describe the concrete legal / ritual / economic articles that
shape everyday history:
- grain tariff reductions / staple grain quotas
- pilgrimage protection
- joint mining rights / joint delve salvage
- dynastic marriage
- demilitarized borders / refugee corridors / prisoner exchange
- war reparations / hostage exchange
- shared seal duty / relic custody / river passage rights

The intent is to make two treaties of the same kind diverge materially, producing
different seasonal outcomes, different failures, and different long-term traces.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_V5_PATH = BASE_DIR / "pbw_world_institutions_v5.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v5 = _load_module(DEFAULT_V5_PATH, "pbw_world_institutions_v5_ext")
v4 = v5.v4
v3 = v4.v3
v2 = v3.v2
v1 = v2.v1

InstitutionalWorldState = v5.InstitutionalWorldState
DiplomaticInstitution = v5.DiplomaticInstitution
GeneratedFaction = v3.GeneratedFaction
DiplomacyRelation = v3.DiplomacyRelation
WorldState = v3.WorldState
LegacyMedium = v2.LegacyMedium

region_lookup = v5.region_lookup
faction_lookup = v5.faction_lookup
pair_key = v5.pair_key
round_obj = v5.round_obj
merge_legacy = v5.merge_legacy
clamp = v5.clamp
apply_region_delta = v5.apply_region_delta
apply_faction_delta = v5.apply_faction_delta
adjust_relation_score = v5.adjust_relation_score
current_relation = v5.current_relation
pair_regions = v5.pair_regions
active_institutions = v5.active_institutions
institutions_for_pair = v5.institutions_for_pair
active_states = v5.active_states
relation_status = v5.relation_status

def dedupe(seq: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@dataclass
class TreatyClause:
    clause_id: str
    institution_id: str
    family: str
    label_ja: str
    category: str
    status: str
    intensity: float
    support: float
    strain: float
    founded_year: int
    founded_season: int
    terms: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ClauseWorldState:
    institutional: InstitutionalWorldState
    clauses: Dict[str, TreatyClause] = field(default_factory=dict)
    institution_clauses: Dict[str, List[str]] = field(default_factory=dict)
    clause_history: List[Dict[str, Any]] = field(default_factory=list)
    last_clause_events: List[Dict[str, Any]] = field(default_factory=list)
    season_reports: List[Dict[str, Any]] = field(default_factory=list)


CLAUSE_LABELS = {
    "grain_tariff_reduction": "穀物関税軽減条項",
    "staple_grain_quota": "主食供給割当条項",
    "pilgrimage_protection": "巡礼路保護条項",
    "joint_mining_rights": "共同採掘権条項",
    "dynastic_marriage": "婚姻同盟条項",
    "demilitarized_border": "非武装境界条項",
    "war_reparations": "戦後賠償条項",
    "prisoner_exchange": "捕虜交換条項",
    "refugee_corridor": "難民回廊条項",
    "joint_delve_salvage": "共同深層回収条項",
    "shared_seal_duty": "共同封印義務条項",
    "river_navigation_rights": "河川通行権条項",
    "hostage_exchange": "人質交換条項",
    "relic_custody": "聖遺物保管条項",
}
CLAUSE_CATEGORY = {
    "grain_tariff_reduction": "economy",
    "staple_grain_quota": "food_relief",
    "pilgrimage_protection": "faith",
    "joint_mining_rights": "resource",
    "dynastic_marriage": "dynastic",
    "demilitarized_border": "security",
    "war_reparations": "postwar",
    "prisoner_exchange": "postwar",
    "refugee_corridor": "humanitarian",
    "joint_delve_salvage": "dungeon",
    "shared_seal_duty": "cosmic_security",
    "river_navigation_rights": "transit",
    "hostage_exchange": "guarantee",
    "relic_custody": "faith",
}
CLAUSE_COMPATIBILITY = {
    "grain_tariff_reduction": {"trade_compact", "truce", "non_aggression_pact"},
    "staple_grain_quota": {"trade_compact", "truce", "vassalage", "defensive_alliance"},
    "pilgrimage_protection": {"religious_concordat", "non_aggression_pact", "truce"},
    "joint_mining_rights": {"trade_compact", "defensive_alliance", "vassalage"},
    "dynastic_marriage": {"non_aggression_pact", "defensive_alliance", "vassalage", "truce"},
    "demilitarized_border": {"non_aggression_pact", "truce", "defensive_alliance"},
    "war_reparations": {"truce", "vassalage"},
    "prisoner_exchange": {"truce", "open_war", "holy_war"},
    "refugee_corridor": {"truce", "defensive_alliance", "religious_concordat"},
    "joint_delve_salvage": {"trade_compact", "defensive_alliance", "non_aggression_pact"},
    "shared_seal_duty": {"defensive_alliance", "religious_concordat", "truce"},
    "river_navigation_rights": {"trade_compact", "non_aggression_pact", "truce"},
    "hostage_exchange": {"truce", "vassalage", "defensive_alliance"},
    "relic_custody": {"religious_concordat", "truce", "holy_war"},
}
MAX_CLAUSES_BY_KIND = {
    "non_aggression_pact": 3,
    "trade_compact": 4,
    "religious_concordat": 4,
    "defensive_alliance": 4,
    "truce": 4,
    "open_war": 2,
    "holy_war": 3,
    "blockade": 2,
    "vassalage": 4,
}
FORMATION_MEDIA = {
    "grain_tariff_reduction": {"制度": 0.14, "伝承": 0.05},
    "staple_grain_quota": {"制度": 0.12, "正史": 0.06},
    "pilgrimage_protection": {"信仰": 0.16, "伝承": 0.08},
    "joint_mining_rights": {"制度": 0.12, "正史": 0.06},
    "dynastic_marriage": {"正史": 0.16, "伝承": 0.05},
    "demilitarized_border": {"制度": 0.14, "正史": 0.06},
    "war_reparations": {"正史": 0.14, "異端文書": 0.06},
    "prisoner_exchange": {"伝承": 0.12, "正史": 0.05},
    "refugee_corridor": {"伝承": 0.10, "制度": 0.06},
    "joint_delve_salvage": {"制度": 0.10, "魂": 0.06},
    "shared_seal_duty": {"制度": 0.10, "信仰": 0.08, "魂": 0.06},
    "river_navigation_rights": {"制度": 0.12, "伝承": 0.06},
    "hostage_exchange": {"正史": 0.10, "伝承": 0.05},
    "relic_custody": {"信仰": 0.14, "異端文書": 0.06},
}
BREAK_MEDIA = {
    "default": {"伝承": 0.10, "異端文書": 0.06},
    "dynastic_marriage": {"伝承": 0.12, "正史": 0.08},
    "war_reparations": {"異端文書": 0.12, "伝承": 0.08},
    "relic_custody": {"異端文書": 0.14, "信仰": 0.08},
    "shared_seal_duty": {"魂": 0.10, "異端文書": 0.10},
}


# ---------- Utility ----------

def stable_int(*parts: Any) -> int:
    s = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:12], 16)


def clause_rng(world: WorldState, inst_id: str, salt: str) -> random.Random:
    return random.Random(stable_int(world.seed, world.calendar_year, world.season_index, inst_id, salt))


def world_and_maps(state: ClauseWorldState) -> Tuple[WorldState, Dict[str, Any], Dict[str, Any]]:
    world = state.institutional.resolved.ext.world
    return world, region_lookup(world), faction_lookup(world)


def avg_region_values(world: WorldState, region_ids: Sequence[str]) -> Dict[str, float]:
    reg = region_lookup(world)
    ids = list(dict.fromkeys(region_ids))
    if not ids:
        return {}
    keys = list(reg[ids[0]].values.keys())
    out: Dict[str, float] = {}
    for key in keys:
        out[key] = sum(reg[rid].values[key] for rid in ids) / len(ids)
    return out


def dominant_resonance_score(world: WorldState, region_ids: Sequence[str], attr: str) -> float:
    reg = region_lookup(world)
    ids = list(dict.fromkeys(region_ids))
    if not ids:
        return 0.0
    return sum(reg[rid].resonance.get(attr, 0.0) for rid in ids) / len(ids)


def pair_metrics(state: ClauseWorldState, inst: DiplomaticInstitution) -> Dict[str, Any]:
    world, reg, fl = world_and_maps(state)
    a = fl[inst.faction_a]
    b = fl[inst.faction_b]
    rel = current_relation(state.institutional, a.faction_id, b.faction_id)
    contact = pair_regions(world, a, b, rel, mode="contact", terms=inst.terms)
    union = pair_regions(world, a, b, rel, mode="union", terms=inst.terms)
    contact_avg = avg_region_values(world, contact)
    union_avg = avg_region_values(world, union)
    metrics = {
        "a": a,
        "b": b,
        "rel": rel,
        "contact_ids": contact,
        "union_ids": union,
        "contact_avg": contact_avg,
        "union_avg": union_avg,
        "food_stress": max(0.0, 100.0 - union_avg.get("food", 50.0)),
        "trade_need": max(0.0, 100.0 - union_avg.get("trade_routes", 50.0)),
        "faith_heat": union_avg.get("faith_density", 50.0),
        "rift_threat": union_avg.get("interworld_intrusion", 0.0) + union_avg.get("miasma_level", 0.0) * 0.6,
        "dungeon_pull": union_avg.get("dungeon_density", 0.0),
        "metal_pull": union_avg.get("metal_stock", 0.0),
        "water_trade": union_avg.get("water", 0.0) + union_avg.get("trade_routes", 0.0),
        "refugee_crisis": union_avg.get("refugee_flow", 0.0) + max(0.0, 50.0 - union_avg.get("housing", 50.0)),
        "succession_heat": union_avg.get("succession_stability", 50.0),
        "legitimacy_avg": (a.legitimacy + b.legitimacy) / 2.0,
        "mil_gap": abs(a.militarization - b.militarization),
        "power_gap": abs((a.legitimacy + a.militarization + a.treasury) - (b.legitimacy + b.militarization + b.treasury)),
        "state_pair": int(a.faction_type in {"state", "tribe"} and b.faction_type in {"state", "tribe"}),
        "religious_pair": int("religion" in {a.faction_type, b.faction_type} or inst.kind in {"religious_concordat", "holy_war"}),
        "trade_pair": int("guild" in {a.faction_type, b.faction_type} or inst.kind == "trade_compact"),
        "war_context": int(inst.kind in {"open_war", "holy_war", "truce"} or any(x.kind in {"open_war", "holy_war"} and x.status in active_states() for x in institutions_for_pair(state.institutional, a.faction_id, b.faction_id))),
        "earth_metal_resonance": max(dominant_resonance_score(world, union, "earth"), dominant_resonance_score(world, union, "metal")),
        "water_resonance": max(dominant_resonance_score(world, union, "water"), dominant_resonance_score(world, union, "ice")),
        "faith_resonance": max(dominant_resonance_score(world, union, "light"), dominant_resonance_score(world, union, "healing")),
        "dark_resonance": max(dominant_resonance_score(world, union, "dark"), dominant_resonance_score(world, union, "mind")),
    }
    return metrics


def clause_ids_for_institution(state: ClauseWorldState, institution_id: str, include_inactive: bool = False) -> List[str]:
    ids = state.institution_clauses.get(institution_id, [])
    out = []
    for cid in ids:
        clause = state.clauses.get(cid)
        if clause is None:
            continue
        if include_inactive or clause.status in {"active", "strained"}:
            out.append(cid)
    return out


def active_clause_families(state: ClauseWorldState, institution_id: str) -> set[str]:
    return {state.clauses[cid].family for cid in clause_ids_for_institution(state, institution_id)}


def clause_target_ids(world: WorldState, inst: DiplomaticInstitution, metrics: Dict[str, Any], mode: str = "contact") -> List[str]:
    a = metrics["a"]
    b = metrics["b"]
    rel = metrics["rel"]
    return pair_regions(world, a, b, rel, mode=mode, terms=inst.terms)


def clause_tags(family: str, metrics: Dict[str, Any]) -> List[str]:
    tags = [family, CLAUSE_CATEGORY[family]]
    if metrics["religious_pair"]:
        tags.append("faith_axis")
    if metrics["trade_pair"]:
        tags.append("trade_axis")
    if metrics["war_context"]:
        tags.append("war_axis")
    if metrics["food_stress"] >= 25:
        tags.append("famine_pressure")
    if metrics["rift_threat"] >= 55:
        tags.append("rift_pressure")
    return dedupe(tags)


def clause_terms(world: WorldState, family: str, inst: DiplomaticInstitution, metrics: Dict[str, Any]) -> Dict[str, Any]:
    rng = clause_rng(world, inst.institution_id, family)
    a = metrics["a"]
    b = metrics["b"]
    if family == "grain_tariff_reduction":
        return {"tariff_cut": round(0.08 + rng.random() * 0.16, 3), "priority_goods": ["穀物", "塩", "薬材"]}
    if family == "staple_grain_quota":
        donor = a.faction_id if a.treasury >= b.treasury else b.faction_id
        recipient = b.faction_id if donor == a.faction_id else a.faction_id
        return {"donor": donor, "recipient": recipient, "quota": round(0.10 + rng.random() * 0.18, 3)}
    if family == "pilgrimage_protection":
        route = clause_target_ids(world, inst, metrics, mode="contact")[: min(5, 2 + rng.randint(0, 2))]
        return {"protected_route": route, "escort_level": round(0.35 + rng.random() * 0.4, 3)}
    if family == "joint_mining_rights":
        a_share = round(0.35 + rng.random() * 0.25, 3)
        return {"royalty_split": {a.faction_id: a_share, b.faction_id: round(max(0.05, 1.0 - a_share), 3)}, "mine_guards": 1 + rng.randint(0, 2)}
    if family == "dynastic_marriage":
        return {"marriage_house_a": f"{a.label_ja}宗家", "marriage_house_b": f"{b.label_ja}宗家", "dowry_weight": round(0.20 + rng.random() * 0.25, 3)}
    if family == "demilitarized_border":
        return {"watch_posts_removed": 1 + rng.randint(1, 4), "buffer_depth": 1 + rng.randint(1, 3)}
    if family == "war_reparations":
        payer = inst.terms.get("target") or inst.terms.get("junior") or (a.faction_id if a.treasury >= b.treasury else b.faction_id)
        recipient = b.faction_id if payer == a.faction_id else a.faction_id
        return {"payer": payer, "recipient": recipient, "tribute": round(0.08 + rng.random() * 0.12, 3), "duration_seasons": 2 + rng.randint(0, 4)}
    if family == "prisoner_exchange":
        return {"exchange_batches": 1 + rng.randint(1, 4), "mediated_by": "中立修道会" if metrics["religious_pair"] else "境界監視官"}
    if family == "refugee_corridor":
        return {"corridor_regions": clause_target_ids(world, inst, metrics, mode="contact")[:4], "escort_ratio": round(0.25 + rng.random() * 0.35, 3)}
    if family == "joint_delve_salvage":
        a_share = round(0.40 + rng.random() * 0.2, 3)
        return {"salvage_split": {a.faction_id: a_share, b.faction_id: round(max(0.05, 1.0 - a_share), 3)}, "licensed_depth": 1 + rng.randint(1, 4)}
    if family == "shared_seal_duty":
        return {"seal_sites": clause_target_ids(world, inst, metrics, mode="contact")[:3], "ritual_frequency": 1 + rng.randint(1, 3)}
    if family == "river_navigation_rights":
        return {"river_toll_cut": round(0.10 + rng.random() * 0.18, 3), "harbor_priority": rng.choice(["穀倉港", "巡礼港", "軍港外縁"])}
    if family == "hostage_exchange":
        return {"hostage_count": 1 + rng.randint(1, 3), "custody_rotation": 1 + rng.randint(1, 2)}
    if family == "relic_custody":
        return {"custodian": a.faction_id if a.legitimacy >= b.legitimacy else b.faction_id, "relic_grade": rng.choice(["聖骨", "神器欠片", "預言碑"])}
    return {}


def clause_score(family: str, inst: DiplomaticInstitution, metrics: Dict[str, Any]) -> float:
    rel = metrics["rel"].score if metrics["rel"] else 0.0
    theology = metrics["rel"].axes.get("theology", 0.5) if metrics["rel"] else 0.5
    territory = metrics["rel"].axes.get("territory", 0.5) if metrics["rel"] else 0.5
    trade = metrics["rel"].axes.get("trade", 0.5) if metrics["rel"] else 0.5
    security = metrics["rel"].axes.get("security", 0.5) if metrics["rel"] else 0.5
    kind = inst.kind
    food = metrics["food_stress"]
    faith = metrics["faith_heat"]
    rift = metrics["rift_threat"]
    dungeon = metrics["dungeon_pull"]
    metal = metrics["metal_pull"]
    refugees = metrics["refugee_crisis"]
    legit = metrics["legitimacy_avg"]
    state_pair = metrics["state_pair"]
    religious_pair = metrics["religious_pair"]
    war_context = metrics["war_context"]
    power_gap = metrics["power_gap"]
    if family == "grain_tariff_reduction":
        return 45 + trade * 26 + food * 0.45 + max(0, rel) * 0.18 - territory * 6 + (8 if kind == "trade_compact" else 0)
    if family == "staple_grain_quota":
        return 40 + food * 0.68 + max(0, rel) * 0.14 + (10 if kind in {"truce", "vassalage"} else 0)
    if family == "pilgrimage_protection":
        return 44 + faith * 0.28 + religious_pair * 12 + max(0, rel) * 0.10 + (1.0 - theology) * 18
    if family == "joint_mining_rights":
        return 38 + metal * 0.45 + metrics["earth_metal_resonance"] * 18 + trade * 12 + (8 if kind == "trade_compact" else 0)
    if family == "dynastic_marriage":
        return 34 + state_pair * 22 + legit * 0.16 + max(0, rel) * 0.20 - war_context * 8 + (6 if kind in {"non_aggression_pact", "defensive_alliance"} else 0)
    if family == "demilitarized_border":
        return 40 + territory * 18 + refugees * 0.18 + max(0, rel) * 0.12 + (12 if kind == "truce" else 0)
    if family == "war_reparations":
        return 42 + war_context * 18 + power_gap * 0.18 + max(0, 30 - rel) * 0.20 + (10 if kind in {"truce", "vassalage"} else 0)
    if family == "prisoner_exchange":
        return 42 + war_context * 18 + refugees * 0.16 + faith * 0.08 + (8 if kind == "truce" else 0)
    if family == "refugee_corridor":
        return 40 + refugees * 0.30 + food * 0.16 + religious_pair * 6 + (8 if kind == "truce" else 0)
    if family == "joint_delve_salvage":
        return 36 + dungeon * 0.40 + trade * 12 + metrics["dark_resonance"] * 10 + (10 if kind == "trade_compact" else 0)
    if family == "shared_seal_duty":
        return 44 + rift * 0.42 + metrics["faith_resonance"] * 10 + religious_pair * 8 + (10 if kind in {"religious_concordat", "defensive_alliance"} else 0)
    if family == "river_navigation_rights":
        return 38 + metrics["water_trade"] * 0.24 + trade * 12 + food * 0.14
    if family == "hostage_exchange":
        return 36 + war_context * 16 + power_gap * 0.16 + territory * 10 + (8 if kind in {"truce", "vassalage"} else 0)
    if family == "relic_custody":
        return 42 + faith * 0.24 + religious_pair * 12 + dungeon * 0.12 + (10 if kind == "religious_concordat" else 0)
    return 0.0


def desired_clause_count(inst: DiplomaticInstitution) -> int:
    base = {
        "trade_compact": 3,
        "religious_concordat": 3,
        "defensive_alliance": 3,
        "non_aggression_pact": 2,
        "truce": 3,
        "open_war": 1,
        "holy_war": 2,
        "blockade": 1,
        "vassalage": 3,
    }[inst.kind]
    if inst.strength >= 85:
        base += 1
    return min(MAX_CLAUSES_BY_KIND[inst.kind], base)


def write_clause_legacies(state: ClauseWorldState, clause: TreatyClause, inst: DiplomaticInstitution, metrics: Dict[str, Any], broken: bool = False) -> List[Dict[str, Any]]:
    world, reg, _ = world_and_maps(state)
    media_map = BREAK_MEDIA.get(clause.family, BREAK_MEDIA["default"]) if broken else FORMATION_MEDIA.get(clause.family, {})
    if not media_map:
        return []
    if clause.family in {"war_reparations", "hostage_exchange"}:
        ids = clause_target_ids(world, inst, metrics, mode="contact")[:4]
    elif clause.family in {"relic_custody", "pilgrimage_protection"}:
        ids = clause_target_ids(world, inst, metrics, mode="contact")[:6]
    else:
        ids = clause_target_ids(world, inst, metrics, mode="union")[:8]
    out: List[Dict[str, Any]] = []
    for rid in ids:
        region = reg[rid]
        for medium, intensity in media_map.items():
            info = merge_legacy(region, medium, clause.tags, intensity)
            out.append({"region_id": rid, "region_name_ja": world.region_meta[rid]["name_ja"], **info})
    return out


def create_clause(state: ClauseWorldState, inst: DiplomaticInstitution, family: str, reason: str, base_score: float) -> TreatyClause:
    world, reg, fl = world_and_maps(state)
    metrics = pair_metrics(state, inst)
    terms = clause_terms(world, family, inst, metrics)
    cid = f"{inst.institution_id}__{family}__{1 + len(state.institution_clauses.get(inst.institution_id, [])):02d}"
    support = max(20.0, min(100.0, 28.0 + base_score * 0.55 + inst.support * 0.18 - inst.breach_risk * 0.06))
    strain = max(0.0, min(100.0, 20.0 + inst.breach_risk * 0.45 + max(0.0, -((metrics['rel'].score if metrics['rel'] else 0.0))) * 0.12))
    intensity = max(25.0, min(95.0, 20.0 + inst.strength * 0.52 + (base_score - 40.0) * 0.20))
    clause = TreatyClause(
        clause_id=cid,
        institution_id=inst.institution_id,
        family=family,
        label_ja=CLAUSE_LABELS[family],
        category=CLAUSE_CATEGORY[family],
        status="active",
        intensity=round(intensity, 3),
        support=round(support, 3),
        strain=round(strain, 3),
        founded_year=world.calendar_year,
        founded_season=world.season_index,
        terms=terms,
        tags=clause_tags(family, metrics),
        history=[{"calendar_year": world.calendar_year, "season_index": world.season_index, "event": "formed", "reason": reason, "intensity": round(intensity, 3)}],
    )
    state.clauses[cid] = clause
    state.institution_clauses.setdefault(inst.institution_id, []).append(cid)
    # small diplomatic consequence
    adjust_relation_score(state.institutional, inst.faction_a, inst.faction_b, 1.5 if family not in {"war_reparations", "hostage_exchange"} else 0.4, f"clause:{family}:form")
    legacies = write_clause_legacies(state, clause, inst, metrics, broken=False)
    event = {
        "kind": "formed",
        "clause_id": clause.clause_id,
        "institution_id": inst.institution_id,
        "institution_kind": inst.kind,
        "family": family,
        "label_ja": clause.label_ja,
        "reason": reason,
        "intensity": clause.intensity,
        "legacies": legacies[:6],
    }
    state.last_clause_events.append(round_obj(event, 3))
    world.history.append({"calendar_year": world.calendar_year, "season_index": world.season_index, "kind": "clause_formed", **round_obj(event, 3)})
    return clause


def clause_support_strain_delta(clause: TreatyClause, inst: DiplomaticInstitution, metrics: Dict[str, Any]) -> Tuple[float, float]:
    rel = metrics["rel"].score if metrics["rel"] else 0.0
    theology = metrics["rel"].axes.get("theology", 0.5) if metrics["rel"] else 0.5
    territory = metrics["rel"].axes.get("territory", 0.5) if metrics["rel"] else 0.5
    food = metrics["food_stress"]
    rift = metrics["rift_threat"]
    refugees = metrics["refugee_crisis"]
    support_delta = 0.0
    strain_delta = 0.0
    fam = clause.family
    if fam in {"grain_tariff_reduction", "staple_grain_quota"}:
        support_delta += food * 0.02 + max(0.0, rel) * 0.01
        strain_delta += max(0.0, inst.breach_risk - 40.0) * 0.04
    if fam in {"pilgrimage_protection", "relic_custody"}:
        support_delta += metrics["faith_heat"] * 0.015 + max(0.0, rel) * 0.008
        strain_delta += theology * 1.6 + max(0.0, inst.breach_risk - 35.0) * 0.03
    if fam in {"joint_mining_rights", "joint_delve_salvage"}:
        support_delta += (metrics["metal_pull"] + metrics["dungeon_pull"]) * 0.01
        strain_delta += territory * 1.4 + max(0.0, inst.breach_risk - 42.0) * 0.04
    if fam == "shared_seal_duty":
        support_delta += rift * 0.018 + metrics["faith_resonance"] * 0.08
        strain_delta += max(0.0, inst.breach_risk - 38.0) * 0.05
    if fam in {"demilitarized_border", "prisoner_exchange", "refugee_corridor", "war_reparations", "hostage_exchange"}:
        support_delta += refugees * 0.012 + max(0.0, rel + 10.0) * 0.008
        strain_delta += territory * 1.2 + max(0.0, -rel) * 0.015
    if fam == "dynastic_marriage":
        support_delta += metrics["legitimacy_avg"] * 0.01 + max(0.0, rel) * 0.014
        strain_delta += max(0.0, 50.0 - metrics["succession_heat"]) * 0.06 + max(0.0, inst.breach_risk - 34.0) * 0.03
    if fam == "river_navigation_rights":
        support_delta += metrics["water_trade"] * 0.01 + max(0.0, rel) * 0.01
        strain_delta += territory * 0.8 + max(0.0, inst.breach_risk - 45.0) * 0.04
    support_delta += inst.support * 0.01 - inst.breach_risk * 0.006
    strain_delta += inst.breach_risk * 0.01 - max(0.0, rel) * 0.004
    return round(support_delta, 3), round(max(-2.0, strain_delta), 3)


def end_clause(state: ClauseWorldState, clause: TreatyClause, inst: DiplomaticInstitution, reason: str, broken: bool = True) -> None:
    if clause.status == "ended":
        return
    world, reg, fl = world_and_maps(state)
    metrics = pair_metrics(state, inst)
    clause.status = "repudiated" if broken else "ended"
    clause.history.append({"calendar_year": world.calendar_year, "season_index": world.season_index, "event": clause.status, "reason": reason, "intensity": clause.intensity})
    clause.intensity = round(max(0.0, clause.intensity - 10.0), 3)
    adjust_relation_score(state.institutional, inst.faction_a, inst.faction_b, -2.0 if broken else -0.8, f"clause:{clause.family}:end")
    inst.breach_risk = round(min(100.0, inst.breach_risk + (5.0 if broken else 2.0)), 3)
    inst.support = round(max(0.0, inst.support - (4.0 if broken else 1.5)), 3)
    legacies = write_clause_legacies(state, clause, inst, metrics, broken=True)
    event = {
        "kind": "repudiated" if broken else "ended",
        "clause_id": clause.clause_id,
        "institution_id": inst.institution_id,
        "family": clause.family,
        "label_ja": clause.label_ja,
        "reason": reason,
        "legacies": legacies[:6],
    }
    state.last_clause_events.append(round_obj(event, 3))
    world.history.append({"calendar_year": world.calendar_year, "season_index": world.season_index, "kind": "clause_broken" if broken else "clause_ended", **round_obj(event, 3)})


def candidate_clause_families(state: ClauseWorldState, inst: DiplomaticInstitution) -> List[Tuple[str, float]]:
    metrics = pair_metrics(state, inst)
    existing = active_clause_families(state, inst.institution_id)
    candidates: List[Tuple[str, float]] = []
    for family, kinds in CLAUSE_COMPATIBILITY.items():
        if inst.kind not in kinds:
            continue
        if family in existing:
            continue
        score = clause_score(family, inst, metrics)
        if score >= 52.0:
            candidates.append((family, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


def bootstrap_clauses_for_institution(state: ClauseWorldState, inst: DiplomaticInstitution, initial: bool = False) -> List[TreatyClause]:
    if inst.status not in active_states():
        return []
    current = clause_ids_for_institution(state, inst.institution_id)
    needed = max(0, desired_clause_count(inst) - len(current))
    if needed <= 0:
        return []
    world, reg, fl = world_and_maps(state)
    rng = clause_rng(world, inst.institution_id, "bootstrap")
    candidates = candidate_clause_families(state, inst)
    if not candidates:
        return []
    # strong candidate + weighted diversity
    chosen: List[Tuple[str, float]] = []
    if candidates:
        chosen.append(candidates[0])
    pool = candidates[1:]
    while len(chosen) < min(needed, len(candidates)) and pool:
        weights = [max(1.0, sc - 45.0) for _, sc in pool]
        idx = rng.choices(range(len(pool)), weights=weights, k=1)[0]
        chosen.append(pool.pop(idx))
    created: List[TreatyClause] = []
    for family, score in chosen[:needed]:
        reason = "initial_bundle" if initial else "amendment"
        created.append(create_clause(state, inst, family, reason=reason, base_score=score))
    return created


def apply_clause_effect(state: ClauseWorldState, clause: TreatyClause, inst: DiplomaticInstitution) -> Optional[Dict[str, Any]]:
    if clause.status not in {"active", "strained"}:
        return None
    world, reg, fl = world_and_maps(state)
    metrics = pair_metrics(state, inst)
    a = metrics["a"]
    b = metrics["b"]
    rel = metrics["rel"]
    union_ids = metrics["union_ids"]
    contact_ids = metrics["contact_ids"]
    effect: Dict[str, Any] = {"clause_id": clause.clause_id, "family": clause.family, "label_ja": clause.label_ja}
    factor = max(0.45, min(1.35, clause.intensity / 70.0))
    region_delta: Dict[str, float] = {}
    faction_events: Dict[str, Dict[str, float]] = {}
    target_ids = union_ids
    if clause.family == "grain_tariff_reduction":
        target_ids = union_ids
        region_delta = {"trade_routes": 2.2, "food": 1.4, "recordkeeping": 0.8}
        faction_events[a.faction_id] = apply_faction_delta(a, treasury=2.2)
        faction_events[b.faction_id] = apply_faction_delta(b, treasury=2.2)
    elif clause.family == "staple_grain_quota":
        donor = clause.terms.get("donor", a.faction_id)
        recipient = clause.terms.get("recipient", b.faction_id)
        donor_f = a if donor == a.faction_id else b
        recipient_f = b if recipient == b.faction_id else a
        target_ids = list(dict.fromkeys(recipient_f.regions + contact_ids[:2]))
        region_delta = {"food": 2.8, "legitimacy": 1.0, "death_rate": -0.8}
        faction_events[donor_f.faction_id] = apply_faction_delta(donor_f, treasury=-2.8)
        faction_events[recipient_f.faction_id] = apply_faction_delta(recipient_f, treasury=1.0, legitimacy=1.4)
    elif clause.family == "pilgrimage_protection":
        target_ids = clause.terms.get("protected_route", contact_ids) or contact_ids
        region_delta = {"faith_density": 2.1, "trade_routes": 1.0, "law_order": 1.0}
        faction_events[a.faction_id] = apply_faction_delta(a, legitimacy=1.2)
        faction_events[b.faction_id] = apply_faction_delta(b, legitimacy=1.2)
    elif clause.family == "joint_mining_rights":
        target_ids = union_ids
        region_delta = {"metal_stock": 2.4, "trade_routes": 0.9, "labor_force": 0.8}
        faction_events[a.faction_id] = apply_faction_delta(a, treasury=2.6)
        faction_events[b.faction_id] = apply_faction_delta(b, treasury=2.6)
    elif clause.family == "dynastic_marriage":
        target_ids = contact_ids
        region_delta = {"succession_stability": 2.0, "legitimacy": 0.8, "class_gap": 0.3}
        faction_events[a.faction_id] = apply_faction_delta(a, legitimacy=1.8)
        faction_events[b.faction_id] = apply_faction_delta(b, legitimacy=1.8)
    elif clause.family == "demilitarized_border":
        target_ids = contact_ids
        region_delta = {"law_order": 1.8, "housing": 0.8, "trade_routes": 0.8, "monster_density": -0.5}
        faction_events[a.faction_id] = apply_faction_delta(a, militarization=-1.2)
        faction_events[b.faction_id] = apply_faction_delta(b, militarization=-1.2)
    elif clause.family == "war_reparations":
        payer = clause.terms.get("payer", a.faction_id)
        recipient = clause.terms.get("recipient", b.faction_id)
        payer_f = a if payer == a.faction_id else b
        recipient_f = b if recipient == b.faction_id else a
        target_ids = list(dict.fromkeys(recipient_f.regions + contact_ids[:2]))
        region_delta = {"housing": 1.0, "recordkeeping": 0.8}
        faction_events[payer_f.faction_id] = apply_faction_delta(payer_f, treasury=-3.8, legitimacy=-0.4)
        faction_events[recipient_f.faction_id] = apply_faction_delta(recipient_f, treasury=3.6, legitimacy=0.8)
    elif clause.family == "prisoner_exchange":
        target_ids = contact_ids
        region_delta = {"housing": 0.8, "refugee_flow": -0.8, "law_order": 0.6}
        faction_events[a.faction_id] = apply_faction_delta(a, legitimacy=0.6)
        faction_events[b.faction_id] = apply_faction_delta(b, legitimacy=0.6)
    elif clause.family == "refugee_corridor":
        target_ids = clause.terms.get("corridor_regions", contact_ids) or contact_ids
        region_delta = {"refugee_flow": -1.6, "housing": 0.8, "death_rate": -0.7, "law_order": 0.5}
        faction_events[a.faction_id] = apply_faction_delta(a, treasury=-1.6, legitimacy=0.8)
        faction_events[b.faction_id] = apply_faction_delta(b, treasury=-1.6, legitimacy=0.8)
    elif clause.family == "joint_delve_salvage":
        target_ids = union_ids
        region_delta = {"trade_routes": 1.2, "recordkeeping": 1.0, "dungeon_density": -0.4, "soul_residue": 0.4}
        faction_events[a.faction_id] = apply_faction_delta(a, treasury=2.8)
        faction_events[b.faction_id] = apply_faction_delta(b, treasury=2.8)
    elif clause.family == "shared_seal_duty":
        target_ids = clause.terms.get("seal_sites", contact_ids) or contact_ids
        region_delta = {"interworld_intrusion": -2.4, "miasma_level": -1.2, "cycle_stability": 1.5, "faith_density": 0.6}
        faction_events[a.faction_id] = apply_faction_delta(a, treasury=-2.4, legitimacy=0.8)
        faction_events[b.faction_id] = apply_faction_delta(b, treasury=-2.4, legitimacy=0.8)
    elif clause.family == "river_navigation_rights":
        target_ids = union_ids
        region_delta = {"trade_routes": 2.0, "food": 1.0, "water": 1.0}
        faction_events[a.faction_id] = apply_faction_delta(a, treasury=2.1)
        faction_events[b.faction_id] = apply_faction_delta(b, treasury=2.1)
    elif clause.family == "hostage_exchange":
        target_ids = contact_ids
        region_delta = {"law_order": 0.8, "succession_stability": 0.7}
        faction_events[a.faction_id] = apply_faction_delta(a, legitimacy=0.4)
        faction_events[b.faction_id] = apply_faction_delta(b, legitimacy=0.4)
    elif clause.family == "relic_custody":
        target_ids = contact_ids
        region_delta = {"faith_density": 1.4, "recordkeeping": 1.4, "soul_residue": -0.4, "law_order": 0.5}
        faction_events[a.faction_id] = apply_faction_delta(a, legitimacy=0.8)
        faction_events[b.faction_id] = apply_faction_delta(b, legitimacy=0.8)
    applied_region = apply_region_delta(world, target_ids, region_delta, factor=factor)
    effect["regions"] = target_ids[:8]
    effect["region_delta"] = round_obj(applied_region, 3)
    effect["faction_delta"] = {fid: round_obj(delta, 3) for fid, delta in faction_events.items()}
    # affect the parent institution slightly
    inst.support = round(min(100.0, inst.support + clause.support * 0.008), 3)
    inst.breach_risk = round(max(0.0, inst.breach_risk - clause.support * 0.005 + clause.strain * 0.003), 3)
    return effect


def apply_clause_preseason_effects(state: ClauseWorldState) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    inst_map = state.institutional.institutions
    for clause in state.clauses.values():
        inst = inst_map.get(clause.institution_id)
        if not inst or inst.status not in active_states():
            continue
        ev = apply_clause_effect(state, clause, inst)
        if ev:
            events.append(ev)
    return round_obj(events, 3)


def maintain_clauses(state: ClauseWorldState) -> None:
    world, reg, fl = world_and_maps(state)
    inst_map = state.institutional.institutions
    for clause in list(state.clauses.values()):
        inst = inst_map.get(clause.institution_id)
        if inst is None:
            continue
        if inst.status not in active_states():
            if clause.status in {"active", "strained"}:
                end_clause(state, clause, inst, reason="institution_inactive", broken=False)
            continue
        sup_delta, strain_delta = clause_support_strain_delta(clause, inst, pair_metrics(state, inst))
        old_status = clause.status
        clause.support = round(max(0.0, min(100.0, clause.support + sup_delta)), 3)
        clause.strain = round(max(0.0, min(100.0, clause.strain + strain_delta)), 3)
        clause.intensity = round(max(8.0, min(100.0, clause.intensity + (clause.support - clause.strain) * 0.02)), 3)
        clause.history.append({
            "calendar_year": world.calendar_year,
            "season_index": world.season_index,
            "event": "maintained",
            "support": clause.support,
            "strain": clause.strain,
            "intensity": clause.intensity,
        })
        if clause.strain >= 82.0 or (clause.support <= 18.0 and clause.strain >= 58.0):
            end_clause(state, clause, inst, reason="clause_break_pressure", broken=True)
            continue
        if clause.strain >= 58.0 and clause.status == "active":
            clause.status = "strained"
        elif clause.strain < 45.0 and clause.support >= 35.0 and clause.status == "strained":
            clause.status = "active"
        if old_status != clause.status:
            event = {
                "kind": "status_shift",
                "clause_id": clause.clause_id,
                "institution_id": clause.institution_id,
                "label_ja": clause.label_ja,
                "from": old_status,
                "to": clause.status,
                "support": clause.support,
                "strain": clause.strain,
            }
            state.last_clause_events.append(round_obj(event, 3))
            world.history.append({"calendar_year": world.calendar_year, "season_index": world.season_index, "kind": "clause_status_shift", **round_obj(event, 3)})


def seek_clause_amendments(state: ClauseWorldState, initial: bool = False) -> None:
    for inst in active_institutions(state.institutional):
        bootstrap_clauses_for_institution(state, inst, initial=initial)


def advance_clause_world_one_season(state: ClauseWorldState, quest_budget: int = 12, intervention_budget: int = 4) -> Dict[str, Any]:
    state.last_clause_events = []
    preseason = apply_clause_preseason_effects(state)
    institution_result = v5.advance_institutional_world_one_season(state.institutional, quest_budget=quest_budget, intervention_budget=intervention_budget)
    maintain_clauses(state)
    seek_clause_amendments(state, initial=False)
    report = {
        "calendar_year": state.institutional.resolved.ext.world.calendar_year,
        "season_index": state.institutional.resolved.ext.world.season_index,
        "clause_upkeep_events": len(preseason),
        "clause_events": len(state.last_clause_events),
        "active_clauses": sum(1 for c in state.clauses.values() if c.status in {"active", "strained"}),
        "strained_clauses": sum(1 for c in state.clauses.values() if c.status == "strained"),
        "repudiated_clauses": sum(1 for c in state.clauses.values() if c.status == "repudiated"),
    }
    state.season_reports.append(report)
    state.clause_history.append({
        "calendar_year": state.institutional.resolved.ext.world.calendar_year,
        "season_index": state.institutional.resolved.ext.world.season_index,
        "pre_clause_effects": round_obj(preseason, 3),
        "clause_events": round_obj(state.last_clause_events, 3),
        "report": round_obj(report, 3),
    })
    return {
        **institution_result,
        "clause_preseason": round_obj(preseason, 3),
        "clause_events": round_obj(state.last_clause_events, 3),
        "clause_report": round_obj(report, 3),
    }


def build_clause_world(seed: int, regions: int, strategy: str = "balanced", schema_path: Path = v2.DEFAULT_SCHEMA_PATH) -> ClauseWorldState:
    institutional = v5.build_institutional_world(seed=seed, regions=regions, strategy=strategy, schema_path=schema_path)
    state = ClauseWorldState(institutional=institutional)
    seek_clause_amendments(state, initial=True)
    return state


def export_clauses(state: ClauseWorldState) -> Dict[str, Any]:
    return {cid: round_obj(asdict(clause), 3) for cid, clause in state.clauses.items()}


def export_clause_world(state: ClauseWorldState) -> Dict[str, Any]:
    return {
        "treaty_clause_world_version": "6.0",
        "institutional_world": v5.export_institutional_world(state.institutional),
        "clauses": export_clauses(state),
        "institution_clauses": {iid: list(ids) for iid, ids in state.institution_clauses.items()},
        "clause_history": round_obj(state.clause_history, 3),
        "last_clause_events": round_obj(state.last_clause_events, 3),
        "season_reports": round_obj(state.season_reports, 3),
    }


def summarize_clause_world(state: ClauseWorldState) -> str:
    world, reg, fl = world_and_maps(state)
    protagonist = state.institutional.resolved.protagonist
    lines: List[str] = []
    lines.append("# PBW Treaty Clause Summary")
    lines.append("")
    lines.append(f"- 世界名: **{world.world_name}**")
    lines.append(f"- 暦: **{world.calendar_name} {world.calendar_year}年**")
    if world.world_era and world.world_era.get("names"):
        lines.append(f"- 現在Era: **{world.world_era['names'].get('official', '無名時代')}** / 民間名 **{world.world_era['names'].get('common', '呼称なし')}**")
    else:
        lines.append("- 現在Era: **未成立**")
    lines.append(f"- 主人公存在級位: **{protagonist.existence_title}** ({protagonist.vessel_points:.1f})")
    lines.append(f"- 有効制度数: **{sum(1 for inst in state.institutional.institutions.values() if inst.status in active_states())}**")
    lines.append(f"- 有効条項数: **{sum(1 for c in state.clauses.values() if c.status in {'active', 'strained'})}**")
    lines.append("")

    lines.append("## 条項の多い制度")
    lines.append("")
    pairs = []
    for inst in state.institutional.institutions.values():
        active_clause_count = len(clause_ids_for_institution(state, inst.institution_id))
        if inst.status in active_states() and active_clause_count:
            pairs.append((active_clause_count, inst))
    if pairs:
        for count, inst in sorted(pairs, key=lambda x: (-x[0], -x[1].strength))[:12]:
            a = fl[inst.faction_a].label_ja
            b = fl[inst.faction_b].label_ja
            fams = [state.clauses[cid].label_ja for cid in clause_ids_for_institution(state, inst.institution_id)[:4]]
            lines.append(f"- {a} ↔ {b}: **{v5.KIND_LABELS[inst.kind]}** / clauses={count} / {', '.join(fams)}")
    else:
        lines.append("- 条項を伴う制度はまだ少ない")
    lines.append("")

    lines.append("## 代表的な条項")
    lines.append("")
    active_clause_list = [c for c in state.clauses.values() if c.status in {"active", "strained"}]
    if active_clause_list:
        for clause in sorted(active_clause_list, key=lambda c: (-c.intensity, c.label_ja))[:16]:
            inst = state.institutional.institutions[clause.institution_id]
            a = fl[inst.faction_a].label_ja
            b = fl[inst.faction_b].label_ja
            lines.append(f"- {a} ↔ {b}: **{clause.label_ja}** / status={clause.status} / intensity={clause.intensity:.1f} / support={clause.support:.1f} / strain={clause.strain:.1f}")
    else:
        lines.append("- 可視的な条項はまだ少ない")
    lines.append("")

    lines.append("## 争点化している条項")
    lines.append("")
    strained = [c for c in state.clauses.values() if c.status == "strained"]
    if strained:
        for clause in sorted(strained, key=lambda c: (-c.strain, c.label_ja))[:12]:
            inst = state.institutional.institutions[clause.institution_id]
            a = fl[inst.faction_a].label_ja
            b = fl[inst.faction_b].label_ja
            lines.append(f"- {a} ↔ {b}: **{clause.label_ja}** / strain={clause.strain:.1f} / support={clause.support:.1f}")
    else:
        lines.append("- 目立つ条項争点はない")
    lines.append("")

    lines.append("## 直近の条項イベント")
    lines.append("")
    if state.last_clause_events:
        for ev in state.last_clause_events[:18]:
            if ev.get("kind") == "formed":
                lines.append(f"- 成立: **{ev['label_ja']}** / reason={ev['reason']} / intensity={ev['intensity']:.1f}")
            elif ev.get("kind") in {"repudiated", "ended"}:
                lines.append(f"- 消滅: **{ev['label_ja']}** / reason={ev['reason']}")
            elif ev.get("kind") == "status_shift":
                lines.append(f"- 変調: **{ev['label_ja']}** / {ev['from']} → {ev['to']} / support={ev['support']:.1f} / strain={ev['strain']:.1f}")
            else:
                lines.append(f"- {json.dumps(ev, ensure_ascii=False)}")
    else:
        lines.append("- 今季の新しい条項イベントはない")
    lines.append("")

    lines.append("## 条項化で見える制度の差")
    lines.append("")
    for inst in sorted([i for i in state.institutional.institutions.values() if i.status in active_states()], key=lambda i: (-i.strength, i.kind))[:12]:
        cids = clause_ids_for_institution(state, inst.institution_id)
        if not cids:
            continue
        rel = current_relation(state.institutional, inst.faction_a, inst.faction_b)
        a = fl[inst.faction_a].label_ja
        b = fl[inst.faction_b].label_ja
        lines.append(f"- {a} ↔ {b}: relation={rel.score if rel else 0.0:.1f}/{rel.status if rel else '不明'}, institution={v5.KIND_LABELS[inst.kind]}, clauses={len(cids)}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PBW treaty clauses v6")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--regions", type=int, default=20)
    parser.add_argument("--seasons", type=int, default=8)
    parser.add_argument("--quests", type=int, default=12)
    parser.add_argument("--budget", type=int, default=4)
    parser.add_argument("--strategy", type=str, default="balanced", choices=sorted(v4.RESOLUTION_STRATEGIES.keys()))
    parser.add_argument("--schema", type=Path, default=v2.DEFAULT_SCHEMA_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state = build_clause_world(seed=args.seed, regions=args.regions, strategy=args.strategy, schema_path=args.schema)
    for _ in range(args.seasons):
        advance_clause_world_one_season(state, quest_budget=args.quests, intervention_budget=args.budget)
    out_json = BASE_DIR / f"pbw_generated_world_seed{args.seed}_v6_treaty_clauses.json"
    out_md = BASE_DIR / f"pbw_generated_world_seed{args.seed}_v6_treaty_clauses_summary.md"
    out_json.write_text(json.dumps(export_clause_world(state), ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(summarize_clause_world(state), encoding="utf-8")
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
