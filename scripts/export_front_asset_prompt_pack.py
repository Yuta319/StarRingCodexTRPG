from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.read_only_ui.controller import build_front_snapshot_payload, viewer_request_from_query


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export front asset prompt pack for equipment and item icon generation")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--seasons", type=int, default=10)
    parser.add_argument("--archetype", default="balanced")
    parser.add_argument("--world-json", dest="world_json", default=None)
    parser.add_argument("--output", default="generated/asset_prompt_packs/front_asset_prompts_seed1729.json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    query = {
        "seasons": [str(args.seasons)],
        "archetype": [args.archetype],
    }
    if args.world_json:
        query["world_json"] = [str(args.world_json)]
    else:
        query["seed"] = [str(args.seed)]
    payload = build_front_snapshot_payload(viewer_request_from_query(query))
    prompt_pack = payload["display"]["assetPromptPack"]
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(prompt_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(target))


if __name__ == "__main__":
    main()
