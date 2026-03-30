from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from jsonschema import Draft202012Validator

from .errors import FreeActionError
from .vice_taboo import TABOO_ENTRY_MAP, VICE_ENTRY_MAP, free_action_result_schema


SKILL_KEYS = {
    "observe": ["stealth", "stewardship"],
    "speak": ["diplomacy", "authority"],
    "inspect": ["ritual", "stewardship"],
    "intervene": ["combat", "ritual", "authority"],
}

TENDENCY_KEYS = {
    "observe": ["prudence"],
    "speak": ["mercy"],
    "inspect": ["prudence"],
    "intervene": ["ambition"],
}

ACTION_FAMILY_RISK = {
    "theft": 1.0,
    "fraud": 1.15,
    "smuggling": 1.1,
    "coercion": 1.18,
    "violence": 1.34,
    "illicit_relationship": 1.08,
    "sacrilege": 1.36,
    "taboo_ritual": 1.42,
    "deception": 1.1,
    "sabotage": 1.28,
    "escape": 1.05,
    "concealment": 1.0,
    "social_manipulation": 1.04,
    "other": 1.0,
}

ACTION_FAMILY_CONTEXT_KEYWORDS = {
    "theft": ["帳", "荷", "札", "倉", "遺物", "配給"],
    "fraud": ["帳", "印", "札", "誓", "記録", "検分"],
    "smuggling": ["渡し", "舟", "荷", "裏口", "検問", "抜け道"],
    "coercion": ["責任", "順", "譲歩", "密書", "弱み", "圧"],
    "violence": ["封鎖", "報復", "崩", "略奪", "襲撃", "検問"],
    "illicit_relationship": ["密会", "寝所", "血統", "継承", "密書"],
    "sacrilege": ["祈", "聖", "遺物", "祠", "祭", "神"],
    "taboo_ritual": ["封", "祈", "遺物", "祠", "譜", "魂", "結界"],
    "deception": ["証言", "噂", "帳", "札", "順", "筋"],
    "sabotage": ["綱", "札", "封", "列", "泥封", "封路"],
    "escape": ["退路", "坑路", "封路", "渡し", "逃げ道"],
    "concealment": ["痕", "帳", "封", "欠番", "隠し"],
    "social_manipulation": ["噂", "責任", "疑い", "列", "順", "空気"],
    "other": [],
}

CRIME_ACTION_FAMILIES = {
    "theft",
    "fraud",
    "smuggling",
    "coercion",
    "violence",
    "deception",
    "sabotage",
    "concealment",
    "social_manipulation",
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, float(value))), 1)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _average(values: Iterable[float], fallback: float = 0.0) -> float:
    materialized = [float(value) for value in values]
    if not materialized:
        return float(fallback)
    return sum(materialized) / len(materialized)


def _text_join(*parts: Any) -> str:
    return " ".join(_text(part) for part in parts if _text(part))


