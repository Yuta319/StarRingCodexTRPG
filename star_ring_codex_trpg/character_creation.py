from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
import copy

from .fantasy_naming_generator import generate_name


@dataclass(frozen=True)
class CharacterProfile:
    name: str
    race: str
    style: str
    temperament: str
    origin: str
    loadout: str = "oathblade"
    source_mode: str = "native"
    source_title: str = ""
    source_name: str = ""
    appearance_notes: str = ""
    reinterpretation_notes: str = ""


RACE_OPTIONS: Dict[str, Dict[str, str]] = {
    "human": {"label": "人間", "summary": "どの局面にも馴染みやすい、標準的な旅人。"},
    "elf": {"label": "エルフ", "summary": "森と月の気配に敏く、儀式や観察に長ける。"},
    "dwarf": {"label": "ドワーフ", "summary": "鍛造と坑道に強く、守りと統治に粘りがある。"},
    "werebeast": {"label": "獣人", "summary": "嗅覚と脚で場を読み、乱戦でも踏ん張りが利く。"},
    "birdfolk": {"label": "翼人", "summary": "見晴らしと伝令に強く、場の変化を拾いやすい。"},
    "fishfolk": {"label": "魚人", "summary": "潮と航路に明るく、水辺の局面で動きやすい。"},
    "dragonewt": {"label": "竜人", "summary": "威圧と胆力を備え、前に出るほど存在感が増す。"},
    "fey": {"label": "妖精族", "summary": "夢と気配を扱い、儀式と交渉の両面で癖が出る。"},
    "demonian": {"label": "魔人", "summary": "契約と代価に敏く、危うい局面で強みが出る。"},
    "fallen": {"label": "堕天族", "summary": "傷を抱えつつも踏みとどまり、危機で意地を見せる。"},
    "plantfolk": {"label": "樹人", "summary": "根気と再生力があり、支え役に回ると強い。"},
    "gemfolk": {"label": "石人", "summary": "結晶のように理を積み、長い局面で崩れにくい。"},
}

STYLE_OPTIONS: Dict[str, Dict[str, Any]] = {
    "vanguard": {
        "label": "前衛",
        "summary": "危うい場面で前に立ち、人を守りながら押し返す。",
        "skill_deltas": {"combat": 8.0, "authority": 3.0},
        "quick_slot_labels": ["踏み込む", "守る", "断つ", "介入"],
    },
    "envoy": {
        "label": "交渉役",
        "summary": "利害を見て話をまとめ、崩れそうな場をつなぎ止める。",
        "skill_deltas": {"diplomacy": 8.0, "authority": 3.0},
        "quick_slot_labels": ["話す", "宥める", "取引", "介入"],
    },
    "seeker": {
        "label": "探究者",
        "summary": "見えない手順や古い理を拾い、奥の理由まで探りにいく。",
        "skill_deltas": {"ritual": 8.0, "stewardship": 2.0},
        "quick_slot_labels": ["調べる", "見抜く", "唱える", "介入"],
    },
    "shadow": {
        "label": "斥候",
        "summary": "足跡と気配を追い、目立たずに決め手を拾い上げる。",
        "skill_deltas": {"stealth": 8.0, "combat": 2.0},
        "quick_slot_labels": ["探る", "忍び寄る", "盗み見る", "介入"],
    },
    "warden": {
        "label": "守り手",
        "summary": "崩れかけた手順と補給を立て直し、全体を支える。",
        "skill_deltas": {"stewardship": 8.0, "authority": 2.0},
        "quick_slot_labels": ["整える", "支える", "指示する", "介入"],
    },
}

