from __future__ import annotations

from typing import Any

from .canonical_naming_sources import export_canonical_naming_sources


_PLACE_ANNOTATIONS = {
    "hub": "《宿場拠点》",
    "dungeon": "《封印遺跡》",
    "region": "《地方》",
}

_STARTER_SOURCE_TERM_OVERRIDES = {
    "澱舟泊（テイシュウ）": {
        "surface_name": "ルアカイの渡し場",
        "display_text": "ルアカイの渡し場",
        "annotation": "《湿地の渡し場》",
    },
    "灰杭関所（エンショウ）": {
        "surface_name": "カルドルンの関所",
        "display_text": "カルドルンの関所",
        "annotation": "《灰杭の関所》",
    },
    "環鈴宿（カンレイ）": {
        "surface_name": "セルミアの宿場",
        "display_text": "セルミアの宿場",
        "annotation": "《街道の宿場》",
    },
    "白灰坑路": {
        "surface_name": "白灰坑道",
        "display_text": "白灰坑道",
        "annotation": "《白灰の坑道》",
    },
    "逆塩祠洞": {
        "surface_name": "塩鏡の祠洞",
        "display_text": "塩鏡の祠洞",
        "annotation": "《塩鏡の祠洞》",
    },
    "鏡泥封庫": {
        "surface_name": "泥鏡の封庫",
        "display_text": "泥鏡の封庫",
        "annotation": "《泥鏡の封庫》",
    },
    "灰縁辺州": {
        "surface_name": "灰の辺境州",
        "display_text": "灰の辺境州",
        "annotation": "《地方》",
    },
    "白祠宗務会": {
        "surface_name": "白祠教会",
        "display_text": "白祠教会",
        "annotation": "《勢力》",
    },
    "瘴冠魔域": {
        "surface_name": "瘴冠領",
        "display_text": "瘴冠領",
        "annotation": "《勢力》",
    },
    "灰縁侯族": {
        "surface_name": "灰縁侯",
        "display_text": "灰縁侯",
        "annotation": "《勢力》",
    },
    "賠償履行争議": {
        "surface_name": "賠償争議",
        "display_text": "賠償争議",
        "annotation": "《局面》",
    },
    "供給割当破綻": {
        "surface_name": "配給割当の崩れ",
        "display_text": "配給割当の崩れ",
        "annotation": "《局面》",
    },
    "供給割当破綻への介入": {
        "surface_name": "配給割当の崩れへの対処",
        "display_text": "配給割当の崩れへの対処",
        "annotation": "《依頼》",
    },
    "人質交換破綻": {
        "surface_name": "人質交換の決裂",
        "display_text": "人質交換の決裂",
        "annotation": "《局面》",
    },
    "人質交換破綻への介入": {
        "surface_name": "人質交換の決裂への対処",
        "display_text": "人質交換の決裂への対処",
        "annotation": "《依頼》",
    },
    "捕虜交換破綻": {
        "surface_name": "捕虜交換の決裂",
        "display_text": "捕虜交換の決裂",
        "annotation": "《局面》",
    },
    "捕虜交換破綻への介入": {
        "surface_name": "捕虜交換の決裂への対処",
        "display_text": "捕虜交換の決裂への対処",
        "annotation": "《依頼》",
    },
    "共同封印義務逸脱": {
        "surface_name": "共同封印の取り決め破り",
        "display_text": "共同封印の取り決め破り",
        "annotation": "《局面》",
    },
    "共同封印義務逸脱への介入": {
        "surface_name": "共同封印の取り決め破りへの対処",
        "display_text": "共同封印の取り決め破りへの対処",
        "annotation": "《依頼》",
    },
    "共同深層回収破綻": {
        "surface_name": "共同深層回収の決裂",
        "display_text": "共同深層回収の決裂",
        "annotation": "《局面》",
    },
    "共同深層回収破綻への介入": {
        "surface_name": "共同深層回収の決裂への対処",
        "display_text": "共同深層回収の決裂への対処",
        "annotation": "《依頼》",
    },
    "婚姻条約継承危機": {
        "surface_name": "婚姻条約の継承危機",
        "display_text": "婚姻条約の継承危機",
        "annotation": "《局面》",
    },
    "婚姻条約継承危機への介入": {
        "surface_name": "婚姻条約の継承危機への対処",
        "display_text": "婚姻条約の継承危機への対処",
        "annotation": "《依頼》",
    },
    "巡礼路襲撃事件": {
        "surface_name": "巡礼路襲撃",
        "display_text": "巡礼路襲撃",
        "annotation": "《局面》",
    },
    "巡礼路襲撃事件への介入": {
        "surface_name": "巡礼路襲撃への対処",
        "display_text": "巡礼路襲撃への対処",
        "annotation": "《依頼》",
    },
    "朝貢納付拒絶": {
        "surface_name": "朝貢の拒否",
        "display_text": "朝貢の拒否",
        "annotation": "《局面》",
    },
    "朝貢納付拒絶への介入": {
        "surface_name": "朝貢の拒否への対処",
        "display_text": "朝貢の拒否への対処",
        "annotation": "《依頼》",
    },
    "黒封使節の遅着": {
        "surface_name": "使節の到着遅れ",
        "display_text": "使節の到着遅れ",
        "annotation": "《事件》",
    },
    "渡し検札の食い違い": {
        "surface_name": "渡し場の検札違い",
        "display_text": "渡し場の検札違い",
        "annotation": "《事件》",
    },
    "環鈴宿の目録欠損": {
        "surface_name": "宿場目録の欠け",
        "display_text": "宿場目録の欠け",
        "annotation": "《事件》",
    },
    "灰杭誓紙の裂け目": {
        "surface_name": "誓紙の裂け目",
        "display_text": "誓紙の裂け目",
        "annotation": "《事件》",
    },
    "白灰坑路の再鳴動": {
        "surface_name": "坑道の再鳴動",
        "display_text": "坑道の再鳴動",
        "annotation": "《事件》",
    },
    "灰杭関所の滞列": {
        "surface_name": "関所前の滞り",
        "display_text": "関所前の滞り",
        "annotation": "《事件》",
    },
    "逆塩祠洞の逆唱": {
        "surface_name": "祠洞の逆さ祈り",
        "display_text": "祠洞の逆さ祈り",
        "annotation": "《事件》",
    },
    "鏡泥封庫の逆照": {
        "surface_name": "封庫の照り返し",
        "display_text": "封庫の照り返し",
        "annotation": "《事件》",
    },
    "渡し荷札の滲み": {
        "surface_name": "荷札の滲み",
        "display_text": "荷札の滲み",
        "annotation": "《事件》",
    },
    "白祠宗務会＝封泥環宗教同盟": {
        "surface_name": "白祠教会と封泥環の宗教同盟",
        "display_text": "白祠教会と封泥環の宗教同盟",
        "annotation": "《制度》",
    },
    "灰縁侯族＝瘴冠魔域属国化盟約": {
        "surface_name": "灰縁侯と瘴冠領の属国盟約",
        "display_text": "灰縁侯と瘴冠領の属国盟約",
        "annotation": "《制度》",
    },
    "白祠宗務会＝瘴冠魔域封鎖令": {
        "surface_name": "白祠教会による瘴冠領封鎖令",
        "display_text": "白祠教会による瘴冠領封鎖令",
        "annotation": "《制度》",
    },
    "白祠宗務会＝瘴冠魔域聖戦布告": {
        "surface_name": "白祠教会による瘴冠領聖戦布告",
        "display_text": "白祠教会による瘴冠領聖戦布告",
        "annotation": "《制度》",
    },
    "穀冠王国＝灰縁侯族不可侵条約": {
        "surface_name": "穀冠王国と灰縁侯の不可侵条約",
        "display_text": "穀冠王国と灰縁侯の不可侵条約",
        "annotation": "《制度》",
    },
    "穀冠王国＝黒鎚採鉱盟通商盟約": {
        "surface_name": "穀冠王国と黒鎚採鉱盟の通商盟約",
        "display_text": "穀冠王国と黒鎚採鉱盟の通商盟約",
        "annotation": "《制度》",
    },
}