def _allowability_profile(
    campaign_state: Mapping[str, Any],
    scene_context: Any,
    normalized_intent: Mapping[str, Any],
    base_intent_type: str,
) -> Dict[str, float]:
    action_family = _text(normalized_intent.get("action_family")) or "other"
    vice_tags = list(normalized_intent.get("vice_tags", []))
    taboo_tags = list(normalized_intent.get("taboo_tags", []))
    target_slots = list(normalized_intent.get("target_role_slots", []))
    event_catalog = campaign_state.get("events", {}).get("catalog", {})
    event = event_catalog.get(campaign_state.get("currentEventId"), {})
    hub = campaign_state.get("hub", {})
    dungeon = campaign_state.get("dungeon", {})
    npcs = campaign_state.get("npcs", {})
    focus_slots = {
        slot_id
        for branch in event.get("branches", [])
        for slot_id in branch.get("focusNpcIds", [])
    }
    event_text = _text_join(
        event.get("label"),
        event.get("summary"),
        event.get("objective"),
        event.get("stakes"),
        event.get("whyImportant"),
        event.get("theme"),
    )
    hub_text = _text_join(hub.get("label"), hub.get("description"), hub.get("pressureStyle"))
    dungeon_text = _text_join(dungeon.get("label"), dungeon.get("description"), dungeon.get("pressureStyle"))
    scene_text = _text_join(event_text, hub_text, dungeon_text)

    capability_bonus = 0.0
    difficulty_shift = 0.0
    exposure_shift = 0.0
    backlash_shift = 0.0
    fit_score = 0.0

    if base_intent_type in event.get("recommendedChoices", []):
        capability_bonus += 3.5
        fit_score += 3.0
    else:
        difficulty_shift += 2.5

    keyword_hits = sum(1 for keyword in ACTION_FAMILY_CONTEXT_KEYWORDS.get(action_family, []) if keyword in scene_text)
    if keyword_hits:
        capability_bonus += min(4.5, keyword_hits * 1.2)
        fit_score += min(4.0, keyword_hits * 0.9)
    else:
        difficulty_shift += 1.5

    focus_hits = sum(1 for slot_id in target_slots if slot_id in focus_slots)
    if focus_hits:
        capability_bonus += focus_hits * 1.4
        fit_score += focus_hits * 1.6
    elif target_slots:
        difficulty_shift += 1.4

    vice_exposure_hits = sum(
        1
        for slot_id in target_slots
        if slot_id in npcs and set(npcs[slot_id].get("viceExposure", [])) & set(vice_tags)
    )
    taboo_exposure_hits = sum(
        1
        for slot_id in target_slots
        if slot_id in npcs and set(npcs[slot_id].get("tabooExposure", [])) & set(taboo_tags)
    )
    if vice_tags:
        fit_score += vice_exposure_hits * 1.2
        capability_bonus += vice_exposure_hits * 0.9
        if target_slots and vice_exposure_hits == 0:
            difficulty_shift += 2.2
            exposure_shift += 2.4
    if taboo_tags:
        fit_score += taboo_exposure_hits * 1.4
        capability_bonus += taboo_exposure_hits * 0.8
        backlash_shift += max(1.0, len(taboo_tags) * 1.8)
        if target_slots and taboo_exposure_hits == 0:
            difficulty_shift += 2.8
            backlash_shift += 3.6

    hub_heat = float(hub.get("heat", 50.0))
    dungeon_threat = float(dungeon.get("threat", 50.0))
    seal_integrity = float(dungeon.get("sealIntegrity", 70.0))
    vice_visibility = float(campaign_state.get("viceVisibility", 0.0))
    public_shame = float(campaign_state.get("publicShame", 0.0))
    taboo_pressure = float(campaign_state.get("tabooPressure", 0.0))

    if action_family in {"theft", "smuggling", "fraud", "deception", "concealment"}:
        if event.get("theme") == "institution":
            capability_bonus += 2.2
            fit_score += 2.0
        if hub_heat >= 64:
            exposure_shift -= 2.0 if action_family in {"theft", "smuggling", "concealment"} else -0.5
        if vice_visibility >= 58 or public_shame >= 55:
            exposure_shift += 4.5
        if action_family == "fraud" and _text(event.get("theme")) == "institution":
            capability_bonus += 1.2

    if action_family in {"coercion", "violence", "sabotage"}:
        if hub_heat >= 58 or dungeon_threat >= 58:
            capability_bonus += 1.6
            fit_score += 1.4
        else:
            exposure_shift += 3.0
        backlash_shift += float(normalized_intent.get("violence_level", 0.0)) * 0.03

    if action_family in {"sacrilege", "taboo_ritual"}:
        if seal_integrity <= 66 or dungeon_threat >= 56:
            capability_bonus += 2.4
            fit_score += 2.0
            backlash_shift += 4.0
        else:
            difficulty_shift += 2.0
        if taboo_pressure >= 60:
            backlash_shift += 4.0
        exposure_shift += 1.6

    if action_family == "escape":
        if dungeon_threat >= 55 or hub_heat >= 60:
            capability_bonus += 1.8
            fit_score += 1.4
        else:
            difficulty_shift += 2.0

    if action_family == "social_manipulation":
        if event.get("theme") == "institution":
            capability_bonus += 1.8
            fit_score += 1.6
        if public_shame >= 55:
            exposure_shift += 2.2

    return {
        "capability_bonus": round(capability_bonus, 1),
        "difficulty_shift": round(difficulty_shift, 1),
        "exposure_shift": round(exposure_shift, 1),
        "backlash_shift": round(backlash_shift, 1),
        "fit_score": round(fit_score, 1),
    }


