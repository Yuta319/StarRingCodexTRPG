from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.fantasy_naming_generator import USER_NAMING_ROOT
from star_ring_codex_trpg.naming_lexicon_compiler import compile_external_lexicons


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile external naming lexicons into one normalized JSON.")
    parser.add_argument(
        "--root",
        default=str(USER_NAMING_ROOT),
        help="外部辞典を読むフォルダ。省略時は .sources/user_shared/naming",
    )
    parser.add_argument(
        "--out",
        default="generated/naming/compiled/external_lexicon_compiled.json",
        help="出力先 JSON",
    )
    parser.add_argument(
        "--allow-errors",
        action="store_true",
        help="validation error があっても可能な範囲で compile を続行します。",
    )
    args = parser.parse_args()

    payload = compile_external_lexicons(
        root=Path(args.root).resolve(),
        fail_on_errors=not args.allow_errors,
    )

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload["validation_summary"]
    print(f"compiled entries: {payload['entry_count']}")
    print(f"duplicate resolutions: {payload['duplicate_resolution_count']}")
    print(f"errors: {summary['error_count']}")
    print(f"warnings: {summary['warning_count']}")
    print(f"output: {out_path}")

    if summary["error_count"] > 0 and not args.allow_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
