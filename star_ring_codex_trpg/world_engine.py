from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import importlib.util
import json
import shutil
import sys

from .errors import AssetLoadError, WorldStateError
from .paths import CANONICAL_ROOT, REFERENCE_ROOT, RUNTIME_ROOT, require_path


ENGINE_FILES = {
    "pbw_world_mythic_integration_v9.py": CANONICAL_ROOT / "pbw_world_mythic_integration_v9.py",
    "pbw_world_historical_resolution_v8.py": REFERENCE_ROOT / "pbw_world_historical_resolution_v8.py",
    "pbw_world_historical_nodes_v7.py": REFERENCE_ROOT / "pbw_world_historical_nodes_v7.py",
}


def load_world_state(path: Path) -> Dict[str, Any]:
    try:
        world_state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorldStateError(f"World JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorldStateError(f"Invalid world JSON: {path} ({exc.msg})") from exc
    validate_world_state(world_state, source_label=str(path))
    return world_state


def _require_mapping(value: Any, label: str, source_label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise WorldStateError(f"Invalid world JSON at {source_label}: `{label}` must be an object")
    return value


def _require_keys(mapping: Dict[str, Any], keys: list[str], label: str, source_label: str) -> None:
    for key in keys:
        if key not in mapping:
            raise WorldStateError(f"Invalid world JSON at {source_label}: missing `{label}.{key}`")


def validate_world_state(world_state: Dict[str, Any], source_label: str = "<generated>") -> None:
    root = _require_mapping(world_state, "world_state", source_label)
    _require_keys(root, ["resolved_world"], "world_state", source_label)
    resolved_world = _require_mapping(root["resolved_world"], "resolved_world", source_label)
    _require_keys(
        resolved_world,
        ["world", "regions", "factions", "institutions", "active_nodes", "chains", "protagonist", "resolution_history", "archived_nodes"],
        "resolved_world",
        source_label,
    )
    world = _require_mapping(resolved_world["world"], "resolved_world.world", source_label)
    _require_keys(
        world,
        ["seed", "world_name", "calendar_name", "calendar_year", "season_index", "main_god_name", "current_world_era"],
        "resolved_world.world",
        source_label,
    )


def prepare_runtime_engine() -> Path:
    engine_root = RUNTIME_ROOT / "world_engine"
    engine_root.mkdir(parents=True, exist_ok=True)
    for filename, source in ENGINE_FILES.items():
        target = engine_root / filename
        try:
            shutil.copy2(require_path(source, filename), target)
        except FileNotFoundError as exc:
            raise AssetLoadError(f"Runtime dependency is missing: {filename} ({source})") from exc
    return engine_root / "pbw_world_mythic_integration_v9.py"


def _load_v9_module() -> Any:
    engine_path = prepare_runtime_engine()
    module_name = "pbw_world_mythic_integration_v9_runtime"
    spec = importlib.util.spec_from_file_location(module_name, engine_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runtime engine from {engine_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def generate_world_state(seed: int, seasons: int = 10, archetype: str = "balanced") -> Dict[str, Any]:
    module = _load_v9_module()
    divine_world = module.simulate(seed=seed, seasons=seasons, archetype=archetype)
    world_state = module.export_world(divine_world)
    validate_world_state(world_state)
    return world_state
