from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json

from .errors import AssetLoadError
from .paths import CANONICAL_ROOT, UI_CONTRACTS_ROOT, require_path


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetLoadError(f"Required asset file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AssetLoadError(f"Asset JSON is invalid: {path} ({exc.msg})") from exc


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise AssetLoadError(f"Required asset text file is missing: {path}") from exc


def _extract_bullets(markdown: str, heading: str) -> List[str]:
    lines = markdown.splitlines()
    bullets: List[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"### {heading}":
            in_section = True
            continue
        if in_section and stripped.startswith("### "):
            break
        if in_section and stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _style_checks(style_engine: Dict[str, Any]) -> List[str]:
    gm_algorithm = style_engine.get("scene_generation_algorithm", {}).get("gm", [])
    npc_algorithm = style_engine.get("scene_generation_algorithm", {}).get("npc", [])
    checks = [
        gm_algorithm[3] if len(gm_algorithm) > 3 else None,
        npc_algorithm[5] if len(npc_algorithm) > 5 else None,
        "抽象語を抑え、行動と視線を先に置いた",
    ]
    return [check for check in checks if check]


@dataclass(frozen=True)
class CanonicalAssets:
    style_engine: Dict[str, Any]
    scene_output_schema: Dict[str, Any]
    ui_examples: Dict[str, Any]
    scene_packet_schema: Dict[str, Any]
    shell_snapshot_schema: Dict[str, Any]
    ui_event_schema: Dict[str, Any]
    npc_guide_text: str
    style_checks: List[str]
    motion_cues: List[str]
    micro_leak_terms: List[str]


def _required_path(path: Path, label: str) -> Path:
    try:
        return require_path(path, label)
    except FileNotFoundError as exc:
        raise AssetLoadError(f"Required asset is missing: {label} ({path})") from exc


def load_canonical_assets(canonical_root: Path | None = None, ui_contracts_root: Path | None = None) -> CanonicalAssets:
    canonical_base = canonical_root or CANONICAL_ROOT
    ui_base = ui_contracts_root or UI_CONTRACTS_ROOT
    style_engine = load_json(_required_path(canonical_base / "pbw_style_engine_v1.json", "style engine"))
    scene_output_schema = load_json(_required_path(canonical_base / "pbw_scene_output_schema_v1.json", "scene output schema"))
    ui_examples = load_json(_required_path(ui_base / "pbw_ui_contracts_examples.json", "UI contract examples"))
    scene_packet_schema = load_json(_required_path(ui_base / "ScenePacketV1.schema.json", "ScenePacketV1 schema"))
    shell_snapshot_schema = load_json(_required_path(ui_base / "ShellSnapshotRM.schema.json", "ShellSnapshotRM schema"))
    ui_event_schema = load_json(_required_path(ui_base / "UiEventEnvelope.schema.json", "UiEventEnvelope schema"))
    npc_guide_text = load_text(_required_path(canonical_base / "pbw_npc発話辞書_v_1_0.md", "NPC guide"))
    motion_cues = _extract_bullets(npc_guide_text, "動作の中断")
    micro_leak_terms = _extract_bullets(npc_guide_text, "微漏出に使いやすい語")

    return CanonicalAssets(
        style_engine=style_engine,
        scene_output_schema=scene_output_schema,
        ui_examples=ui_examples,
        scene_packet_schema=scene_packet_schema,
        shell_snapshot_schema=shell_snapshot_schema,
        ui_event_schema=ui_event_schema,
        npc_guide_text=npc_guide_text,
        style_checks=_style_checks(style_engine),
        motion_cues=motion_cues or ["指先がわずかにもたつく", "手を止める", "杯を口元で止める"],
        micro_leak_terms=micro_leak_terms or ["わずかに", "しばらく", "低く"],
    )
