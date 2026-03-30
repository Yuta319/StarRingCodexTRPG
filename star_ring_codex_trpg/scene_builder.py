from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .assets import CanonicalAssets
from .gameplay_experience import (
    active_scene_npcs,
    build_player_trace,
    current_dungeon,
    current_event,
    current_hub,
    emotion_text,
    relation_text,
    role_text,
    scene_archive_brief,
)


def slugify(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in text).strip("_")


def relation_stage_from_breach(breach: float) -> str:
    if breach >= 85:
        return "S6"
    if breach >= 70:
        return "S5"
    if breach >= 55:
        return "S4"
    if breach >= 40:
        return "S3"
    if breach >= 25:
        return "S2"
    if breach >= 10:
        return "S1"
    return "S0"


def rupture_stage_from_node(node: Dict[str, Any]) -> str:
    score = float(node.get("severity", 0.0)) * 0.6 + float(node.get("urgency", 0.0)) * 0.4
    if score >= 92:
        return "clear_break"
    if score >= 75:
        return "local_break"
    if score >= 55:
        return "micro_leak"
    return "stable"


def faction_role_label(faction_type: str) -> str:
    return {
        "state": "行政代表",
        "religion": "宗務代表",
        "guild": "利権代表",
        "tribe": "氏族代表",
        "demon_domain": "魔域代行",
    }.get(faction_type, "代表")


def representative_name(label: str, faction_type: str) -> str:
    suffix = {
        "state": "の執達吏",
        "religion": "の神官",
        "guild": "の帳場頭",
        "tribe": "の使者",
        "demon_domain": "の代行者",
    }.get(faction_type, "の代表")
    return f"{label}{suffix}"


@dataclass(frozen=True)
class SceneContext:
    world: Dict[str, Any]
    cycle_state: Dict[str, Any]
    regions: Dict[str, Dict[str, Any]]
    factions: Dict[str, Dict[str, Any]]
    focus_node: Dict[str, Any]
    focus_region: Dict[str, Any]
    focus_region_id: str
    focus_institution: Optional[Dict[str, Any]]
    focus_chain: Optional[Dict[str, Any]]
    faction_ids: List[str]


def _score_node(node: Dict[str, Any]) -> float:
    return float(node.get("severity", 0.0)) * 0.7 + float(node.get("urgency", 0.0)) * 0.3


