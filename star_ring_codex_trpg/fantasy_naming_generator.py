from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import random
from pathlib import Path
from typing import Any, Iterable

from .paths import PROJECT_ROOT


USER_NAMING_ROOT = PROJECT_ROOT / ".sources" / "user_shared" / "naming"
NAMING_CORE_PATH = USER_NAMING_ROOT / "Fantasy_Naming_System_Core.json"
CITY_DICTIONARY_PATH = USER_NAMING_ROOT / "fantasy_city_naming_dictionary.json"
PERSON_DICTIONARY_PATH = USER_NAMING_ROOT / "fantasy_personal_name_dictionary.json"
EQUIPMENT_DICTIONARY_PATH = USER_NAMING_ROOT / "fantasy_equipment_naming_dictionary.json"
MAX_NAME_SEARCH_ATTEMPTS = 64
CATEGORY_ALIASES = {
    "equipment": "item",
}
VALID_GENERATION_CATEGORIES = {"city", "place", "person", "item"}


KANA_OVERRIDES = {
    "al": "アル",
    "val": "ヴァル",
    "bel": "ベル",
    "ber": "ベル",
    "ed": "エド",
    "leon": "レオン",
    "ser": "セル",
    "kil": "キル",
    "ard": "アルド",
    "ion": "イオン",
    "a": "ア",
    "an": "アン",
    "as": "アス",
    "wick": "ウィック",
    "abbey": "アビー",
    "bloom": "ブルーム",
    "bri": "ブライ",
    "field": "フィールド",
    "gard": "ガルド",
    "ford": "フォード",
    "bridge": "ブリッジ",
    "crest": "クレスト",
    "core": "コア",
    "dan": "ダン",
    "keep": "キープ",
    "wall": "ウォール",
    "vale": "ヴェイル",
    "mere": "ミア",
    "gate": "ゲート",
    "hall": "ホール",
    "hearth": "ハース",
    "minster": "ミンスター",
    "chapel": "チャペル",
    "ric": "リク",
    "trion": "トリオン",
    "vein": "ヴェイン",
    "ele": "エレ",
    "lira": "リラ",
    "syl": "シル",
    "lune": "ルナ",
    "riel": "リエル",
    "thiel": "ティエル",
    "sera": "セラ",
    "cael": "ケイル",
    "fiara": "フィアラ",
    "forge": "フォージ",
    "fang": "ファング",
    "grove": "グローヴ",
    "wein": "ウェイン",
    "loria": "ロリア",
    "sia": "シア",
    "wen": "ウェン",
    "ena": "エナ",
    "elle": "エル",
    "is": "イス",
    "fel": "フェル",
    "seris": "セリス",
    "kar": "カル",
    "dor": "ドル",
    "grim": "グリム",
    "bar": "バル",
    "hald": "ハルド",
    "del": "デル",
    "rok": "ロク",
    "drum": "ドラム",
    "dorn": "ドルン",
    "hold": "ホールド",
    "dol": "ドル",
    "rik": "リク",
    "ka": "カ",
    "gram": "グラム",
    "brok": "ブロク",
    "ras": "ラス",
    "fen": "フェン",
    "rask": "ラスク",
    "skar": "スカル",
    "gar": "ガル",
    "mok": "モク",
    "ul": "ウル",
    "camp": "キャンプ",
    "watch": "ウォッチ",
    "scar": "スカー",
    "fire": "ファイア",
    "den": "デン",
    "gal": "ガル",
    "knar": "クナー",
    "ska": "スカ",
    "run": "ルン",
    "zal": "ザル",
    "ga": "ガ",
    "ok": "オク",
    "ae": "アエ",
    "ael": "アエル",
    "zeph": "ゼフ",
    "tia": "ティア",
    "tiar": "ティア",
    "orin": "オリン",
    "cae": "カエ",
    "nest": "ネスト",
    "perch": "パーチ",
    "spire": "スパイア",
    "aeria": "エアリア",
    "aris": "アリス",
    "choir": "クワイア",
    "ris": "リス",
    "iel": "イエル",
    "aron": "アロン",
    "siel": "シエル",
    "nere": "ネレ",
    "kai": "カイ",
    "moa": "モア",
    "rua": "ルア",
    "tala": "タラ",
    "nalu": "ナル",
    "cove": "コーヴ",
    "reef": "リーフ",
    "lua": "ルア",
    "mora": "モラ",
    "nui": "ヌイ",
    "shoal": "ショール",
    "tide": "タイド",
    "isle": "アイル",
    "loa": "ロア",
    "nari": "ナリ",
    "roa": "ロア",
    "mar": "マル",
    "azh": "アズ",
    "zhar": "ザール",
    "rak": "ラク",
    "vash": "ヴァシュ",
    "kesh": "ケシュ",
    "azar": "アザル",
    "ur": "ウル",
    "zaal": "ザール",
    "uram": "ウラム",
    "kaan": "カーン",
    "zar": "ザル",
    "tem": "テム",
    "thron": "スロン",
    "esh": "エシュ",
    "var": "ヴァル",
    "mi": "ミ",
    "mir": "ミル",
    "eira": "エイラ",
    "fia": "フィア",
    "vela": "ヴェラ",
    "glen": "グレン",
    "reine": "レイン",
    "miel": "ミエル",
    "court": "コート",
    "moon": "ムーン",
    "ene": "エネ",
    "zev": "ゼヴ",
    "vex": "ヴェクス",
    "zel": "ゼル",
    "zeth": "ゼス",
    "keth": "ケス",
    "mor": "モル",
    "nox": "ノクス",
    "cell": "セル",
    "lock": "ロック",
    "seal": "シール",
    "archive": "アーカイブ",
    "xil": "シル",
    "et": "エト",
    "ket": "ケット",
    "ash": "アッシュ",
    "vael": "ヴェイル",
    "kain": "カイン",
    "mour": "ムール",
    "sel": "セル",
    "rest": "レスト",
    "gray": "グレイ",
    "basil": "バジル",
    "sanct": "サンクト",
    "sol": "ソル",
    "vel": "ヴェル",
    "vain": "ヴェイン",
    "veil": "ヴェイル",
    "ro": "ロ",
    "ver": "ヴェル",
    "rowe": "ロウ",
    "briar": "ブライア",
    "thorn": "ソーン",
    "lora": "ローラ",
    "wyn": "ウィン",
    "patch": "パッチ",
    "hedge": "ヘッジ",
    "vera": "ヴェラ",
    "ria": "リア",
    "verna": "ヴェルナ",
    "garden": "ガーデン",
    "spring": "スプリング",
    "ori": "オリ",
    "orix": "オリクス",
    "lex": "レクス",
    "sarn": "サルン",
    "dri": "ドリ",
    "on": "オン",
    "or": "オル",
    "orn": "オルン",
    "pit": "ピット",
    "peak": "ピーク",
    "ledge": "レッジ",
    "drium": "ドリウム",
    "cor": "コル",
    "vol": "ヴォル",
    "im": "イム",
    "ar": "アル",
    "dim": "ディム",
    "kaar": "カール",
    "lance": "ランス",
    "lexar": "レクサル",
    "maze": "メイズ",
    "root": "ルート",
    "song": "ソング",
    "vault": "ヴォルト",
    "ward": "ウォード",
    "zet": "ゼット",
    "zor": "ゾル",
    "selene": "セレネ",
}


