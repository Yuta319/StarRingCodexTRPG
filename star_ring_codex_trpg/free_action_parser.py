from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .campaign_content import canonical_role_slot_id
from .errors import FreeActionError
from .vice_taboo import TABOO_ENTRY_MAP, VICE_ENTRY_MAP, exposure_profile_for_slot


ACTION_FAMILY_KEYWORDS = {
    "theft": [
        "盗",
        "盗み",
        "盗み出",
        "持ち出",
        "奪",
        "窃取",
        "失敬",
        "拝借",
        "くすね",
        "抜き取",
        "かっぱら",
        "掠め取",
        "猫ばば",
        "失せ物に見せかけ",
    ],
    "fraud": [
        "偽装",
        "偽造",
        "詐",
        "帳尻",
        "ごまか",
        "偽許可",
        "なりすまし",
        "改ざん",
        "改竄",
        "書き換",
        "差し替",
        "捏造",
        "でっちあげ",
        "通行札を偽",
        "浄化済みと偽",
    ],
    "smuggling": [
        "密輸",
        "横流し",
        "裏口",
        "抜け道",
        "こっそり運",
        "搬出",
        "持ち込み",
        "隠し荷",
        "船底",
        "検問を抜",
        "渡しを抜",
        "封路をすり抜",
        "舟に紛らせ",
    ],
    "coercion": [
        "脅",
        "脅迫",
        "強要",
        "口止め",
        "盾に",
        "言うことを聞かせ",
        "揺さぶ",
        "圧をかけ",
        "締め上げ",
        "弱みを握",
        "弱みを突",
        "恫喝",
        "黙らせ",
    ],
    "violence": [
        "殴",
        "斬",
        "刺",
        "殺",
        "血",
        "襲",
        "暴",
        "壊して進",
        "叩き伏せ",
        "切り伏せ",
        "拉致",
        "袋叩き",
        "焼き払",
    ],
    "illicit_relationship": [
        "逢瀬",
        "密会",
        "寝所",
        "関係",
        "不倫",
        "婚姻破り",
        "情を通",
        "手をつけ",
        "通じ合",
        "囲い込",
    ],
    "sacrilege": [
        "冒涜",
        "聖遺物を汚",
        "神前",
        "聖域を荒",
        "祈りを汚",
        "浄化済みと偽",
        "遺物を汚",
        "祭具を汚",
        "祠を汚",
        "聖別を偽",
        "供物を荒ら",
        "祈り場を穢",
        "穢す",
    ],
    "taboo_ritual": [
        "禁譜",
        "鐘譜",
        "禁書",
        "禁術",
        "魂",
        "霊",
        "輪廻",
        "封印を破",
        "封印札を剥",
        "結界を破",
        "儀礼を崩",
        "真名を消",
        "昇神",
        "魂を縛",
        "輪廻を止",
        "禁じ手",
        "封路をこじ開け",
    ],
    "deception": [
        "だま",
        "欺",
        "偽名",
        "偽り",
        "作り話",
        "誤認",
        "はぐらか",
        "口八丁",
        "話を盛",
        "煙に巻",
        "虚偽",
        "言い逃れ",
        "目くらまし",
    ],
    "sabotage": [
        "妨害",
        "破壊",
        "切断",
        "崩す",
        "火をつけ",
        "使えなく",
        "台無し",
        "壊す",
        "止める",
        "詰まらせ",
        "足止め",
        "封路を崩",
        "綱を切",
        "札を破",
    ],
    "escape": [
        "逃げ",
        "脱出",
        "脱走",
        "抜ける",
        "逃がす",
        "姿をくらま",
        "身を隠し",
        "離脱",
        "振り切",
        "抜け出",
        "潜り抜け",
    ],
    "concealment": [
        "隠",
        "隠す",
        "埋める",
        "消す",
        "証拠を消",
        "ごまかして伏せ",
        "隠ぺい",
        "隠蔽",
        "揉み消",
        "火消し",
        "帳消し",
    ],
    "social_manipulation": [
        "噂",
        "煽",
        "扇動",
        "懐柔",
        "言いくるめ",
        "世論",
        "流言",
        "吹き込",
        "囁",
        "けしかけ",
        "印象操作",
        "空気を作",
        "同情を集め",
    ],
}

