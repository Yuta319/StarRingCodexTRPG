from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.naming_dictionary_importer import import_naming_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a naming bundle index and its referenced dictionaries.")
    parser.add_argument("index_path", help="bundle index JSON path")
    args = parser.parse_args()

    payload = import_naming_bundle(Path(args.index_path))
    print(f"bundle: {payload['bundle_name']}")
    print(f"imported: {payload['imported_count']}")
    for result in payload["results"]:
        print(f"- {result['role']}: {result['destination_path']}")


if __name__ == "__main__":
    main()