TAG_TO_CITY_NOUN = {
    "王権": "城塞",
    "誓約": "誓壁",
    "紋章": "紋章街",
    "騎士": "城門",
    "月": "湖都",
    "水": "水都",
    "森": "森都",
    "循環": "環都",
    "炉": "鍛都",
    "鍛造": "炉都",
    "石": "坑道門",
    "誓印": "誓印門",
    "狩猟": "狩場町",
    "群れ": "群都",
    "牙": "牙砦",
    "追跡": "追風砦",
    "風": "風見塔",
    "空": "空都",
    "祈り": "祈塔都市",
    "伝令": "飛脚門",
    "潮": "港",
    "航路": "波路港",
    "海": "海都",
    "記憶歌": "歌港",
    "火": "炎都",
    "血統": "王城",
    "威光": "輝城",
    "夢": "夢見郷",
    "花": "花都",
    "魅了": "花街",
    "贈与": "贈都",
    "契約": "契市",
    "封印": "封門",
    "真名": "秘名都",
    "対価": "価街",
    "断罪": "断罪門",
    "贖罪": "贖いの砦",
    "欠損": "灰砦",
    "灰": "灰都",
    "成長": "芽吹きの里",
    "根": "根城",
    "境界": "境都",
    "再生": "再生の街",
    "結晶": "晶都",
    "共鳴": "響都",
    "断面": "石郭",
    "記憶": "記憶廊",
}


