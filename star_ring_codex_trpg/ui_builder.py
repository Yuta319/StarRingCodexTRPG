from __future__ import annotations

from typing import Any, Dict
import copy

from .assets import CanonicalAssets
from .gameplay_experience import current_dungeon, current_event, current_hub, current_session
from .scene_builder import SceneContext, slugify
from .text.text_composer import compose_world_pulse_copy


def infer_bar(base: float, bonus: float) -> Dict[str, int]:
    maximum = int(round(base + bonus))
    current = int(round(maximum * 0.82))
    return {"current": current, "max": maximum}


def event_vectors(theme: str) -> list[str]:
    return {
        "institution": ["diplomacy", "stewardship", "authority"],
        "hub": ["stewardship", "diplomacy", "stealth"],
        "dungeon": ["stealth", "ritual", "authority"],
    }.get(theme, ["diplomacy", "stewardship", "authority"])


def build_shell_snapshot(
    world_data: Dict[str, Any],
    scene_packet: Dict[str, Any],
    context: SceneContext,
    assets: CanonicalAssets,
) -> Dict[str, Any]:
    resolved_world = world_data["resolved_world"]
    world = context.world
    protagonist = resolved_world["protagonist"]
    cycle_state = context.cycle_state
    final_branch = world_data.get("final_branch_history", [])[-1] if world_data.get("final_branch_history") else {}
    pantheon = world_data.get("pantheon", [])
    focus_node = context.focus_node
    focus_chain = context.focus_chain
    focus_institution = context.focus_institution
    session = current_session(world_data)
    event = current_event(world_data)
    hub = current_hub(world_data)
    dungeon = current_dungeon(world_data)
    pulse_copy = compose_world_pulse_copy(cycle_state)

    shell = copy.deepcopy(assets.ui_examples["shellSnapshotExample"])
    shell["sessionId"] = f"sess_{world['seed']}"
    shell["generatedAt"] = f"{int(world['calendar_year']):04d}-01-01T00:00:00+09:00"
    shell["shellMode"] = "intervention"
    shell["worldSpine"] = {
        "worldName": world["world_name"],
        "calendarName": world["calendar_name"],
        "year": int(world["calendar_year"]),
        "seasonIndex": int(world["season_index"]),
        "eraLabel": world["current_world_era"],
        "mainGodLabel": world["main_god_name"],
        "activeChainLabel": (focus_chain or {}).get("label_ja", "局地事件"),
        "cycleDistortion": round(float(cycle_state.get("distortion", 0.0)), 1),
        "divineWarPressure": round(float(cycle_state.get("divine_war_pressure", 0.0)), 1),
        "dominantBranch": final_branch.get("dominant_branch", "未確定"),
        "topNotes": [event["label"], f"{hub['label']}: {hub['statusLabel']}", f"{dungeon['label']}: {dungeon['statusLabel']}"],
        "syncState": "synced",
    }

    skills = {key: round(float(value), 1) for key, value in protagonist.get("skills", {}).items()}
    tendencies = {key: round(float(value), 1) for key, value in protagonist.get("tendencies", {}).items()}
    vessel_points = round(float(protagonist.get("vessel_points", 0.0)), 1)
    blessings = [
        {
            "blessingId": "main_god_mark",
            "label": f"{world['main_god_name']}の徴",
            "tier": "major",
            "tone": "holy",
        }
    ]
    if pantheon:
        blessings.append(
            {
                "blessingId": f"pantheon_{slugify(str(pantheon[0].get('god_id', 'god')))}",
                "label": pantheon[0].get("label_ja", "神意"),
                "tier": "minor",
                "tone": "seal",
            }
        )

    shell["actorRail"] = {
        "actorId": "protagonist_main",
        "label": protagonist.get("label_ja", "旅人"),
        "hp": infer_bar(90, float(skills.get("combat", 40.0)) * 0.9),
        "mp": infer_bar(40, float(skills.get("ritual", 40.0)) * 0.7),
        "exp": {"current": int(vessel_points) % 1000, "next": round(vessel_points + 320.0, 1), "label": "Vessel換算"},
        "vessel": vessel_points,
        "existenceTitle": protagonist.get("existence_title", "無銘の旅人"),
        "skills": skills,
        "tendencies": tendencies,
        "statuses": [
            {"statusId": "era_pressure", "label": world["current_world_era"], "tone": "warning"},
            {"statusId": "cycle_distortion", "label": "輪廻歪み", "tone": "warning"},
            {
                "statusId": "session_phase",
                "label": f"{session['phaseLabel']} {session['turnInSession']}/{session['maxTurns']}",
                "tone": "neutral",
            },
        ],
        "blessings": blessings,
        "quickSlots": [
            {"slotIndex": 0, "slotType": "skill", "label": "観察", "actionRef": "skill.observe"},
            {"slotIndex": 1, "slotType": "skill", "label": "交渉", "actionRef": "skill.negotiate"},
            {"slotIndex": 2, "slotType": "skill", "label": "調査", "actionRef": "skill.inspect"},
            {"slotIndex": 3, "slotType": "skill", "label": "介入", "actionRef": "skill.intervene"},
        ],
    }

    beat = (scene_packet.get("npcBeats") or [{}])[0]
    shell["scenePacket"] = scene_packet
    shell["contextRail"] = {
        "companions": [{"companionId": "cmp_record", "label": "記録役", "role": "観測補佐"}],
        "npcFocus": {
            "npcId": beat.get("npcId", "npc_focus"),
            "displayName": beat.get("displayName", "代表者"),
            "role": "焦点人物",
            "relationSummary": "利害の均衡を崩さぬよう距離を取っている",
            "emotionSummary": "疲れを隠して手順を守ろうとしている",
            "suppression": beat.get("suppression", "high"),
            "ruptureState": beat.get("ruptureState", "micro_leak"),
        },
        "activeNode": {
            "nodeId": focus_node["node_id"],
            "title": focus_node.get("title", "事件"),
            "chainLabel": (focus_chain or {}).get("label_ja", "局地連鎖"),
            "institutionLabel": focus_institution.get("label_ja", "") if focus_institution else "",
            "questTitle": event["objective"],
            "severity": round(float(focus_node.get("severity", 0.0)), 1),
            "urgency": round(float(focus_node.get("urgency", 0.0)), 1),
            "stage": int(focus_node.get("stage", 1)),
            "status": focus_node.get("status", "active"),
            "recommendedVectors": event_vectors(event["theme"]),
            "projectedLegacies": focus_node.get("projected_legacies", []),
        },
        "institutionAlert": {
            "institutionId": focus_institution.get("institution_id", "") if focus_institution else "",
            "label": focus_institution.get("label_ja", "") if focus_institution else "",
            "status": focus_institution.get("status", "none") if focus_institution else "none",
            "breachRisk": round(float(focus_institution.get("breach_risk", 0.0)), 1) if focus_institution else 0.0,
        },
        "worldPulse": {
            "cycleDistortion": round(float(cycle_state.get("distortion", 0.0)), 1),
            "apotheosisFlux": round(float(cycle_state.get("apotheosis_flux", 0.0)), 1),
            "successionPressure": round(float(cycle_state.get("succession_pressure", 0.0)), 1),
            "divineWarPressure": round(float(cycle_state.get("divine_war_pressure", 0.0)), 1),
            "topNote": pulse_copy["summaryText"],
        },
    }
    shell["hotbar"] = assets.ui_examples["shellSnapshotExample"]["hotbar"]
    shell["badges"] = [
        {
            "badgeId": "quest_badge",
            "target": "node_board",
            "label": "介入候補あり",
            "tone": "warn",
            "count": min(9, max(1, len(resolved_world.get("active_nodes", {})))),
        }
    ]
    shell["overlays"] = [{"overlayId": "olv_intervention", "type": "intervention", "state": "hidden"}]
    shell["lastSeq"] = 2000 + int(world["season_index"])
    return shell


