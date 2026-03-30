from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import copy
import json
import tempfile

from .assets import load_canonical_assets
from .gameplay_experience import ensure_campaign_state, prepare_next_session
from .gpt_read_model import build_gpt_read_model_from_bundle
from .paths import PROJECT_ROOT, RUNTIME_ROOT
from .playable_loop import play_choice, play_free_action
from .runner import build_bundle, build_bundle_from_world_state, dump_bundle


SAMPLES_ROOT = PROJECT_ROOT / "samples"


@dataclass(frozen=True)
class CleanupReport:
    removed_saves: int
    removed_ui_sessions: int
    kept_saves: int
    kept_ui_sessions: int
    removed_paths: tuple[str, ...]


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _play_choices(world_state: Dict[str, Any], choice_ids: Iterable[str]) -> Dict[str, Any]:
    current = copy.deepcopy(world_state)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_world = Path(temp_dir) / "release_sample_world.json"
        for choice_id in choice_ids:
            _write_json(temp_world, current)
            result = play_choice(choice_id=choice_id, seed=None, world_json=temp_world)
            current = result["after"]["bundle"]["world_state"]
    return current


def _play_free_action(world_state: Dict[str, Any], action_text: str) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_world = Path(temp_dir) / "release_sample_world.json"
        _write_json(temp_world, world_state)
        result = play_free_action(action_text=action_text, seed=None, world_json=temp_world)
        return result["after"]["bundle"]["world_state"]


def _sample_save_world(world_state: Dict[str, Any], save_id: str, save_path: Path) -> Dict[str, Any]:
    state = ensure_campaign_state(copy.deepcopy(world_state))
    state["campaign_state"]["saveMeta"] = {
        "saveId": save_id,
        "savePath": str(save_path.resolve()),
        "savedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return state


def build_release_samples(output_root: Optional[Path] = None) -> Dict[str, str]:
    root = output_root or SAMPLES_ROOT
    canonical_assets = load_canonical_assets()

    opening_1729 = build_bundle(seed=1729, seasons=10, archetype="balanced", assets=canonical_assets)
    opening_2048 = build_bundle(seed=2048, seasons=10, archetype="balanced", assets=canonical_assets)

    bundle_1729_path = root / "bundles" / "seed1729_opening_bundle.json"
    bundle_2048_path = root / "bundles" / "seed2048_opening_bundle.json"
    dump_bundle(opening_1729, bundle_1729_path)
    dump_bundle(opening_2048, bundle_2048_path)

    current_world = copy.deepcopy(opening_1729["world_state"])
    current_world = _play_choices(current_world, ["observe", "inspect", "speak"])
    save_path = root / "saves" / "seed1729_turn3_save.json"
    sample_save_world = _sample_save_world(current_world, "sample_seed1729_turn3", save_path)
    _write_json(save_path, sample_save_world)

    campaign_world = copy.deepcopy(opening_1729["world_state"])
    campaign_world = _play_free_action(campaign_world, "夜中に宿の裏から入り、裏帳面を盗み出す")
    campaign_world = _play_choices(campaign_world, ["observe", "inspect", "speak", "observe", "intervene", "inspect"])
    campaign_world = prepare_next_session(campaign_world)
    campaign_world = _play_choices(campaign_world, ["observe", "inspect"])
    campaign_path = root / "campaigns" / "seed1729_two_sessions_world.json"
    _write_json(campaign_path, campaign_world)

    campaign_bundle = build_bundle_from_world_state(campaign_world, canonical_assets)
    gpt_read_model = build_gpt_read_model_from_bundle(
        campaign_bundle,
        request_seed=1729,
        request_world_json=campaign_path,
        request_archetype="balanced",
        request_seasons=10,
    )
    gpt_path = root / "gpt" / "seed1729_two_sessions_read_model.json"
    _write_json(gpt_path, gpt_read_model)

    manifest = {
        "samples": {
            "openingBundle1729": str(bundle_1729_path.resolve()),
            "openingBundle2048": str(bundle_2048_path.resolve()),
            "sampleSave": str(save_path.resolve()),
            "sampleCampaignWorld": str(campaign_path.resolve()),
            "sampleGptReadModel": str(gpt_path.resolve()),
        },
        "notes": [
            "sample save は /api/load-session の savePath でも読める。",
            "sample campaign は archive / nextSessionHook / current scene echo が入った状態。",
            "sample GPT read model は narration 専用で、truth mutation はしない。",
        ],
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)

    return {
        "bundle1729": str(bundle_1729_path.resolve()),
        "bundle2048": str(bundle_2048_path.resolve()),
        "sampleSave": str(save_path.resolve()),
        "sampleCampaignWorld": str(campaign_path.resolve()),
        "sampleGptReadModel": str(gpt_path.resolve()),
        "manifest": str(manifest_path.resolve()),
    }


def cleanup_runtime_artifacts(
    *,
    runtime_root: Path = RUNTIME_ROOT,
    keep_recent_saves: int = 40,
    keep_recent_ui_sessions: int = 120,
    dry_run: bool = True,
) -> CleanupReport:
    save_root = runtime_root / "session_saves"
    ui_root = runtime_root / "ui_sessions"

    save_paths = sorted(save_root.glob("save_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    ui_paths = sorted(ui_root.glob("world_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)

    removable_saves = save_paths[keep_recent_saves:]
    removable_ui = ui_paths[keep_recent_ui_sessions:]

    removed_paths: list[str] = []
    if not dry_run:
        for path in [*removable_saves, *removable_ui]:
            if path.exists():
                path.unlink()
                removed_paths.append(str(path.resolve()))
    else:
        removed_paths = [str(path.resolve()) for path in [*removable_saves, *removable_ui]]

    return CleanupReport(
        removed_saves=len(removable_saves),
        removed_ui_sessions=len(removable_ui),
        kept_saves=min(len(save_paths), keep_recent_saves),
        kept_ui_sessions=min(len(ui_paths), keep_recent_ui_sessions),
        removed_paths=tuple(removed_paths),
    )