VICE_KEYWORD_HINTS = {
    "fraud": ["偽造", "偽り", "偽装", "浄化済みと偽", "数字をごまか", "改ざん", "書き換え", "差し替え"],
    "blackmail": ["弱みを突", "脅", "口止め", "揺さぶ", "圧をかけ", "恫喝"],
    "theft": ["盗", "持ち出", "剥ぎ取り", "拝借", "くすね", "抜き取"],
    "smuggling": ["横流し", "抜け道", "密輸", "隠し荷", "検問を抜", "裏口"],
    "bribery_corruption": ["袖の下", "収賄", "見逃し料", "役職売買", "賄賂", "口利き料"],
    "oathbreaking": ["誓いを破", "停戦破り", "背信", "誓約を捨て", "保護誓約を破"],
    "unlawful_killing": ["私刑", "見せしめに殺", "黙らせるために殺", "報復殺人"],
}

TABOO_KEYWORD_HINTS = {
    "sealed_text_usage": ["禁譜", "鐘譜", "禁書", "禁術", "封印文", "禁じ手の譜", "逆唱"],
    "ward_breaking": ["封印札", "結界", "封印を破", "札を剥が", "護符を剥が", "封路をこじ開け"],
    "false_sanctification": ["浄化済みと偽", "浄化済み", "清めたと偽", "偽の清め", "偽の聖別"],
    "relic_defilement": ["聖遺物", "遺物を汚", "封箱を汚", "祭具を汚", "供物を荒らす"],
    "corpse_desecration": ["死体を暴", "墓を荒ら", "遺体から剥ぎ", "祈りなき焼却", "死者を汚"],
    "sanctuary_violation": ["聖域を荒", "神殿で殺", "避難民を引きずり出", "聖域で拘束"],
    "false_oracle": ["神託を偽", "神名を騙", "偽の御告げ", "夢告を捏造"],
    "spirit_binding": ["魂を縛", "亡魂を拘束", "怨霊を使", "魂片を保存"],
}

MEANS_KEYWORDS = [
    ("夜", "夜間行動"),
    ("裏", "裏手経由"),
    ("密か", "密行"),
    ("帳", "帳簿工作"),
    ("印", "印章操作"),
    ("抜け道", "抜け道利用"),
    ("倉庫", "倉庫潜入"),
    ("検問", "検問すり抜け"),
    ("舟", "舟路利用"),
    ("渡し", "渡し場利用"),
    ("封印", "封印干渉"),
    ("結界", "結界干渉"),
    ("祈", "儀礼操作"),
    ("偽名", "偽名利用"),
    ("賄賂", "金銭工作"),
    ("袖の下", "金銭工作"),
    ("噂", "流言操作"),
    ("脅", "脅し"),
    ("殺", "殺害"),
    ("逃", "逃走"),
]

GAIN_KEYWORDS = {
    "survival": ["生き延び", "助か", "逃げ切", "守る", "救う"],
    "wealth": ["金", "報酬", "財", "売る", "儲"],
    "status": ["名声", "地位", "立場", "信用", "優位"],
    "secrecy": ["隠", "知られず", "気づかれず", "痕跡を消"],
    "revenge": ["復讐", "仕返し", "報い"],
    "desire": ["欲望", "惚", "恋", "執着"],
    "power": ["支配", "権力", "従わせ", "握る"],
    "faith": ["信仰", "加護", "神", "祈り"],
    "escape": ["脱出", "逃げ", "逃が"],
}

JUSTIFICATION_KEYWORDS = {
    "survival": ["生きるため", "助かるため", "飢えるより"],
    "fear": ["怖", "脅され", "恐"],
    "revenge": ["復讐", "報い", "仕返し"],
    "greater_good": ["皆のため", "より大きな目的", "全体のため", "秩序のため"],
    "loyalty": ["仲間のため", "味方のため", "忠義", "恩"],
    "desire": ["欲しい", "欲望", "惚れ", "執着"],
    "greed": ["金のため", "儲け", "利得", "得を"],
    "humiliation": ["屈辱", "舐められ", "恥"],
    "faith": ["神のため", "信仰のため", "祈りのため"],
    "coercion": ["脅されて", "強いられ", "命令された"],
}

