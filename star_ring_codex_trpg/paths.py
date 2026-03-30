from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_ROOT = PROJECT_ROOT / ".sources"
CANONICAL_ROOT = SOURCES_ROOT / "handoff" / "PBW_Codex_Handoff_Pack_v1"
REFERENCE_ROOT = SOURCES_ROOT / "reference" / "StarRingCodexRPG"
USER_SHARED_ROOT = SOURCES_ROOT / "user_shared" / "free_action"
UI_CONTRACTS_ROOT = CANONICAL_ROOT / "pbw_ui_contracts_v1"
RUNTIME_ROOT = PROJECT_ROOT / ".runtime"
GENERATED_ROOT = PROJECT_ROOT / "generated"


def require_path(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path