def derived_intent_type(parsed_action: Mapping[str, Any]) -> str:
    explicit = _text(parsed_action.get("derived_intent_type"))
    if explicit in SKILL_KEYS:
        return explicit
    normalized = parsed_action.get("normalized_intent", {})
    action_family = _text(normalized.get("action_family")) or "other"
    secrecy_level = float(normalized.get("secrecy_level", 0.0))
    violence_level = float(normalized.get("violence_level", 0.0))
    taboo_level = float(normalized.get("taboo_level", 0.0))
    if action_family in {"violence", "sacrilege", "taboo_ritual"}:
        return "intervene"
    if action_family in {"coercion", "social_manipulation", "illicit_relationship"}:
        return "speak"
    if action_family in {"fraud", "deception", "sabotage"}:
        return "inspect"
    if action_family in {"theft", "smuggling", "escape", "concealment"}:
        return "observe" if secrecy_level >= 58 else "inspect"
    if violence_level >= 62 or taboo_level >= 65:
        return "intervene"
    if secrecy_level >= 65:
        return "observe"
    return "inspect"


def _goal_alignment(goal: str) -> float:
    positive = ("守", "救", "止", "確保", "証拠", "保つ", "逃が")
    negative = ("奪", "壊", "汚", "脅", "消す")
    score = 0.0
    if any(token in goal for token in positive):
        score += 1.0
    if any(token in goal for token in negative):
        score -= 1.0
    return score


def _capability(
    world_state: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    normalized_intent: Mapping[str, Any],
    base_intent_type: str,
    allowability_profile: Mapping[str, Any],
) -> float:
    protagonist = world_state.get("resolved_world", {}).get("protagonist", {})
    skills = protagonist.get("skills", {})
    tendencies = protagonist.get("tendencies", {})
    skill_score = _average((float(skills.get(key, 45.0)) for key in SKILL_KEYS[base_intent_type]), 45.0)
    tendency_score = _average((float(tendencies.get(key, 50.0)) for key in TENDENCY_KEYS[base_intent_type]), 50.0)
    target_slots = normalized_intent.get("target_role_slots", [])
    npcs = campaign_state.get("npcs", {})
    trust_support = _average(((float(npcs[slot]["trust"]) - 50.0) for slot in target_slots if slot in npcs), 0.0)
    stress_drag = _average(((float(npcs[slot]["stress"]) - 50.0) for slot in target_slots if slot in npcs), 0.0)
    secrecy_bonus = float(normalized_intent.get("secrecy_level", 0.0)) * (0.06 if base_intent_type in {"observe", "inspect"} else 0.03)
    violence_bonus = float(normalized_intent.get("violence_level", 0.0)) * (0.03 if base_intent_type == "intervene" else -0.01)
    means_bonus = len(normalized_intent.get("means", [])) * 1.4
    capability = (
        skill_score * 0.66
        + tendency_score * 0.24
        + trust_support * 0.18
        - stress_drag * 0.12
        + secrecy_bonus
        + violence_bonus
        + means_bonus
        + float(allowability_profile.get("capability_bonus", 0.0))
    )
    return round(capability, 1)