ROLE_SLOT_ALIAS_HINTS = {
    "slot_truce_warden": ["停戦執行官", "執行官", "停戦役", "停戦の役人"],
    "slot_cantor": ["祈鐘士", "祈り手", "鐘の祈り手", "祈鐘の座"],
    "slot_ledger_clerk": ["目録官", "記録役", "帳場", "帳付け役", "帳簿役"],
    "slot_tunnel_guide": ["坑路案内", "坑道案内", "坑路の案内", "坑道の案内"],
    "slot_quartermaster": ["宿場差配", "差配", "宿場役", "配給役"],
    "slot_relic_keeper": ["遺物番", "遺物の番", "保管役", "遺物保管役"],
    "slot_oath_scribe": ["誓紙検分官", "検分官", "誓紙役", "誓いの検分役"],
    "slot_ferrymaster": ["渡し守", "舟守", "舟番", "舟頭", "渡し場の役"],
    "slot_ward_mason": ["封継師", "封師", "結界継ぎ手", "封路の継ぎ手"],
}

LIKELY_COSTS_BY_FAMILY = {
    "theft": ["発覚時の信用低下", "報復の危険"],
    "fraud": ["帳尻の不整合拡大", "制度への不信"],
    "smuggling": ["抜け道の露見", "検問強化"],
    "coercion": ["関係悪化", "報復の火種"],
    "violence": ["報復連鎖", "場の緊張悪化"],
    "sacrilege": ["信仰の分裂", "汚れの残留"],
    "taboo_ritual": ["封印負担の増加", "禁忌の痕の残留"],
    "deception": ["疑いの拡散", "証言の食い違い"],
    "sabotage": ["復旧負担", "監視強化"],
    "escape": ["追跡再開", "保護網の弱体化"],
    "concealment": ["後からの発覚", "証拠の欠落への疑い"],
    "social_manipulation": ["噂の反転", "関係悪化"],
    "other": ["思わぬ副作用", "次の疑い"],
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, float(value))), 1)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(text: str) -> str:
    normalized = " ".join(str(text or "").replace("\n", " ").split())
    replacements = {
        "改竄": "改ざん",
        "隠ぺい": "隠蔽",
        "けしかける": "けしかけ",
        "言いくるめる": "言いくるめ",
        "持ち去る": "持ち出す",
        "抜け出す": "抜け出",
    }
    for before, after in replacements.items():
        normalized = normalized.replace(before, after)
    return normalized


def _clean_summary(text: str, limit: int = 240) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:16]


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def _weighted_keyword_score(text: str, keywords: Iterable[str]) -> float:
    score = 0.0
    for keyword in keywords:
        if not keyword or keyword not in text:
            continue
        score += max(1.0, len(keyword) * 0.35)
    return score


def _match_catalog_tags(text: str, entry_map: Mapping[str, Mapping[str, Any]]) -> List[str]:
    matches: List[str] = []
    for entry_id, entry in entry_map.items():
        label = _text(entry.get("label_ja"))
        typical_forms = [_text(value) for value in entry.get("typical_forms", [])]
        if label and label.replace("・", "") in text.replace("・", ""):
            matches.append(entry_id)
            continue
        if any(form and form in text for form in typical_forms):
            matches.append(entry_id)
    return matches


def _supplement_tags(text: str, current: List[str], hints: Mapping[str, List[str]], entry_map: Mapping[str, Mapping[str, Any]]) -> List[str]:
    merged = list(current)
    for entry_id, keywords in hints.items():
        if entry_id in entry_map and _contains_any(text, keywords) and entry_id not in merged:
            merged.append(entry_id)
    return merged


