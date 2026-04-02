from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import json

from ..character_creation import CharacterProfile, parse_character_profile_payload
from ..character_genesis import apply_character_genesis
from ..errors import UiRequestError
from ..display_naming import apply_fantasy_display_naming
from ..gameplay_experience import build_campaign_display
from ..gpt_read_model import build_gpt_read_model_from_bundle
from ..front_hubs import build_player_front_hubs
from ..paths import RUNTIME_ROOT
from ..playable_loop import play_choice, play_free_action
from ..runner import build_bundle, build_bundle_from_world_state
from ..session_persistence import (
    build_next_session_state,
    resolve_saved_session_path,
    save_session_state,
)
from ..text.text_composer import (
    compose_action_mode_guide,
    compose_active_node_panel_copy,
    compose_institution_alert_panel_copy,
    compose_session_opening_guide,
    compose_transition_message,
    compose_world_pulse_panel_copy,
)


@dataclass(frozen=True)
class ViewerRequest:
    seed: Optional[int]
    seasons: int
    archetype: str
    world_json: Optional[Path]
    character_profile: Optional[CharacterProfile]


@dataclass(frozen=True)
class PlayRequest:
    choice_id: str
    seed: Optional[int]
    world_json: Optional[Path]


@dataclass(frozen=True)
class FreeActionRequest:
    action_text: str
    seed: Optional[int]
    world_json: Optional[Path]


@dataclass(frozen=True)
class SaveSessionRequest:
    world_json: Optional[Path]
    world_state: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class LoadSessionRequest:
    save_id: Optional[str]
    save_path: Optional[Path]


@dataclass(frozen=True)
class NextSessionRequest:
    world_json: Path


@dataclass(frozen=True)
class FinalizeCharacterRequest:
    world_json: Path
    proposal: Dict[str, Any]


UI_SESSION_ROOT = RUNTIME_ROOT / "ui_sessions"


def _first(query: Mapping[str, list[str]], key: str) -> Optional[str]:
    values = query.get(key) or []
    return values[0].strip() if values else None


def viewer_request_from_query(query: Mapping[str, list[str]]) -> ViewerRequest:
    seed_raw = _first(query, "seed")
    world_json_raw = _first(query, "world_json")
    seasons_raw = _first(query, "seasons")
    archetype = _first(query, "archetype") or "balanced"

    if seed_raw and world_json_raw:
        raise UiRequestError("Provide either `seed` or `world_json`, not both.")

    seasons = 10
    if seasons_raw:
        try:
            seasons = int(seasons_raw)
        except ValueError as exc:
            raise UiRequestError("`seasons` must be an integer.") from exc

    if world_json_raw:
        return ViewerRequest(seed=None, seasons=seasons, archetype=archetype, world_json=Path(world_json_raw), character_profile=None)

    character_profile = parse_character_profile_payload(
        {
            "character_name": _first(query, "character_name"),
            "character_race": _first(query, "character_race"),
            "character_style": _first(query, "character_style"),
            "character_temperament": _first(query, "character_temperament"),
            "character_origin": _first(query, "character_origin"),
            "character_loadout": _first(query, "character_loadout"),
            "character_source_mode": _first(query, "character_source_mode"),
            "character_source_title": _first(query, "character_source_title"),
            "character_source_name": _first(query, "character_source_name"),
            "character_appearance_notes": _first(query, "character_appearance_notes"),
            "character_reinterpretation_notes": _first(query, "character_reinterpretation_notes"),
        }
    )

    seed = 1729
    if seed_raw:
        try:
            seed = int(seed_raw)
        except ValueError as exc:
            raise UiRequestError("`seed` must be an integer.") from exc
    return ViewerRequest(seed=seed, seasons=seasons, archetype=archetype, world_json=None, character_profile=character_profile)


