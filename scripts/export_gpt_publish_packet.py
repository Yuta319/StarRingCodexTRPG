from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.custom_gpt_bundle_support import export_custom_gpt_publish_packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a self-contained publish packet for GPT editor registration")
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
        help="Optional explicit output directory for the publish packet",
    )
    parser.add_argument("--seed", type=int, default=1729, help="Seed used for live smoke validation")
    parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout per request")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for transient HTTP failures")
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=1.0,
        help="Delay between transient-failure retries",
    )
    parser.add_argument(
        "--skip-live-smoke",
        action="store_true",
        help="Skip live smoke and only export local packet files",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also create a zip archive next to the publish packet directory",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    packet = export_custom_gpt_publish_packet(
        args.bundle_root,
        output_dir=args.output_dir,
        seed=args.seed,
        timeout_seconds=args.timeout_seconds,
        smoke_retries=args.retries,
        smoke_retry_delay_seconds=args.retry_delay_seconds,
        include_live_smoke=not args.skip_live_smoke,
        create_zip=args.zip,
    )
    print(json.dumps(packet.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