TAG_TO_PERSON_NOUN = {
    "王権": "王家の継ぎ手",
    "誓約": "誓いの守り手",
    "紋章": "紋章士",
    "騎士": "騎士見習い",
    "月": "月守",
    "水": "水読み",
    "森": "森渡り",
    "循環": "巡り手",
    "炉": "炉守",
    "鍛造": "鍛え手",
    "石": "石工",
    "誓印": "印の番人",
    "狩猟": "狩人",
    "群れ": "群れの先触れ",
    "牙": "牙持ち",
    "追跡": "追跡者",
    "風": "風読み",
    "空": "空見",
    "祈り": "祈り手",
    "伝令": "伝令役",
    "潮": "潮見",
    "航路": "航路守",
    "海": "海渡り",
    "記憶歌": "歌い手",
    "火": "火守",
    "血統": "血統の子",
    "威光": "威光の担い手",
    "夢": "夢見",
    "花": "花守",
    "魅了": "魅了術師",
    "贈与": "贈り手",
    "契約": "契約者",
    "封印": "封印守",
    "真名": "名を知る者",
    "対価": "代価の使い手",
    "断罪": "断罪者",
    "贖罪": "贖い手",
    "欠損": "欠けた継ぎ手",
    "灰": "灰纏い",
    "成長": "芽吹き手",
    "根": "根守",
    "境界": "境の番人",
    "再生": "再生の巫者",
    "結晶": "晶人",
    "共鳴": "共鳴士",
    "断面": "断面見",
    "記憶": "記憶持ち",
}


TYPE_TO_ITEM_NOUN = {
    "bow": "弓",
    "warhammer": "戦槌",
    "grimoire": "魔導書",
    "sword": "剣",
    "shield": "盾",
    "staff": "杖",
    "spear": "槍",
    "ring": "指輪",
    "amulet": "護符",
}


TAG_TO_ITEM_PREFIX = {
    "王権": "王旗",
    "誓約": "誓印",
    "紋章": "紋章",
    "騎士": "白騎",
    "月": "月枝",
    "水": "水鏡",
    "森": "森詠み",
    "循環": "輪環",
    "炉": "炉火",
    "鍛造": "鍛印",
    "石": "礎石",
    "誓印": "誓印",
    "狩猟": "狩牙",
    "群れ": "群声",
    "牙": "牙",
    "追跡": "追風",
    "風": "風詠み",
    "空": "空歌",
    "祈り": "祈鐘",
    "伝令": "飛書",
    "潮": "潮見",
    "航路": "航路",
    "海": "海歌",
    "記憶歌": "記憶歌",
    "火": "炎紋",
    "血統": "血継",
    "威光": "威光",
    "夢": "夢見",
    "花": "花冠",
    "魅了": "魅惑",
    "贈与": "贈り物",
    "契約": "契約",
    "封印": "封鍵",
    "真名": "真名",
    "対価": "代価",
    "断罪": "断罪",
    "贖罪": "贖い",
    "欠損": "欠片",
    "灰": "灰",
    "成長": "芽吹き",
    "根": "根守",
    "境界": "境界",
    "再生": "再生",
    "結晶": "結晶",
    "共鳴": "共鳴",
    "断面": "断面",
    "記憶": "記憶",
}


