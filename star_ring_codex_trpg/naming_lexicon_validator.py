from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

from .fantasy_naming_generator import NAMING_CORE_PATH, USER_NAMING_ROOT, load_naming_core, normalize_category


VALID_CATEGORIES = {"city", "place", "person", "item"}
ASCII_NAME_PATTERN = re.compile(r"[A-Za-z]{3,}")
SPACEY_ASCII_PATTERN = re.compile(r"[A-Za-z][A-Za-z\s'-]+[A-Za-z]")


@dataclass(frozen=True)
class LexiconIssue:
    level: str
    code: str
    entry_index: int | None
    message: str


@dataclass(frozen=True)
class LexiconFileReport:
    path: str
    schema_name: str
    entry_count: int
    errors: list[LexiconIssue]
    warnings: list[LexiconIssue]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "schema_name": self.schema_name,
            "entry_count": self.entry_count,
            "ok": self.ok,
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
        }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_entries_lexicon_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("entries"), list)


def _payload_has_non_ui_only_entries(payload: Any) -> bool:
    if not _is_entries_lexicon_payload(payload):
        return False
    for raw in payload.get("entries", []):
        if not isinstance(raw, dict):
            continue
        if not bool(raw.get("ui_only")):
            return True
    return False


def _has_repeated_chunk(text: str) -> bool:
    source = str(text or "")
    for size in range(2, min(5, (len(source) // 2) + 1)):
        seen: set[str] = set()
        for index in range(0, len(source) - size + 1):
            chunk = source[index : index + size]
            if chunk in seen:
                return True
            seen.add(chunk)
    return False


def _make_issue(level: str, code: str, message: str, entry_index: int | None = None) -> LexiconIssue:
    return LexiconIssue(level=level, code=code, entry_index=entry_index, message=message)


def _normalize_string(value: Any) -> str:
    return str(value or "").strip()


def _validate_entry(
    raw: Any,
    *,
    index: int,
    known_races: set[str],
    duplicate_keys: set[tuple[str, str, str, str]],
    seen_surface_names: dict[tuple[str, str], set[str]],
) -> tuple[list[LexiconIssue], list[LexiconIssue]]:
    errors: list[LexiconIssue] = []
    warnings: list[LexiconIssue] = []
    if not isinstance(raw, dict):
        errors.append(_make_issue("error", "entry-not-object", "entry は object である必要があります。", index))
        return errors, warnings

    surface_name = _normalize_string(raw.get("surface_name") or raw.get("name"))
    category = normalize_category(raw.get("category"))
    race = _normalize_string(raw.get("race")).lower()
    item_type = _normalize_string(raw.get("item_type") or raw.get("type")).lower()
    annotation = _normalize_string(raw.get("annotation"))
    semantic_tags_raw = raw.get("semantic_tags", [])
    source_terms_raw = raw.get("source_terms")
    if source_terms_raw is None:
        source_terms_raw = raw.get("canonical_terms", [])

    if not surface_name:
        errors.append(_make_issue("error", "missing-surface-name", "surface_name は必須です。", index))
    if category not in VALID_CATEGORIES:
        errors.append(
            _make_issue(
                "error",
                "invalid-category",
                "category は city / place / person / item のいずれかである必要があります。equipment は item として扱われます。",
                index,
            )
        )

    if semantic_tags_raw is not None and not isinstance(semantic_tags_raw, list):
        errors.append(_make_issue("error", "invalid-semantic-tags", "semantic_tags は配列である必要があります。", index))
        semantic_tags: list[str] = []
    else:
        semantic_tags = [_normalize_string(tag) for tag in semantic_tags_raw if _normalize_string(tag)]

    if source_terms_raw is not None and not isinstance(source_terms_raw, list):
        errors.append(_make_issue("error", "invalid-source-terms", "source_terms は配列である必要があります。", index))
    else:
        source_terms = [_normalize_string(term) for term in source_terms_raw if _normalize_string(term)]

    if race and race not in known_races:
        warnings.append(
            _make_issue(
                "warning",
                "unknown-race",
                f"race '{race}' は core 辞典に未登録です。将来拡張なら問題ありませんが、現在の生成器では優先一致しません。",
                index,
            )
        )

    if not annotation:
        warnings.append(
            _make_issue(
                "warning",
                "missing-annotation",
                "annotation がありません。詳細表示で補助説明が弱くなります。",
                index,
            )
        )
    elif not (annotation.startswith("《") and annotation.endswith("》")):
        warnings.append(
            _make_issue(
                "warning",
                "annotation-format",
                "annotation は 《...》 形式を推奨します。",
                index,
            )
        )

    if not semantic_tags:
        warnings.append(
            _make_issue(
                "warning",
                "missing-semantic-tags",
                "semantic_tags がありません。意味連携や注釈生成の手がかりが弱くなります。",
                index,
            )
        )

    if category in VALID_CATEGORIES and not source_terms:
        warnings.append(
            _make_issue(
                "warning",
                "missing-source-terms",
                "source_terms がありません。既存 canonical 名から UI 表示名へ差し替える場合は指定してください。",
                index,
            )
        )

    if category == "item" and not item_type:
        warnings.append(
            _make_issue(
                "warning",
                "missing-item-type",
                "item category では item_type があると一致精度が上がります。",
                index,
            )
        )
    if category != "item" and item_type:
        warnings.append(
            _make_issue(
                "warning",
                "unused-item-type",
                "item_type は item category 以外では使われません。",
                index,
            )
        )

    if surface_name:
        if "《" in surface_name or "》" in surface_name:
            warnings.append(
                _make_issue(
                    "warning",
                    "inline-annotation",
                    "surface_name に注釈を含めず、annotation に分離してください。",
                    index,
                )
            )
        if ASCII_NAME_PATTERN.search(surface_name):
            warnings.append(
                _make_issue(
                    "warning",
                    "raw-ascii-name",
                    "surface_name に英字が含まれています。主表示は日本語 UI で意味が通る形を優先してください。",
                    index,
                )
            )
        if SPACEY_ASCII_PATTERN.fullmatch(surface_name):
            warnings.append(
                _make_issue(
                    "warning",
                    "raw-english-name",
                    "surface_name が英語そのままに見えます。UI 主表示には不向きです。",
                    index,
                )
            )
        if len(surface_name) > 14:
            warnings.append(
                _make_issue(
                    "warning",
                    "long-surface-name",
                    "surface_name がやや長いです。UI では省略や折り返しが増える可能性があります。",
                    index,
                )
            )
        if _has_repeated_chunk(surface_name):
            warnings.append(
                _make_issue(
                    "warning",
                    "repeated-chunk",
                    "surface_name に同じ塊の繰り返しがあり、語感が不自然に見える可能性があります。",
                    index,
                )
            )

        dedupe_key = (surface_name, category, race, item_type)
        if dedupe_key in duplicate_keys:
            errors.append(
                _make_issue(
                    "error",
                    "duplicate-entry",
                    "同一の surface_name/category/race/item_type の組み合わせが重複しています。",
                    index,
                )
            )
        else:
            duplicate_keys.add(dedupe_key)

        scope_key = (surface_name, category)
        prior_races = seen_surface_names.setdefault(scope_key, set())
        if prior_races and race not in prior_races:
            warnings.append(
                _make_issue(
                    "warning",
                    "surface-name-collision",
                    "同じ surface_name が同一 category 内の別 race でも使われています。意図した共有名か確認してください。",
                    index,
                )
            )
        prior_races.add(race or "*")

    return errors, warnings


def validate_lexicon_file(path: Path, *, core_path: Path | None = None) -> LexiconFileReport:
    known_races = set(load_naming_core(core_path or NAMING_CORE_PATH)["races"].keys())
    errors: list[LexiconIssue] = []
    warnings: list[LexiconIssue] = []
    schema_name = path.stem
    entry_count = 0

    try:
        payload = _load_json(path)
    except json.JSONDecodeError as exc:
        errors.append(_make_issue("error", "invalid-json", f"JSON の読み込みに失敗しました: {exc.msg}"))
        return LexiconFileReport(
            path=str(path),
            schema_name=schema_name,
            entry_count=0,
            errors=errors,
            warnings=warnings,
        )

    if not isinstance(payload, dict):
        errors.append(_make_issue("error", "invalid-root", "辞典ファイルの top-level は object である必要があります。"))
        return LexiconFileReport(
            path=str(path),
            schema_name=schema_name,
            entry_count=0,
            errors=errors,
            warnings=warnings,
        )

    schema_name = _normalize_string(payload.get("name")) or path.stem
    entries = payload.get("entries")
    if not isinstance(entries, list):
        errors.append(_make_issue("error", "missing-entries", "entries 配列が必要です。"))
        return LexiconFileReport(
            path=str(path),
            schema_name=schema_name,
            entry_count=0,
            errors=errors,
            warnings=warnings,
        )

    duplicate_keys: set[tuple[str, str, str, str]] = set()
    seen_surface_names: dict[tuple[str, str], set[str]] = {}
    for index, raw in enumerate(entries):
        entry_errors, entry_warnings = _validate_entry(
            raw,
            index=index,
            known_races=known_races,
            duplicate_keys=duplicate_keys,
            seen_surface_names=seen_surface_names,
        )
        errors.extend(entry_errors)
        warnings.extend(entry_warnings)

    entry_count = len(entries)
    if not payload.get("schema_version"):
        warnings.append(_make_issue("warning", "missing-schema-version", "schema_version がありません。"))

    return LexiconFileReport(
        path=str(path),
        schema_name=schema_name,
        entry_count=entry_count,
        errors=errors,
        warnings=warnings,
    )


def iter_external_lexicon_paths(root: Path | None = None) -> list[Path]:
    target_root = root or USER_NAMING_ROOT
    if not target_root.exists():
        return []
    paths: list[Path] = []
    for path in sorted(target_root.glob("*.json")):
        if path.name == NAMING_CORE_PATH.name:
            continue
        if path.name.endswith(".template.json"):
            continue
        try:
            payload = _load_json(path)
        except json.JSONDecodeError:
            continue
        if _payload_has_non_ui_only_entries(payload):
            paths.append(path)
    return paths


def validate_lexicon_collection(paths: list[Path] | None = None, *, root: Path | None = None) -> dict[str, Any]:
    target_paths = paths if paths is not None else iter_external_lexicon_paths(root)
    reports = [validate_lexicon_file(path) for path in target_paths]
    error_count = sum(len(report.errors) for report in reports)
    warning_count = sum(len(report.warnings) for report in reports)
    return {
        "root": str(root or USER_NAMING_ROOT),
        "file_count": len(reports),
        "error_count": error_count,
        "warning_count": warning_count,
        "ok": error_count == 0,
        "reports": [report.to_dict() for report in reports],
    }