def _pick_focus_node(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    return sorted(nodes, key=lambda item: (-_score_node(item), str(item.get("node_id", ""))))[0]


def _fallback_node_from_history(history_item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "node_id": history_item["node_id"],
        "node_type": history_item.get("event_family", "historical_resolution"),
        "event_family": history_item.get("event_family", "historical_resolution"),
        "title": history_item.get("node_title", history_item["node_id"]),
        "description": "解決済みの歴史事件を scene として再読している。",
        "severity": history_item.get("difficulty", 0.0),
        "urgency": history_item.get("capability", 0.0),
        "source_institution_id": None,
        "source_clause_id": None,
        "factions": [],
        "regions": [],
        "promoted_from": history_item.get("event_family", "resolution"),
        "chain_id": None,
        "stage": 1,
        "status": history_item.get("resulting_status", "resolved"),
        "projected_legacies": history_item.get("realized_media", []),
        "quest_offers": [],
    }


def select_scene_context(world_data: Dict[str, Any]) -> SceneContext:
    resolved_world = world_data["resolved_world"]
    world = resolved_world["world"]
    regions = resolved_world["regions"]
    factions = resolved_world["factions"]
    institutions = resolved_world["institutions"]
    chains = resolved_world["chains"]
    active_nodes = resolved_world.get("active_nodes", {})
    archived_nodes = resolved_world.get("archived_nodes", {})
    resolution_history = resolved_world.get("resolution_history", [])

    if active_nodes:
        focus_node = _pick_focus_node(list(active_nodes.values()))
    elif archived_nodes:
        focus_node = _pick_focus_node(list(archived_nodes.values()))
    elif resolution_history:
        focus_node = _fallback_node_from_history(resolution_history[-1])
    else:
        raise RuntimeError(
            "TODO: world state has no active/archived node or resolution history, so a canonical scene cannot be rendered."
        )

    region_id = (focus_node.get("regions") or [next(iter(regions))])[0]
    if region_id not in regions:
        raise RuntimeError(f"TODO: focus node region is missing from world state: {region_id}")
    focus_region = regions[region_id]

    focus_institution = None
    institution_id = focus_node.get("source_institution_id")
    if institution_id:
        focus_institution = institutions.get(institution_id)

    faction_ids = [faction_id for faction_id in focus_node.get("factions", []) if faction_id in factions]
    if not faction_ids and focus_institution:
        for faction_id in [focus_institution.get("party_a"), focus_institution.get("party_b")]:
            if faction_id and faction_id in factions:
                faction_ids.append(faction_id)
    if not faction_ids:
        raise RuntimeError(
            "TODO: focus node has no canonical faction context, so NPC beats cannot be generated without inventing actors."
        )

    focus_chain = None
    chain_id = focus_node.get("chain_id")
    if chain_id:
        focus_chain = chains.get(chain_id)

    return SceneContext(
        world=world,
        cycle_state=world_data.get("cycle_state", {}),
        regions=regions,
        factions=factions,
        focus_node=focus_node,
        focus_region=focus_region,
        focus_region_id=region_id,
        focus_institution=focus_institution,
        focus_chain=focus_chain,
        faction_ids=faction_ids[:2],
    )


def _scene_choices() -> List[Dict[str, str]]:
    return [
        {"id": "observe", "label": "周囲の様子を見る", "risk_hint": "low"},
        {"id": "speak_issuer", "label": "関係者に話を聞く", "relation_hint": "issuer"},
        {"id": "inspect_terms", "label": "記録と条文を確かめる", "risk_hint": "medium"},
        {"id": "trace_pressure", "label": "危険の出どころを追う", "risk_hint": "high"},
    ]


def _choice_chips() -> List[Dict[str, Any]]:
    return [
        {"choiceId": "observe", "label": "周囲の様子を見る", "intentType": "observe", "emphasis": "primary"},
        {"choiceId": "speak", "label": "関係者に話を聞く", "intentType": "speak"},
        {"choiceId": "inspect", "label": "記録と条文を確かめる", "intentType": "inspect"},
        {"choiceId": "intervene", "label": "危険を承知で踏み込む", "intentType": "intervene", "emphasis": "risky"},
    ]


def _npc_line_bundle(index: int, assets: CanonicalAssets) -> Tuple[str, str, str, str, str, str, str]:
    motion = assets.motion_cues[index % len(assets.motion_cues)].rstrip("。") + "。"
    if index == 0:
        return (
            motion,
            "こちらの出方を量るように、先に文言だけを整えてくる。",
            "譲歩を口にする前に、どこまで責任を切り離せるかを探っている。",
            "ほんの一瞬だけ、失うものの大きさが声の底に落ちた。",
            "場を仕切るつもりで、一歩だけ前へ出る。",
            "こちらを値踏みしながらも、追い返しきれずにいる。",
            "平静を装っているが、息の継ぎ目がわずかに浅い。",
        )
    return (
        motion,
        "返答の前に、門と人の流れを見比べている。",
        "こちらへ近づく気配はあるが、決定的な言葉だけを飲み込んだ。",
        "怒りよりも、長引く面倒への疲れが先ににじむ。",
        "列の外側から、崩れた均衡を見張っている。",
        "介入を期待しつつも、先に頼るのは避けたがっている。",
        "苛立ちより疲労が先に見える。",
    )


def build_scene_output(world_data: Dict[str, Any], assets: CanonicalAssets) -> Tuple[Dict[str, Any], Dict[str, Any], SceneContext]:
    context = select_scene_context(world_data)
    world = context.world
    focus_node = context.focus_node
    focus_region = context.focus_region
    focus_institution = context.focus_institution
    hub = current_hub(world_data)
    dungeon = current_dungeon(world_data)
    event = current_event(world_data)
    trace = build_player_trace(world_data)
    archive_brief = scene_archive_brief(world_data)
    faction_labels = [context.factions[faction_id]["label_ja"] for faction_id in context.faction_ids]

    region_label = focus_region.get("label_ja", context.focus_region_id)
    scene_title = focus_node.get("title", "事件")
    description = focus_node.get("description", "違約の積み重ねが表面化している。")
    institution_label = focus_institution.get("label_ja") if focus_institution else None
    chapter_title = f"{world['calendar_name']} {world['calendar_year']}年 / {world['current_world_era']}"
    headline = f"{event['label']}の余波が、{region_label}の「{scene_title}」へ直結している。"
    if archive_brief.get("headlineText"):
        headline = f"{archive_brief['headlineText']} {headline}"

    lines = [
        *list(archive_brief.get("openingLines", []))[:3],
        f"{region_label}では、{scene_title}をめぐるざわめきが、もう奥に隠れきっていない。",
        f"{'と'.join(faction_labels) if faction_labels else '複数勢力'}のあいだで責任の押し付け合いが始まり、見張りも通行人も視線を落ち着けられずにいる。",
        description,
        f"固有事件「{event['label']}」では、{event['summaryText']}",
        event["importanceText"],
        hub["supportText"],
        dungeon["supportText"],
        trace["summary"],
        (
            f"もともとの約定は「{institution_label}」だが、その文言はもう現場を縛りきれていない。"
            if institution_label
            else "小さなほころびが、いまや一つの事件として姿を持ち始めていた。"
        ),
        "聞き流して通れる気配ではない。手を入れるなら、今のうちだ。",
    ]

    breach = float(focus_institution.get("breach_risk", focus_node.get("severity", 50.0))) if focus_institution else float(
        focus_node.get("severity", 50.0)
    )
    relation_stage = relation_stage_from_breach(breach)
    rupture_stage = rupture_stage_from_node(focus_node)

    npc_beats_output: List[Dict[str, Any]] = []
    npc_beats_scene: List[Dict[str, Any]] = []
    for index, npc in enumerate(active_scene_npcs(world_data, context.faction_ids)):
        motion, first, second, third, _role_beat, _relation_beat, _emotion_beat = _npc_line_bundle(index, assets)
        npc_beats_output.append(
            {
                "npc_id": npc["npcId"],
                "display_name": npc["displayName"],
                "role": npc["role"],
                "relation_stage": relation_stage,
                "rupture_stage": rupture_stage,
                "motion_cue": motion,
                "first_line": f"{first} {npc['agenda']}",
                "second_line": second,
                "third_line_or_null": third,
                "subsurface_note": f"{npc['affiliationLabel']}の都合と保身が、表情の奥でせめぎ合っている。",
            }
        )
        npc_beats_scene.append(
            {
                "npcId": npc["npcId"],
                "displayName": npc["displayName"],
                "roleBeat": role_text(npc, event),
                "relationBeat": relation_text(npc),
                "emotionBeat": emotion_text(npc),
                "suppression": "medium" if rupture_stage == "clear_break" else "high",
                "ruptureState": rupture_stage,
            }
        )

    objective = event["objective"]
    scene_output = {
        "player_facing": {
            "chapter_title": chapter_title,
            "scene_title": scene_title,
            "scene_record": "\n".join(lines),
            "current_objective": objective,
            "choices": _scene_choices(),
        },
        "dramatic_layers": {
            "scene_pulse": f"{region_label}で事件の熱が表面化している",
            "human_drama": {
                "label": event["label"],
                "subtext": event["summaryText"],
                "cannot_say": event["whyImportant"],
            },
            "relation_cost": f"{institution_label or '既存制度'}と{hub['label']}の傷みが、人間関係の負債として噴き出している",
            "memory_echo": f"{dungeon['label']}に沈んだ見逃しが、いまの空気を重くしている",
            "world_echo": f"{event['stakes']} この局地のほころびは、時代全体の圧力へつながっている",
        },
        "npc_beats": npc_beats_output,
        "internal": {"style_checks": assets.style_checks, "violations": []},
    }

    scene_packet = {
        "sceneId": f"scene_{context.focus_region_id}_{slugify(focus_node['node_id'])}",
        "locationLabel": region_label,
        "focusLabel": scene_title,
        "playerFacing": {"headline": headline, "lines": lines[:6], "choiceChips": _choice_chips()},
        "dramaticLayers": {
            "place": region_label,
            "focus": scene_title,
            "discrepancy": event["summaryText"],
            "reaction": f"{hub['label']}の荒れ方と{dungeon['label']}の封印の揺れが、同じ局面を別方向から押している",
            "aftermath": event["stakes"],
        },
        "npcBeats": npc_beats_scene,
        "linkedNodeIds": [focus_node["node_id"]],
        "internalFoldCount": len(scene_output["internal"]["style_checks"]),
        "renderHints": {
            "preferredMode": "intervention",
            "showDiceTray": True,
            "highlightNodeId": focus_node["node_id"],
        },
    }
    return scene_output, scene_packet, context
