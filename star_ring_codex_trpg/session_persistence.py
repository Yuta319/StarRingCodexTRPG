from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional
import copy
import json

from .errors import WorldStateError
from .gameplay_experience import ensure_campaign_state, prepare_next_session
from .paths import RUNTIME_ROOT
from .world_engine import load_world_state


SESSION_SAVE_ROOT = RUNTIME_ROOT / "session_saves"


def _timestamp_label(now: datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%S")


def _saved_at(now: datetime) -> str:
    return now.astimezone().isoformat(timespec="seconds")


def _load_source_state(world_json: Optional[Path], world_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if world_json is not None and world_state is not None:
        raise WorldStateError("Provide either `world_json` or `world_state`, not both.")
    if world_json is not None:
        return load_world_state(world_json)
    if world_state is not None:
        return copy.deepcopy(world_state)
    raise WorldStateError("Either `world_json` or `world_state` is required.")


def _session_summary(world_state: Dict[str, Any]) -> Dict[str, Any]:
    campaign = ensure_campaign_state(world_state)["campaign_state"]
    ending = campaign.get("lastEnding")
    if isinstance(ending, dict):
        return {
            "sessionNumber": ending["sessionNumber"],
            "title": ending["title"],
            "tone": ending["tone"],
            "summary": ending["summary"],
        }
    session = campaign["session"]
    current_event = campaign["events"]["catalog"][campaign["currentEventId"]]
    return {
        "sessionNumber": session["sessionNumber"],
        "title": current_event["label"],
        "tone": None,
        "summary": f"第{session['sessionNumber']}セッションの{session['turnInSession']}/{session['maxTurns']}手目。事件は「{current_event['label']}」。",
    }


def _unique_save_identity(base_id: str) -> str:
    SESSION_SAVE_ROOT.mkdir(parents=True, exist_ok=True)
    candidate = base_id
    counter = 2
    while (SESSION_SAVE_ROOT / f"{candidate}.json").exists():
        candidate = f"{base_id}_{counter}"
        counter += 1
    return candidate


def save_session_state(
    *,
    world_json: Optional[Path] = None,
    world_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = ensure_campaign_state(_load_source_state(world_json, world_state))
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = sha256(payload.encode("utf-8")).hexdigest()[:12]
    now = datetime.now().astimezone()
    save_id = _unique_save_identity(f"save_{_timestamp_label(now)}_{digest}")
    save_path = (SESSION_SAVE_ROOT / f"{save_id}.json").resolve()
    saved_at = _saved_at(now)

    campaign = copy.deepcopy(state["campaign_state"])
    campaign["saveMeta"] = {
        "saveId": save_id,
        "savePath": str(save_path),
        "savedAt": saved_at,
    }
    state["campaign_state"] = campaign
    save_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "saveId": save_id,
        "savePath": str(save_path),
        "savedAt": saved_at,
        "sessionSummary": _session_summary(state),
    }


def resolve_saved_session_path(*, save_id: Optional[str] = None, save_path: Optional[Path] = None) -> Path:
    if save_id and save_path is not None:
        raise WorldStateError("Provide either `saveId` or `savePath`, not both.")
    if save_path is not None:
        target = save_path
    elif save_id:
        target = SESSION_SAVE_ROOT / f"{save_id}.json"
    else:
        candidates = sorted(SESSION_SAVE_ROOT.glob("save_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise WorldStateError("No saved session was found. Save a session first.")
        target = candidates[0]
    if not target.exists():
        raise WorldStateError(f"Saved session not found: {target}")
    return target.resolve()


def load_saved_session_state(*, save_id: Optional[str] = None, save_path: Optional[Path] = None) -> Dict[str, Any]:
    return ensure_campaign_state(load_world_state(resolve_saved_session_path(save_id=save_id, save_path=save_path)))


def build_next_session_state(world_json: Path) -> Dict[str, Any]:
    return prepare_next_session(load_world_state(world_json))