def _normalize_role_display(label: str, role_label: str) -> tuple[str, str]:
    name = str(label or "").strip()
    role = str(role_label or "").strip()
    if not name or not role:
        return name, name
    if name.startswith(role):
        bare_name = name[len(role) :].strip()
        if bare_name:
            return bare_name, f"{bare_name}〈{role}〉"
    return name, name


def _annotation_for_entry(category: str, raw: dict[str, Any]) -> str:
    if category == "place":
        subtype = str(raw.get("subtype") or "").strip().lower()
        return _PLACE_ANNOTATIONS.get(subtype, "《地点》")
    if category == "person":
        role_label = str(raw.get("role_label") or "").strip()
        return f"《{role_label}》" if role_label else "《人物》"
    if category == "equipment":
        subtitle = str(raw.get("subtitle") or "").strip()
        slot = str(raw.get("slot") or "").strip()
        if subtitle:
            return f"《{subtitle.split(' / ')[0]}》"
        if slot:
            return f"《{slot}》"
        subtype = str(raw.get("subtype") or "").strip()
        return f"《{subtype}》" if subtype else "《装備》"
    if category == "item":
        subtype = str(raw.get("subtype") or "").strip()
        group = str(raw.get("group") or "").strip()
        if subtype == "spell":
            return "《魔法》"
        if group:
            return f"《{group}》"
        if subtype:
            return f"《{subtype}》"
        return "《道具》"
    if category == "event":
        subtype = str(raw.get("subtype") or "").strip()
        if subtype in {"active_node", "historical_node"}:
            return "《局面》"
        if subtype == "quest_offer":
            return "《依頼》"
        return "《事件》"
    if category == "faction":
        return "《勢力》"
    if category == "institution":
        return "《制度》"
    return "《名称候補》"


