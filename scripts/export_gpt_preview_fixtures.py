from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_preview_fixtures import export_custom_gpt_preview_fixtures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export local sample fixtures for GPT editor preview comparison")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path(".tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1"),
        help="Path to the Custom GPT bundle root",
    )
    parser.add_argument("--seed", type=int, default=1729, help="Seed used to build local preview fixtures")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional explicit output directory for preview fixtures",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    fixtures = export_custom_gpt_preview_fixtures(
        args.bundle_root,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    print(json.dumps(fixtures.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
