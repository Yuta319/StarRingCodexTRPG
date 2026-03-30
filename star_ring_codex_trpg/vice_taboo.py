from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Iterable, List, Mapping
import copy
import json

from .errors import AssetLoadError
from .paths import USER_SHARED_ROOT, require_path


VICE_CATALOG_PATH = USER_SHARED_ROOT / "pbw_vice_catalog_v1.json"
TABOO_CATALOG_PATH = USER_SHARED_ROOT / "pbw_taboo_catalog_v1.json"
FREE_ACTION_RESULT_SCHEMA_PATH = USER_SHARED_ROOT / "pbw_free_action_structured_result_schema_v1.json"


def _load_json(path, label: str) -> Dict[str, Any]:
    try:
        target = require_path(path, label)
        return json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetLoadError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise AssetLoadError(f"{label} is not valid JSON: {exc}") from exc


@lru_cache(maxsize=1)
def _vice_catalog_cached() -> Dict[str, Any]:
    return _load_json(VICE_CATALOG_PATH, "Vice catalog")


@lru_cache(maxsize=1)
def _taboo_catalog_cached() -> Dict[str, Any]:
    return _load_json(TABOO_CATALOG_PATH, "Taboo catalog")


@lru_cache(maxsize=1)
def _free_action_schema_cached() -> Dict[str, Any]:
    return _load_json(FREE_ACTION_RESULT_SCHEMA_PATH, "Free action structured result schema")


def vice_catalog() -> Dict[str, Any]:
    return copy.deepcopy(_vice_catalog_cached())


def taboo_catalog() -> Dict[str, Any]:
    return copy.deepcopy(_taboo_catalog_cached())


def free_action_result_schema() -> Dict[str, Any]:
    return copy.deepcopy(_free_action_schema_cached())


VICE_CATALOG = vice_catalog()
TABOO_CATALOG = taboo_catalog()
VICE_ENTRY_MAP = {entry["id"]: entry for entry in VICE_CATALOG.get("entries", [])}
TABOO_ENTRY_MAP = {entry["id"]: entry for entry in TABOO_CATALOG.get("entries", [])}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, float(value))), 1)


def _average(values: Iterable[float], fallback: float = 0.0) -> float:
    materialized = [float(value) for value in values]
    if not materialized:
        return float(fallback)
    return sum(materialized) / len(materialized)


def _entry_affinity_match(entry: Mapping[str, Any], role_label: str) -> bool:
    lowered = str(role_label).strip()
    for raw_affinity in entry.get("role_slot_affinities", []):
        affinity = str(raw_affinity).strip()
        if not affinity:
            continue
        if affinity in lowered or lowered in affinity:
            return True
    return False


def exposure_profile_for_role(role_label: str, *, home: str = "world") -> Dict[str, Any]:
    vice_ids = [entry_id for entry_id, entry in VICE_ENTRY_MAP.items() if _entry_affinity_match(entry, role_label)]
    taboo_ids = [entry_id for entry_id, entry in TABOO_ENTRY_MAP.items() if _entry_affinity_match(entry, role_label)]
    if not vice_ids and home in {"hub", "dungeon"}:
        vice_ids = ["fraud", "theft"] if home == "hub" else ["smuggling", "vice_market"]
    if not taboo_ids and home == "dungeon":
        taboo_ids = ["sealed_text_usage", "ward_breaking"]
    motive_axes: List[str] = []
    for vice_id in vice_ids:
        motive_axes.extend(VICE_ENTRY_MAP[vice_id].get("primary_motives", [])[:2])
    for taboo_id in taboo_ids:
        motive_axes.extend(TABOO_ENTRY_MAP[taboo_id].get("primary_motives", [])[:1])
    deduped_axes: List[str] = []
    seen: set[str] = set()
    for axis in motive_axes:
        text = str(axis).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped_axes.append(text)
        if len(deduped_axes) >= 6:
            break
    return {
        "viceIds": vice_ids[:4],
        "tabooIds": taboo_ids[:4],
        "motivePressure": deduped_axes,
    }