def _difficulty(
    world_state: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    scene_context: Any,
    normalized_intent: Mapping[str, Any],
    allowability_profile: Mapping[str, Any],
) -> float:
    node = getattr(scene_context, "focus_node", {}) or {}
    event_catalog = campaign_state.get("events", {}).get("catalog", {})
    event = event_catalog.get(campaign_state.get("currentEventId"), {})
    hub = campaign_state.get("hub", {})
    dungeon = campaign_state.get("dungeon", {})
    vice_pressure = float(campaign_state.get("vicePressure", 0.0))
    taboo_pressure = float(campaign_state.get("tabooPressure", 0.0))
    severity = float(node.get("severity", 55.0))
    urgency = float(node.get("urgency", 55.0))
    stage = float(node.get("stage", 1.0))
    event_pressure = float(event.get("pressure", 50.0))
    secrecy_level = float(normalized_intent.get("secrecy_level", 0.0))
    violence_level = float(normalized_intent.get("violence_level", 0.0))
    taboo_level = float(normalized_intent.get("taboo_level", 0.0))
    action_family = _text(normalized_intent.get("action_family")) or "other"
    risk_multiplier = ACTION_FAMILY_RISK.get(action_family, 1.0)

    base = (
        severity * 0.22
        + urgency * 0.12
        + stage * 2.8
        + event_pressure * 0.1
        + float(hub.get("heat", 50.0)) * 0.06
        + float(dungeon.get("threat", 50.0)) * 0.04
        + (100.0 - float(dungeon.get("sealIntegrity", 70.0))) * 0.05
        + vice_pressure * 0.04
        + taboo_pressure * 0.05
        + secrecy_level * 0.02
        + violence_level * 0.04
        + taboo_level * 0.05
    )
    adjusted = base * risk_multiplier + float(allowability_profile.get("difficulty_shift", 0.0))
    return round(adjusted, 1)


def _vice_score(normalized_intent: Mapping[str, Any], campaign_state: Mapping[str, Any]) -> float:
    action_family = _text(normalized_intent.get("action_family")) or "other"
    vice_tags = list(normalized_intent.get("vice_tags", []))
    secrecy_level = float(normalized_intent.get("secrecy_level", 0.0))
    base = len(vice_tags) * 12.0 + float(campaign_state.get("vicePressure", 0.0)) * 0.46 + secrecy_level * 0.08
    if action_family in {"theft", "fraud", "smuggling", "coercion", "violence", "deception", "sabotage"}:
        base += 10.0
    if action_family == "social_manipulation":
        base += 6.0
    return _clamp(base)


def _taboo_score(normalized_intent: Mapping[str, Any], campaign_state: Mapping[str, Any]) -> float:
    taboo_tags = list(normalized_intent.get("taboo_tags", []))
    taboo_level = float(normalized_intent.get("taboo_level", 0.0))
    base = len(taboo_tags) * 15.0 + float(campaign_state.get("tabooPressure", 0.0)) * 0.5 + taboo_level * 0.18
    return _clamp(base)


def _discovery_score(
    normalized_intent: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    delta: float,
    allowability_profile: Mapping[str, Any],
) -> float:
    npcs = campaign_state.get("npcs", {})
    target_slots = normalized_intent.get("target_role_slots", [])
    target_stress = _average((float(npcs[slot]["stress"]) for slot in target_slots if slot in npcs), 55.0)
    target_trust = _average((float(npcs[slot]["trust"]) for slot in target_slots if slot in npcs), 45.0)
    secrecy_level = float(normalized_intent.get("secrecy_level", 0.0))
    violence_level = float(normalized_intent.get("violence_level", 0.0))
    score = (
        45.0
        + violence_level * 0.42
        - secrecy_level * 0.36
        + float(campaign_state.get("viceVisibility", 0.0)) * 0.22
        + float(campaign_state.get("publicShame", 0.0)) * 0.16
        + target_stress * 0.12
        - target_trust * 0.08
        - delta * 0.32
        + float(allowability_profile.get("exposure_shift", 0.0))
    )
    return _clamp(score)


def _discovery_state(score: float) -> str:
    if score < 28:
        return "unseen"
    if score < 54:
        return "suspected"
    if score < 76:
        return "contested"
    return "exposed"