def build_ui_event(world_data: Dict[str, Any], shell_snapshot: Dict[str, Any], assets: CanonicalAssets) -> Dict[str, Any]:
    resolution_history = world_data["resolved_world"].get("resolution_history", [])
    event = copy.deepcopy(assets.ui_examples["uiEventExample"])
    event["seq"] = shell_snapshot["lastSeq"]
    event["sessionId"] = shell_snapshot["sessionId"]
    event["occurredAt"] = shell_snapshot["generatedAt"]

    if resolution_history:
        latest = resolution_history[-1]
        event["eventId"] = f"evt_{slugify(latest['node_id'])}_{latest['year']}_{latest['season']}"
        event["type"] = "node.resolution.committed"
        event["payload"] = {
            "nodeId": latest["node_id"],
            "approach": latest.get("approach", "observe"),
            "outcome": latest.get("outcome", "unknown"),
            "vesselDelta": round(float(latest.get("vessel_gain", 0.0)), 1),
            "realizedMedia": latest.get("realized_media", []),
        }
        event["invalidate"] = ["actorRail", "contextRail", "worldSpine", "journal"]
        event["uiHints"] = [
            {"type": "toast", "key": "node-updated", "level": "success"},
            {"type": "fx.vessel_gain", "amount": round(float(latest.get("vessel_gain", 0.0)), 1)},
            {"type": "highlight.hotbar", "target": "journal"},
        ]
    else:
        event["eventId"] = "evt_snapshot_generated"
        event["type"] = "snapshot.generated"
        event["payload"] = {"message": "snapshot generated"}
        event["invalidate"] = ["worldSpine", "contextRail"]
        event["uiHints"] = [{"type": "toast", "key": "snapshot-ready", "level": "info"}]
    return event
