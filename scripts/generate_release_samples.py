from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.release_support import build_release_samples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate release sample files for StarRingCodexTRPG")
    parser.add_argument("--output-root", type=Path, default=Path("samples"), help="Output directory for sample files")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest = build_release_samples(args.output_root)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