TEMPERAMENT_OPTIONS: Dict[str, Dict[str, Any]] = {
    "mercy": {
        "label": "情に厚い",
        "summary": "切り捨てるより、助ける道を先に探す。",
        "tendency_deltas": {"mercy": 10.0},
    },
    "prudence": {
        "label": "慎重",
        "summary": "ひと呼吸置いてから動き、崩れる順番を見ている。",
        "tendency_deltas": {"prudence": 10.0},
    },
    "ambition": {
        "label": "野心家",
        "summary": "勝ち筋を逃さず、立場を一段上げる機会に敏い。",
        "tendency_deltas": {"ambition": 10.0},
    },
    "zeal": {
        "label": "熱意が強い",
        "summary": "正しいと思ったことに勢いよく踏み込む。",
        "tendency_deltas": {"zeal": 10.0},
    },
    "stoic": {
        "label": "寡黙",
        "summary": "言葉より行動で示し、揺れても顔には出しにくい。",
        "tendency_deltas": {"prudence": 6.0, "mercy": 3.0},
    },
    "curious": {
        "label": "好奇心が強い",
        "summary": "危うさの中にも答えを探し、未知に手を伸ばしてしまう。",
        "tendency_deltas": {"ambition": 4.0, "prudence": 4.0},
    },
    "rebellious": {
        "label": "反骨が強い",
        "summary": "押しつけられた理屈に従わず、納得できるまで噛みつく。",
        "tendency_deltas": {"zeal": 6.0, "ambition": 3.0},
    },
    "devout": {
        "label": "敬虔",
        "summary": "祈りと誓いを裏切らず、背負った役目に筋を通そうとする。",
        "tendency_deltas": {"mercy": 4.0, "zeal": 5.0},
    },
}

ORIGIN_OPTIONS: Dict[str, Dict[str, Any]] = {
    "ford": {
        "label": "渡し場育ち",
        "summary": "人と荷が行き交う境目で、揉め事の収め方を見て育った。",
        "skill_deltas": {"diplomacy": 2.0, "stewardship": 1.0},
        "semantic_tags": ["潮", "誓約"],
    },
    "shrine": {
        "label": "祠育ち",
        "summary": "祈りと手順の近くで育ち、形に残らない気配にも目が利く。",
        "skill_deltas": {"ritual": 3.0},
        "semantic_tags": ["月", "循環"],
    },
    "mine": {
        "label": "坑道育ち",
        "summary": "崩落と補給の重さを知っていて、場を保たせる勘がある。",
        "skill_deltas": {"combat": 1.0, "stewardship": 2.0},
        "semantic_tags": ["石", "鍛造"],
    },
    "road": {
        "label": "街道育ち",
        "summary": "検札と荷の流れを見て育ち、動く人の都合に明るい。",
        "skill_deltas": {"authority": 2.0, "stealth": 1.0},
        "semantic_tags": ["風", "騎士"],
    },
    "marsh": {
        "label": "湿地育ち",
        "summary": "見えにくい道を覚えていて、痕跡や抜け道を拾いやすい。",
        "skill_deltas": {"stealth": 3.0},
        "semantic_tags": ["森", "水"],
    },
    "court": {
        "label": "宮廷育ち",
        "summary": "視線と儀礼の強い場所で育ち、立場の差と空気の変化に敏い。",
        "skill_deltas": {"authority": 3.0, "diplomacy": 1.0},
        "semantic_tags": ["王権", "紋章"],
    },
    "harbor": {
        "label": "港育ち",
        "summary": "荷と噂が集まる波止場で育ち、よそ者の流れと相場に明るい。",
        "skill_deltas": {"diplomacy": 2.0, "stealth": 1.0},
        "semantic_tags": ["潮", "航路"],
    },
    "caravan": {
        "label": "隊商育ち",
        "summary": "長い道と売買の駆け引きを知り、移動中でも立て直しが利く。",
        "skill_deltas": {"stewardship": 2.0, "diplomacy": 2.0},
        "semantic_tags": ["交易", "境界"],
    },
    "cloister": {
        "label": "修道院育ち",
        "summary": "静かな祈りと禁則の中で育ち、逸脱と沈黙の重さを知っている。",
        "skill_deltas": {"ritual": 2.0, "authority": 1.0},
        "semantic_tags": ["祈り", "封印"],
    },
    "frontier": {
        "label": "辺境育ち",
        "summary": "壁の外に近い土地で育ち、足場の悪さと少人数の守りに慣れている。",
        "skill_deltas": {"combat": 2.0, "stealth": 1.0},
        "semantic_tags": ["灰", "境界"],
    },
}