def _outcome_and_band(
    normalized_intent: Mapping[str, Any],
    delta: float,
    discovery_state: str,
    vice_score: float,
    taboo_score: float,
    secrecy_level: float,
    violence_level: float,
    allowability_profile: Mapping[str, Any],
) -> tuple[str, str]:
    action_family = _text(normalized_intent.get("action_family")) or "other"
    backlash_pressure = taboo_score * 0.62 + violence_level * 0.24 + float(allowability_profile.get("backlash_shift", 0.0))
    fit_score = float(allowability_profile.get("fit_score", 0.0))
    exposure_shift = float(allowability_profile.get("exposure_shift", 0.0))

    if delta >= 10:
        if action_family in CRIME_ACTION_FAMILIES and secrecy_level >= 60 and discovery_state in {"unseen", "suspected"} and exposure_shift <= 3.0:
            return "concealed_success", "costly" if vice_score >= 48 or taboo_score >= 36 else "clean"
        if discovery_state == "exposed":
            return "exposed", "mixed"
        return "success", "clean" if vice_score < 45 and taboo_score < 35 else "costly"

    if delta >= 6:
        if action_family in CRIME_ACTION_FAMILIES and secrecy_level >= 58 and discovery_state in {"unseen", "suspected"}:
            return "concealed_success", "costly"
        if discovery_state == "exposed":
            return "exposed", "mixed"
        return "success", "costly" if vice_score >= 45 or taboo_score >= 35 else "clean"

    if delta >= 1:
        if discovery_state == "exposed":
            return "exposed", "mixed"
        if action_family in CRIME_ACTION_FAMILIES and secrecy_level >= 72 and discovery_state == "suspected" and fit_score >= 2.0:
            return "concealed_success", "costly"
        return "partial_success", "mixed"

    if action_family in {"sacrilege", "taboo_ritual"} and delta <= -14 and taboo_score >= 32:
        return "backlash", "disastrous"
    if backlash_pressure >= 72 and (taboo_score >= 48 or action_family in {"sacrilege", "taboo_ritual", "violence"}):
        return "backlash", "disastrous"
    if action_family in CRIME_ACTION_FAMILIES and discovery_state in {"contested", "exposed"} and delta <= -4 and (secrecy_level < 55 or exposure_shift >= 2.0):
        return "exposed", "disastrous" if delta < -10 else "mixed"
    if discovery_state == "exposed":
        return "exposed", "disastrous" if delta < -6 else "mixed"
    if delta >= -6 and fit_score >= 1.5:
        return "partial_success", "costly"
    if backlash_pressure >= 62 and action_family in {"sacrilege", "taboo_ritual", "sabotage"}:
        return "backlash", "disastrous"
    return "failure", "costly" if delta >= -12 else "disastrous"


def _note(outcome: str, action_family: str, discovery_state: str) -> str:
    family_label = VICE_ENTRY_MAP.get(action_family, {}).get("label_ja") or action_family.replace("_", " ")
    notes = {
        "success": f"{family_label}の狙いは通り、場の流れを一度こちらへ寄せた。",
        "partial_success": f"{family_label}は通ったが、借りと疑いが残った。",
        "failure": f"{family_label}は狙い通りに決まらず、場に痛みだけが残った。",
        "exposed": f"{family_label}の筋は表に出て、隠していた利害まで疑われ始めた。",
        "concealed_success": f"{family_label}は気づかれ切らないまま通ったが、跡だけは残った。",
        "backlash": f"{family_label}は逆流し、禁忌や報復がこちらへ返ってきた。",
    }
    suffix = {
        "unseen": "まだ誰も確信していない。",
        "suspected": "薄い疑いだけが残っている。",
        "contested": "誰がやったかで見立てが割れている。",
        "exposed": "もう隠しきれない。",
    }
    return f"{notes[outcome]} {suffix[discovery_state]}"


def _goal_marks(normalized_intent: Mapping[str, Any], outcome: str) -> List[str]:
    goal = _text(normalized_intent.get("goal"))
    prefix = {
        "success": "自由行動の結果",
        "partial_success": "自由行動の代償",
        "failure": "自由行動の失敗",
        "exposed": "自由行動の露見",
        "concealed_success": "自由行動の隠れた成功",
        "backlash": "自由行動の反動",
    }[outcome]
    return [f"{prefix}: {goal}。"]


def _narrative_trace(entry_map: Mapping[str, Mapping[str, Any]], tag_ids: Iterable[str], prefix: str) -> List[str]:
    lines: List[str] = []
    for tag_id in tag_ids:
        entry = entry_map.get(tag_id)
        if not entry:
            continue
        label = _text(entry.get("label_ja")) or tag_id
        narratives = [str(item).strip() for item in entry.get("default_consequences", {}).get("narrative", []) if str(item).strip()]
        hint = narratives[0] if narratives else label
        lines.append(f"{prefix}: {label}の痕として「{hint}」が残った。")
    return lines[:6]


