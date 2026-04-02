from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json

from .assets import CanonicalAssets, load_canonical_assets
from .character_creation import CharacterProfile, apply_character_profile
from .gameplay_experience import ensure_campaign_state
from .scene_builder import build_scene_output
from .ui_builder import build_shell_snapshot, build_ui_event
from .validation import ensure_contracts_valid, validate_contracts
from .world_engine import generate_world_state, load_world_state


def build_bundle_from_world_state(
    world_state: Dict[str, Any],
    canonical_assets: CanonicalAssets,
    include_runtime_context: bool = False,
) -> Dict[str, Any]:
    experience_world = ensure_campaign_state(world_state)
    scene_output, scene_packet, context = build_scene_output(experience_world, canonical_assets)
    shell_snapshot = build_shell_snapshot(experience_world, scene_packet, context, canonical_assets)
    ui_event = build_ui_event(experience_world, shell_snapshot, canonical_assets)
    validation = validate_contracts(
        scene_packet,
        shell_snapshot,
        ui_event,
        {
            "scene_packet": canonical_assets.scene_packet_schema,
            "shell_snapshot": canonical_assets.shell_snapshot_schema,
            "ui_event": canonical_assets.ui_event_schema,
        },
    )
    ensure_contracts_valid(validation)
    resolved_world = experience_world["resolved_world"]["world"]
    bundle = {
        "seed": resolved_world.get("seed"),
        "world_state": experience_world,
        "scene_output": scene_output,
        "scene_packet": scene_packet,
        "shell_snapshot": shell_snapshot,
        "ui_event": ui_event,
        "validation": validation,
    }
    if include_runtime_context:
        bundle["scene_context"] = context
        bundle["assets"] = canonical_assets
    return bundle


def build_bundle(
    seed: Optional[int] = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
    world_json: Optional[Path] = None,
    character_profile: Optional[CharacterProfile] = None,
    assets: Optional[CanonicalAssets] = None,
    include_runtime_context: bool = False,
) -> Dict[str, Any]:
    canonical_assets = assets or load_canonical_assets()
    if world_json is not None:
        world_state = load_world_state(world_json)
    else:
        if seed is None:
            raise ValueError("seed is required when world_json is not provided")
        world_state = generate_world_state(seed=seed, seasons=seasons, archetype=archetype)
        if character_profile is not None:
            world_state = apply_character_profile(world_state, character_profile, seed=seed)
    return build_bundle_from_world_state(world_state, canonical_assets, include_runtime_context=include_runtime_context)


def dump_bundle(bundle: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    return payload