def _action_family_from_text(text: str, vice_tags: List[str], taboo_tags: List[str]) -> str:
    scores: Dict[str, float] = {family: 0.0 for family in ACTION_FAMILY_KEYWORDS}
    for family, keywords in ACTION_FAMILY_KEYWORDS.items():
        scores[family] += _weighted_keyword_score(text, keywords)
    if taboo_tags:
        scores["taboo_ritual"] += len(taboo_tags) * 3.5
        if {"relic_defilement", "sanctuary_violation", "false_sanctification"} & set(taboo_tags):
            scores["sacrilege"] += 3.0
    if vice_tags:
        for tag in vice_tags:
            if tag in scores:
                scores[tag] += 3.0
    if _contains_any(text, ["賄賂", "袖の下", "口利き料", "見逃し料"]):
        scores["fraud"] += 2.5
        scores["coercion"] += 1.0
    if _contains_any(text, ["噂を流", "吹き込", "印象操作", "空気を作"]):
        scores["social_manipulation"] += 3.0
    if _contains_any(text, ["死体", "墓", "遺体", "骨"]):
        scores["taboo_ritual"] += 2.8
    if _contains_any(text, ["封印", "結界", "禁書", "禁譜"]) and _contains_any(text, ["こじ開け", "剥が", "使", "唱"]):
        scores["taboo_ritual"] += 4.5
    best_family = max(scores, key=scores.get)
    if scores[best_family] <= 0.0:
        return "other"
    return best_family


def _derive_base_intent_type(action_family: str, secrecy_level: float, violence_level: float, taboo_level: float) -> str:
    if action_family in {"violence", "sacrilege", "taboo_ritual"}:
        return "intervene"
    if action_family in {"coercion", "social_manipulation", "illicit_relationship"}:
        return "speak"
    if action_family in {"fraud", "deception", "sabotage"}:
        return "inspect"
    if action_family in {"theft", "smuggling", "escape", "concealment"}:
        return "observe" if secrecy_level >= 58 else "inspect"
    if violence_level >= 62 or taboo_level >= 65:
        return "intervene"
    if secrecy_level >= 65:
        return "observe"
    return "inspect"


def _extract_means(text: str, action_family: str) -> List[str]:
    means: List[str] = []
    for keyword, label in MEANS_KEYWORDS:
        if keyword in text and label not in means:
            means.append(label)
    family_defaults = {
        "theft": "物の持ち出し",
        "fraud": "書類の細工",
        "smuggling": "非正規の搬送",
        "coercion": "圧力をかける",
        "violence": "実力行使",
        "sacrilege": "聖なるものへの干渉",
        "taboo_ritual": "禁じ手の儀礼",
        "deception": "虚偽の筋立て",
        "sabotage": "機能の妨害",
        "escape": "離脱経路の確保",
        "concealment": "痕跡隠し",
        "social_manipulation": "言葉で流れを変える",
        "other": "独自の手段",
    }
    if not means:
        means.append(family_defaults[action_family])
    return means[:8]


def _extract_expected_gains(text: str, action_family: str) -> List[str]:
    gains: List[str] = []
    for gain, keywords in GAIN_KEYWORDS.items():
        if _contains_any(text, keywords):
            gains.append(gain)
    if not gains:
        default = {
            "theft": "wealth",
            "fraud": "status",
            "smuggling": "survival",
            "coercion": "power",
            "violence": "survival",
            "sacrilege": "power",
            "taboo_ritual": "power",
            "deception": "secrecy",
            "sabotage": "escape",
            "escape": "escape",
            "concealment": "secrecy",
            "social_manipulation": "status",
            "other": "survival",
        }
        gains.append(default[action_family])
    return gains[:5]


def _extract_justifications(text: str) -> List[str]:
    frames = [frame for frame, keywords in JUSTIFICATION_KEYWORDS.items() if _contains_any(text, keywords)]
    return frames[:4] or ["survival"]


def _likely_costs(action_family: str, taboo_tags: List[str]) -> List[str]:
    costs = list(LIKELY_COSTS_BY_FAMILY.get(action_family, LIKELY_COSTS_BY_FAMILY["other"]))
    if taboo_tags:
        costs.append("禁忌の痕が残る")
    return costs[:8]