def _institution_patch(
    normalized_intent: Mapping[str, Any],
    outcome: str,
    goal_alignment: float,
    scene_context: Any,
) -> List[Dict[str, Any]]:
    institution_ids = list(normalized_intent.get("target_institutions", []))
    if not institution_ids and getattr(scene_context, "focus_institution", None):
        institution_ids = [scene_context.focus_institution["institution_id"]]
    if not institution_ids:
        return []
    family = _text(normalized_intent.get("action_family")) or "other"
    breach_base = {
        "theft": 4.0,
        "fraud": 5.0,
        "smuggling": 4.0,
        "coercion": 5.0,
        "violence": 8.0,
        "sacrilege": 7.0,
        "taboo_ritual": 7.5,
        "deception": 4.0,
        "sabotage": 6.0,
        "escape": 2.5,
        "concealment": 2.0,
        "social_manipulation": 3.0,
        "other": 3.0,
    }[family]
    if outcome in {"success", "concealed_success"} and goal_alignment > 0:
        breach_delta = -2.0
        support_delta = 2.0
    elif outcome == "partial_success":
        breach_delta = breach_base * 0.3
        support_delta = -1.0
    elif outcome == "failure":
        breach_delta = breach_base
        support_delta = -2.5
    elif outcome == "exposed":
        breach_delta = breach_base + 1.5
        support_delta = -4.0
    else:
        breach_delta = breach_base + 3.0
        support_delta = -5.0
    status_after = "strained" if breach_delta > 0 else "active"
    return [
        {
            "institution_id": institution_id,
            "breach_risk_delta": round(breach_delta, 1),
            "support_delta": round(support_delta, 1),
            "status_after": status_after,
        }
        for institution_id in institution_ids[:8]
    ]


def _npc_patch(normalized_intent: Mapping[str, Any], outcome: str, discovery_state: str, taboo_score: float) -> List[Dict[str, Any]]:
    patches = []
    action_family = _text(normalized_intent.get("action_family")) or "other"
    for role_slot_id in list(normalized_intent.get("target_role_slots", []))[:8]:
        trust_delta = -1.0
        stress_delta = 2.0
        if outcome == "concealed_success":
            trust_delta = -2.0
            stress_delta = 4.0
        elif outcome == "success":
            trust_delta = -1.0
            stress_delta = 1.5
        elif outcome == "partial_success":
            trust_delta = -2.5
            stress_delta = 4.5
        elif outcome == "failure":
            trust_delta = -3.0
            stress_delta = 5.0
        elif outcome == "exposed":
            trust_delta = -4.5
            stress_delta = 7.0
        elif outcome == "backlash":
            trust_delta = -5.5
            stress_delta = 9.0
        patch = {
            "role_slot_id": role_slot_id,
            "trust_delta": round(trust_delta, 1),
            "stress_delta": round(stress_delta, 1),
        }
        if action_family in {"fraud", "deception", "theft", "coercion", "social_manipulation"}:
            patch["secret_state_after"] = "exposed" if outcome in {"exposed", "backlash"} else "hinted" if discovery_state != "unseen" else "hidden"
        if action_family in {"coercion", "violence", "blackmail", "social_manipulation"} or outcome in {"failure", "backlash"}:
            patch["weakness_revealed"] = discovery_state in {"suspected", "contested", "exposed"}
        if outcome == "backlash" and action_family in {"violence", "taboo_ritual", "sacrilege"}:
            patch["occupant_status_after"] = "missing" if taboo_score >= 72 else "suspended"
        elif outcome == "exposed" and action_family in {"fraud", "deception", "sabotage"}:
            patch["occupant_status_after"] = "suspended"
        patches.append(patch)
    return patches


