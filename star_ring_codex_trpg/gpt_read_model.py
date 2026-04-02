from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import copy

from .assets import load_canonical_assets
from .display_naming import apply_fantasy_display_naming
from .front_hubs import build_player_front_hubs
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
    character_profile = bundle["world_state"].get("resolved_world", {}).get("protagonist", {}).get("character_profile") or {}
    if character_profile:
        custom_opening_lines = list(character_profile.get("customOpeningLines") or [])
        opening_lines = list(character_profile.get("openingLines") or [])
        existing_lines = list(display["sessionOpeningGuide"].get("lines") or [])
        if custom_opening_lines:
            display["sessionOpeningGuide"]["lines"] = custom_opening_lines[:4]
        else:
            display["sessionOpeningGuide"]["lines"] = opening_lines[:2] + existing_lines[:2]
        display["sessionOpeningGuide"]["headline"] = character_profile.get("customOpeningHeadline") or f"{character_profile.get('name', '主人公')}の導入"
    display["actionGuide"] = compose_action_mode_guide(display.get("currentEvent", {}), display.get("storyGuide", {}))
    display["worldPulsePanel"] = compose_world_pulse_panel_copy(display["worldPulse"], display["worldPulseGuide"])
    display["activeNodeGuide"] = compose_active_node_panel_copy(display["activeNode"])
    display["institutionAlertGuide"] = compose_institution_alert_panel_copy(display["institutionAlert"], display.get("currentEvent", {}))
    display["characterProfile"] = character_profile
    display.update(build_player_front_hubs(bundle["world_state"], display))
    return apply_fantasy_display_naming(display)