def exposure_profile_for_slot(npc: Mapping[str, Any]) -> Dict[str, Any]:
    explicit_vice_ids = [str(entry_id).strip() for entry_id in list(npc.get("viceExposure", [])) if str(entry_id).strip()]
    explicit_taboo_ids = [str(entry_id).strip() for entry_id in list(npc.get("tabooExposure", [])) if str(entry_id).strip()]
    if not explicit_vice_ids and not explicit_taboo_ids:
        return exposure_profile_for_role(str(npc.get("roleLabel", "")), home=str(npc.get("locationKey", "world")))

    motive_axes: List[str] = []
    for vice_id in explicit_vice_ids:
        motive_axes.extend(VICE_ENTRY_MAP.get(vice_id, {}).get("primary_motives", [])[:2])
    for taboo_id in explicit_taboo_ids:
        motive_axes.extend(TABOO_ENTRY_MAP.get(taboo_id, {}).get("primary_motives", [])[:1])

    deduped_axes: List[str] = []
    seen: set[str] = set()
    for axis in motive_axes:
        text = str(axis).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped_axes.append(text)
        if len(deduped_axes) >= 6:
            break
    return {
        "viceIds": explicit_vice_ids[:4],
        "tabooIds": explicit_taboo_ids[:4],
        "motivePressure": deduped_axes,
    }


def _vice_sources(campaign_state: Mapping[str, Any], law_order: float) -> List[str]:
    hub = campaign_state.get("hub", {})
    event_catalog = campaign_state.get("events", {}).get("catalog", {})
    current_event = event_catalog.get(campaign_state.get("currentEventId"), {})
    lines = []
    if float(hub.get("heat", 0.0)) >= 50:
        lines.append("拠点の緊張が高く、横流しや見逃しが起こりやすい。")
    if float(current_event.get("pressure", 0.0)) >= 58:
        lines.append("いまの事件が長引き、保身や偽装に流れやすい。")
    if law_order <= 46:
        lines.append("地域の秩序が薄く、抜け道と口止めが通りやすい。")
    return lines[:3]


def _taboo_sources(campaign_state: Mapping[str, Any], distortion: float) -> List[str]:
    dungeon = campaign_state.get("dungeon", {})
    lines = []
    if float(dungeon.get("sealIntegrity", 100.0)) <= 60:
        lines.append("封印が弱く、禁じ手に頼る誘惑が強い。")
    if float(dungeon.get("threat", 0.0)) >= 52:
        lines.append("坑路の危険が高く、儀礼破りでも進みたくなる。")
    if distortion >= 52:
        lines.append("世界のゆらぎが強く、禁忌の痕が残りやすい。")
    return lines[:3]


