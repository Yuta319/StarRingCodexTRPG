from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .errors import StarRingCodexError
from .playable_loop import play_choice


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="StarRingCodexTRPG minimal playable loop")
    parser.add_argument("--choice-id", required=True, help="Choice id to resolve")
    parser.add_argument("--seed", type=int, default=1729, help="Seed for world generation")
    parser.add_argument("--seasons", type=int, default=10, help="Season count for v9 world generation")
    parser.add_argument("--archetype", default="balanced", help="World archetype for v9 world generation")
    parser.add_argument("--world-json", type=Path, help="Existing world state JSON path")
    parser.add_argument("--output", type=Path, help="Output JSON path. If omitted, JSON is printed to stdout.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    argv = argv or sys.argv[1:]
    if args.world_json is not None and "--seed" in argv:
        parser.error("--seed and --world-json cannot be used together")
    try:
        result = play_choice(
            choice_id=args.choice_id,
            seed=None if args.world_json else args.seed,
            seasons=args.seasons,
            archetype=args.archetype,
            world_json=args.world_json,
        )
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload)
    except StarRingCodexError as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
