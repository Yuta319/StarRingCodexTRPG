from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.fantasy_naming_generator import generate_batch, generate_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate names from Fantasy_Naming_System_Core.")
    parser.add_argument("--race", required=True, help="Race id such as human, elf, dwarf")
    parser.add_argument("--category", required=True, choices=["city", "place", "person", "item", "equipment"])
    parser.add_argument("--count", type=int, default=1, help="Number of names to generate")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--item-type", default="", help="Optional item type such as bow, warhammer, grimoire")
    parser.add_argument("--semantic-tag", action="append", default=[], help="Optional semantic tag. Repeatable.")
    parser.add_argument("--annotation", default="", help="Optional explicit annotation override")
    parser.add_argument("--out", default="", help="Optional JSON output path")
    parser.add_argument("--no-external", action="store_true", help="Ignore external lexicon entries and use procedural generation only.")
    args = parser.parse_args()

    semantic_tags = [tag for tag in args.semantic_tag if str(tag or "").strip()]
    annotation = args.annotation.strip() or None
    item_type = args.item_type.strip() or None

    if args.count == 1:
        result = generate_name(
            race=args.race,
            category=args.category,
            seed=args.seed,
            semantic_tags=semantic_tags or None,
            annotation=annotation,
            item_type=item_type,
            prefer_external=not args.no_external,
        )
        payload = {
            "surface_name": result.surface_name,
            "category": result.category,
            "race": result.race,
            "source_label": result.source_label,
            "semantic_tags": result.semantic_tags,
            "annotation": result.annotation,
            "full_display": result.full_display,
            "phoneme": result.phoneme,
            "suffix": result.suffix,
            "item_type": item_type,
            "origin": result.origin,
            "source_file": result.source_file,
        }
    else:
        payload = {
            "race": args.race,
            "category": args.category,
            "count": args.count,
            "seed": args.seed,
            "item_type": item_type,
            "semantic_tags": semantic_tags,
            "entries": generate_batch(
                race=args.race,
                category=args.category,
                count=args.count,
                seed=args.seed,
                semantic_tags=semantic_tags or None,
                annotation=annotation,
                item_type=item_type,
                prefer_external=not args.no_external,
            ),
        }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
