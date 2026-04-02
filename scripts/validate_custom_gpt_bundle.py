from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_bundle_support import validate_custom_gpt_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the bundled Custom GPT editor input pack and OpenAPI contract")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path(".tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1"),
        help="Path to the Custom GPT bundle root",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = validate_custom_gpt_bundle(args.bundle_root)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if not report.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
