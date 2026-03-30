"""PBW World Turn Algorithm v1

A lightweight, implementation-oriented skeleton aligned with
pbw_world_simulator_schema_v3.json.

This module is intentionally incomplete in content breadth, but complete in shape:
- seasonal region update
- operator scoring
- phenomenon generation
- regional phase clustering
- world era synthesis
- protagonist vessel gain evaluation

All macro variables are normalized to 0..100.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from statistics import mean
from typing import Dict, List, Tuple, Iterable, Optional

ATTRS = [
    "fire", "water", "wind", "earth", "light", "dark",
    "explosion", "ice", "thunder", "metal", "healing", "mind",
]

CORE_KEYS = [
    "food", "water", "housing", "timber", "metal_stock", "medicine", "trade_routes", "labor_force",
    "population", "birth_rate", "death_rate", "age_structure", "refugee_flow", "monster_density", "plague_load",
    "legitimacy", "faith_density", "class_gap", "slavery_rate", "succession_stability", "law_order", "recordkeeping", "racial_tension",
    "mana_level", "miasma_level", "divine_interference", "interworld_intrusion", "dungeon_density", "cycle_stability", "soul_residue",
]

ISSUE_TAGS = [
    "food_scarcity", "housing_crisis", "mana_shortage", "mana_surplus", "miasma_flood",
    "dungeon_boom", "population_boom", "divine_war", "interworld_intrusion"
]

PHENOMENON_SIGNATURES: Dict[Tuple[str, str], Dict[str, float]] = {
    ("food", "scarcity"): {"earth": 0.45, "water": 0.25, "healing": 0.20, "metal": 0.10},
    ("mana_level", "surplus"): {"light": 0.25, "water": 0.20, "mind": 0.25, "wind": 0.10, "dark": 0.20},
    ("mana_level", "scarcity"): {"earth": 0.25, "metal": 0.20, "light": 0.15, "mind": 0.10},
    ("miasma_level", "surplus"): {"dark": 0.30, "explosion": 0.15, "mind": 0.10, "earth": 0.10},
    ("dungeon_density", "fixation"): {"earth": 0.20, "dark": 0.25, "metal": 0.10, "mystic": 0.0},
    ("interworld_intrusion", "runaway"): {"mind": 0.25, "dark": 0.20, "water": 0.10, "light": 0.10},
    ("legitimacy", "collapse"): {"light": 0.20, "dark": 0.20, "earth": 0.10, "mind": 0.10},
    ("faith_density", "runaway"): {"light": 0.30, "mind": 0.25, "water": 0.10, "dark": 0.10},
}
# Clean unsupported key introduced above if present.
for sig in PHENOMENON_SIGNATURES.values():
    sig.pop("mystic", None)

# Sparse influence matrix around centered values (x-50)/50.
CROSS_INFLUENCE: Dict[str, Dict[str, float]] = {
    "food": {
        "water": 0.18, "labor_force": 0.16, "trade_routes": 0.10, "medicine": 0.06,
        "population": -0.20, "plague_load": -0.14, "monster_density": -0.16, "miasma_level": -0.12,
    },
    "housing": {
        "timber": 0.16, "metal_stock": 0.10, "labor_force": 0.12,
        "population": -0.18, "refugee_flow": -0.18, "miasma_level": -0.08,
    },
    "legitimacy": {
        "food": 0.10, "housing": 0.05, "law_order": 0.18, "recordkeeping": 0.10, "faith_density": 0.08,
        "class_gap": -0.14, "slavery_rate": -0.10, "refugee_flow": -0.08, "racial_tension": -0.16,
    },
    "law_order": {
        "legitimacy": 0.16, "recordkeeping": 0.12, "trade_routes": 0.08,
        "miasma_level": -0.10, "monster_density": -0.12, "racial_tension": -0.14,
    },
    "population": {
        "food": 0.16, "housing": 0.10, "medicine": 0.08,
        "plague_load": -0.18, "monster_density": -0.10, "miasma_level": -0.08,
    },
    "faith_density": {
        "divine_interference": 0.18, "recordkeeping": 0.08, "legitimacy": 0.06,
        "interworld_intrusion": 0.06, "class_gap": -0.06,
    },
    "mana_level": {
        "cycle_stability": 0.16, "faith_density": 0.08, "water": 0.05,
        "population": -0.10, "interworld_intrusion": -0.12, "dungeon_density": -0.10,
    },
    "miasma_level": {
        "dungeon_density": 0.18, "soul_residue": 0.14, "interworld_intrusion": 0.10,
        "cycle_stability": -0.14, "law_order": -0.06,
    },
    "dungeon_density": {
        "miasma_level": 0.18, "soul_residue": 0.14, "law_order": -0.10, "cycle_stability": -0.10,
    },
    "interworld_intrusion": {
        "mana_level": 0.10, "miasma_level": 0.10, "cycle_stability": -0.18, "recordkeeping": -0.04,
    },
}

EQUILIBRIUM_PULL: Dict[str, float] = {
    "food": 0.08, "housing": 0.07, "population": 0.05, "legitimacy": 0.05,
    "law_order": 0.06, "faith_density": 0.04, "mana_level": 0.06, "miasma_level": 0.05,
    "dungeon_density": 0.04, "interworld_intrusion": 0.04,
}

ISSUE_TO_SENSITIVITY_TAG = {
    "food_scarcity": "food_scarcity",
    "housing_crisis": "housing_crisis",
    "mana_shortage": "mana_shortage",
    "mana_surplus": "mana_surplus",
    "miasma_flood": "miasma_flood",
    "dungeon_boom": "dungeon_boom",
    "population_boom": "population_boom",
    "divine_war": "divine_war",
    "interworld_intrusion": "interworld_intrusion",
}

MEDIA_WEIGHTS = {
    "law": 1.30,
    "architecture": 1.15,
    "ritual": 1.20,
    "song": 0.90,
    "chronicle": 1.00,
    "curse": 1.10,
    "soul_residue": 1.35,
    "place_name": 0.85,
}


def clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, x))


def center(x: float) -> float:
    return (x - 50.0) / 50.0


def scarcity(x: float, low: float = 40.0) -> float:
    return max(0.0, min(1.0, (low - x) / low))


def surplus(x: float, high: float = 70.0) -> float:
    return max(0.0, min(1.0, (x - high) / max(1.0, 100.0 - high)))


def imbalance(a: float, b: float) -> float:
    return abs(a - b) / 100.0


def acceleration(now: float, prev: float) -> float:
    return max(0.0, min(1.0, abs(now - prev) / 20.0))


def rupture(now: float, prev: float) -> float:
    return max(0.0, min(1.0, max(0.0, prev - now) / 25.0))


def collapse(now: float, prev: float) -> float:
    return scarcity(now, 35.0) * max(0.0, min(1.0, (prev - now) / 15.0))


def fixation(now: float, prev: float) -> float:
    return surplus(now, 70.0) * max(0.0, min(1.0, 1.0 - abs(now - prev) / 10.0))


def runaway(now: float, prev: float) -> float:
    return surplus(now, 70.0) * max(0.0, min(1.0, max(0.0, now - prev) / 15.0))


def contamination(pure: float, pollute: float) -> float:
    return max(0.0, min(1.0, pollute / (pure + pollute + 1.0)))


@dataclass
class LegacyMedium:
    medium: str
    tags: List[str]
    intensity: float  # 0..1


@dataclass
class Phenomenon:
    region_id: str
    variable: str
    operator: str
    score: float
    tags: List[str]
    signature: Dict[str, float]
    names: Dict[str, str] = field(default_factory=dict)


@dataclass
class RegionState:
    region_id: str
    biome_tags: List[str]
    dominant_races: Dict[str, float]  # race_id -> share 0..1
    resonance: Dict[str, float]       # attr -> 0..1
    values: Dict[str, float]          # core values 0..100
    prev_values: Dict[str, float]
    equilibrium_targets: Dict[str, float]
    history_window: List[Dict[str, float]] = field(default_factory=list)
    legacies: List[LegacyMedium] = field(default_factory=list)
    adjacent: List[str] = field(default_factory=list)


@dataclass
class FactionState:
    faction_id: str
    faction_type: str
    regions: List[str]
    policy_profile: Dict[str, float] = field(default_factory=dict)
    legitimacy: float = 50.0
    militarization: float = 50.0


@dataclass
class ProtagonistImpact:
    affected_population: int
    systems_affected_count: int
    impact_tier: str  # micro/local/regional/macro/meta/mythic
    persistence_years: float
    sacrifice_cost: float  # 0..1
    law_deformation: float # 0..1
    media_outputs: Dict[str, float]  # medium -> intensity 0..1


IMPACT_TIER = {
    "micro": 1,
    "local": 2,
    "regional": 4,
    "macro": 8,
    "meta": 13,
    "mythic": 21,
}


def weighted_mean(pairs: Iterable[Tuple[float, float]], default: float = 1.0) -> float:
    total_w = 0.0
    acc = 0.0
    for value, weight in pairs:
        acc += value * weight
        total_w += weight
    return acc / total_w if total_w > 0 else default


def apply_equilibrium_pull(region: RegionState) -> None:
    for key, pull in EQUILIBRIUM_PULL.items():
        if key in region.values and key in region.equilibrium_targets:
            region.values[key] = clamp(region.values[key] + pull * (region.equilibrium_targets[key] - region.values[key]))



def apply_cross_influences(region: RegionState) -> None:
    snapshot = dict(region.values)
    for target, srcs in CROSS_INFLUENCE.items():
        if target not in region.values:
            continue
        delta = 0.0
        for src, coeff in srcs.items():
            if src in snapshot:
                delta += coeff * center(snapshot[src])
        # seasonal update scale
        region.values[target] = clamp(region.values[target] + 8.0 * delta)



def compute_pressures(region: RegionState) -> Dict[str, float]:
    v = region.values
    p = region.prev_values

    food_stress = (
        0.35 * scarcity(v["food"], 40)
        + 0.20 * rupture(v["trade_routes"], p["trade_routes"])
        + 0.15 * surplus(v["population"], 65)
        + 0.15 * (v["plague_load"] / 100.0)
        + 0.15 * (v["refugee_flow"] / 100.0)
    )
    housing_stress = (
        0.40 * scarcity(v["housing"], 45)
        + 0.20 * surplus(v["population"], 65)
        + 0.20 * (v["refugee_flow"] / 100.0)
        + 0.10 * rupture(v["law_order"], p["law_order"])
        + 0.10 * contamination(v["housing"], v["miasma_level"])
    )
    faith_schism = (
        0.30 * runaway(v["faith_density"], p["faith_density"])
        + 0.20 * (v["divine_interference"] / 100.0)
        + 0.20 * collapse(v["legitimacy"], p["legitimacy"])
        + 0.15 * scarcity(v["recordkeeping"], 40)
        + 0.15 * imbalance(v["faith_density"], v["law_order"])
    )
    legitimacy_crisis = (
        0.30 * collapse(v["legitimacy"], p["legitimacy"])
        + 0.20 * (v["class_gap"] / 100.0)
        + 0.15 * food_stress
        + 0.15 * scarcity(v["succession_stability"], 45)
        + 0.10 * (v["slavery_rate"] / 100.0)
        + 0.10 * faith_schism
    )
    mana_crisis = (
        0.40 * scarcity(v["mana_level"], 40)
        + 0.20 * rupture(v["cycle_stability"], p["cycle_stability"])
        + 0.20 * (v["interworld_intrusion"] / 100.0)
        + 0.20 * imbalance(v["mana_level"], v["population"])
    )
    mana_surge = (
        0.35 * surplus(v["mana_level"], 70)
        + 0.20 * runaway(v["divine_interference"], p["divine_interference"])
        + 0.15 * imbalance(v["mana_level"], v["cycle_stability"])
        + 0.15 * (v["faith_density"] / 100.0)
        + 0.15 * resonance_scalar(region, {"light": 0.25, "water": 0.20, "mind": 0.25})
    )
    miasma_bloom = (
        0.35 * surplus(v["miasma_level"], 70)
        + 0.20 * fixation(v["dungeon_density"], p["dungeon_density"])
        + 0.15 * rupture(v["cycle_stability"], p["cycle_stability"])
        + 0.15 * (v["monster_density"] / 100.0)
        + 0.15 * (v["soul_residue"] / 100.0)
    )
    dungeon_fixation_pressure = (
        0.35 * fixation(v["dungeon_density"], p["dungeon_density"])
        + 0.20 * surplus(v["miasma_level"], 70)
        + 0.20 * (v["soul_residue"] / 100.0)
        + 0.15 * rupture(v["cycle_stability"], p["cycle_stability"])
        + 0.10 * imbalance(v["dungeon_density"], v["law_order"])
    )
    interworld_bleed = (
        0.40 * runaway(v["interworld_intrusion"], p["interworld_intrusion"])
        + 0.20 * rupture(v["cycle_stability"], p["cycle_stability"])
        + 0.15 * surplus(v["mana_level"], 70)
        + 0.15 * surplus(v["miasma_level"], 70)
        + 0.10 * scarcity(v["recordkeeping"], 40)
    )
    demon_lord_pressure = (
        0.30 * miasma_bloom
        + 0.20 * legitimacy_crisis
        + 0.20 * faith_schism
        + 0.15 * scarcity(v["law_order"], 40)
        + 0.15 * (v["monster_density"] / 100.0)
    )

    return {
        "food_stress": min(1.0, food_stress),
        "housing_stress": min(1.0, housing_stress),
        "faith_schism": min(1.0, faith_schism),
        "legitimacy_crisis": min(1.0, legitimacy_crisis),
        "mana_crisis": min(1.0, mana_crisis),
        "mana_surge": min(1.0, mana_surge),
        "miasma_bloom": min(1.0, miasma_bloom),
        "dungeon_fixation": min(1.0, dungeon_fixation_pressure),
        "interworld_bleed": min(1.0, interworld_bleed),
        "demon_lord_pressure": min(1.0, demon_lord_pressure),
    }



def resonance_scalar(region: RegionState, signature: Dict[str, float]) -> float:
    # region resonance is assumed 0..1
    total = 0.0
    weight = 0.0
    for attr, coeff in signature.items():
        total += region.resonance.get(attr, 0.0) * coeff
        weight += coeff
    score = total / weight if weight > 0 else 0.0
    return 0.5 + score  # ~0.5..1.5



def legacy_amp(region: RegionState, tags: List[str]) -> float:
    matches = 0
    intensity = 0.0
    for legacy in region.legacies:
        if any(tag in legacy.tags for tag in tags):
            matches += 1
            intensity += legacy.intensity
    return 1.0 + 0.15 * matches + 0.10 * intensity



def family_affinity(variable: str, operator: str) -> float:
    table = {
        ("food", "scarcity"): 1.20,
        ("food", "surplus"): 0.80,
        ("mana_level", "surplus"): 1.10,
        ("mana_level", "scarcity"): 1.10,
        ("miasma_level", "surplus"): 1.15,
        ("dungeon_density", "fixation"): 1.20,
        ("interworld_intrusion", "runaway"): 1.25,
        ("legitimacy", "collapse"): 1.10,
        ("faith_density", "runaway"): 1.15,
    }
    return table.get((variable, operator), 0.75)



def build_tags(variable: str, operator: str) -> List[str]:
    tags = [variable, operator]
    if variable == "food" and operator == "scarcity":
        tags += ["famine", "migration", "hoarding"]
    elif variable == "mana_level" and operator == "surplus":
        tags += ["miracle", "overload", "dream", "sanctification"]
    elif variable == "mana_level" and operator == "scarcity":
        tags += ["arcane_decline", "ritual_failure", "healer_crisis"]
    elif variable == "miasma_level" and operator == "surplus":
        tags += ["corruption", "monster", "mutation", "dungeon"]
    elif variable == "dungeon_density" and operator == "fixation":
        tags += ["deep_layer", "seal", "loot", "territorialization"]
    elif variable == "interworld_intrusion" and operator == "runaway":
        tags += ["rift", "otherworld", "translation", "boundary_failure"]
    elif variable == "legitimacy" and operator == "collapse":
        tags += ["succession", "civil_war", "tax_refusal"]
    elif variable == "faith_density" and operator == "runaway":
        tags += ["prophecy", "schism", "pilgrimage", "inquisition"]
    return tags



def phenomenon_base_score(region: RegionState, variable: str, operator: str) -> float:
    now = region.values[variable]
    prev = region.prev_values[variable]
    if operator == "scarcity":
        return scarcity(now, 40)
    if operator == "surplus":
        return surplus(now, 70)
    if operator == "fixation":
        return fixation(now, prev)
    if operator == "runaway":
        return runaway(now, prev)
    if operator == "collapse":
        return collapse(now, prev)
    return 0.0



def race_amp(region: RegionState, race_profiles: Dict[str, Dict], issue_tag: str) -> float:
    vals = []
    for race_id, share in region.dominant_races.items():
        macro = race_profiles.get(race_id, {}).get("simulation_genome", {}).get("macro_sensitivity", {})
        level = macro.get(issue_tag, "medium")
        numeric = {
            "very_low": 0.70,
            "low": 0.80,
            "low_to_medium": 0.90,
            "medium": 1.00,
            "medium_high": 1.10,
            "high": 1.20,
            "very_high": 1.35,
        }.get(level, 1.0)
        vals.append((numeric, share))
    return weighted_mean(vals, default=1.0)



def duration_amp(region: RegionState, variable: str, operator: str) -> float:
    # Count last 8 turns with same operator above threshold.
    if not region.history_window:
        return 1.0
    count = 0
    for hist in region.history_window:
        now = hist.get(variable, 50.0)
        prev = hist.get(f"prev_{variable}", now)
        score = 0.0
        if operator == "scarcity":
            score = scarcity(now, 40)
        elif operator == "surplus":
            score = surplus(now, 70)
        elif operator == "fixation":
            score = fixation(now, prev)
        elif operator == "runaway":
            score = runaway(now, prev)
        elif operator == "collapse":
            score = collapse(now, prev)
        if score >= 0.25:
            count += 1
    return 1.0 + min(0.6, 0.08 * count)



def generate_phenomena(region: RegionState, race_profiles: Dict[str, Dict]) -> List[Phenomenon]:
    candidates: List[Tuple[str, str, str]] = [
        ("food", "scarcity", "food_scarcity"),
        ("housing", "scarcity", "housing_crisis"),
        ("mana_level", "scarcity", "mana_shortage"),
        ("mana_level", "surplus", "mana_surplus"),
        ("miasma_level", "surplus", "miasma_flood"),
        ("dungeon_density", "fixation", "dungeon_boom"),
        ("population", "surplus", "population_boom"),
        ("interworld_intrusion", "runaway", "interworld_intrusion"),
        ("faith_density", "runaway", "divine_war"),
        ("legitimacy", "collapse", "divine_war"),
    ]
    result: List[Phenomenon] = []
    for variable, operator, issue_tag in candidates:
        base = phenomenon_base_score(region, variable, operator)
        if base < 0.18:
            continue
        signature = PHENOMENON_SIGNATURES.get((variable, operator), {})
        score = (
            base
            * family_affinity(variable, operator)
            * resonance_scalar(region, signature)
            * race_amp(region, race_profiles, issue_tag)
            * legacy_amp(region, build_tags(variable, operator))
            * duration_amp(region, variable, operator)
        )
        if score >= 0.32:
            result.append(
                Phenomenon(
                    region_id=region.region_id,
                    variable=variable,
                    operator=operator,
                    score=round(score, 4),
                    tags=build_tags(variable, operator),
                    signature=signature,
                )
            )
    return sorted(result, key=lambda p: p.score, reverse=True)



def name_phenomenon(p: Phenomenon, main_god_name: str, year: int) -> Dict[str, str]:
    lexeme = {
        ("food", "scarcity"): ("施穀", "灰麦", "断穀", "飢饉"),
        ("mana_level", "surplus"): ("星脈", "白く眠らぬ", "偽潮", "星脈祈誦"),
        ("mana_level", "scarcity"): ("術式", "灯の痩せた", "断光", "枯灯"),
        ("miasma_level", "surplus"): ("瘴潮", "黒い胞子の", "穢環", "瘴域"),
        ("dungeon_density", "fixation"): ("深層封鎖", "穴の開いた", "逆封", "深層固洞"),
        ("interworld_intrusion", "runaway"): ("裂境", "向こう側が近い", "逆輪", "異界浸出"),
        ("legitimacy", "collapse"): ("冠位断絶", "王のいない", "偽冠", "断冠"),
        ("faith_density", "runaway"): ("神託巡礼", "泣く鐘の", "逆祈", "信仰熱"),
    }.get((p.variable, p.operator), ("再編", "名もなき", "断", "変相"))
    official, popular_stem, heretical_stem, chronicle_stem = lexeme
    return {
        "official": f"{official}期",
        "popular": f"{popular_stem}年",
        "heretical": f"{heretical_stem}禍",
        "chronicle": f"{main_god_name}暦{year}年より続く{chronicle_stem}期",
    }



def cluster_regional_phases(regions: List[RegionState], region_phenomena: Dict[str, List[Phenomenon]]) -> List[Dict]:
    # Minimal clustering: same dominant (variable, operator) among adjacent regions.
    by_key: Dict[Tuple[str, str], List[Phenomenon]] = {}
    for phs in region_phenomena.values():
        for p in phs:
            by_key.setdefault((p.variable, p.operator), []).append(p)

    phases = []
    for key, items in by_key.items():
        covered_regions = {p.region_id for p in items}
        if len(covered_regions) < 1:
            continue
        score = mean([p.score for p in items]) * min(1.0, 0.5 + 0.15 * len(covered_regions))
        if score >= 0.55:
            tags = sorted({t for p in items for t in p.tags})
            phases.append({
                "key": key,
                "regions": sorted(covered_regions),
                "score": round(score, 4),
                "tags": tags,
            })
    return sorted(phases, key=lambda x: x["score"], reverse=True)



def synthesize_world_era(phases: List[Dict], total_regions: int) -> Optional[Dict]:
    if not phases:
        return None
    best = phases[0]
    geographic_coverage = len(best["regions"]) / max(1, total_regions)
    score = 0.30 * best["score"] + 0.25 * geographic_coverage + 0.20 * min(1.0, len(best["regions"]) / 4.0) + 0.15 * min(1.0, len(best["tags"]) / 8.0) + 0.10 * 0.5
    if score < 0.68:
        return None
    return {
        "driver": best["key"],
        "regions": best["regions"],
        "tags": best["tags"],
        "score": round(score, 4),
    }



def evaluate_protagonist_gain(impact: ProtagonistImpact) -> float:
    tier = IMPACT_TIER[impact.impact_tier]
    base = (
        sqrt(impact.affected_population + 1)
        * tier
        * (0.6 + 0.2 * impact.systems_affected_count)
        * (0.5 + impact.persistence_years / 20.0)
        * (1.0 + impact.sacrifice_cost)
        * (1.0 + impact.law_deformation)
    )
    total = 0.0
    for medium, intensity in impact.media_outputs.items():
        total += base * MEDIA_WEIGHTS.get(medium, 1.0) * intensity
    return round(total, 4)



def advance_region_one_season(region: RegionState, race_profiles: Dict[str, Dict]) -> Tuple[RegionState, Dict[str, float], List[Phenomenon]]:
    # keep previous snapshot
    region.prev_values = dict(region.values)

    apply_equilibrium_pull(region)
    apply_cross_influences(region)

    pressures = compute_pressures(region)
    phenomena = generate_phenomena(region, race_profiles)

    # push to history window (compressed form)
    hist = dict(region.values)
    for k, v in region.prev_values.items():
        hist[f"prev_{k}"] = v
    region.history_window.append(hist)
    if len(region.history_window) > 8:
        region.history_window.pop(0)

    return region, pressures, phenomena


if __name__ == "__main__":
    # Minimal demonstration
    race_profiles = {
        "human": {"simulation_genome": {"macro_sensitivity": {"food_scarcity": "high", "mana_surplus": "medium_high", "divine_war": "high"}}},
        "elf": {"simulation_genome": {"macro_sensitivity": {"food_scarcity": "medium", "mana_surplus": "high", "interworld_intrusion": "high"}}},
        "fey": {"simulation_genome": {"macro_sensitivity": {"mana_surplus": "very_high", "interworld_intrusion": "high", "divine_war": "medium_high"}}},
    }

    region = RegionState(
        region_id="moon_tide_coast",
        biome_tags=["coast", "mist_forest"],
        dominant_races={"elf": 0.5, "fey": 0.2, "human": 0.3},
        resonance={a: 0.1 for a in ATTRS},
        values={k: 50.0 for k in CORE_KEYS},
        prev_values={k: 50.0 for k in CORE_KEYS},
        equilibrium_targets={k: 50.0 for k in CORE_KEYS},
    )
    region.resonance.update({"water": 0.9, "mind": 0.8, "light": 0.6})
    region.values.update({
        "mana_level": 84.0,
        "faith_density": 78.0,
        "divine_interference": 74.0,
        "cycle_stability": 46.0,
        "interworld_intrusion": 58.0,
        "recordkeeping": 43.0,
    })
    region.prev_values.update({
        "mana_level": 72.0,
        "faith_density": 66.0,
        "divine_interference": 60.0,
        "interworld_intrusion": 45.0,
        "cycle_stability": 53.0,
    })

    _, pressures, phenomena = advance_region_one_season(region, race_profiles)
    print("Pressures:")
    for k, v in pressures.items():
        print(f"  {k}: {v:.3f}")
    print("\nPhenomena:")
    for p in phenomena[:5]:
        p.names = name_phenomenon(p, main_god_name="ミレイア", year=312)
        print(f"  {p.variable} x {p.operator} -> {p.score:.3f} / {p.names['official']} / {p.names['popular']}")