LOADOUT_OPTIONS: Dict[str, Dict[str, Any]] = {
    "oathblade": {
        "label": "誓約の旅装",
        "summary": "直剣と手灯で、列と約束を守るための基本装備。",
        "weapon_label": "直剣",
        "offhand_slot_label": "左手灯具",
        "offhand_base": "灯",
        "themes": ["誓約", "灯", "印章"],
    },
    "trailbow": {
        "label": "斥候の旅装",
        "summary": "弓と索具で、先を見て安全な道を拾うための装備。",
        "weapon_label": "弓",
        "offhand_slot_label": "左手索具",
        "offhand_base": "索具",
        "themes": ["索具", "羽根", "道標"],
    },
    "ritescribe": {
        "label": "儀式の旅装",
        "summary": "杖と書板で、祈りと手順を扱うための装備。",
        "weapon_label": "杖",
        "offhand_slot_label": "左手書板",
        "offhand_base": "書板",
        "themes": ["祈り", "書板", "封印"],
    },
    "wardenhammer": {
        "label": "守り手の旅装",
        "summary": "戦槌と護灯で、崩れた列や補給を立て直すための装備。",
        "weapon_label": "戦槌",
        "offhand_slot_label": "左手護灯",
        "offhand_base": "護灯",
        "themes": ["護り", "鎚", "補給"],
    },
    "shadowknife": {
        "label": "影歩きの旅装",
        "summary": "短剣と鍵具で、隠れた手順や抜け道を拾うための装備。",
        "weapon_label": "短剣",
        "offhand_slot_label": "左手鍵具",
        "offhand_base": "鍵具",
        "themes": ["鍵", "影", "偵察"],
    },
    "tailored": {
        "label": "設定から組む",
        "summary": "人物設定と転生元の面影を基に、初期装備一式を組み直す。",
        "weapon_label": "",
        "offhand_slot_label": "左手補助具",
        "offhand_base": "補助具",
        "themes": ["継承", "旅装", "面影"],
    },
}

SOURCE_MODE_OPTIONS: Dict[str, Dict[str, str]] = {
    "native": {
        "label": "この世界の旅人",
        "summary": "この世界で生きてきた人物として導入へ入る。",
    },
    "reincarnated": {
        "label": "別世界からの転生者",
        "summary": "別世界の面影を持ち込んだ人物として、この世界へ入り直す。",
    },
}

RACE_SKILL_DELTAS: Dict[str, Dict[str, float]] = {
    "human": {},
    "elf": {"ritual": 4.0, "stealth": 2.0},
    "dwarf": {"combat": 3.0, "stewardship": 4.0},
    "werebeast": {"combat": 4.0, "stealth": 3.0},
    "birdfolk": {"diplomacy": 2.0, "authority": 2.0, "stealth": 1.0},
    "fishfolk": {"diplomacy": 2.0, "ritual": 2.0, "stealth": 1.0},
    "dragonewt": {"combat": 4.0, "authority": 3.0},
    "fey": {"ritual": 4.0, "diplomacy": 2.0},
    "demonian": {"ritual": 3.0, "authority": 2.0, "stealth": 1.0},
    "fallen": {"combat": 2.0, "ritual": 2.0, "authority": 1.0},
    "plantfolk": {"stewardship": 4.0, "ritual": 1.0},
    "gemfolk": {"ritual": 2.0, "stewardship": 3.0, "authority": 1.0},
}

DEFAULT_CHARACTER_PROFILE = CharacterProfile(
    name="",
    race="human",
    style="vanguard",
    temperament="prudence",
    origin="ford",
    loadout="oathblade",
    source_mode="native",
)


def _normalize_choice(value: object, options: Mapping[str, Any], default: str) -> str:
    key = str(value or "").strip().lower()
    return key if key in options else default


def _normalize_text(value: object, limit: int) -> str:
    raw = str(value or "").replace("\r", "\n")
    collapsed = "\n".join(part.strip() for part in raw.split("\n"))
    collapsed = "\n".join(part for part in collapsed.split("\n") if part)
    return collapsed[:limit].strip()


