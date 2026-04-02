from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.fantasy_naming_generator import generate_plan_batches


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate multiple naming batches from a plan JSON.")
    parser.add_argument("--plan", required=True, help="Path to batch plan JSON")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    parser.add_argument("--no-external", action="store_true", help="Ignore external lexicon entries and use procedural generation only.")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    plan = _load_json(plan_path)
    payload = generate_plan_batches(plan, prefer_external=not args.no_external)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