def _world_patch(normalized_intent: Mapping[str, Any], outcome: str, vice_score: float, taboo_score: float, discovery_state: str) -> Dict[str, float]:
    action_family = _text(normalized_intent.get("action_family")) or "other"
    vice_tags = list(normalized_intent.get("vice_tags", []))
    taboo_tags = list(normalized_intent.get("taboo_tags", []))
    public_infamy_delta = 0.0
    hidden_crimes_delta = 0.0
    if outcome == "concealed_success":
        hidden_crimes_delta = 4.0 + len(vice_tags) * 1.2
        public_infamy_delta = 1.0 if discovery_state == "suspected" else 0.0
    elif outcome == "success":
        public_infamy_delta = 2.0 if discovery_state in {"suspected", "contested"} else 0.5
        hidden_crimes_delta = 1.0
    elif outcome == "partial_success":
        public_infamy_delta = 3.0
        hidden_crimes_delta = 2.0
    elif outcome == "failure":
        public_infamy_delta = 2.0
        hidden_crimes_delta = 1.5
    elif outcome == "exposed":
        public_infamy_delta = 6.0
        hidden_crimes_delta = -2.0
    else:
        public_infamy_delta = 7.0
        hidden_crimes_delta = 0.0
    law_order_delta = -1.5 - len(vice_tags) * 0.5 - (1.2 if action_family in {"violence", "sabotage"} else 0.0)
    if outcome in {"success", "concealed_success"} and _goal_alignment(_text(normalized_intent.get("goal"))) > 0:
        law_order_delta += 0.8
    taboo_pressure_delta = len(taboo_tags) * 4.2 + float(normalized_intent.get("taboo_level", 0.0)) * 0.04
    if outcome == "backlash":
        taboo_pressure_delta += 5.0
    vice_pressure_delta = len(vice_tags) * 3.4 + vice_score * 0.04
    moral_corrosion_delta = len(vice_tags) * 2.2 + vice_score * 0.02 + (3.0 if outcome == "concealed_success" else 1.0)
    ritual_pollution_delta = len(taboo_tags) * 4.0 + taboo_score * 0.03
    legitimacy_delta = -1.0 - public_infamy_delta * 0.3 - taboo_pressure_delta * 0.05
    return {
        "law_order_delta": round(law_order_delta, 1),
        "vice_pressure_delta": round(vice_pressure_delta, 1),
        "taboo_pressure_delta": round(taboo_pressure_delta, 1),
        "moral_corrosion_delta": round(moral_corrosion_delta, 1),
        "public_infamy_delta": round(public_infamy_delta, 1),
        "hidden_crimes_delta": round(hidden_crimes_delta, 1),
        "ritual_pollution_delta": round(ritual_pollution_delta, 1),
        "legitimacy_delta": round(legitimacy_delta, 1),
    }


def _node_patch(outcome: str, delta: float, action_family: str) -> Dict[str, Any]:
    severe_family = action_family in {"violence", "sabotage", "taboo_ritual", "sacrilege"}
    if outcome == "success":
        severity_delta = -12.0 if severe_family else -9.0
        urgency_delta = -6.0 if severe_family else -4.0
        status_after = "resolved" if delta >= 20 else "cooling"
    elif outcome == "concealed_success":
        severity_delta = -5.0 if severe_family else -3.5
        urgency_delta = -2.8 if severe_family else -1.6
        status_after = "cooling" if delta >= 16 else "active"
    elif outcome == "partial_success":
        severity_delta = -6.0
        urgency_delta = -2.0
        status_after = "cooling"
    elif outcome == "failure":
        severity_delta = 4.0
        urgency_delta = 5.0
        status_after = "active"
    elif outcome == "exposed":
        severity_delta = 6.0
        urgency_delta = 7.0
        status_after = "active"
    else:
        severity_delta = 10.0
        urgency_delta = 11.0
        status_after = "active"
    return {
        "severity_delta": round(severity_delta, 1),
        "urgency_delta": round(urgency_delta, 1),
        "status_after": status_after,
    }