def _scene_surface(bundle: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    scene_packet = display["scenePacket"]
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
                "roleLabel": npc.get("roleLabel") or npc.get("role"),
                "occupantLabel": npc["displayName"],
                "summaryText": npc.get("summaryText", ""),
                "attitudeText": npc.get("attitudeText", ""),
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


def _character_genesis_surface(display: Dict[str, Any]) -> Dict[str, Any]:
    profile = copy.deepcopy(display.get("characterProfile") or {})
    equipment_hub = display.get("equipmentHub") or {}
    asset_prompt_pack = display.get("assetPromptPack") or {}
    boon_seed = copy.deepcopy(profile.get("starterBoonSeed") or {})
    constraints = copy.deepcopy(profile.get("generationConstraints") or {})
    portrait_guide = copy.deepcopy(asset_prompt_pack.get("portraitGuide") or {})
    starter_loadout = []
    for item in (equipment_hub.get("slots") or [])[:6]:
        starter_loadout.append(
            {
                "slotLabel": item.get("slotLabel"),
                "name": item.get("name"),
                "subtitle": item.get("subtitle"),
                "rarityLabel": item.get("rarityLabel"),
                "stats": list(item.get("stats") or []),
                "flavorText": item.get("flavorText"),
            }
        )
    return {
        "profile": {
            "name": profile.get("name"),
            "raceLabel": profile.get("raceLabel"),
            "styleLabel": profile.get("styleLabel"),
            "temperamentLabel": profile.get("temperamentLabel"),
            "originLabel": profile.get("originLabel"),
            "loadoutLabel": profile.get("loadoutLabel"),
            "sourceModeLabel": profile.get("sourceModeLabel"),
            "sourceTitle": profile.get("sourceTitle"),
            "sourceName": profile.get("sourceName"),
            "summaryText": profile.get("summaryText"),
            "appearanceNotes": profile.get("appearanceNotes"),
            "reinterpretationNotes": profile.get("reinterpretationNotes"),
            "selectedOpeningVariantLabel": profile.get("selectedOpeningVariantLabel"),
        },
        "openingVariants": copy.deepcopy(profile.get("openingVariants") or []),
        "openingPromptHint": profile.get("openingPromptHint"),
        "starterLoadout": starter_loadout,
        "starterBoonSeed": boon_seed,
        "constraints": constraints,
        "portraitGuide": {
            "styleSummary": portrait_guide.get("styleSummary"),
            "negativePrompt": portrait_guide.get("negativePrompt"),
            "consistencyRules": list(portrait_guide.get("consistencyRules") or []),
            "referenceHandling": list(portrait_guide.get("referenceHandling") or []),
        },
        "gptTasks": [
            "設定と転生元の要素を踏まえて、開始装備一式の意味づけと見た目を語れる。",
            "ただし性能値は constraints の上限を超えない前提で語る。world truth を直接変更しない。",
            "starterBoonSeed を起点に、恩恵と恩寵の手触りを語れるが、件数は constraints を超えない。",
            "openingVariants を種にして、導入は 2〜4 文で自由に組み替えてよい。",
        ],
    }


def _new_game_genesis_surface(display: Dict[str, Any]) -> Dict[str, Any]:
    genesis = copy.deepcopy(display.get("newGameGenesis") or {})
    if not genesis:
        return {}
    return {
        "profileSurface": copy.deepcopy(genesis.get("profileSurface") or {}),
        "openingSummary": genesis.get("openingSummary"),
        "phaseEventLabels": list(genesis.get("phaseEventLabels") or []),
        "hub": copy.deepcopy(genesis.get("hub") or {}),
        "dungeon": copy.deepcopy(genesis.get("dungeon") or {}),
        "incitingIncident": copy.deepcopy(genesis.get("incitingIncident") or {}),
        "storyAxes": list(genesis.get("storyAxes") or []),
        "preferredFactions": list(genesis.get("preferredFactions") or []),
        "castSeed": copy.deepcopy(genesis.get("castSeed") or []),
        "gptTasks": [
            "新規開始では openingSummary, incitingIncident, storyAxes を起点に、この世界固有の導入を組み立てる。",
            "phaseEventLabels はセッション1の火種として扱い、別のイベントへ勝手に差し替えない。",
            "castSeed の agenda と affiliationLabel を見て、最初に誰が何を守りたいかを明確に語る。",
        ],
    }


def _opening_package_surface(display: Dict[str, Any]) -> Dict[str, Any]:
    profile = copy.deepcopy(display.get("characterProfile") or {})
    genesis = copy.deepcopy(display.get("newGameGenesis") or {})
    session_opening = copy.deepcopy(display.get("sessionOpeningGuide") or {})
    cast_seed = list(genesis.get("castSeed") or [])
    prompt_hint = profile.get("openingPromptHint") or ""
    if not prompt_hint:
        anchors = [
            f"{profile.get('name') or '主人公'}の導入を 2〜4 文で語る。",
            f"導入見出しは「{session_opening.get('headline') or '旅の始まり'}」。",
            f"最初の火種は「{(genesis.get('incitingIncident') or {}).get('label') or '開始局面'}」。",
        ]
        if (genesis.get("hub") or {}).get("label"):
            anchors.append(f"拠点は {(genesis.get('hub') or {}).get('label')}。")
        if (genesis.get("dungeon") or {}).get("label"):
            anchors.append(f"坑路は {(genesis.get('dungeon') or {}).get('label')}。")
        if cast_seed:
            anchors.append(
                "最初に強く関わるのは "
                + "、".join(
                    f"{item.get('displayName')}（{item.get('roleLabel') or item.get('role') or '関係者'}）"
                    for item in cast_seed[:3]
                    if item.get("displayName")
                )
                + "。"
            )
        anchors.append("意味を先に、雰囲気はその後に置く。truth は増やさない。")
        prompt_hint = " ".join(part for part in anchors if part)
    return {
        "headline": session_opening.get("headline"),
        "selectedVariantLabel": profile.get("selectedOpeningVariantLabel"),
        "promptHint": prompt_hint,
        "openingLines": list(session_opening.get("lines") or []),
        "anchors": {
            "incitingIncidentLabel": (genesis.get("incitingIncident") or {}).get("label"),
            "incitingIncidentSummary": (genesis.get("incitingIncident") or {}).get("summary"),
            "hubLabel": (genesis.get("hub") or {}).get("label"),
            "dungeonLabel": (genesis.get("dungeon") or {}).get("label"),
            "castLabels": [
                {
                    "displayName": item.get("displayName"),
                    "roleLabel": item.get("roleLabel") or item.get("role"),
                    "affiliationLabel": item.get("affiliationLabel"),
                    "agenda": item.get("agenda"),
                }
                for item in cast_seed[:4]
            ],
            "storyAxes": list(genesis.get("storyAxes") or []),
        },
        "outputRules": [
            "導入は 2〜4 文で語る。",
            "最初に意味と状況、その後に雰囲気を置く。",
            "truth にない設定や勝手な既成事実を増やさない。",
            "確定前の導入・装備・恩恵は必ず案として扱う。",
        ],
        "finalizeReminder": "プレイヤーが同意したら finalizeCharacter を呼び、返り値を正本として開始導入を確定する。",
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
            "gptResponsibilities": ["narration", "npc_dialogue_surface", "free_action_narrative_surface", "character_genesis_surface"],
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
            "characterGenesis": _character_genesis_surface(display),
            "newGameGenesis": _new_game_genesis_surface(display),
            "openingPackage": _opening_package_surface(display),
        },
        "world": {
            "worldSpine": copy.deepcopy(display["worldSpine"]),
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
            "openingTask": "scene.openingLines と guidance.sessionOpeningGuide を基に、guidance.openingPackage があればそれを優先し、必要なら guidance.characterGenesis.openingVariants と guidance.newGameGenesis を使って、場面の導入を 2〜4 文で語る。",
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