@dataclass(frozen=True)
class GeneratedName:
    surface_name: str
    category: str
    race: str
    semantic_tags: list[str]
    annotation: str
    full_display: str
    phoneme: str
    suffix: str
    source_label: str
    origin: str
    source_file: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_naming_core(path: Path | None = None) -> dict[str, Any]:
    target = path or NAMING_CORE_PATH
    return _load_json(target)


@lru_cache(maxsize=8)
def load_city_dictionary(path: Path | None = None) -> dict[str, Any] | None:
    target = path or CITY_DICTIONARY_PATH
    if not target.exists():
        return None
    payload = _load_json(target)
    return payload if isinstance(payload.get("races"), dict) else None


@lru_cache(maxsize=8)
def load_person_dictionary(path: Path | None = None) -> dict[str, Any] | None:
    target = path or PERSON_DICTIONARY_PATH
    if not target.exists():
        return None
    payload = _load_json(target)
    return payload if isinstance(payload.get("races"), dict) else None


@lru_cache(maxsize=8)
def load_equipment_dictionary(path: Path | None = None) -> dict[str, Any] | None:
    target = path or EQUIPMENT_DICTIONARY_PATH
    if not target.exists():
        return None
    payload = _load_json(target)
    return payload if isinstance(payload.get("races"), dict) else None


def _normalize_external_entry(path: Path, raw: dict[str, Any]) -> dict[str, Any]:
    surface_name = str(raw.get("surface_name") or raw.get("name") or "").strip()
    if not surface_name:
        return {}
    semantic_tags = [str(tag).strip() for tag in raw.get("semantic_tags", []) if str(tag).strip()]
    display_text = str(raw.get("display_text") or raw.get("display_name") or "").strip()
    source_terms_raw = raw.get("source_terms")
    if source_terms_raw is None:
        source_terms_raw = raw.get("canonical_terms", [])
    source_terms = [str(term).strip() for term in source_terms_raw if str(term).strip()]
    return {
        "surface_name": surface_name,
        "display_text": display_text,
        "category": normalize_category(raw.get("category")),
        "race": str(raw.get("race") or "").strip().lower(),
        "ui_only": bool(raw.get("ui_only")),
        "semantic_tags": semantic_tags,
        "annotation": str(raw.get("annotation") or "").strip(),
        "item_type": str(raw.get("item_type") or raw.get("type") or "").strip().lower(),
        "source_terms": source_terms,
        "priority": int(raw.get("priority") or 0),
        "source_label": str(raw.get("source_label") or raw.get("source") or path.stem),
        "source_file": path.name,
    }


@lru_cache(maxsize=4)
def load_external_lexicon_entries(root: Path | None = None, include_ui_only: bool = True) -> tuple[dict[str, Any], ...]:
    target_root = root or USER_NAMING_ROOT
    if not target_root.exists():
        return tuple()
    entries: list[dict[str, Any]] = []
    for path in sorted(target_root.glob("*.json")):
        if path.name == NAMING_CORE_PATH.name:
            continue
        if path.name.endswith(".template.json"):
            continue
        payload = _load_json(path)
        raw_entries = payload.get("entries", [])
        if not isinstance(raw_entries, list):
            continue
        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            normalized = _normalize_external_entry(path, raw)
            if not include_ui_only and normalized.get("ui_only"):
                continue
            if normalized.get("surface_name") and normalized.get("category"):
                entries.append(normalized)
    return tuple(entries)


