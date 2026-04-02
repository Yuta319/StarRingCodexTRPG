from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_bundle_support import build_custom_gpt_editor_paste_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a paste-ready GPT editor pack with expanded Instructions and starters")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path(".tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1"),
        help="Path to the Custom GPT bundle root",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional explicit output path for the paste-ready markdown",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    pack = build_custom_gpt_editor_paste_pack(args.bundle_root, output_path=args.output_path)
    print(json.dumps(pack.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