def _detect_levels(text: str, vice_tags: List[str], taboo_tags: List[str], action_family: str) -> tuple[float, float, float]:
    secrecy = 28.0
    violence = 6.0
    taboo = 4.0
    if _contains_any(text, ["夜", "裏", "密か", "隠", "気づかれず", "こっそり", "痕跡を消"]):
        secrecy += 32.0
    if action_family in {"theft", "smuggling", "deception", "concealment", "fraud"}:
        secrecy += 12.0
    if _contains_any(text, ["拝借", "抜き取", "すり替", "裏帳面", "偽名"]):
        secrecy += 8.0
    if _contains_any(text, ["殴", "斬", "刺", "殺", "脅", "武器", "血"]):
        violence += 48.0
    if action_family in {"violence", "coercion", "sabotage"}:
        violence += 18.0
    if _contains_any(text, ["恫喝", "締め上げ", "拉致"]):
        violence += 10.0
    if taboo_tags:
        taboo += len(taboo_tags) * 18.0
    if _contains_any(text, ["禁", "魂", "輪廻", "聖遺物", "神託", "聖域", "封印", "結界"]):
        taboo += 22.0
    if _contains_any(text, ["浄化済みと偽", "偽の聖別", "死体", "墓荒らし", "真名を消", "昇神", "霊縛"]):
        taboo += 16.0
    return _clamp(secrecy), _clamp(violence), _clamp(taboo)


def _short_name(display_name: str, role_label: str) -> str:
    return display_name.replace(role_label, "", 1).strip() if display_name.startswith(role_label) else display_name


def _target_role_slots(text: str, campaign_state: Mapping[str, Any], action_family: str) -> List[str]:
    slots: List[str] = []
    npcs = campaign_state.get("npcs", {})
    for raw_slot_id, npc in npcs.items():
        slot_id = canonical_role_slot_id(str(raw_slot_id))
        aliases = {
            _text(npc.get("roleLabel")),
            _text(npc.get("displayName")),
            _short_name(_text(npc.get("displayName")), _text(npc.get("roleLabel"))),
        }
        aliases.update(ROLE_SLOT_ALIAS_HINTS.get(slot_id, []))
        if any(alias and alias in text for alias in aliases):
            slots.append(slot_id)
    if slots:
        return list(dict.fromkeys(slots))[:6]

    defaults = {
        "theft": ["slot_ledger_clerk", "slot_quartermaster", "slot_ferrymaster"],
        "fraud": ["slot_ledger_clerk", "slot_oath_scribe", "slot_truce_warden"],
        "smuggling": ["slot_ferrymaster", "slot_tunnel_guide", "slot_quartermaster"],
        "coercion": ["slot_truce_warden", "slot_ledger_clerk", "slot_oath_scribe"],
        "violence": ["slot_truce_warden", "slot_tunnel_guide"],
        "sacrilege": ["slot_cantor", "slot_relic_keeper", "slot_ward_mason"],
        "taboo_ritual": ["slot_cantor", "slot_relic_keeper", "slot_ward_mason"],
        "deception": ["slot_ledger_clerk", "slot_quartermaster", "slot_oath_scribe"],
        "sabotage": ["slot_tunnel_guide", "slot_relic_keeper", "slot_ward_mason"],
        "escape": ["slot_tunnel_guide", "slot_quartermaster", "slot_ferrymaster"],
        "concealment": ["slot_ledger_clerk"],
        "social_manipulation": ["slot_truce_warden", "slot_cantor", "slot_quartermaster"],
        "other": [],
    }
    return [slot_id for slot_id in defaults.get(action_family, []) if slot_id in npcs][:6]


def _target_institutions(
    text: str,
    world_state: Mapping[str, Any],
    scene_context: Optional[Any],
) -> List[str]:
    resolved_world = world_state.get("resolved_world", {})
    institutions = resolved_world.get("institutions", {})
    matches = []
    for institution_id, institution in institutions.items():
        label = _text(institution.get("label_ja"))
        if label and label in text:
            matches.append(institution_id)
    if matches:
        return list(dict.fromkeys(matches))[:6]
    if scene_context is not None and getattr(scene_context, "focus_institution", None):
        institution = getattr(scene_context, "focus_institution")
        institution_id = _text(institution.get("institution_id"))
        if institution_id:
            return [institution_id]
    return []


