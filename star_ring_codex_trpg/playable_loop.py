from __future__ import annotations

from typing import Any, Dict, Optional

from .assets import CanonicalAssets
from .free_action_adjudicator import adjudicate_free_action
from .free_action_parser import parse_free_action
from .free_action_recorder import apply_free_action_result
from .gameplay_experience import advance_campaign_state
from .intent import choice_to_intent
from .resolution import apply_resolution, resolve_intent
from .runner import build_bundle, build_bundle_from_world_state


def _public_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in bundle.items() if key not in {"scene_context", "assets"}}


def play_choice(
    choice_id: str,
    seed: Optional[int] = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
    world_json=None,
    assets: Optional[CanonicalAssets] = None,
) -> Dict[str, Any]:
    before_bundle = build_bundle(
        seed=seed,
        seasons=seasons,
        archetype=archetype,
        world_json=world_json,
        assets=assets,
        include_runtime_context=True,
    )
    canonical_assets = assets or before_bundle["assets"]
    intent = choice_to_intent(choice_id)
    resolution = resolve_intent(before_bundle["world_state"], before_bundle["scene_context"], intent)
    updated_world = apply_resolution(before_bundle["world_state"], before_bundle["scene_context"], intent, resolution)
    progressed_world = advance_campaign_state(updated_world, choice_id, intent.to_dict(), resolution.to_dict())
    after_bundle = build_bundle_from_world_state(progressed_world, canonical_assets)
    before_public = _public_bundle(before_bundle)
    return {
        "choice_id": choice_id,
        "intent": intent.to_dict(),
        "resolution": resolution.to_dict(),
        "before": {
            "scene_title": before_bundle["scene_output"]["player_facing"]["scene_title"],
            "active_node": before_bundle["shell_snapshot"]["contextRail"]["activeNode"],
            "institution_alert": before_bundle["shell_snapshot"]["contextRail"]["institutionAlert"],
            "world_pulse": before_bundle["shell_snapshot"]["contextRail"]["worldPulse"],
            "bundle": before_public,
        },
        "after": {
            "scene_title": after_bundle["scene_output"]["player_facing"]["scene_title"],
            "active_node": after_bundle["shell_snapshot"]["contextRail"]["activeNode"],
            "institution_alert": after_bundle["shell_snapshot"]["contextRail"]["institutionAlert"],
            "world_pulse": after_bundle["shell_snapshot"]["contextRail"]["worldPulse"],
            "bundle": after_bundle,
        },
    }


def play_free_action(
    action_text: str,
    seed: Optional[int] = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
    world_json=None,
    assets: Optional[CanonicalAssets] = None,
) -> Dict[str, Any]:
    before_bundle = build_bundle(
        seed=seed,
        seasons=seasons,
        archetype=archetype,
        world_json=world_json,
        assets=assets,
        include_runtime_context=True,
    )
    canonical_assets = assets or before_bundle["assets"]
    campaign_state = before_bundle["world_state"]["campaign_state"]
    parsed_action = parse_free_action(
        action_text,
        before_bundle["world_state"],
        campaign_state,
        before_bundle["scene_context"],
    )
    structured_result = adjudicate_free_action(
        parsed_action,
        before_bundle["world_state"],
        campaign_state,
        before_bundle["scene_context"],
    )
    updated_world = apply_free_action_result(before_bundle["world_state"], before_bundle["scene_context"], structured_result)
    after_bundle = build_bundle_from_world_state(updated_world, canonical_assets)
    before_public = _public_bundle(before_bundle)
    return {
        "action_text": action_text,
        "structured_result": structured_result,
        "before": {
            "scene_title": before_bundle["scene_output"]["player_facing"]["scene_title"],
            "active_node": before_bundle["shell_snapshot"]["contextRail"]["activeNode"],
            "institution_alert": before_bundle["shell_snapshot"]["contextRail"]["institutionAlert"],
            "world_pulse": before_bundle["shell_snapshot"]["contextRail"]["worldPulse"],
            "bundle": before_public,
        },
        "after": {
            "scene_title": after_bundle["scene_output"]["player_facing"]["scene_title"],
            "active_node": after_bundle["shell_snapshot"]["contextRail"]["activeNode"],
            "institution_alert": after_bundle["shell_snapshot"]["contextRail"]["institutionAlert"],
            "world_pulse": after_bundle["shell_snapshot"]["contextRail"]["worldPulse"],
            "bundle": after_bundle,
        },
    }
