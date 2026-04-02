from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.naming_lexicon_scaffolder import generate_initial_ui_naming_lexicon


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the first-pass active UI naming lexicon.")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--seasons", type=int, default=10)
    parser.add_argument("--archetype", default="balanced")
    parser.add_argument(
        "--out",
        default=".sources/user_shared/naming/canonical_ui_naming_lexicon.json",
        help="出力先 JSON",
    )
    args = parser.parse_args()

    payload = generate_initial_ui_naming_lexicon(
        seed=args.seed,
        seasons=args.seasons,
        archetype=args.archetype,
    )
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"entries: {payload['entry_count']}")
    print(f"output: {out_path}")


if __name__ == "__main__":
    main()