def parse_character_profile_payload(payload: Mapping[str, Any]) -> Optional[CharacterProfile]:
    name = str(payload.get("character_name") or payload.get("name") or "").strip()
    race_raw = payload.get("character_race") or payload.get("race")
    style_raw = payload.get("character_style") or payload.get("style")
    temperament_raw = payload.get("character_temperament") or payload.get("temperament")
    origin_raw = payload.get("character_origin") or payload.get("origin")
    loadout_raw = payload.get("character_loadout") or payload.get("loadout")
    source_mode_raw = payload.get("character_source_mode") or payload.get("source_mode")
    source_title = _normalize_text(payload.get("character_source_title") or payload.get("source_title"), 80)
    source_name = _normalize_text(payload.get("character_source_name") or payload.get("source_name"), 80)
    appearance_notes = _normalize_text(payload.get("character_appearance_notes") or payload.get("appearance_notes"), 320)
    reinterpretation_notes = _normalize_text(
        payload.get("character_reinterpretation_notes") or payload.get("reinterpretation_notes"), 320
    )
    if not any(
        [
            name,
            race_raw,
            style_raw,
            temperament_raw,
            origin_raw,
            loadout_raw,
            source_mode_raw,
            source_title,
            source_name,
            appearance_notes,
            reinterpretation_notes,
        ]
    ):
        return None
    return CharacterProfile(
        name=name,
        race=_normalize_choice(race_raw, RACE_OPTIONS, DEFAULT_CHARACTER_PROFILE.race),
        style=_normalize_choice(style_raw, STYLE_OPTIONS, DEFAULT_CHARACTER_PROFILE.style),
        temperament=_normalize_choice(temperament_raw, TEMPERAMENT_OPTIONS, DEFAULT_CHARACTER_PROFILE.temperament),
        origin=_normalize_choice(origin_raw, ORIGIN_OPTIONS, DEFAULT_CHARACTER_PROFILE.origin),
        loadout=_normalize_choice(loadout_raw, LOADOUT_OPTIONS, DEFAULT_CHARACTER_PROFILE.loadout),
        source_mode=_normalize_choice(source_mode_raw, SOURCE_MODE_OPTIONS, DEFAULT_CHARACTER_PROFILE.source_mode),
        source_title=source_title,
        source_name=source_name,
        appearance_notes=appearance_notes,
        reinterpretation_notes=reinterpretation_notes,
    )


def character_profile_query_payload(profile: CharacterProfile) -> Dict[str, str]:
    payload = {
        "character_race": profile.race,
        "character_style": profile.style,
        "character_temperament": profile.temperament,
        "character_origin": profile.origin,
        "character_loadout": profile.loadout,
        "character_source_mode": profile.source_mode,
    }
    if profile.name.strip():
        payload["character_name"] = profile.name.strip()
    if profile.source_title.strip():
        payload["character_source_title"] = profile.source_title.strip()
    if profile.source_name.strip():
        payload["character_source_name"] = profile.source_name.strip()
    if profile.appearance_notes.strip():
        payload["character_appearance_notes"] = profile.appearance_notes.strip()
    if profile.reinterpretation_notes.strip():
        payload["character_reinterpretation_notes"] = profile.reinterpretation_notes.strip()
    return payload


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _merge_deltas(*parts: Mapping[str, float]) -> Dict[str, float]:
    merged: Dict[str, float] = {}
    for part in parts:
        for key, value in part.items():
            merged[key] = merged.get(key, 0.0) + float(value)
    return merged


def _semantic_tags(profile: CharacterProfile) -> list[str]:
    origin = ORIGIN_OPTIONS[profile.origin]
    style = STYLE_OPTIONS[profile.style]
    primary_tag = {
        "vanguard": "騎士",
        "envoy": "誓約",
        "seeker": "月",
        "shadow": "追跡",
        "warden": "境界",
    }[profile.style]
    return list(dict.fromkeys([*origin.get("semantic_tags", []), primary_tag]))