def derive_vice_taboo_state(world_state: Mapping[str, Any], campaign_state: Mapping[str, Any]) -> Dict[str, Any]:
    resolved_world = world_state.get("resolved_world", {})
    regions = resolved_world.get("regions", {})
    institutions = resolved_world.get("institutions", {})
    cycle_state = world_state.get("cycle_state", {})
    npcs = campaign_state.get("npcs", {})
    hub = campaign_state.get("hub", {})
    dungeon = campaign_state.get("dungeon", {})
    event_catalog = campaign_state.get("events", {}).get("catalog", {})
    current_event = event_catalog.get(campaign_state.get("currentEventId"), {})

    law_order = _average((region.get("values", {}).get("law_order", 50.0) for region in regions.values()), 50.0)
    region_legitimacy = _average((region.get("values", {}).get("legitimacy", 50.0) for region in regions.values()), 50.0)
    institution_support = _average((institution.get("support", 50.0) for institution in institutions.values()), 50.0)
    trust = _average((npc.get("trust", 50.0) for npc in npcs.values()), 50.0)
    stress = _average((npc.get("stress", 50.0) for npc in npcs.values()), 50.0)
    hinted_count = sum(1 for npc in npcs.values() if npc.get("secretState") == "hinted")
    exposed_count = sum(1 for npc in npcs.values() if npc.get("secretState") == "exposed")
    known_weaknesses = sum(1 for npc in npcs.values() if npc.get("knownWeakness"))
    role_slot_suspicion = _average((value for value in dict(campaign_state.get("roleSlotSuspicion") or {}).values()), 0.0)
    role_slot_distrust = _average((value for value in dict(campaign_state.get("roleSlotDistrust") or {}).values()), 0.0)
    role_slot_retaliation = _average((value for value in dict(campaign_state.get("roleSlotRetaliation") or {}).values()), 0.0)

    prior_public_infamy = float(campaign_state.get("publicInfamy", 0.0))
    prior_hidden_crimes = float(campaign_state.get("hiddenCrimes", 0.0))
    prior_moral_corrosion = float(campaign_state.get("moralCorrosion", 0.0))
    prior_ritual_pollution = float(campaign_state.get("ritualPollution", 0.0))

    collective_efficacy = _clamp(
        float(hub.get("stability", 50.0)) * 0.3
        + float(hub.get("supply", 50.0)) * 0.22
        + (100.0 - float(hub.get("heat", 50.0))) * 0.12
        + (100.0 - float(dungeon.get("threat", 50.0))) * 0.1
        + law_order * 0.14
        + trust * 0.12
        - max(0.0, stress - trust) * 0.08
    )
    vice_pressure = _clamp(
        float(current_event.get("pressure", 0.0)) * 0.28
        + float(hub.get("heat", 0.0)) * 0.26
        + max(0.0, 58.0 - law_order) * 0.8
        + max(0.0, 55.0 - collective_efficacy) * 0.55
        + prior_hidden_crimes * 0.16
        + role_slot_suspicion * 0.24
        + role_slot_distrust * 0.18
        + hinted_count * 2.0
        + exposed_count * 4.0
    )
    taboo_pressure = _clamp(
        float(cycle_state.get("distortion", 0.0)) * 0.22
        + float(cycle_state.get("divine_war_pressure", 0.0)) * 0.16
        + float(dungeon.get("threat", 0.0)) * 0.24
        + max(0.0, 68.0 - float(dungeon.get("sealIntegrity", 100.0))) * 0.62
        + prior_ritual_pollution * 0.2
        + role_slot_retaliation * 0.28
    )
    moral_corrosion = _clamp(
        prior_moral_corrosion * 0.58
        + vice_pressure * 0.26
        + max(0.0, stress - trust) * 0.45
        + known_weaknesses * 2.3
        + role_slot_distrust * 0.22
    )
    vice_visibility = _clamp(
        prior_public_infamy * 0.42
        + float(hub.get("heat", 0.0)) * 0.25
        + float(current_event.get("pressure", 0.0)) * 0.12
        + role_slot_distrust * 0.18
        + hinted_count * 4.0
        + exposed_count * 7.0
    )
    public_shame = _clamp(prior_public_infamy * 0.55 + vice_visibility * 0.35 + taboo_pressure * 0.12)
    hidden_depravity = _clamp(
        prior_hidden_crimes * 0.7
        + hinted_count * 5.0
        + known_weaknesses * 2.5
        + vice_pressure * 0.18
        + role_slot_suspicion * 0.26
    )
    ritual_pollution = _clamp(
        prior_ritual_pollution * 0.62
        + taboo_pressure * 0.32
        + exposed_count * 1.4
        + role_slot_retaliation * 0.2
    )
    public_legitimacy = _clamp(
        region_legitimacy * 0.52
        + institution_support * 0.28
        + collective_efficacy * 0.2
        - public_shame * 0.22
        - role_slot_distrust * 0.18
    )

    return {
        "vicePressure": vice_pressure,
        "tabooPressure": taboo_pressure,
        "moralCorrosion": moral_corrosion,
        "viceVisibility": vice_visibility,
        "publicShame": public_shame,
        "hiddenDepravity": hidden_depravity,
        "ritualPollution": ritual_pollution,
        "collectiveEfficacy": collective_efficacy,
        "publicLegitimacy": public_legitimacy,
        "publicInfamy": _clamp(prior_public_infamy),
        "hiddenCrimes": _clamp(prior_hidden_crimes),
        "viceSources": _vice_sources(campaign_state, law_order),
        "tabooSources": _taboo_sources(campaign_state, float(cycle_state.get("distortion", 0.0))),
    }