def _character_profile_request_payload(profile: Optional[CharacterProfile]) -> Optional[Dict[str, str]]:
    if profile is None:
        return None
    return {
        "name": profile.name,
        "race": profile.race,
        "style": profile.style,
        "temperament": profile.temperament,
        "origin": profile.origin,
        "loadout": profile.loadout,
        "source_mode": profile.source_mode,
        "source_title": profile.source_title,
        "source_name": profile.source_name,
        "appearance_notes": profile.appearance_notes,
        "reinterpretation_notes": profile.reinterpretation_notes,
    }


def _persist_world_state(world_state: Dict[str, Any]) -> str:
    UI_SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(world_state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
    target = UI_SESSION_ROOT / f"world_{digest}.json"
    if not target.exists():
        target.write_text(json.dumps(world_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def _raw_display_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
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
    display.update(build_campaign_display(bundle["world_state"], scene_packet["focusLabel"]))
    session = display.get("playCycle", {})
    archive_review = display.get("archiveReview") or {}
    next_session_hook = display.get("nextSessionHook") or {}
    character_profile = bundle["world_state"].get("resolved_world", {}).get("protagonist", {}).get("character_profile") or {}
    display["characterProfile"] = character_profile
    display["sessionOpeningGuide"] = compose_session_opening_guide(
        session,
        bundle["world_state"].get("campaign_state", {}).get("sessionOpeningHooks", {}).get(str(session.get("sessionNumber", 1))),
        archive_review,
        next_session_hook,
    )
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
    display.update(build_player_front_hubs(bundle["world_state"], display))
    return display


def _display_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    display = _raw_display_from_bundle(bundle)
    return apply_fantasy_display_naming(display)


def _bundle_payload(bundle: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "seed": bundle["seed"],
        "scene_output": bundle["scene_output"],
        "scene_packet": bundle["scene_packet"],
        "shell_snapshot": bundle["shell_snapshot"],
        "ui_event": bundle["ui_event"],
        "validation": bundle["validation"],
        "world_state": bundle["world_state"],
    }


def _play_source_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Optional[str]]:
    return {
        "seed": None,
        "world_json": _persist_world_state(bundle["world_state"]),
    }


def _read_model_from_after_bundle(after_bundle: Dict[str, Any]) -> tuple[Dict[str, Optional[str]], Dict[str, Any]]:
    play_source = _play_source_from_bundle(after_bundle)
    world_json = play_source.get("world_json")
    read_model = build_gpt_read_model_from_bundle(
        after_bundle,
        request_seed=None,
        request_world_json=Path(world_json) if world_json else None,
        request_archetype="balanced",
        request_seasons=10,
    )
    return play_source, read_model


def _front_snapshot_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "playSource": _play_source_from_bundle(bundle),
        "display": _display_from_bundle(bundle),
    }


def _compact_transition_payload(
    *,
    choice_id: str,
    intent_type: str,
    outcome: str,
    before_scene: str,
    after_scene: str,
    message: str,
    discovery_state: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "choiceId": choice_id,
        "intentType": intent_type,
        "outcome": outcome,
        "beforeScene": before_scene,
        "afterScene": after_scene,
        "message": message,
    }
    if discovery_state:
        payload["discoveryState"] = discovery_state
    return payload


def build_ui_payload(request: ViewerRequest) -> Dict[str, Any]:
    bundle = build_bundle(
        seed=request.seed,
        seasons=request.seasons,
        archetype=request.archetype,
        world_json=request.world_json,
        character_profile=request.character_profile,
    )
    return {
        "request": {
            "seed": request.seed,
            "seasons": request.seasons,
            "archetype": request.archetype,
            "world_json": str(request.world_json) if request.world_json else None,
            "character_profile": _character_profile_request_payload(request.character_profile),
        },
        "playSource": _play_source_from_bundle(bundle),
        "bundle": _bundle_payload(bundle),
        "display": _display_from_bundle(bundle),
    }


def build_front_snapshot_payload(request: ViewerRequest) -> Dict[str, Any]:
    bundle = build_bundle(
        seed=request.seed,
        seasons=request.seasons,
        archetype=request.archetype,
        world_json=request.world_json,
        character_profile=request.character_profile,
    )
    return {
        "request": {
            "seed": request.seed,
            "seasons": request.seasons,
            "archetype": request.archetype,
            "world_json": str(request.world_json) if request.world_json else None,
            "character_profile": _character_profile_request_payload(request.character_profile),
        },
        **_front_snapshot_from_bundle(bundle),
    }


def build_gpt_read_model_payload(request: ViewerRequest) -> Dict[str, Any]:
    bundle = build_bundle(
        seed=request.seed,
        seasons=request.seasons,
        archetype=request.archetype,
        world_json=request.world_json,
        character_profile=request.character_profile,
    )
    return {
        "request": {
            "seed": request.seed,
            "seasons": request.seasons,
            "archetype": request.archetype,
            "world_json": str(request.world_json) if request.world_json else None,
            "character_profile": _character_profile_request_payload(request.character_profile),
        },
        "playSource": _play_source_from_bundle(bundle),
        "readModel": build_gpt_read_model_from_bundle(
            bundle,
            request_seed=request.seed,
            request_world_json=request.world_json,
            request_archetype=request.archetype,
            request_seasons=request.seasons,
        ),
    }


def play_request_from_body(body: Dict[str, Any], *, prefer_world_json_when_both: bool = False) -> PlayRequest:
    choice_id = str(body.get("choiceId") or "").strip()
    seed_raw = body.get("seed")
    world_json_raw = body.get("world_json")

    if not choice_id:
        raise UiRequestError("`choiceId` is required.")
    if seed_raw is not None and world_json_raw and not prefer_world_json_when_both:
        raise UiRequestError("Provide either `seed` or `world_json`, not both.")

    seed: Optional[int] = None
    if seed_raw is not None:
        if not isinstance(seed_raw, int):
            raise UiRequestError("`seed` must be an integer or null.")
        seed = seed_raw

    world_json = None
    if world_json_raw:
        if not isinstance(world_json_raw, str):
            raise UiRequestError("`world_json` must be a string or null.")
        world_json = Path(world_json_raw)
        if prefer_world_json_when_both:
            seed = None

    if seed is None and world_json is None:
        raise UiRequestError("Either `seed` or `world_json` is required for /api/play.")

    return PlayRequest(choice_id=choice_id, seed=seed, world_json=world_json)


def free_action_request_from_body(body: Dict[str, Any], *, prefer_world_json_when_both: bool = False) -> FreeActionRequest:
    action_text = str(body.get("actionText") or "").strip()
    seed_raw = body.get("seed")
    world_json_raw = body.get("world_json")

    if not action_text:
        raise UiRequestError("`actionText` is required.")
    if seed_raw is not None and world_json_raw and not prefer_world_json_when_both:
        raise UiRequestError("Provide either `seed` or `world_json`, not both.")

    seed: Optional[int] = None
    if seed_raw is not None:
        if not isinstance(seed_raw, int):
            raise UiRequestError("`seed` must be an integer or null.")
        seed = seed_raw

    world_json = None
    if world_json_raw:
        if not isinstance(world_json_raw, str):
            raise UiRequestError("`world_json` must be a string or null.")
        world_json = Path(world_json_raw)
        if prefer_world_json_when_both:
            seed = None

    if seed is None and world_json is None:
        raise UiRequestError("Either `seed` or `world_json` is required for /api/free-action.")

    return FreeActionRequest(action_text=action_text, seed=seed, world_json=world_json)


def save_session_request_from_body(body: Dict[str, Any]) -> SaveSessionRequest:
    world_json_raw = body.get("world_json")
    world_state_raw = body.get("world_state")
    if world_json_raw and world_state_raw is not None:
        raise UiRequestError("Provide either `world_json` or `world_state`, not both.")
    if world_json_raw:
        if not isinstance(world_json_raw, str):
            raise UiRequestError("`world_json` must be a string or null.")
        return SaveSessionRequest(world_json=Path(world_json_raw), world_state=None)
    if world_state_raw is not None:
        if not isinstance(world_state_raw, dict):
            raise UiRequestError("`world_state` must be an object when provided.")
        return SaveSessionRequest(world_json=None, world_state=world_state_raw)
    raise UiRequestError("Either `world_json` or `world_state` is required for /api/save-session.")


def load_session_request_from_body(body: Dict[str, Any]) -> LoadSessionRequest:
    save_id_raw = body.get("saveId")
    save_path_raw = body.get("savePath")
    if save_id_raw and save_path_raw:
        raise UiRequestError("Provide either `saveId` or `savePath`, not both.")
    save_id = None
    save_path = None
    if save_id_raw is not None:
        if not isinstance(save_id_raw, str):
            raise UiRequestError("`saveId` must be a string when provided.")
        save_id = save_id_raw.strip() or None
    if save_path_raw is not None:
        if not isinstance(save_path_raw, str):
            raise UiRequestError("`savePath` must be a string when provided.")
        cleaned = save_path_raw.strip()
        save_path = Path(cleaned) if cleaned else None
    return LoadSessionRequest(save_id=save_id, save_path=save_path)


def next_session_request_from_body(body: Dict[str, Any]) -> NextSessionRequest:
    world_json_raw = body.get("world_json")
    if not isinstance(world_json_raw, str) or not world_json_raw.strip():
        raise UiRequestError("`world_json` is required for /api/next-session.")
    return NextSessionRequest(world_json=Path(world_json_raw.strip()))


def finalize_character_request_from_body(body: Dict[str, Any]) -> FinalizeCharacterRequest:
    world_json_raw = body.get("world_json")
    if not isinstance(world_json_raw, str) or not world_json_raw.strip():
        raise UiRequestError("`world_json` is required for /api/finalize-character.")
    proposal_raw = body.get("proposal")
    if proposal_raw is None:
        proposal_raw = {
            key: value
            for key, value in body.items()
            if key
            not in {
                "world_json",
            }
        }
    if not isinstance(proposal_raw, dict):
        raise UiRequestError("`proposal` must be an object when provided.")
    return FinalizeCharacterRequest(world_json=Path(world_json_raw.strip()), proposal=proposal_raw)


def build_play_payload(request: PlayRequest) -> Dict[str, Any]:
    result = play_choice(
        choice_id=request.choice_id,
        seed=request.seed,
        world_json=request.world_json,
    )
    after_bundle = result["after"]["bundle"]
    transition = after_bundle["world_state"]["campaign_state"].get("lastTransition") or {}
    return {
        "playSource": _play_source_from_bundle(after_bundle),
        "bundle": _bundle_payload(after_bundle),
        "display": _display_from_bundle(after_bundle),
        "transition": {
            "choiceId": request.choice_id,
            "intentType": result["intent"]["intent_type"],
            "outcome": result["resolution"]["outcome"],
            "beforeScene": result["before"]["scene_title"],
            "afterScene": result["after"]["scene_title"],
            "message": compose_transition_message(transition, result["resolution"]["outcome"]),
            "campaign": transition,
        },
    }


def build_gpt_play_payload(request: PlayRequest) -> Dict[str, Any]:
    result = play_choice(
        choice_id=request.choice_id,
        seed=request.seed,
        world_json=request.world_json,
    )
    after_bundle = result["after"]["bundle"]
    transition = after_bundle["world_state"]["campaign_state"].get("lastTransition") or {}
    play_source, read_model = _read_model_from_after_bundle(after_bundle)
    return {
        "playSource": play_source,
        "readModel": read_model,
        "transition": _compact_transition_payload(
            choice_id=request.choice_id,
            intent_type=result["intent"]["intent_type"],
            outcome=result["resolution"]["outcome"],
            before_scene=result["before"]["scene_title"],
            after_scene=result["after"]["scene_title"],
            message=compose_transition_message(transition, result["resolution"]["outcome"]),
        ),
    }


def build_front_play_payload(request: PlayRequest) -> Dict[str, Any]:
    result = play_choice(
        choice_id=request.choice_id,
        seed=request.seed,
        world_json=request.world_json,
    )
    after_bundle = result["after"]["bundle"]
    transition = after_bundle["world_state"]["campaign_state"].get("lastTransition") or {}
    return {
        **_front_snapshot_from_bundle(after_bundle),
        "transition": {
            "choiceId": request.choice_id,
            "intentType": result["intent"]["intent_type"],
            "outcome": result["resolution"]["outcome"],
            "beforeScene": result["before"]["scene_title"],
            "afterScene": result["after"]["scene_title"],
            "message": compose_transition_message(transition, result["resolution"]["outcome"]),
        },
    }


def build_free_action_payload(request: FreeActionRequest) -> Dict[str, Any]:
    result = play_free_action(
        action_text=request.action_text,
        seed=request.seed,
        world_json=request.world_json,
    )
    after_bundle = result["after"]["bundle"]
    structured_result = result["structured_result"]
    transition = after_bundle["world_state"]["campaign_state"].get("lastTransition") or {}
    free_action = after_bundle["world_state"]["campaign_state"].get("lastFreeAction") or {}
    action_summary = structured_result["source"]["player_summary"]
    message = (
        f"{action_summary}。"
        f"{structured_result['adjudication']['note']} "
        f"{free_action.get('logs', {}).get('afterglow', structured_result['consequence']['logs']['afterglow'])}"
    )
    return {
        "playSource": _play_source_from_bundle(after_bundle),
        "bundle": _bundle_payload(after_bundle),
        "display": _display_from_bundle(after_bundle),
        "structuredResult": structured_result,
        "transition": {
            "choiceId": "custom_action",
            "intentType": structured_result["normalized_intent"]["intent_type"],
            "outcome": structured_result["adjudication"]["outcome"],
            "beforeScene": result["before"]["scene_title"],
            "afterScene": result["after"]["scene_title"],
            "message": message,
            "campaign": transition,
        },
    }


def build_gpt_free_action_payload(request: FreeActionRequest) -> Dict[str, Any]:
    result = play_free_action(
        action_text=request.action_text,
        seed=request.seed,
        world_json=request.world_json,
    )
    after_bundle = result["after"]["bundle"]
    structured_result = result["structured_result"]
    transition = after_bundle["world_state"]["campaign_state"].get("lastTransition") or {}
    free_action = after_bundle["world_state"]["campaign_state"].get("lastFreeAction") or {}
    action_summary = structured_result["source"]["player_summary"]
    message = (
        f"{action_summary}。"
        f"{structured_result['adjudication']['note']} "
        f"{free_action.get('logs', {}).get('afterglow', structured_result['consequence']['logs']['afterglow'])}"
    )
    play_source, read_model = _read_model_from_after_bundle(after_bundle)
    return {
        "playSource": play_source,
        "readModel": read_model,
        "structuredResult": {
            "summary": action_summary,
            "residue": free_action.get("freeActionResidueLabel") or "",
            "intentType": structured_result["normalized_intent"]["intent_type"],
            "outcome": structured_result["adjudication"]["outcome"],
            "successBand": structured_result["adjudication"]["success_band"],
            "discoveryState": structured_result["adjudication"]["discovery_state"],
            "note": structured_result["adjudication"]["note"],
            "viceTags": list(structured_result["normalized_intent"].get("vice_tags", [])),
            "tabooTags": list(structured_result["normalized_intent"].get("taboo_tags", [])),
        },
        "transition": _compact_transition_payload(
            choice_id="custom_action",
            intent_type=structured_result["normalized_intent"]["intent_type"],
            outcome=structured_result["adjudication"]["outcome"],
            before_scene=result["before"]["scene_title"],
            after_scene=result["after"]["scene_title"],
            message=message,
            discovery_state=structured_result["adjudication"]["discovery_state"],
        ),
    }


def build_front_free_action_payload(request: FreeActionRequest) -> Dict[str, Any]:
    result = play_free_action(
        action_text=request.action_text,
        seed=request.seed,
        world_json=request.world_json,
    )
    after_bundle = result["after"]["bundle"]
    structured_result = result["structured_result"]
    transition = after_bundle["world_state"]["campaign_state"].get("lastTransition") or {}
    free_action = after_bundle["world_state"]["campaign_state"].get("lastFreeAction") or {}
    action_summary = structured_result["source"]["player_summary"]
    message = (
        f"{action_summary}。"
        f"{structured_result['adjudication']['note']} "
        f"{free_action.get('logs', {}).get('afterglow', structured_result['consequence']['logs']['afterglow'])}"
    )
    return {
        **_front_snapshot_from_bundle(after_bundle),
        "structuredResult": {
            "summary": action_summary,
            "residue": free_action.get("freeActionResidueLabel") or "",
            "intentType": structured_result["normalized_intent"]["intent_type"],
            "outcome": structured_result["adjudication"]["outcome"],
            "successBand": structured_result["adjudication"]["success_band"],
            "discoveryState": structured_result["adjudication"]["discovery_state"],
            "note": structured_result["adjudication"]["note"],
            "viceTags": list(structured_result["normalized_intent"].get("vice_tags", [])),
            "tabooTags": list(structured_result["normalized_intent"].get("taboo_tags", [])),
        },
        "transition": _compact_transition_payload(
            choice_id="custom_action",
            intent_type=structured_result["normalized_intent"]["intent_type"],
            outcome=structured_result["adjudication"]["outcome"],
            before_scene=result["before"]["scene_title"],
            after_scene=result["after"]["scene_title"],
            message=message,
            discovery_state=structured_result["adjudication"]["discovery_state"],
        ),
    }


def build_save_session_payload(request: SaveSessionRequest) -> Dict[str, Any]:
    return save_session_state(world_json=request.world_json, world_state=request.world_state)


def build_load_session_payload(request: LoadSessionRequest) -> Dict[str, Any]:
    resolved_path = resolve_saved_session_path(save_id=request.save_id, save_path=request.save_path)
    bundle = build_bundle(world_json=resolved_path)
    save_meta = bundle["world_state"]["campaign_state"].get("saveMeta") or {}
    return {
        "request": {
            "saveId": request.save_id,
            "savePath": str(request.save_path) if request.save_path else None,
            "resolvedSavePath": str(resolved_path),
        },
        "saveMeta": save_meta,
        "playSource": _play_source_from_bundle(bundle),
        "bundle": _bundle_payload(bundle),
        "display": _display_from_bundle(bundle),
    }


def build_gpt_load_session_payload(request: LoadSessionRequest) -> Dict[str, Any]:
    resolved_path = resolve_saved_session_path(save_id=request.save_id, save_path=request.save_path)
    bundle = build_bundle(world_json=resolved_path)
    save_meta = bundle["world_state"]["campaign_state"].get("saveMeta") or {}
    play_source, read_model = _read_model_from_after_bundle(bundle)
    return {
        "request": {
            "saveId": request.save_id,
            "savePath": str(request.save_path) if request.save_path else None,
            "resolvedSavePath": str(resolved_path),
        },
        "saveMeta": save_meta,
        "playSource": play_source,
        "readModel": read_model,
    }


def build_front_load_session_payload(request: LoadSessionRequest) -> Dict[str, Any]:
    resolved_path = resolve_saved_session_path(save_id=request.save_id, save_path=request.save_path)
    bundle = build_bundle(world_json=resolved_path)
    save_meta = bundle["world_state"]["campaign_state"].get("saveMeta") or {}
    return {
        "request": {
            "saveId": request.save_id,
            "savePath": str(request.save_path) if request.save_path else None,
            "resolvedSavePath": str(resolved_path),
        },
        "saveMeta": save_meta,
        **_front_snapshot_from_bundle(bundle),
    }


def _finalize_character_bundle(request: FinalizeCharacterRequest) -> tuple[Dict[str, Any], Dict[str, Any]]:
    before_bundle = build_bundle(world_json=request.world_json, include_runtime_context=True)
    display = _raw_display_from_bundle(before_bundle)
    updated_world, applied = apply_character_genesis(
        before_bundle["world_state"],
        equipment_hub=display.get("equipmentHub") or {},
        proposal=request.proposal,
    )
    after_bundle = build_bundle_from_world_state(updated_world, before_bundle["assets"])
    return after_bundle, applied


def build_front_finalize_character_payload(request: FinalizeCharacterRequest) -> Dict[str, Any]:
    bundle, applied = _finalize_character_bundle(request)
    return {
        "request": {
            "world_json": str(request.world_json),
        },
        **_front_snapshot_from_bundle(bundle),
        "appliedGenesis": applied,
        "transition": {
            "choiceId": "character_finalize",
            "intentType": "character_genesis",
            "outcome": "applied" if applied else "no_change",
            "message": "主人公の開始装備・恩恵・導入案を反映しました。" if applied else "反映できる開始案はありませんでした。",
        },
    }


def build_gpt_finalize_character_payload(request: FinalizeCharacterRequest) -> Dict[str, Any]:
    bundle, applied = _finalize_character_bundle(request)
    play_source, read_model = _read_model_from_after_bundle(bundle)
    return {
        "request": {
            "world_json": str(request.world_json),
        },
        "playSource": play_source,
        "readModel": read_model,
        "appliedGenesis": applied,
        "transition": {
            "choiceId": "character_finalize",
            "intentType": "character_genesis",
            "outcome": "applied" if applied else "no_change",
            "message": "主人公の開始装備・恩恵・導入案を反映しました。" if applied else "反映できる開始案はありませんでした。",
        },
    }


def build_next_session_payload(request: NextSessionRequest) -> Dict[str, Any]:
    updated_world = build_next_session_state(request.world_json)
    runtime_world_json = Path(_persist_world_state(updated_world))
    bundle = build_bundle(world_json=runtime_world_json)
    campaign = bundle["world_state"]["campaign_state"]
    return {
        "request": {
            "world_json": str(request.world_json),
        },
        "playSource": _play_source_from_bundle(bundle),
        "bundle": _bundle_payload(bundle),
        "display": _display_from_bundle(bundle),
        "nextSessionHook": campaign.get("nextSessionHook"),
        "sessionArchiveSize": len(campaign.get("sessionArchive", [])),
    }


def build_front_next_session_payload(request: NextSessionRequest) -> Dict[str, Any]:
    updated_world = build_next_session_state(request.world_json)
    runtime_world_json = Path(_persist_world_state(updated_world))
    bundle = build_bundle(world_json=runtime_world_json)
    campaign = bundle["world_state"]["campaign_state"]
    return {
        "request": {
            "world_json": str(request.world_json),
        },
        **_front_snapshot_from_bundle(bundle),
        "nextSessionHook": campaign.get("nextSessionHook"),
        "sessionArchiveSize": len(campaign.get("sessionArchive", [])),
    }


def build_gpt_next_session_payload(request: NextSessionRequest) -> Dict[str, Any]:
    updated_world = build_next_session_state(request.world_json)
    runtime_world_json = Path(_persist_world_state(updated_world))
    bundle = build_bundle(world_json=runtime_world_json)
    campaign = bundle["world_state"]["campaign_state"]
    play_source, read_model = _read_model_from_after_bundle(bundle)
    return {
        "request": {
            "world_json": str(request.world_json),
        },
        "playSource": play_source,
        "readModel": read_model,
        "nextSessionHook": campaign.get("nextSessionHook"),
        "sessionArchiveSize": len(campaign.get("sessionArchive", [])),
    }