def _starter_boon_seed(profile: CharacterProfile) -> Dict[str, Any]:
    visible_map = {
        "vanguard": ("境界踏破", "危うい局面で一歩前に出るとき、最初の判断がぶれにくい。"),
        "envoy": ("誓約の舌", "対立の席で、相手の譲れない線を見抜きやすい。"),
        "seeker": ("遺響の目", "古い理や隠れた手順に触れるとき、違和感を拾いやすい。"),
        "shadow": ("影継ぎの足", "隠し通路や抜け道を探すとき、最初の糸口をつかみやすい。"),
        "warden": ("守りの手", "崩れた列や補給を立て直すとき、手順の優先順が見えやすい。"),
    }
    dormant_map = {
        "native": ("祝印の残り火", "この世界に元からあった縁が、危機で薄く助ける。"),
        "reincarnated": ("異界の残響", "元の世界の感覚が、ときどきこの世界の理をずらして見せる。"),
    }
    visible_label, visible_summary = visible_map[profile.style]
    dormant_label, dormant_summary = dormant_map[profile.source_mode]
    return {
        "visibleBoon": {"label": visible_label, "summary": visible_summary, "kind": "恩恵"},
        "dormantGrace": {"label": dormant_label, "summary": dormant_summary, "kind": "恩寵"},
        "caps": {
            "visibleBoonCount": 1,
            "dormantGraceCount": 1,
            "stackingRule": "開始時は恩恵1件と潜在恩寵1件まで。以後は backend 側の進行でのみ増減する。",
        },
    }


def _generation_constraints() -> Dict[str, Any]:
    return {
        "skillSoftCap": 78.0,
        "skillFloor": 35.0,
        "starterAttackCap": 165,
        "starterDefenseCap": 54,
        "starterSupportCap": 48,
        "starterLoadoutPieces": 6,
        "visibleBoonCount": 1,
        "dormantGraceCount": 1,
        "forbidden": [
            "開始時から世界観を壊す現代兵器",
            "開始時から空中要塞級の遺物",
            "一撃で局面を終了させる性能",
            "複数の恩寵を重ねた無制限強化",
        ],
    }


def _opening_variants(profile: CharacterProfile, name: str) -> list[Dict[str, str]]:
    race = RACE_OPTIONS[profile.race]
    style = STYLE_OPTIONS[profile.style]
    origin = ORIGIN_OPTIONS[profile.origin]
    loadout = LOADOUT_OPTIONS[profile.loadout]
    source_mode = SOURCE_MODE_OPTIONS[profile.source_mode]
    variants = [
        {
            "label": "静かな導入",
            "summary": f"{name}は{origin['label']}で身につけた所作を崩さず、{loadout['label']}を整えたまま最初の局面へ入る。",
        },
        {
            "label": "不穏な導入",
            "summary": f"{race['label']}の{style['label']}として見られる{name}だが、足元にはもう次のトラブルの気配が寄っている。",
        },
        {
            "label": "転機の導入",
            "summary": f"{source_mode['label']}としての面影を抱えたまま、{name}はこの世界の役目を引き受ける。"
            if profile.source_mode == "reincarnated"
            else f"{name}はこの世界の旅人として、ごく自然な顔で局面の中心へ踏み込んでいく。",
        },
    ]
    return variants


def _resolve_name(profile: CharacterProfile, seed: int | None) -> str:
    if profile.name.strip():
        return profile.name.strip()
    try:
        generated = generate_name(
            race=profile.race,
            category="person",
            seed=seed,
            semantic_tags=_semantic_tags(profile),
        )
        return generated.surface_name
    except Exception:
        fallback_by_race = {
            "human": "リオネル",
            "elf": "セリル",
            "dwarf": "ドルク",
            "werebeast": "ガルン",
            "birdfolk": "オリエル",
            "fishfolk": "ルア",
            "dragonewt": "ザルク",
            "fey": "ミレア",
            "demonian": "ヴェル",
            "fallen": "カイン",
            "plantfolk": "ヴェラ",
            "gemfolk": "オリク",
        }
        return fallback_by_race.get(profile.race, "無銘の旅人")


