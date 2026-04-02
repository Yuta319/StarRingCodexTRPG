from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.canonical_naming_sources import export_canonical_naming_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Export canonical source terms for external naming dictionaries.")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--seasons", type=int, default=10)
    parser.add_argument("--archetype", default="balanced")
    parser.add_argument(
        "--out",
        default="generated/naming/source_terms/canonical_sources_seed1729.json",
        help="出力先 JSON",
    )
    args = parser.parse_args()

    payload = export_canonical_naming_sources(
        seed=args.seed,
        seasons=args.seasons,
        archetype=args.archetype,
    )
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exported groups: {', '.join(payload['groups'].keys())}")
    print(f"output: {out_path}")


if __name__ == "__main__":
    main()
