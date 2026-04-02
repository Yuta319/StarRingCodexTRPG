from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_bundle_support import (
    build_custom_gpt_publish_workspace,
    prepare_custom_gpt_publish_release,
)

FIELD_FRAGMENT_KEYS = {
    "name": "name.txt",
    "description": "description.txt",
    "instructions": "instructions.txt",
    "conversation_starters": "conversation_starters.txt",
    "builder_website": "builder_website.txt",
    "privacy_policy_url": "privacy_policy_url.txt",
    "actions_import_path": "actions_import_path.txt",
    "actions_server_url": "actions_server_url.txt",
}


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
    parser.add_argument("--retries", type=int, default=2, help="Retry count for transient HTTP failures when preparing")
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=1.0,
        help="Delay between transient-failure retries when preparing",
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
    parser.add_argument(
        "--copy",
        choices=sorted(FIELD_FRAGMENT_KEYS.keys()),
        default=None,
        help="Copy one editor field fragment directly to the clipboard",
    )
    parser.add_argument(
        "--show-field",
        choices=sorted(FIELD_FRAGMENT_KEYS.keys()),
        default=None,
        help="Print one editor field fragment to stdout",
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


def _field_fragment_path(workspace: dict, key: str) -> Path:
    return Path(workspace["field_fragments_dir"]) / FIELD_FRAGMENT_KEYS[key]


def _read_field_fragment(workspace: dict, key: str) -> str:
    path = _field_fragment_path(workspace, key)
    if not path.exists():
        raise FileNotFoundError(f"field fragment is missing: {path}")
    return path.read_text(encoding="utf-8")


def _copy_to_clipboard(text: str) -> None:
    try:
        subprocess.run(["clip"], input=text, text=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("clipboard utility 'clip' was not found on this system") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("failed to copy text to the clipboard") from exc


def main() -> None:
    args = build_parser().parse_args()
    if args.prepare:
        prepare_custom_gpt_publish_release(
            args.bundle_root,
            output_dir=args.packet_dir,
            smoke_retries=args.retries,
            smoke_retry_delay_seconds=args.retry_delay_seconds,
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

    if args.show_field:
        print("\n--- field fragment ---")
        print(_read_field_fragment(workspace.local_paths, args.show_field).rstrip())

    if args.copy:
        text = _read_field_fragment(workspace.local_paths, args.copy)
        _copy_to_clipboard(text)
        print(f"\nCopied field fragment: {args.copy}")

    if args.open:
        for key in ("dashboard", "handoff", "field_fragments_dir", "preview_scorecard"):
            _open_target(workspace.local_paths[key])
        for key in (
            "gpt_editor_url",
            "gpt_create_help_url",
            "gpt_publish_help_url",
            "gpt_actions_help_url",
            "builder_website",
            "privacy_policy_url",
        ):
            _open_target(workspace.urls[key])


if __name__ == "__main__":
    main()