def _logs(parsed_action: Mapping[str, Any], outcome: str, discovery_state: str) -> Dict[str, str]:
    normalized = parsed_action.get("normalized_intent", {})
    summary = _text(parsed_action.get("source", {}).get("player_summary")) or "自由行動を試みた"
    session_summary = {
        "success": f"{summary}。狙いは通り、いまの争点を一度押し返した。",
        "partial_success": f"{summary}。前には進んだが、借りと疑いが残った。",
        "failure": f"{summary}。狙いは崩れ、場の痛みだけが増えた。",
        "exposed": f"{summary}。行いは表に出て、責任の追及が始まった。",
        "concealed_success": f"{summary}。狙いは通ったが、気配だけが残った。",
        "backlash": f"{summary}。禁じ手の反動で状況が悪い方向へ返ってきた。",
    }[outcome]
    afterglow = {
        "unseen": "まだ誰も確信していないが、静かな違和感だけが残る。",
        "suspected": "薄い疑いが残り、視線だけが少し重くなった。",
        "contested": "誰がやったかで見立てが割れ、場の信用が細った。",
        "exposed": "誰の仕業かが見え、関係のひびがはっきりした。",
    }[discovery_state]
    archive_note = f"{_text(normalized.get('goal')) or '自由行動の狙い'}の結果として、次節へ痕が持ち越された。"
    return {
        "session_summary": session_summary[:220],
        "afterglow": afterglow[:220],
        "archive_note": archive_note[:220],
    }


def validate_structured_result(result: Mapping[str, Any]) -> None:
    validator = Draft202012Validator(free_action_result_schema())
    errors = sorted(validator.iter_errors(result), key=lambda item: list(item.path))
    if errors:
        details = "; ".join(f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}" for error in errors)
        raise FreeActionError(f"Structured free action result is invalid: {details}")


def adjudicate_free_action(
    parsed_action: Mapping[str, Any],
    world_state: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    scene_context: Any,
) -> Dict[str, Any]:
    normalized = dict(parsed_action.get("normalized_intent", {}))
    base_intent_type = derived_intent_type(parsed_action)
    allowability_profile = _allowability_profile(campaign_state, scene_context, normalized, base_intent_type)
    capability = _capability(world_state, campaign_state, normalized, base_intent_type, allowability_profile)
    difficulty = _difficulty(world_state, campaign_state, scene_context, normalized, allowability_profile)
    delta = round(capability - difficulty, 1)
    vice_score = _vice_score(normalized, campaign_state)
    taboo_score = _taboo_score(normalized, campaign_state)
    discovery_score = _discovery_score(normalized, campaign_state, delta, allowability_profile)
    discovery_state = _discovery_state(discovery_score)
    outcome, success_band = _outcome_and_band(
        normalized,
        delta,
        discovery_state,
        vice_score,
        taboo_score,
        float(normalized.get("secrecy_level", 0.0)),
        float(normalized.get("violence_level", 0.0)),
        allowability_profile,
    )
    goal_alignment = _goal_alignment(_text(normalized.get("goal")))

    result = {
        "schema_version": "1.0",
        "action_id": parsed_action["action_id"],
        "session": dict(parsed_action["session"]),
        "source": dict(parsed_action["source"]),
        "normalized_intent": normalized,
        "adjudication": {
            "outcome": outcome,
            "success_band": success_band,
            "discovery_state": discovery_state,
            "difficulty": difficulty,
            "capability": capability,
            "delta": delta,
            "vice_score": vice_score,
            "taboo_score": taboo_score,
            "note": _note(outcome, _text(normalized.get("action_family")) or "other", discovery_state)[:220],
        },
        "consequence": {
            "node_patch": _node_patch(outcome, delta, _text(normalized.get("action_family")) or "other"),
            "institution_patch": _institution_patch(normalized, outcome, goal_alignment, scene_context),
            "world_patch": _world_patch(normalized, outcome, vice_score, taboo_score, discovery_state),
            "campaign_patch": {
                "world_marks_append": _goal_marks(normalized, outcome),
                "vice_trace_append": _narrative_trace(VICE_ENTRY_MAP, normalized.get("vice_tags", []), "悪徳の痕"),
                "taboo_trace_append": _narrative_trace(TABOO_ENTRY_MAP, normalized.get("taboo_tags", []), "禁忌の痕"),
                "next_session_hook_append": [f"{_text(parsed_action.get('source', {}).get('player_summary'))}の余波が次節に残る。"],
            },
            "npc_patch": _npc_patch(normalized, outcome, discovery_state, taboo_score),
            "logs": _logs(parsed_action, outcome, discovery_state),
        },
        "recording": {
            "persist_structured_result": True,
            "persist_raw_text": False,
            "replay_safe": True,
            "privacy_tier": "session_internal",
        },
    }
    validate_structured_result(result)
    return result