def _notes_for_entry(raw: dict[str, Any]) -> str:
    for key in ("note", "description", "stakes", "subtitle"):
        text = str(raw.get(key) or "").strip()
        if text:
            return text
    return ""


def _scaffold_entry(category: str, raw: dict[str, Any]) -> dict[str, Any]:
    current_label = str(raw.get("label") or "").strip()
    role_label = str(raw.get("role_label") or "").strip()
    if category == "person":
        surface_name, display_text = _normalize_role_display(current_label, role_label)
    else:
        surface_name = current_label
        display_text = current_label

    entry = {
        "surface_name": surface_name,
        "display_text": display_text,
        "category": category,
        "race": "",
        "ui_only": True,
        "source_terms": [str(term).strip() for term in raw.get("source_terms", []) if str(term).strip()],
        "semantic_tags": [],
        "annotation": _annotation_for_entry(category, raw),
        "priority": 50,
        "source_label": "canonical_source_scaffold",
        "current_label": current_label,
    }
    notes = _notes_for_entry(raw)
    if notes:
        entry["notes"] = notes
    return entry


def scaffold_external_lexicon_from_canonical_sources(payload: dict[str, Any]) -> dict[str, Any]:
    groups = payload.get("groups", {})
    entries: list[dict[str, Any]] = []
    for category in ("place", "person", "event", "faction", "institution", "equipment", "item"):
        for raw in groups.get(category, []):
            if not isinstance(raw, dict):
                continue
            entries.append(_scaffold_entry(category, raw))

    return {
        "schema_version": "1.0",
        "name": "Canonical_UI_Naming_Lexicon_Draft",
        "seed": payload.get("seed"),
        "seasons": payload.get("seasons"),
        "archetype": payload.get("archetype"),
        "entry_count": len(entries),
        "entries": entries,
    }


def build_initial_ui_naming_lexicon(payload: dict[str, Any]) -> dict[str, Any]:
    draft = scaffold_external_lexicon_from_canonical_sources(payload)
    entries: list[dict[str, Any]] = []
    for entry in draft["entries"]:
        next_entry = dict(entry)
        for source_term in next_entry.get("source_terms", []):
            override = _STARTER_SOURCE_TERM_OVERRIDES.get(str(source_term))
            if override:
                next_entry.update(override)
                break
        next_entry["source_label"] = "initial_ui_naming_lexicon"
        entries.append(next_entry)

    return {
        "schema_version": "1.0",
        "name": "Initial_UI_Naming_Lexicon",
        "seed": draft.get("seed"),
        "seasons": draft.get("seasons"),
        "archetype": draft.get("archetype"),
        "entry_count": len(entries),
        "entries": entries,
    }


def generate_scaffold_external_lexicon(
    *,
    seed: int = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
) -> dict[str, Any]:
    payload = export_canonical_naming_sources(
        seed=seed,
        seasons=seasons,
        archetype=archetype,
    )
    return scaffold_external_lexicon_from_canonical_sources(payload)


def generate_initial_ui_naming_lexicon(
    *,
    seed: int = 1729,
    seasons: int = 10,
    archetype: str = "balanced",
) -> dict[str, Any]:
    payload = export_canonical_naming_sources(
        seed=seed,
        seasons=seasons,
        archetype=archetype,
    )
    return build_initial_ui_naming_lexicon(payload)