def _seed_rng(seed: int | None, *parts: str) -> random.Random:
    base = str(seed if seed is not None else 1729)
    return random.Random(":".join((base, *parts)))


def _require_race(core: dict[str, Any], race: str) -> dict[str, Any]:
    try:
        return core["races"][race]
    except KeyError as exc:
        known = ", ".join(sorted(core["races"].keys()))
        raise ValueError(f"unknown race: {race}. known races: {known}") from exc


def normalize_category(category: Any) -> str:
    raw = str(category or "").strip().lower()
    return CATEGORY_ALIASES.get(raw, raw)


def _wrap_annotation(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("《") and cleaned.endswith("》"):
        return cleaned
    return f"《{cleaned}》"


def _dictionary_root_for(core_path: Path | None) -> Path:
    return core_path.parent if core_path is not None else USER_NAMING_ROOT


def _load_specialized_dictionary(category: str, root: Path) -> dict[str, Any] | None:
    if category in {"city", "place"}:
        return load_city_dictionary(root / CITY_DICTIONARY_PATH.name)
    if category == "person":
        return load_person_dictionary(root / PERSON_DICTIONARY_PATH.name)
    if category == "item":
        return load_equipment_dictionary(root / EQUIPMENT_DICTIONARY_PATH.name)
    return None


def _choose_specialized_parts(
    *,
    category: str,
    race: str,
    seed: int | None,
    index: int,
    item_type: str | None,
    root: Path,
) -> tuple[str, str, str, str] | None:
    dictionary = _load_specialized_dictionary(category, root)
    if not dictionary:
        return None
    race_entry = dictionary.get("races", {}).get(race)
    if not isinstance(race_entry, dict):
        return None

    rng = _seed_rng(seed, race, category, str(index), item_type or "", dictionary.get("name", ""))
    if category in {"city", "place"}:
        phoneme = _choose(race_entry.get("roots", []), rng)
        suffix_key = "city" if category == "city" else "town"
        suffix_pool = (race_entry.get("suffixes") or {}).get(suffix_key, [])
        suffix = _choose(suffix_pool, rng)
        annotation_pool = race_entry.get("annotation_pool", [])
    elif category == "person":
        phoneme = _choose(race_entry.get("given_roots", []), rng)
        suffix = _choose(race_entry.get("given_suffixes", []), rng)
        annotation_pool = race_entry.get("titles", [])
    else:
        phoneme = _choose(race_entry.get("roots", []), rng)
        suffix = _choose(race_entry.get("suffixes", []), rng)
        annotation_pool = race_entry.get("annotations", [])

    annotation_text = _wrap_annotation(_choose(annotation_pool, rng)) if annotation_pool else ""
    return phoneme, suffix, annotation_text, str(dictionary.get("name") or race_entry.get("label") or race)


def _suffix_key(category: str) -> str:
    mapping = {
        "city": "city_suffix",
        "place": "city_suffix",
        "person": "person_suffix",
        "item": "item_suffix",
    }
    if category not in mapping:
        raise ValueError("category must be one of: city, place, person, item")
    return mapping[category]


def _to_katakana(fragment: str) -> str:
    cleaned = str(fragment or "").strip().lower()
    if not cleaned:
        return ""
    if cleaned in KANA_OVERRIDES:
        return KANA_OVERRIDES[cleaned]
    return cleaned.upper()


def _choose(values: Iterable[str], rng: random.Random) -> str:
    options = [value for value in values if str(value or "").strip()]
    if not options:
        raise ValueError("expected at least one candidate")
    return rng.choice(options)


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


def _is_acceptable_generated_name(surface_name: str, phoneme: str, suffix: str) -> bool:
    phoneme_kana = _to_katakana(phoneme)
    suffix_kana = _to_katakana(suffix)
    if not surface_name:
        return False
    if phoneme_kana == suffix_kana:
        return False
    if _has_repeated_chunk(surface_name):
        return False
    return True


def _tag_overlap(left: list[str], right: list[str]) -> bool:
    if not left or not right:
        return True
    return bool(set(left) & set(right))


def _find_external_candidates(
    *,
    category: str,
    race: str,
    item_type: str | None,
    semantic_tags: list[str],
    root: Path | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entry in load_external_lexicon_entries(root):
        if entry["category"] != category:
            continue
        if entry["race"] and entry["race"] != race:
            continue
        if entry.get("ui_only"):
            continue
        if category == "item" and entry["item_type"] and entry["item_type"] != str(item_type or "").strip().lower():
            continue
        if not _tag_overlap(semantic_tags, entry["semantic_tags"]):
            continue
        candidates.append(entry)
    candidates.sort(key=lambda item: (-item["priority"], item["surface_name"], item["source_file"]))
    return candidates


def _city_annotation(tag: str) -> str:
    prefix = TAG_TO_ITEM_PREFIX.get(tag, tag)
    noun = TAG_TO_CITY_NOUN.get(tag, "街")
    if prefix and prefix in noun:
        return f"《{noun}》"
    if prefix:
        return f"《{prefix}の{noun}》"
    return f"《{noun}》"


def _person_annotation(tag: str) -> str:
    noun = TAG_TO_PERSON_NOUN.get(tag, "旅人")
    return f"《{noun}》"


def _item_annotation(tag: str, item_type: str | None) -> str:
    noun = TYPE_TO_ITEM_NOUN.get(str(item_type or "").strip().lower(), "遺物")
    prefix = TAG_TO_ITEM_PREFIX.get(tag, tag)
    return f"《{prefix}の{noun}》"


def build_annotation(category: str, semantic_tags: list[str], item_type: str | None = None) -> str:
    tag = semantic_tags[0] if semantic_tags else "古き"
    if category in {"city", "place"}:
        return _city_annotation(tag)
    if category == "person":
        return _person_annotation(tag)
    return _item_annotation(tag, item_type)


def generate_name(
    *,
    race: str,
    category: str,
    seed: int | None = None,
    index: int = 0,
    semantic_tags: list[str] | None = None,
    annotation: str | None = None,
    item_type: str | None = None,
    core_path: Path | None = None,
    prefer_external: bool = True,
) -> GeneratedName:
    core = load_naming_core(core_path)
    category = normalize_category(category)
    if category not in VALID_GENERATION_CATEGORIES:
        raise ValueError("category must be one of: city, place, person, item")
    race_entry = _require_race(core, race)
    naming_root = _dictionary_root_for(core_path)
    tags = list(semantic_tags or race_entry.get("semantic_links", [])[:2] or ["古き"])
    if prefer_external:
        external = _find_external_candidates(
            category=category,
            race=race,
            item_type=item_type,
            semantic_tags=tags,
            root=naming_root,
        )
        if external:
            picked = external[index % len(external)]
            final_annotation = annotation or picked["annotation"] or build_annotation(category, tags, item_type)
            return GeneratedName(
                surface_name=picked["surface_name"],
                category=category,
                race=race,
                semantic_tags=tags,
                annotation=final_annotation,
                full_display=f"{picked['surface_name']}{final_annotation}",
                phoneme="",
                suffix="",
                source_label=picked["source_label"],
                origin="external",
                source_file=picked["source_file"],
            )
    for offset in range(MAX_NAME_SEARCH_ATTEMPTS):
        current_index = index + offset
        specialized = _choose_specialized_parts(
            category=category,
            race=race,
            seed=seed,
            index=current_index,
            item_type=item_type,
            root=naming_root,
        )
        if specialized is not None:
            phoneme, suffix, specialized_annotation, source_label = specialized
            final_annotation = annotation or specialized_annotation or build_annotation(category, tags, item_type)
            source_file = {
                "city": CITY_DICTIONARY_PATH.name,
                "place": CITY_DICTIONARY_PATH.name,
                "person": PERSON_DICTIONARY_PATH.name,
                "item": EQUIPMENT_DICTIONARY_PATH.name,
            }[category]
        else:
            rng = _seed_rng(seed, race, category, str(current_index), item_type or "")
            phoneme = _choose(race_entry["phonemes"], rng)
            suffix = _choose(race_entry[_suffix_key(category)], rng)
            final_annotation = annotation or build_annotation(category, tags, item_type)
            source_label = str(race_entry.get("label") or race)
            source_file = (core_path or NAMING_CORE_PATH).name
        surface_name = f"{_to_katakana(phoneme)}{_to_katakana(suffix)}"
        if not _is_acceptable_generated_name(surface_name, phoneme, suffix):
            continue
        return GeneratedName(
            surface_name=surface_name,
            category=category,
            race=race,
            semantic_tags=tags,
            annotation=final_annotation,
            full_display=f"{surface_name}{final_annotation}",
            phoneme=phoneme,
            suffix=suffix,
            source_label=source_label,
            origin="generated",
            source_file=source_file,
        )
    raise ValueError(f"unable to generate an acceptable {category} name for race={race}")


def generate_batch(
    *,
    race: str,
    category: str,
    count: int,
    seed: int | None = None,
    semantic_tags: list[str] | None = None,
    annotation: str | None = None,
    item_type: str | None = None,
    core_path: Path | None = None,
    prefer_external: bool = True,
) -> list[dict[str, Any]]:
    category = normalize_category(category)
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    attempts = 0
    index = 0
    while len(entries) < count and attempts < count * 20:
        generated = generate_name(
            race=race,
            category=category,
            seed=seed,
            index=index,
            semantic_tags=semantic_tags,
            annotation=annotation,
            item_type=item_type,
            core_path=core_path,
            prefer_external=prefer_external,
        )
        attempts += 1
        index += 1
        if generated.surface_name in seen:
            continue
        seen.add(generated.surface_name)
        entries.append(
            {
                "surface_name": generated.surface_name,
                "category": generated.category,
                "race": generated.race,
                "source_label": generated.source_label,
                "semantic_tags": generated.semantic_tags,
                "annotation": generated.annotation,
                "full_display": generated.full_display,
                "phoneme": generated.phoneme,
                "suffix": generated.suffix,
                "item_type": item_type,
                "origin": generated.origin,
                "source_file": generated.source_file,
            }
        )
    return entries


def generate_plan_batches(
    plan: dict[str, Any],
    *,
    prefer_external: bool = True,
) -> dict[str, Any]:
    plan_seed = int(plan.get("seed", 1729))
    batches: list[dict[str, Any]] = []
    for index, batch in enumerate(plan.get("batches", [])):
        race = str(batch["race"]).strip()
        category = normalize_category(batch["category"])
        count = int(batch["count"])
        item_type = str(batch.get("item_type") or "").strip() or None
        semantic_tags = [str(tag).strip() for tag in batch.get("semantic_tags", []) if str(tag).strip()] or None
        annotation = str(batch.get("annotation") or "").strip() or None
        seed = int(batch.get("seed", plan_seed + index))
        entries = generate_batch(
            race=race,
            category=category,
            count=count,
            seed=seed,
            semantic_tags=semantic_tags,
            annotation=annotation,
            item_type=item_type,
            prefer_external=prefer_external,
        )
        batches.append(
            {
                "label": str(batch.get("label") or f"{race}_{category}"),
                "race": race,
                "category": category,
                "count": count,
                "seed": seed,
                "item_type": item_type,
                "semantic_tags": semantic_tags or [],
                "entries": entries,
            }
        )
    return {
        "schema_version": "1.0",
        "plan_name": str(plan.get("name") or "fantasy_name_batch_plan"),
        "seed": plan_seed,
        "batch_count": len(batches),
        "batches": batches,
    }