def _target_regions(
    text: str,
    world_state: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    scene_context: Optional[Any],
) -> List[str]:
    resolved_world = world_state.get("resolved_world", {})
    regions = resolved_world.get("regions", {})
    matches = []
    for region_id, region in regions.items():
        label = _text(region.get("label_ja"))
        if label and label in text:
            matches.append(region_id)
    if matches:
        return list(dict.fromkeys(matches))[:6]
    for current in (campaign_state.get("hub"), campaign_state.get("dungeon")):
        region_id = _text((current or {}).get("regionId"))
        if region_id and region_id not in matches:
            matches.append(region_id)
    if scene_context is not None:
        for region_id in getattr(scene_context, "focus_node", {}).get("regions", []):
            if region_id not in matches:
                matches.append(region_id)
    return matches[:6]


def _goal_text(summary: str, action_family: str) -> str:
    templates = {
        "theft": "必要な物証を確保し、相手より先に流れを握る",
        "fraud": "記録や印を操作し、責任の流れを有利に曲げる",
        "smuggling": "表の流れを避けて、必要なものを通す",
        "coercion": "圧をかけて相手の判断をこちらへ寄せる",
        "violence": "実力で障害を押しのけ、場の主導権を奪う",
        "sacrilege": "聖なる境界を越えてでも必要な結果を取る",
        "taboo_ritual": "禁じ手を使ってでも状況を動かす",
        "deception": "虚偽の筋で相手の見立てをずらす",
        "sabotage": "仕組みを崩して相手の手を遅らせる",
        "escape": "捕捉を避けて安全圏へ抜ける",
        "concealment": "痕跡を伏せて追及を遅らせる",
        "social_manipulation": "言葉と噂で場の判断を揺らす",
        "other": summary,
    }
    return _clean_summary(templates.get(action_family, summary), 160)


def _summary_anchor(
    world_state: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    target_role_slots: Iterable[str],
    target_institutions: Iterable[str],
    target_regions: Iterable[str],
) -> str:
    npcs = campaign_state.get("npcs", {})
    for role_slot_id in target_role_slots:
        npc = npcs.get(role_slot_id)
        if npc and _text(npc.get("roleLabel")):
            return _text(npc.get("roleLabel"))
    institutions = world_state.get("resolved_world", {}).get("institutions", {})
    for institution_id in target_institutions:
        institution = institutions.get(institution_id)
        if institution and _text(institution.get("label_ja")):
            return _text(institution.get("label_ja"))
    regions = world_state.get("resolved_world", {}).get("regions", {})
    for region_id in target_regions:
        region = regions.get(region_id)
        if region and _text(region.get("label_ja")):
            return _text(region.get("label_ja"))
    for current in (campaign_state.get("hub"), campaign_state.get("dungeon")):
        if current and _text(current.get("label")):
            return _text(current.get("label"))
    return "場の裏側"


def _player_summary(
    action_family: str,
    anchor: str,
    vice_tags: List[str],
    taboo_tags: List[str],
) -> str:
    templates = {
        "theft": f"{anchor}まわりの物証を抜き取ろうとした",
        "fraud": f"{anchor}まわりの記録を作り替えようとした",
        "smuggling": f"{anchor}まわりで表に出せない荷を通そうとした",
        "coercion": f"{anchor}まわりの判断を脅しで曲げようとした",
        "violence": f"{anchor}まわりで実力に訴えた",
        "illicit_relationship": f"{anchor}まわりで私的なつながりを利用しようとした",
        "sacrilege": f"{anchor}まわりの聖なる境界に手をかけた",
        "taboo_ritual": f"{anchor}まわりで禁じ手の儀礼を試した",
        "deception": f"{anchor}まわりへ偽りの筋を流した",
        "sabotage": f"{anchor}まわりの仕組みを崩そうとした",
        "escape": f"{anchor}まわりから追跡を逃れようとした",
        "concealment": f"{anchor}まわりの痕跡を伏せようとした",
        "social_manipulation": f"{anchor}まわりに噂を流して判断を揺らそうとした",
        "other": f"{anchor}まわりへ裏の手を伸ばした",
    }
    summary = templates.get(action_family, templates["other"])
    if "blackmail" in vice_tags:
        summary = f"{anchor}まわりの弱みを材料に判断を曲げようとした"
    elif "bribery_corruption" in vice_tags:
        summary = f"{anchor}まわりで見逃しと便宜を買おうとした"
    elif taboo_tags and action_family not in {"sacrilege", "taboo_ritual"}:
        summary = f"{anchor}まわりで禁じ手を交えた裏工作を試した"
    elif vice_tags and action_family == "other":
        summary = f"{anchor}まわりで後ろ暗い手を試した"
    return _clean_summary(summary, 120)