def build_runtime_character_profile(profile: CharacterProfile, seed: int | None) -> Dict[str, Any]:
    race = RACE_OPTIONS[profile.race]
    style = STYLE_OPTIONS[profile.style]
    temperament = TEMPERAMENT_OPTIONS[profile.temperament]
    origin = ORIGIN_OPTIONS[profile.origin]
    loadout = LOADOUT_OPTIONS[profile.loadout]
    source_mode = SOURCE_MODE_OPTIONS[profile.source_mode]
    name = _resolve_name(profile, seed)
    source_summary = ""
    if profile.source_mode == "reincarnated":
        if profile.source_title and profile.source_name:
            source_summary = f"{profile.source_title}での{profile.source_name}としての面影を、まだ薄く引きずっている。"
        elif profile.source_title:
            source_summary = f"{profile.source_title}での記憶を、まだ薄く引きずっている。"
        elif profile.source_name:
            source_summary = f"{profile.source_name}として生きた面影が、まだ薄く残っている。"
        else:
            source_summary = "別世界の面影を、まだ薄く引きずっている。"
    opening_lines = [
        f"{name}は{origin['label']}の空気を知る{race['label']}だ。",
        f"{style['summary']} 装備は{loadout['label']}を選んだ。",
    ]
    if source_summary:
        opening_lines.append(source_summary)
    else:
        opening_lines.append(source_mode["summary"])
    opening_lines.append(origin["summary"])
    boon_seed = _starter_boon_seed(profile)
    opening_variants = _opening_variants(profile, name)
    summary = f"{origin['label']}の{race['label']}。役回りは{style['label']}、装備は{loadout['label']}、気質は{temperament['label']}。"
    if source_summary:
        summary = f"{summary} {source_summary}"
    return {
        "name": name,
        "race": profile.race,
        "raceLabel": race["label"],
        "raceSummary": race["summary"],
        "style": profile.style,
        "styleLabel": style["label"],
        "styleSummary": style["summary"],
        "temperament": profile.temperament,
        "temperamentLabel": temperament["label"],
        "temperamentSummary": temperament["summary"],
        "origin": profile.origin,
        "originLabel": origin["label"],
        "originSummary": origin["summary"],
        "loadout": profile.loadout,
        "loadoutLabel": loadout["label"],
        "loadoutSummary": loadout["summary"],
        "sourceMode": profile.source_mode,
        "sourceModeLabel": source_mode["label"],
        "sourceModeSummary": source_mode["summary"],
        "sourceTitle": profile.source_title,
        "sourceName": profile.source_name,
        "sourceSummary": source_summary,
        "appearanceNotes": profile.appearance_notes,
        "reinterpretationNotes": profile.reinterpretation_notes,
        "summaryText": summary,
        "openingLines": opening_lines,
        "openingVariants": opening_variants,
        "quickSlotLabels": list(style["quick_slot_labels"]),
        "starterBoonSeed": boon_seed,
        "generationConstraints": _generation_constraints(),
    }


def apply_character_profile(
    world_state: Dict[str, Any],
    profile: CharacterProfile,
    *,
    seed: int | None = None,
) -> Dict[str, Any]:
    patched = copy.deepcopy(world_state)
    protagonist = patched["resolved_world"]["protagonist"]
    runtime_profile = build_runtime_character_profile(profile, seed)
    protagonist["label_ja"] = runtime_profile["name"]
    protagonist["race"] = profile.race
    protagonist["build_style"] = profile.style
    protagonist["character_profile"] = runtime_profile

    skill_deltas = _merge_deltas(
        RACE_SKILL_DELTAS.get(profile.race, {}),
        STYLE_OPTIONS[profile.style].get("skill_deltas", {}),
        ORIGIN_OPTIONS[profile.origin].get("skill_deltas", {}),
    )
    next_skills = dict(protagonist.get("skills", {}))
    for key, base_value in next_skills.items():
        adjusted = float(base_value) + skill_deltas.get(key, 0.0)
        next_skills[key] = round(_clamp(adjusted, 35.0, 78.0), 1)
    protagonist["skills"] = next_skills

    tendency_deltas = TEMPERAMENT_OPTIONS[profile.temperament].get("tendency_deltas", {})
    next_tendencies = dict(protagonist.get("tendencies", {}))
    for key, base_value in next_tendencies.items():
        adjusted = float(base_value) + float(tendency_deltas.get(key, 0.0))
        next_tendencies[key] = round(_clamp(adjusted, 30.0, 80.0), 1)
    protagonist["tendencies"] = next_tendencies
    return patched
