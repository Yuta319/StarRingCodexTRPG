from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import copy

from .assets import load_canonical_assets
from .gameplay_experience import build_campaign_display
from .runner import build_bundle
from .text.text_composer import (
    compose_action_mode_guide,
    compose_active_node_panel_copy,
    compose_institution_alert_panel_copy,
    compose_session_opening_guide,
    compose_world_pulse_panel_copy,
)


def _display_for_gpt(bundle: Dict[str, Any]) -> Dict[str, Any]:
    shell_snapshot = bundle["shell_snapshot"]
    scene_packet = shell_snapshot["scenePacket"]
    context_rail = shell_snapshot["contextRail"]
    display = {
        "actorRail": shell_snapshot["actorRail"],
        "worldSpine": shell_snapshot["worldSpine"],
        "worldPulse": context_rail["worldPulse"],
        "activeNode": context_rail["activeNode"],
        "institutionAlert": context_rail["institutionAlert"],
        "scenePacket": scene_packet,
        "npcBeats": scene_packet["npcBeats"],
    }
    scene_title = bundle["scene_output"]["player_facing"]["scene_title"]
    display.update(build_campaign_display(bundle["world_state"], scene_title))
    session = display.get("playCycle", {})
    archive_review = display.get("archiveReview") or {}
    next_session_hook = display.get("nextSessionHook") or {}
    display["sessionOpeningGuide"] = compose_session_opening_guide(
        session,
        bundle["world_state"].get("campaign_state", {}).get("sessionOpeningHooks", {}).get(str(session.get("sessionNumber", 1))),
        archive_review,
        next_session_hook,
    )
    display["actionGuide"] = compose_action_mode_guide(display.get("currentEvent", {}), display.get("storyGuide", {}))
    display["worldPulsePanel"] = compose_world_pulse_panel_copy(display["worldPulse"], display["worldPulseGuide"])
    display["activeNodeGuide"] = compose_active_node_panel_copy(display["activeNode"])
    display["institutionAlertGuide"] = compose_institution_alert_panel_copy(display["institutionAlert"], display.get("currentEvent", {}))
    return display


