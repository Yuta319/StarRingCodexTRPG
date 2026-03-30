from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.release_support import cleanup_runtime_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cleanup old runtime save and UI session files")
    parser.add_argument("--keep-saves", type=int, default=40, help="How many recent session saves to keep")
    parser.add_argument("--keep-ui-sessions", type=int, default=120, help="How many recent UI session worlds to keep")
    parser.add_argument("--apply", action="store_true", help="Actually delete old files. Default is dry-run")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = cleanup_runtime_artifacts(
        keep_recent_saves=args.keep_saves,
        keep_recent_ui_sessions=args.keep_ui_sessions,
        dry_run=not args.apply,
    )
    print(
        json.dumps(
            {
                "dryRun": not args.apply,
                "removedSaves": report.removed_saves,
                "removedUiSessions": report.removed_ui_sessions,
                "keptSaves": report.kept_saves,
                "keptUiSessions": report.kept_ui_sessions,
                "removedPaths": list(report.removed_paths),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
