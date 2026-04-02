from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_bundle_support import export_custom_gpt_editor_field_fragments


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export per-field GPT editor text fragments")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path(".tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1"),
        help="Path to the Custom GPT bundle root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional explicit output directory for field fragments",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = export_custom_gpt_editor_field_fragments(args.bundle_root, output_dir=args.output_dir)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