def _scene_surface(bundle: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    scene_packet = bundle["scene_packet"]
    player_facing = scene_packet["playerFacing"]
    return {
        "sceneId": scene_packet["sceneId"],
        "title": scene_packet["focusLabel"],
        "location": scene_packet["locationLabel"],
        "headline": player_facing["headline"],
        "openingLines": list(player_facing["lines"]),
        "dramaticLayers": copy.deepcopy(scene_packet["dramaticLayers"]),
        "choiceSurface": [
            {
                "choiceId": choice["choiceId"],
                "label": choice["label"],
                "recommended": choice["choiceId"] in set(display.get("currentEvent", {}).get("recommendedChoices", [])),
            }
            for choice in player_facing["choiceChips"]
        ],
    }


def _cast_surface(display: Dict[str, Any]) -> list[Dict[str, Any]]:
    cast: list[Dict[str, Any]] = []
    for npc in display.get("namedCast", []):
        cast.append(
            {
                "roleSlotId": npc["npcId"],
                "roleLabel": npc["role"],
                "occupantLabel": npc["displayName"],
                "trustText": npc["trustText"],
                "stressText": npc["stressText"],
                "conflictText": npc["conflictText"],
                "traceText": npc["traceText"],
                "secretText": npc["secretText"],
                "weaknessText": npc["weaknessText"],
            }
        )
    return cast


def _archive_surface(display: Dict[str, Any]) -> Dict[str, Any]:
    inspector = display.get("archiveInspector") or {}
    entries = []
    for entry in (inspector.get("entries") or [])[:3]:
        entries.append(
            {
                "sessionNumber": entry["sessionNumber"],
                "title": entry["title"],
                "tone": entry["tone"],
                "openingSummary": entry["openingSummary"],
                "keyRoleLabel": entry["keyRoleLabel"],
                "keyOccupantLabel": entry["keyOccupantLabel"],
                "protected": entry["protected"],
                "lost": entry["lost"],
                "carriedForward": entry["carriedForward"],
                "archivedCauseEcho": entry.get("archivedCauseEcho", ""),
                "resurfacingRisk": entry.get("resurfacingRisk", ""),
                "viceSummary": entry.get("viceSummary", ""),
                "tabooSummary": entry.get("tabooSummary", ""),
                "hiddenCrimeSummary": entry.get("hiddenCrimeSummary", ""),
                "ritualPollutionSummary": entry.get("ritualPollutionSummary", ""),
                "hookConnections": list(entry.get("hookConnections", [])),
            }
        )
    return {
        "latestArchiveSummary": (display.get("archiveReview") or {}).get("latestArchiveSummary", ""),
        "resurfacingSpark": (display.get("archiveReview") or {}).get("resurfacingSpark", ""),
        "hiddenWound": (display.get("archiveReview") or {}).get("hiddenWound", ""),
        "entries": entries,
    }


def _next_hook_surface(display: Dict[str, Any]) -> Dict[str, Any]:
    hook = display.get("nextSessionHook") or {}
    return {
        "nextMainEventCandidates": list(hook.get("nextMainEventCandidates", [])),
        "carriedPressures": list(hook.get("carriedPressures", [])),
        "npcCarryOvers": list(hook.get("npcCarryOvers", [])),
        "scarsRemaining": list(hook.get("scarsRemaining", [])),
        "protectedAssets": list(hook.get("protectedAssets", [])),
        "archivedCauseEchoes": list(hook.get("archivedCauseEchoes", [])),
        "resurfacingRisks": list(hook.get("resurfacingRisks", [])),
        "unresolvedVice": list(hook.get("unresolvedVice", [])),
        "unresolvedTaboo": list(hook.get("unresolvedTaboo", [])),
    }


def _free_action_surface(bundle: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    last_free_action = display.get("lastFreeAction") or {}
    latest = {
        "summary": last_free_action.get("summary") or last_free_action.get("freeActionSummary") or "",
        "outcome": ((last_free_action.get("adjudication") or {}).get("outcome") or ""),
        "afterglow": ((last_free_action.get("logs") or {}).get("afterglow") or ""),
        "residue": last_free_action.get("freeActionResidueLabel") or "",
    }
    return {
        "latest": latest,
        "narrativeSurfaceRules": [
            "自由入力の原文は保存しない。語りは summary と structured result の outcome から作る。",
            "結果の確定、世界状態の変更、保存は backend のみが行う。",
            "語りでは成功・露見・反動の手触りを補うが、truth を言い換えて改変しない。",
        ],
    }


def build_gpt_read_model_from_bundle(
    bundle: Dict[str, Any],
    *,
    request_seed: Optional[int] = None,
    request_world_json: Optional[Path] = None,
    request_archetype: str = "balanced",
    request_seasons: int = 10,
) -> Dict[str, Any]:
    display = _display_for_gpt(bundle)
    campaign = bundle["world_state"]["campaign_state"]
    return {
        "version": "gpt_read_model_v1",
        "contracts": {
            "truthMutation": "backend_only",
            "rawFreeTextPersisted": False,
            "roleSlotPrimary": True,
            "gptResponsibilities": ["narration", "npc_dialogue_surface", "free_action_narrative_surface"],
            "gptMustNot": ["mutate_world_state", "override_resolution", "persist_raw_free_text", "edit_saves_directly"],
        },
        "source": {
            "seed": request_seed if request_seed is not None else bundle.get("seed"),
            "worldJson": str(request_world_json) if request_world_json else None,
            "archetype": request_archetype,
            "seasons": request_seasons,
            "sessionNumber": display["playCycle"]["sessionNumber"],
            "turnInSession": display["playCycle"]["turnInSession"],
            "phaseLabel": display["playCycle"]["phaseLabel"],
        },
        "scene": _scene_surface(bundle, display),
        "guidance": {
            "sessionOpeningGuide": copy.deepcopy(display["sessionOpeningGuide"]),
            "storyGuide": copy.deepcopy(display["storyGuide"]),
            "actionGuide": copy.deepcopy(display["actionGuide"]),
        },
        "world": {
            "worldSpine": copy.deepcopy(bundle["shell_snapshot"]["worldSpine"]),
            "worldPulse": copy.deepcopy(display["worldPulsePanel"]),
            "currentEvent": {
                "label": display["currentEvent"]["label"],
                "statusLabel": display["currentEvent"]["statusLabel"],
                "summaryText": display["currentEvent"]["summaryText"],
                "importanceText": display["currentEvent"]["importanceText"],
                "lastOutcomeText": display["currentEvent"]["lastOutcomeText"],
                "branchPreview": copy.deepcopy(display["currentEvent"]["branchPreview"]),
            },
            "activeNode": {
                **copy.deepcopy(display["activeNode"]),
                "guide": copy.deepcopy(display["activeNodeGuide"]),
            },
            "institutionAlert": {
                **copy.deepcopy(display["institutionAlert"]),
                "guide": copy.deepcopy(display["institutionAlertGuide"]),
            },
            "hub": copy.deepcopy(display["hub"]),
            "dungeon": copy.deepcopy(display["dungeon"]),
            "endingForecast": copy.deepcopy(display["endingForecast"]),
        },
        "cast": _cast_surface(display),
        "memory": {
            "archiveSummary": _archive_surface(display),
            "nextSessionHook": _next_hook_surface(display),
            "sessionEnding": copy.deepcopy(display.get("sessionEnding")),
        },
        "freeActionSurface": _free_action_surface(bundle, display),
        "narrationPolicy": {
            "tone": "意味を先に、雰囲気はその後に置く。",
            "openingTask": "scene.openingLines と guidance.sessionOpeningGuide を基に、場面の導入を 2〜4 文で語る。",
            "npcTask": "cast を見て current occupant の反応を台詞や地の文で補う。",
            "hookTask": "memory.nextSessionHook を使い、次に何が再燃するかを短く示す。",
        },
        "runtime": {
            "readOnly": True,
            "sceneId": bundle["scene_packet"]["sceneId"],
            "sessionId": bundle["shell_snapshot"]["sessionId"],
            "archiveCount": len(campaign.get("sessionArchive", [])),
        },
    }


def build_gpt_read_model(
    *,
    seed: Optional[int] = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
    world_json: Optional[Path] = None,
) -> Dict[str, Any]:
    bundle = build_bundle(
        seed=seed,
        seasons=seasons,
        archetype=archetype,
        world_json=world_json,
        assets=load_canonical_assets(),
    )
    return build_gpt_read_model_from_bundle(
        bundle,
        request_seed=seed,
        request_world_json=world_json,
        request_archetype=archetype,
        request_seasons=seasons,
    )
