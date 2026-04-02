from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.naming_dictionary_importer import import_naming_dictionary


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a naming dictionary into .sources/user_shared/naming.")
    parser.add_argument("source", help="読み込む JSON ファイル")
    args = parser.parse_args()

    result = import_naming_dictionary(Path(args.source))
    print(f"role: {result['role']}")
    print(f"source: {result['source_path']}")
    print(f"destination: {result['destination_path']}")


if __name__ == "__main__":
    main()
