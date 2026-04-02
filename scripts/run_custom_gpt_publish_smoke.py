from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_publish_smoke import run_custom_gpt_publish_smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run live smoke checks for the published Custom GPT support surfaces")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path(".tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1"),
        help="Path to the Custom GPT bundle root",
    )
    parser.add_argument("--seed", type=int, default=1729, help="Seed used for snapshot/read-model smoke checks")
    parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout per request")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for transient HTTP failures")
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=1.0,
        help="Delay between transient-failure retries",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_custom_gpt_publish_smoke(
        args.bundle_root,
        seed=args.seed,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        retry_delay_seconds=args.retry_delay_seconds,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if not report.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
