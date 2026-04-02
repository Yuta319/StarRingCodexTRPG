from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from star_ring_codex_trpg.fantasy_naming_generator import USER_NAMING_ROOT
from star_ring_codex_trpg.naming_lexicon_validator import validate_lexicon_collection, validate_lexicon_file


def _resolve_targets(raw_paths: list[str]) -> tuple[list[Path] | None, Path | None]:
    if not raw_paths:
        return None, USER_NAMING_ROOT
    paths = [Path(value).resolve() for value in raw_paths]
    if len(paths) == 1 and paths[0].is_dir():
        return None, paths[0]
    return paths, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate external naming lexicons before importing them.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="辞典ファイルか、辞典フォルダを指定します。省略時は .sources/user_shared/naming を見ます。",
    )
    parser.add_argument("--json-out", help="検証結果を JSON で保存します。")
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="warning が1件でもあれば終了コードを 1 にします。",
    )
    args = parser.parse_args()

    explicit_paths, root = _resolve_targets(args.paths)
    if explicit_paths is not None:
        payload = {
            "root": "",
            "file_count": len(explicit_paths),
            "reports": [validate_lexicon_file(path).to_dict() for path in explicit_paths],
        }
        payload["error_count"] = sum(len(report["errors"]) for report in payload["reports"])
        payload["warning_count"] = sum(len(report["warnings"]) for report in payload["reports"])
        payload["ok"] = payload["error_count"] == 0
    else:
        payload = validate_lexicon_collection(root=root)

    if args.json_out:
        output_path = Path(args.json_out).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"checked files: {payload['file_count']}")
    print(f"errors: {payload['error_count']}")
    print(f"warnings: {payload['warning_count']}")
    for report in payload["reports"]:
        status = "OK" if not report["errors"] else "ERROR"
        print(f"- {status} {report['path']}")
        for issue in report["errors"]:
            index_text = f" entry[{issue['entry_index']}]" if issue["entry_index"] is not None else ""
            print(f"  [error] {issue['code']}{index_text}: {issue['message']}")
        for issue in report["warnings"]:
            index_text = f" entry[{issue['entry_index']}]" if issue["entry_index"] is not None else ""
            print(f"  [warn]  {issue['code']}{index_text}: {issue['message']}")

    if payload["error_count"] > 0:
        return 1
    if args.fail_on_warnings and payload["warning_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
