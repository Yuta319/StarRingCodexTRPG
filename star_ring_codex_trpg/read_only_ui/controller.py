from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import json

from ..errors import UiRequestError
from ..gameplay_experience import build_campaign_display
from ..gpt_read_model import build_gpt_read_model_from_bundle
from ..paths import RUNTIME_ROOT
from ..playable_loop import play_choice, play_free_action
from ..runner import build_bundle
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
        return ViewerRequest(seed=None, seasons=seasons, archetype=archetype, world_json=Path(world_json_raw))

    seed = 1729
    if seed_raw:
        try:
            seed = int(seed_raw)
        except ValueError as exc:
            raise UiRequestError("`seed` must be an integer.") from exc
    return ViewerRequest(seed=seed, seasons=seasons, archetype=archetype, world_json=None)


def _persist_world_state(world_state: Dict[str, Any]) -> str:
    UI_SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(world_state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
    target = UI_SESSION_ROOT / f"world_{digest}.json"
    if not target.exists():
        target.write_text(json.dumps(world_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def _display_from_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
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


def build_ui_payload(request: ViewerRequest) -> Dict[str, Any]:
    bundle = build_bundle(
        seed=request.seed,
        seasons=request.seasons,
        archetype=request.archetype,
        world_json=request.world_json,
    )
    return {
        "request": {
            "seed": request.seed,
            "seasons": request.seasons,
            "archetype": request.archetype,
            "world_json": str(request.world_json) if request.world_json else None,
        },
        "playSource": _play_source_from_bundle(bundle),
        "bundle": _bundle_payload(bundle),
        "display": _display_from_bundle(bundle),
    }


def build_gpt_read_model_payload(request: ViewerRequest) -> Dict[str, Any]:
    bundle = build_bundle(
        seed=request.seed,
        seasons=request.seasons,
        archetype=request.archetype,
        world_json=request.world_json,
    )
    return {
        "request": {
            "seed": request.seed,
            "seasons": request.seasons,
            "archetype": request.archetype,
            "world_json": str(request.world_json) if request.world_json else None,
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


def play_request_from_body(body: Dict[str, Any]) -> PlayRequest:
    choice_id = str(body.get("choiceId") or "").strip()
    seed_raw = body.get("seed")
    world_json_raw = body.get("world_json")

    if not choice_id:
        raise UiRequestError("`choiceId` is required.")
    if seed_raw is not None and world_json_raw:
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

    if seed is None and world_json is None:
        raise UiRequestError("Either `seed` or `world_json` is required for /api/play.")

    return PlayRequest(choice_id=choice_id, seed=seed, world_json=world_json)


def free_action_request_from_body(body: Dict[str, Any]) -> FreeActionRequest:
    action_text = str(body.get("actionText") or "").strip()
    seed_raw = body.get("seed")
    world_json_raw = body.get("world_json")

    if not action_text:
        raise UiRequestError("`actionText` is required.")
    if seed_raw is not None and world_json_raw:
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
