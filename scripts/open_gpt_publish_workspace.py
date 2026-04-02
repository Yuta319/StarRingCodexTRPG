from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import sys
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_bundle_support import (
    build_custom_gpt_publish_workspace,
    prepare_custom_gpt_publish_release,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print or open the local files and live URLs needed for GPT editor registration"
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path(".tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1"),
        help="Path to the Custom GPT bundle root",
    )
    parser.add_argument(
        "--packet-dir",
        type=Path,
        default=None,
        help="Optional explicit publish packet directory",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Rebuild the publish packet before opening the workspace",
    )
    parser.add_argument(
        "--skip-live-smoke",
        action="store_true",
        help="Skip live smoke when used together with --prepare",
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Do not create a zip archive when used together with --prepare",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the key local files and live URLs after printing the workspace manifest",
    )
    return parser


def _open_target(target: str) -> None:
    path = Path(target)
    if path.exists():
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return
        except AttributeError:
            webbrowser.open(path.resolve().as_uri())
            return
    webbrowser.open(target)


def main() -> None:
    args = build_parser().parse_args()
    if args.prepare:
        prepare_custom_gpt_publish_release(
            args.bundle_root,
            output_dir=args.packet_dir,
            include_live_smoke=not args.skip_live_smoke,
            create_zip=not args.no_zip,
        )

    workspace = build_custom_gpt_publish_workspace(args.bundle_root, packet_dir=args.packet_dir)
    print(json.dumps(workspace.to_dict(), ensure_ascii=False, indent=2))
    if workspace.missing:
        print(
            "\nMissing local paths detected. Run `py -3 scripts\\prepare_gpt_publish_release.py` first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if args.open:
        for key in ("dashboard", "handoff", "field_fragments_dir", "preview_scorecard"):
            _open_target(workspace.local_paths[key])
        for key in ("builder_website", "privacy_policy_url"):
            _open_target(workspace.urls[key])


if __name__ == "__main__":
    main()
