from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "output" / "imagegen" / "icons-final"
DEFAULT_TARGET = PROJECT_ROOT / "chrome_extension" / "assets" / "icons"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync generated icon PNGs into the Chrome extension asset folder.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--target", default=str(DEFAULT_TARGET))
    parser.add_argument("--max-dim", type=int, default=384)
    return parser


def resize_png(source: Path, target: Path, max_dim: int) -> None:
    with Image.open(source) as image:
        image = image.convert("RGBA")
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="PNG", optimize=True)


def main() -> None:
    args = build_parser().parse_args()
    source = Path(args.source)
    target = Path(args.target)
    if not source.exists():
        raise SystemExit(f"Source folder not found: {source}")

    count = 0
    for path in sorted(source.glob("*.png")):
        resize_png(path, target / path.name, args.max_dim)
        count += 1
    print(f"synced={count}")
    print(str(target))


if __name__ == "__main__":
    main()