def parse_free_action(
    text: str,
    world_state: Mapping[str, Any],
    campaign_state: Mapping[str, Any],
    scene_context: Optional[Any] = None,
) -> Dict[str, Any]:
    cleaned_text = _clean_summary(text, 400)
    if not cleaned_text:
        raise FreeActionError("自由入力は空にできません。")

    vice_tags = _supplement_tags(cleaned_text, _match_catalog_tags(cleaned_text, VICE_ENTRY_MAP), VICE_KEYWORD_HINTS, VICE_ENTRY_MAP)
    taboo_tags = _supplement_tags(cleaned_text, _match_catalog_tags(cleaned_text, TABOO_ENTRY_MAP), TABOO_KEYWORD_HINTS, TABOO_ENTRY_MAP)
    action_family = _action_family_from_text(cleaned_text, vice_tags, taboo_tags)
    if not vice_tags and action_family in VICE_ENTRY_MAP:
        vice_tags = [action_family]
    if not taboo_tags and action_family in TABOO_ENTRY_MAP:
        taboo_tags = [action_family]
    secrecy_level, violence_level, taboo_level = _detect_levels(cleaned_text, vice_tags, taboo_tags, action_family)
    base_intent_type = _derive_base_intent_type(action_family, secrecy_level, violence_level, taboo_level)
    target_role_slots = _target_role_slots(cleaned_text, campaign_state, action_family)
    if not target_role_slots:
        exposure_ranked = sorted(
            campaign_state.get("npcs", {}).values(),
            key=lambda npc: len(exposure_profile_for_slot(npc).get("viceIds", [])) + len(exposure_profile_for_slot(npc).get("tabooIds", [])),
            reverse=True,
        )
        target_role_slots = [canonical_role_slot_id(npc["npcId"]) for npc in exposure_ranked[:1]]
    target_institutions = _target_institutions(cleaned_text, world_state, scene_context)
    target_regions = _target_regions(cleaned_text, world_state, campaign_state, scene_context)

    session = campaign_state.get("session", {})
    seed = world_state.get("resolved_world", {}).get("world", {}).get("seed", "seed")
    digest = _hash_text(cleaned_text)
    action_id = f"fa_{seed}_s{int(session.get('sessionNumber', 1)):02d}_t{int(session.get('turnInSession', 1)):02d}_{digest[:8]}"
    summary_anchor = _summary_anchor(world_state, campaign_state, target_role_slots, target_institutions, target_regions)
    player_summary = _player_summary(action_family, summary_anchor, vice_tags, taboo_tags)

    return {
        "action_id": action_id,
        "session": {
            "session_number": int(session.get("sessionNumber", 1)),
            "turn_counter": int(session.get("turnCounter", 1)),
            "phase_label": _text(session.get("phaseLabel")) or "偵察局面",
        },
        "source": {
            "input_mode": "free_text",
            "player_summary": player_summary,
            "raw_text_hash": digest,
            "persist_raw_text": False,
        },
        "normalized_intent": {
            "action_family": action_family,
            "intent_type": "custom_action",
            "goal": _goal_text(cleaned_text, action_family),
            "means": _extract_means(cleaned_text, action_family),
            "target_role_slots": target_role_slots[:6],
            "target_institutions": target_institutions[:6],
            "target_regions": target_regions[:6],
            "secrecy_level": secrecy_level,
            "violence_level": violence_level,
            "taboo_level": taboo_level,
            "vice_tags": vice_tags[:8],
            "taboo_tags": taboo_tags[:8],
            "expected_gains": _extract_expected_gains(cleaned_text, action_family),
            "likely_costs": _likely_costs(action_family, taboo_tags),
            "justification_frames": _extract_justifications(cleaned_text),
        },
        "derived_intent_type": base_intent_type,
    }
