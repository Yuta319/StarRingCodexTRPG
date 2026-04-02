from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List
import json
import random

from .character_creation import LOADOUT_OPTIONS
from .paths import CANONICAL_ROOT, REFERENCE_ROOT


def _load_json(path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _equipment_lexicon() -> Dict[str, Any]:
    return _load_json(CANONICAL_ROOT / "equipment_name_lexicon_v1.json")


@lru_cache(maxsize=1)
def _race_designs() -> Dict[str, Dict[str, Any]]:
    payload = _load_json(CANONICAL_ROOT / "TRPG_Race_Attribute_Culture_Motif_Design.json")
    return {entry["id"]: entry for entry in payload["races"]}


@lru_cache(maxsize=1)
def _magic_catalog() -> Dict[str, Any]:
    return _load_json(REFERENCE_ROOT / "trpg_magic_system_for_codex.normalized.json")


ATTRIBUTE_TO_MAGIC = {
    "light": "光／回復",
    "earth": "地／金",
    "wind": "風／雷",
    "fire": "火",
    "water": "水／氷",
    "dark": "闇／精神",
}

ATTRIBUTE_TO_GEAR = {
    "火": "火",
    "水": "潮",
    "風": "風",
    "地": "石",
    "光": "光",
    "闇": "影",
}

WEAPON_TO_GEAR = {
    "直剣": "直剣",
    "大剣": "大剣",
    "刀": "刀",
    "槍": "槍",
    "斧": "斧",
    "戦槌": "戦槌",
    "弓": "弓",
    "短剣": "短剣",
    "杖": "杖",
    "魔導書": "魔導書",
}

WEAPON_KEYWORDS = [
    ("大剣", ["大剣", "両手剣", "グレートソード"]),
    ("直剣", ["直剣", "片手剣", "剣士"]),
    ("刀", ["刀", "太刀", "侍"]),
    ("槍", ["槍", "ランス", "ポールアーム"]),
    ("斧", ["斧", "アックス"]),
    ("戦槌", ["戦槌", "ハンマー", "メイス"]),
    ("弓", ["弓", "ボウ", "弓使い", "アーチャー"]),
    ("短剣", ["短剣", "ダガー", "双短剣", "暗器"]),
    ("杖", ["杖", "スタッフ", "魔術師", "術士"]),
    ("魔導書", ["魔導書", "グリモア", "書板", "書物"]),
]

OFFHAND_BY_WEAPON = {
    "大剣": ("左手印具", "印具"),
    "直剣": ("左手灯具", "灯"),
    "刀": ("左手札具", "札具"),
    "槍": ("左手旗具", "旗具"),
    "斧": ("左手鎖具", "鎖具"),
    "戦槌": ("左手護灯", "護灯"),
    "弓": ("左手索具", "索具"),
    "短剣": ("左手鍵具", "鍵具"),
    "杖": ("左手書板", "書板"),
    "魔導書": ("左手写本", "写本"),
}

EVENT_TO_GEAR = {
    "渡し": "渡し",
    "検札": "検札",
    "検疫": "検札",
    "誓": "誓い",
    "塩": "塩",
    "封": "封印",
    "舟": "舟",
    "灰": "灰",
}


def _dedupe(values: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def _seed_rng(world_state: Dict[str, Any], salt: str) -> random.Random:
    world = world_state.get("world", {})
    seed = int(world.get("seed", 1729))
    mixed = f"{seed}:{salt}:{world_state.get('calendar_year', 0)}:{world_state.get('season_index', 0)}"
    return random.Random(mixed)


def _protagonist(world_state: Dict[str, Any]) -> Dict[str, Any]:
    return world_state.get("resolved_world", {}).get("protagonist", {})


def _event_terms(display: Dict[str, Any]) -> List[str]:
    current_event = display.get("currentEvent") or {}
    active_node = display.get("activeNode") or {}
    raw = " ".join(
        filter(
            None,
            [
                current_event.get("label"),
                current_event.get("summaryText"),
                active_node.get("title"),
                active_node.get("questTitle"),
            ],
        )
    )
    mapping = [
        ("渡し", "渡し"),
        ("検疫", "検札"),
        ("誓", "誓"),
        ("塩", "塩"),
        ("封", "封"),
        ("舟", "舟"),
        ("灰", "灰"),
    ]
    terms = [label for needle, label in mapping if needle in raw]
    return terms or ["旅", "白耀", "境"]


def _race_id(world_state: Dict[str, Any]) -> str:
    race_id = (_protagonist(world_state).get("race") or "human").strip().lower()
    return race_id or "human"


def _race_naming_profile(race_id: str) -> Dict[str, Any]:
    profiles = _equipment_lexicon()["race_lexicon"]
    return profiles.get(race_id, profiles["human"])


def _race_design_profile(race_id: str) -> Dict[str, Any]:
    profiles = _race_designs()
    return profiles.get(race_id, profiles["human"])


def _loadout_profile(world_state: Dict[str, Any]) -> Dict[str, Any]:
    character_profile = _protagonist(world_state).get("character_profile") or {}
    loadout_id = str(character_profile.get("loadout") or "oathblade").strip().lower()
    return LOADOUT_OPTIONS.get(loadout_id, LOADOUT_OPTIONS["oathblade"])


def _build_context(world_state: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    lexicon = _equipment_lexicon()
    race_id = _race_id(world_state)
    naming = _race_naming_profile(race_id)
    design = _race_design_profile(race_id)
    loadout = _loadout_profile(world_state)
    primary_attribute = design.get("primary_attribute") or naming.get("primary_attribute") or "light"
    primary_weapon = design.get("primary_weapon") or naming.get("primary_weapon") or "straight_sword"
    attr_cfg = lexicon["attribute_lexicon"].get(primary_attribute, lexicon["attribute_lexicon"]["light"])
    weapon_cfg = lexicon["weapon_lexicon"].get(primary_weapon, lexicon["weapon_lexicon"]["straight_sword"])
    visual_rules = design.get("visual_design_rules", {})
    motif_rules = design.get("motif_design_rules", {})
    palette = _dedupe(
        list(visual_rules.get("primary_colors", []))
        + list(visual_rules.get("accent_colors", []))
        + ["黒", "琥珀", "白金"]
    )[:5]
    materials = _dedupe(
        list(attr_cfg.get("materials", []))
        + list(naming.get("materials", []))
        + list(visual_rules.get("materials", []))
    )[:5]
    motifs = _dedupe(
        list(naming.get("motifs", []))
        + list(attr_cfg.get("motifs", []))
        + list(motif_rules.get("frequent_motifs", []))
    )[:6]
    return {
        "lexicon": lexicon,
        "protagonist": _protagonist(world_state),
        "naming": naming,
        "design": design,
        "attr_cfg": attr_cfg,
        "weapon_cfg": weapon_cfg,
        "loadout": loadout,
        "palette": palette,
        "materials": materials,
        "motifs": motifs,
        "event_terms": _event_terms(display),
        "rng": _seed_rng(world_state, "front_hubs"),
    }


def _gear_term(term: str) -> str:
    raw = str(term or "").strip()
    for needle, label in EVENT_TO_GEAR.items():
        if needle in raw:
            return label
    return "旅"


def _gear_attribute(attr_cfg: Dict[str, Any]) -> str:
    return ATTRIBUTE_TO_GEAR.get(str(attr_cfg.get("label_ja") or "").strip(), "Radiant")


def _gear_weapon(weapon_cfg: Dict[str, Any]) -> str:
    return WEAPON_TO_GEAR.get(str(weapon_cfg.get("label_ja") or "").strip(), "剣")


def _profile_keywords_text(protagonist: Dict[str, Any]) -> str:
    profile = protagonist.get("character_profile") or {}
    return " ".join(
        filter(
            None,
            [
                profile.get("appearanceNotes"),
                profile.get("reinterpretationNotes"),
                profile.get("sourceTitle"),
                profile.get("sourceName"),
                profile.get("loadoutLabel"),
                profile.get("styleLabel"),
            ],
        )
    )


def _tailored_weapon_and_offhand(protagonist: Dict[str, Any], fallback_weapon: str) -> tuple[str, str, str]:
    raw = _profile_keywords_text(protagonist)
    for weapon_label, needles in WEAPON_KEYWORDS:
        if any(needle in raw for needle in needles):
            offhand_slot, offhand_base = OFFHAND_BY_WEAPON.get(weapon_label, ("左手補助具", "補助具"))
            return weapon_label, offhand_slot, offhand_base
    offhand_slot, offhand_base = OFFHAND_BY_WEAPON.get(fallback_weapon, ("左手補助具", "補助具"))
    return fallback_weapon, offhand_slot, offhand_base


def _pick_spell_set(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    catalog = _magic_catalog()
    design = ctx["design"]
    wanted = [ATTRIBUTE_TO_MAGIC.get(design.get("primary_attribute", "light"), "光／回復")]
    for affinity in design.get("secondary_affinities", [])[:2]:
        wanted.append(ATTRIBUTE_TO_MAGIC.get(affinity, "光／回復"))

    spells: List[Dict[str, Any]] = []
    for attribute_label in wanted:
        attribute_spells = [spell for spell in catalog["preset_spells"] if spell.get("attribute") == attribute_label]
        spells.extend(attribute_spells[:2])

    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for spell in spells:
        spell_id = spell.get("id")
        if not spell_id or spell_id in seen:
            continue
        seen.add(spell_id)
        deduped.append(spell)
    return deduped[:4]


def _rarity_label(rng: random.Random, rarity: str) -> str:
    fallback = {
        "common": ["旅用", "現場支給"],
        "uncommon": ["現場仕立て", "実戦仕立て"],
        "rare": ["秘蔵", "継承"],
    }
    titles = _equipment_lexicon().get("rarity_titles", {}).get(rarity) or fallback.get(rarity) or [rarity]
    return rng.choice(titles)


def _icon_prompt(
    *,
    label: str,
    category: str,
    materials: List[str],
    motifs: List[str],
    palette: List[str],
    flavor: str,
) -> str:
    motif_text = ", ".join(motifs[:3])
    material_text = ", ".join(materials[:3])
    palette_text = ", ".join(palette[:4])
    return (
        "Use case: stylized-concept\n"
        f"Asset type: {category} inventory icon\n"
        f"Primary request: original dark fantasy icon art for {label}\n"
        "Scene/backdrop: isolated item on transparent background or a very dark neutral void only\n"
        "Style/medium: painterly high-fidelity dark fantasy item art, austere sacred motifs, original game icon, not branded\n"
        "Composition/framing: centered square icon, single object only, full silhouette visible, readable at small size\n"
        "Lighting/mood: moody warm rim light, bronze and ash atmosphere\n"
        f"Color palette: {palette_text}\n"
        f"Materials/textures: {material_text}\n"
        f"Constraints: include motifs {motif_text}; absolutely no text, letters, runes, tags, seals with writing, hanging parchment labels, watermark, hands, or extra props; preserve a clear icon silhouette\n"
        "Avoid: clutter, UI frames, duplicate objects, readable symbols, banners with lettering\n"
        f"Flavor anchor: {flavor}"
    )


def _showcase_prompt(
    *,
    label: str,
    category: str,
    materials: List[str],
    motifs: List[str],
    palette: List[str],
    flavor: str,
) -> str:
    motif_text = ", ".join(motifs[:4])
    material_text = ", ".join(materials[:4])
    palette_text = ", ".join(palette[:5])
    return (
        "Use case: stylized-concept\n"
        f"Asset type: {category} codex illustration\n"
        f"Primary request: original dark fantasy showcase art for {label}\n"
        "Scene/backdrop: museum-like void, faint ash and dust, no character hands visible\n"
        "Style/medium: monumental dark fantasy item portrait, somber sacred atmosphere, painterly realism, restrained and elegant, not branded\n"
        "Composition/framing: vertical 3:4 item showcase, single subject, centered but slightly elevated, readable silhouette and engraved details\n"
        "Lighting/mood: low-key directional light with warm metallic rim, solemn and ancient\n"
        f"Color palette: {palette_text}\n"
        f"Materials/textures: {material_text}\n"
        f"Constraints: make motifs legible: {motif_text}; no text overlay; no watermark; no human figure; preserve silhouette clarity\n"
        "Avoid: busy background, modern props, floating UI, duplicate items\n"
        f"Flavor anchor: {flavor}"
    )


def _equipment_item(
    *,
    slot_id: str,
    slot_label: str,
    name: str,
    subtitle: str,
    rarity: str,
    rarity_label: str,
    stats: List[str],
    flavor: str,
    materials: List[str],
    motifs: List[str],
    palette: List[str],
    kind: str,
) -> Dict[str, Any]:
    icon_key = f"{slot_id}_{kind}".replace("-", "_")
    return {
        "slotId": slot_id,
        "slotLabel": slot_label,
        "itemId": f"eq_{slot_id}",
        "name": name,
        "subtitle": subtitle,
        "kind": kind,
        "rarity": rarity,
        "rarityLabel": rarity_label,
        "stats": stats,
        "flavorText": flavor,
        "iconKey": icon_key,
        "iconFilename": f"{icon_key}.png",
        "assetState": "queued",
        "assetPrompt": _icon_prompt(
            label=name,
            category=kind,
            materials=materials,
            motifs=motifs,
            palette=palette,
            flavor=flavor,
        ),
        "showcasePrompt": _showcase_prompt(
            label=name,
            category=kind,
            materials=materials,
            motifs=motifs,
            palette=palette,
            flavor=flavor,
        ),
    }


def _focus_item(
    *,
    slot_id: str,
    slot_label: str,
    name: str,
    subtitle: str,
    rarity: str,
    rarity_label: str,
    stats: List[str],
    flavor: str,
    materials: List[str],
    motifs: List[str],
    palette: List[str],
) -> Dict[str, Any]:
    item = _equipment_item(
        slot_id=slot_id,
        slot_label=slot_label,
        name=name,
        subtitle=subtitle,
        rarity=rarity,
        rarity_label=rarity_label,
        stats=stats,
        flavor=flavor,
        materials=materials,
        motifs=motifs,
        palette=palette,
        kind="focus",
    )
    item["assetPrompt"] = (
        "Use case: stylized-concept\n"
        f"Asset type: focus inventory icon\n"
        f"Primary request: original dark fantasy reliquary lantern icon for {name}\n"
        "Scene/backdrop: isolated single lantern on transparent background or very dark neutral void only\n"
        "Style/medium: painterly high-fidelity dark fantasy item icon, sacred and austere, not branded\n"
        "Composition/framing: centered square icon, single lantern only, readable silhouette, no accessories orbiting around it\n"
        "Lighting/mood: internal ember glow, warm rim light, solemn chapel gloom\n"
        f"Color palette: {', '.join(palette[:4])}\n"
        f"Materials/textures: {', '.join(materials[:3])}\n"
        f"Constraints: include motifs {', '.join(motifs[:3])}; absolutely no text, letters, runes, paper slips, cloth tags, hanging parchment, seals with writing, emblems with characters, hands, chains, or extra props; preserve clean icon silhouette\n"
        "Avoid: banners, scrolls, labels, books, duplicate objects, readable symbols, UI frames\n"
        f"Flavor anchor: {flavor}"
    )
    return item


def _equipment_slots(world_state: Dict[str, Any], display: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = _build_context(world_state, display)
    protagonist = ctx["protagonist"]
    naming = ctx["naming"]
    attr_cfg = ctx["attr_cfg"]
    weapon_cfg = ctx["weapon_cfg"]
    loadout = ctx["loadout"]
    character_profile = protagonist.get("character_profile") or {}
    materials = ctx["materials"]
    palette = ctx["palette"]
    rng = ctx["rng"]

    race_motif = rng.choice(naming["motifs"])
    event_term = rng.choice(ctx["event_terms"])
    attr_motif = rng.choice(attr_cfg["motifs"])
    gear_term = _gear_term(event_term)
    gear_attr = _gear_attribute(attr_cfg)
    fallback_weapon = _gear_weapon(weapon_cfg)
    is_tailored = str(character_profile.get("loadout") or "").strip().lower() == "tailored"
    gear_weapon = str(loadout.get("weapon_label") or fallback_weapon)
    offhand_slot_label = str(loadout.get("offhand_slot_label") or "左手聖具")
    offhand_base = str(loadout.get("offhand_base") or "灯")
    if is_tailored:
        gear_weapon, offhand_slot_label, offhand_base = _tailored_weapon_and_offhand(protagonist, fallback_weapon)
    loadout_themes = _dedupe(list(loadout.get("themes", [])) + [race_motif, attr_motif, event_term])
    combat = round(float(protagonist.get("skills", {}).get("combat", 50.0)), 1)
    ritual = round(float(protagonist.get("skills", {}).get("ritual", 50.0)), 1)
    authority = round(float(protagonist.get("skills", {}).get("authority", 50.0)), 1)

    return [
        _equipment_item(
            slot_id="main_hand",
            slot_label="右手武器",
            name=f"{gear_term}の{gear_weapon}",
            subtitle=f"{gear_weapon} / {gear_attr}",
            rarity="royal",
            rarity_label=_rarity_label(rng, "royal"),
            stats=[f"攻撃 {int(92 + combat)}", f"信仰補正 {int(28 + ritual / 2)}", "戦技: 誓約の返し"],
            flavor=f"{loadout['summary']} {event_term}の局面で抜くために整えられており、目立ちすぎず、それでも役割が通る形に収められている。",
            materials=materials,
            motifs=loadout_themes[:3],
            palette=palette,
            kind="weapon",
        ),
        _focus_item(
            slot_id="off_hand",
            slot_label=offhand_slot_label,
            name=f"{gear_term}の{offhand_base}",
            subtitle=f"{offhand_base} / 補助具",
            rarity="sacred",
            rarity_label=_rarity_label(rng, "sacred"),
            stats=[f"防御 {int(38 + authority / 2)}", f"詠唱補助 {int(20 + ritual / 2)}", "固有: 露見抑制"],
            flavor=f"{loadout['summary']} {event_term}の手順を見失わないための補助具で、見落としを減らす一方、持ち手の迷いまでは隠せない。",
            materials=materials,
            motifs=loadout_themes[1:4],
            palette=palette,
        ),
        _equipment_item(
            slot_id="head",
            slot_label="頭防具",
            name="旅人の冠",
            subtitle="頭防具 / 冠",
            rarity="crafted",
            rarity_label=_rarity_label(rng, "crafted"),
            stats=["物理 21", "精神 26", "発見力 +8"],
            flavor="王都の役人が使う冠を簡素にした品。門をくぐる者の立場を、ひと目で分かるようにしている。",
            materials=materials,
            motifs=[race_motif, "冠", event_term],
            palette=palette,
            kind="armor",
        ),
        _equipment_item(
            slot_id="body",
            slot_label="胴防具",
            name=f"{gear_term}の外套",
            subtitle="胴防具 / 外套",
            rarity="crafted",
            rarity_label=_rarity_label(rng, "crafted"),
            stats=["物理 42", "信仰 36", "耐候 +14"],
            flavor="潮気と灰をはじく外套。背の紋は所属章ではなく、通行を許された者だと示すための印だ。",
            materials=materials,
            motifs=[event_term, race_motif, "外套"],
            palette=palette,
            kind="armor",
        ),
        _equipment_item(
            slot_id="arms",
            slot_label="腕防具",
            name="誓いの手甲",
            subtitle="腕防具 / 手甲",
            rarity="uncommon",
            rarity_label=_rarity_label(rng, "uncommon"),
            stats=["物理 18", "器用 12", "手順補正 +6"],
            flavor="誓紙を扱うときに手元がぶれないよう補強された手甲。誓いを破る場では、冷えが先に指へ返る。",
            materials=materials,
            motifs=["鍵", "誓約", race_motif],
            palette=palette,
            kind="armor",
        ),
        _equipment_item(
            slot_id="legs",
            slot_label="脚防具",
            name="湿地の長靴",
            subtitle="脚防具 / 長靴",
            rarity="mundane",
            rarity_label=_rarity_label(rng, "mundane"),
            stats=["機動 24", "静歩 18", "湿地適性 +10"],
            flavor="泥と板橋で足音を抑える長靴。逃げるためではなく、ぬかるみで踏みとどまるために作られている。",
            materials=materials,
            motifs=["舟", "波紋", event_term],
            palette=palette,
            kind="armor",
        ),
    ]


def _apply_equipment_overrides(slots: List[Dict[str, Any]], character_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    overrides = character_profile.get("starterEquipmentOverrides") or {}
    if not isinstance(overrides, dict):
        return slots
    patched: List[Dict[str, Any]] = []
    for item in slots:
        slot_id = str(item.get("slotId") or "").strip()
        patch = overrides.get(slot_id) if slot_id else None
        if isinstance(patch, dict):
            patched.append({**item, **patch})
        else:
            patched.append(item)
    return patched


def _relics(world_state: Dict[str, Any], display: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = _build_context(world_state, display)
    palette = ctx["palette"]
    materials = ctx["materials"]
    event_term = ctx["event_terms"][0]
    return [
        {
            "itemId": "relic_white_oath",
            "name": "白誓の指輪",
            "subtitle": "遺物 / 誓約",
            "rarity": "sacred",
            "rarityLabel": "聖別",
            "flavorText": f"{event_term}の場で交わした約束を確かめるための指輪。嘘の約束には反応せず、保留になった取り決めの前でだけ鈍く光る。",
            "iconKey": "relic_white_oath",
            "iconFilename": "relic_white_oath.png",
            "assetState": "queued",
            "assetPrompt": _icon_prompt(
                label="白誓の指輪",
                category="relic icon",
                materials=materials,
                motifs=[event_term, "環", "十字"],
                palette=palette,
                flavor="誓いの熱と白金の冷たさが同居する遺物",
            ),
            "showcasePrompt": _showcase_prompt(
                label="白誓の指輪",
                category="relic illustration",
                materials=materials,
                motifs=[event_term, "環", "十字"],
                palette=palette,
                flavor=f"{event_term}の場で交わした約束を確かめるための指輪。",
            ),
        },
        {
            "itemId": "relic_marsh_key",
            "name": "渡し場の鍵印",
            "subtitle": "遺物 / 通行印",
            "rarity": "royal",
            "rarityLabel": "管理保管",
            "flavorText": "渡し場の順番を記録する古い通行印。誰が先を譲り、誰が割り込んだかを見分けるために使われてきた。",
            "iconKey": "relic_marsh_key",
            "iconFilename": "relic_marsh_key.png",
            "assetState": "queued",
            "assetPrompt": _icon_prompt(
                label="渡し場の鍵印",
                category="relic icon",
                materials=materials,
                motifs=["鍵", "舟", event_term],
                palette=palette,
                flavor="湿地の塩気を帯びた、古い通行印の遺物",
            ),
            "showcasePrompt": _showcase_prompt(
                label="渡し場の鍵印",
                category="relic illustration",
                materials=materials,
                motifs=["鍵", "舟", event_term],
                palette=palette,
                flavor="渡し場の優先順を記録する古い鍵印。",
            ),
        },
    ]


def _inventory(world_state: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    ctx = _build_context(world_state, display)
    palette = ctx["palette"]
    materials = ctx["materials"]
    current_event = display.get("currentEvent") or {}
    item_specs = [
        {
            "itemId": "consumable_salt_vial",
            "name": "塩見の小瓶",
            "category": "consumable",
            "quantity": 4,
            "rarity": "common",
            "description": "札と印泥の筋を見分けるための塩液。光にかざすと偽装の継ぎ目が浮く。",
            "motifs": ["塩", "瓶", "白滴"],
        },
        {
            "itemId": "consumable_heal_broth",
            "name": "回復湯",
            "category": "consumable",
            "quantity": 2,
            "rarity": "common",
            "description": "負傷者列に配るための薄い回復湯。戦場より避難列で価値がある。",
            "motifs": ["湯", "粥", "布巻き"],
        },
        {
            "itemId": "tool_ledger_lens",
            "name": "帳面レンズ",
            "category": "tool",
            "quantity": 1,
            "rarity": "rare",
            "description": "上書きされた帳面の筆圧差を見るためのレンズ。急いで消した数字ほどよく見える。",
            "motifs": ["帳面", "レンズ", "線刻"],
        },
        {
            "itemId": "quest_ferry_ticket",
            "name": "通行札の写し",
            "category": "quest_item",
            "quantity": 1,
            "rarity": "rare",
            "description": "今回の局面そのものに紐づく記録片。次の判断を誤ると、ただの証拠ではなく火種になる。",
            "motifs": ["札", "印泥", "写し"],
        },
    ]
    items = []
    for spec in item_specs:
        items.append(
            {
                **spec,
                "iconKey": spec["itemId"],
                "iconFilename": f"{spec['itemId']}.png",
                "assetState": "queued",
                "assetPrompt": _icon_prompt(
                    label=spec["name"],
                    category=f"{spec['category']} icon",
                    materials=materials,
                    motifs=spec["motifs"],
                    palette=palette,
                    flavor=spec["description"],
                ),
            }
        )
    groups = [
        {"groupId": "consumables", "label": "消耗品", "items": [item for item in items if item["category"] == "consumable"]},
        {"groupId": "tools", "label": "道具", "items": [item for item in items if item["category"] == "tool"]},
        {"groupId": "quest", "label": "重要品", "items": [item for item in items if item["category"] == "quest_item"]},
    ]
    return {
        "capacity": {"used": 8, "max": 24},
        "quickUse": [items[0]["itemId"], items[1]["itemId"]],
        "groups": groups,
    }


def _attuned_spells(world_state: Dict[str, Any], display: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = _build_context(world_state, display)
    spells = _pick_spell_set(ctx)
    entries = []
    for spell in spells:
        entries.append(
            {
                "spellId": spell["id"],
                "name": spell["name"],
                "attribute": spell["attribute"],
                "rank": spell["rank"],
                "mpCost": spell["mp_cost"],
                "description": spell["description"],
                "iconKey": f"spell_{spell['id']}",
                "iconFilename": f"spell_{spell['id']}.png",
                "assetState": "queued",
                "assetPrompt": _icon_prompt(
                    label=spell["name"],
                    category="spell icon",
                    materials=["光粒", "印章煙", "薄金属"],
                    motifs=[spell["attribute"], spell["form"], spell["rank"]],
                    palette=["黒", "琥珀", "白金", "群青"],
                    flavor=spell["description"],
                ),
                "showcasePrompt": _showcase_prompt(
                    label=spell["name"],
                    category="spell sigil illustration",
                    materials=["光粒", "印章煙", "薄金属"],
                    motifs=[spell["attribute"], spell["form"], spell["rank"]],
                    palette=["黒", "琥珀", "白金", "群青"],
                    flavor=spell["description"],
                ),
            }
        )
    return entries


def _portrait_style_guide(ctx: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    palette_text = ", ".join(ctx["palette"][:5])
    material_text = ", ".join(ctx["materials"][:4])
    motifs_text = ", ".join(_dedupe(list(ctx["motifs"]) + list(ctx["loadout"].get("themes", [])))[:5])
    race_label = profile.get("raceLabel") or "旅人"
    style_label = profile.get("styleLabel") or "旅人"
    origin_label = profile.get("originLabel") or "どこかの出"
    loadout_label = profile.get("loadoutLabel") or ctx["loadout"]["label"]
    source_mode = profile.get("sourceMode") or "native"
    source_text = ""
    if source_mode == "reincarnated":
        source_bits = [profile.get("sourceTitle"), profile.get("sourceName")]
        source_bits = [str(bit).strip() for bit in source_bits if str(bit or "").strip()]
        if source_bits:
            source_text = f"元の面影: {' / '.join(source_bits)}。"
        else:
            source_text = "元の世界の面影を薄く残す。"
    appearance_bits = [
        str(profile.get("appearanceNotes") or "").strip(),
        str(profile.get("reinterpretationNotes") or "").strip(),
    ]
    appearance_bits = [bit for bit in appearance_bits if bit]
    house_prompt = (
        "Use case: stylized-concept\n"
        "Asset type: shared character illustration guide for protagonist and major NPCs\n"
        "Primary request: unified dark fantasy character art direction for an original TRPG cast\n"
        "Style/medium: painterly dark fantasy character illustration, restrained realism, readable face design, original game art, consistent brushwork and material rendering across all cast\n"
        "Composition/framing: clear silhouette, readable costume layers, no chaotic action pose unless explicitly requested\n"
        "Lighting/mood: low-key sacred atmosphere, warm rim light with cool shadow fill, solemn but human\n"
        f"Color palette: {palette_text}\n"
        f"Materials/textures: {material_text}\n"
        f"Constraints: world motifs should stay consistent across all characters: {motifs_text}; armor and cloth should feel handmade, ritual, weathered, and grounded; avoid mixing radically different rendering styles between characters\n"
        "Avoid: photoreal actor likeness, glossy MMO screenshot look, cel-shaded anime look, chibi proportions, comic outlines, modern streetwear, sci-fi surfaces, floating UI, text, watermark"
    )
    negative_prompt = (
        "禁止: スクリーンショットのUI/HUD/ロゴ/ギルドマーク/文字を残すこと、現代服、SF装備、過度な露出、極端なデフォルメ、"
        "別作品の衣装や紋章のそのままの複製、顔が見えない構図、複数人物、武器で顔を隠す構図、過剰な発光、過剰な被写界深度。"
    )
    reference_handling = [
        "参照画像がある場合は、顔立ちの印象、髪型の輪郭、年齢感、体格、主な配色、印象的な装飾や武器のシルエットを優先して拾う。",
        "元画像のUI、ロゴ、HUD、作品固有の紋章、文字は捨てる。服の素材や模様は、この世界の宗務会・街道・湿地・坑道の意匠へ置き換える。",
        "同じキャラクターで顔アイコンと立ち絵を作るときは、髪色、瞳色、肌色、顔の骨格、装備の主色を固定する。",
    ]
    if source_text:
        reference_handling.append(f"転生導入では、{source_text}")
    consistency_rules = [
        f"{race_label} / {style_label} / {origin_label} / {loadout_label} の情報を毎回 prompt に入れる。",
        "主要人物は全員、同じ陰影の強さと筆致で描く。",
        "顔アイコンは胸上、立ち絵は全身3/4立ちを基本にする。",
    ]
    if appearance_bits:
        consistency_rules.append(f"主人公の外見メモ: {' / '.join(appearance_bits)}")
    return {
        "styleSummary": f"{race_label}の{style_label}を基準に、全キャラクターを同じ筆致と陰影でそろえる。",
        "housePrompt": house_prompt,
        "negativePrompt": negative_prompt,
        "referenceHandling": reference_handling,
        "consistencyRules": consistency_rules,
    }


def _portrait_prompt(
    *,
    ctx: Dict[str, Any],
    profile: Dict[str, Any],
    featured_item: Dict[str, Any],
    crop: str,
) -> str:
    palette_text = ", ".join(ctx["palette"][:5])
    material_text = ", ".join(ctx["materials"][:4])
    motifs_text = ", ".join(_dedupe(list(ctx["motifs"]) + list(ctx["loadout"].get("themes", [])))[:5])
    race_label = profile.get("raceLabel") or "旅人"
    style_label = profile.get("styleLabel") or "旅人"
    origin_label = profile.get("originLabel") or "どこかの出"
    loadout_label = profile.get("loadoutLabel") or ctx["loadout"]["label"]
    subject_name = profile.get("name") or ctx["protagonist"].get("label_ja") or "主人公"
    source_mode = profile.get("sourceMode") or "native"
    source_text = ""
    if source_mode == "reincarnated":
        source_bits = [profile.get("sourceTitle"), profile.get("sourceName")]
        source_bits = [str(bit).strip() for bit in source_bits if str(bit or "").strip()]
        if source_bits:
            source_text = f"Reincarnation anchor: reinterpret a character remembered as {' / '.join(source_bits)} into this world."
        else:
            source_text = "Reincarnation anchor: preserve the feeling of a character from another world, but redesign them as an original resident of this setting."
    appearance_bits = [
        str(profile.get("appearanceNotes") or "").strip(),
        str(profile.get("reinterpretationNotes") or "").strip(),
    ]
    appearance_bits = [bit for bit in appearance_bits if bit]
    crop_line = (
        "Composition/framing: vertical 3:4 full-body standing portrait, calm 3/4 view, face visible, hands and signature gear readable"
        if crop == "full"
        else "Composition/framing: square bust portrait for face icon, shoulders to head, face clearly readable, neutral background, no gear blocking the jawline"
    )
    return (
        "Use case: stylized-concept\n"
        f"Asset type: {'protagonist standing portrait' if crop == 'full' else 'protagonist face icon'}\n"
        f"Primary request: original dark fantasy {'full-body portrait' if crop == 'full' else 'bust portrait'} of {subject_name}\n"
        "Scene/backdrop: subtle dark fantasy studio backdrop with faint ash, shrine smoke, or weathered stone atmosphere only\n"
        f"Subject: {race_label}, {style_label}, {origin_label}, equipped in {loadout_label}, signature item {featured_item.get('name') or '旅装'}\n"
        "Style/medium: painterly dark fantasy character illustration, restrained realism, original game art, unified house style shared with all NPC portraits\n"
        f"{crop_line}\n"
        "Lighting/mood: low-key solemn lighting, warm rim light and cool fill, readable face and material contrast\n"
        f"Color palette: {palette_text}\n"
        f"Materials/textures: {material_text}\n"
        f"Constraints: keep motifs coherent with this world: {motifs_text}; no extra characters; preserve a readable silhouette and costume layering; if reference images or screenshots are supplied, preserve facial impression, hairstyle silhouette, age impression, body type, signature colors, and key accessory or weapon silhouette while redesigning all materials and ornament into this world's original motifs\n"
        "Avoid: text, watermark, UI, HUD, logos, copied franchise insignia, modern zippers, sci-fi panels, chibi proportions, cel-shaded MMO screenshot look, overexposed bloom, face obscured by weapon or hair\n"
        f"Character notes: {profile.get('summaryText') or f'{race_label}の旅人'}"
        + (f"\nAppearance notes: {' / '.join(appearance_bits)}" if appearance_bits else "")
        + (f"\n{source_text}" if source_text else "")
    )


def _protagonist_portrait_entries(
    *,
    world_state: Dict[str, Any],
    display: Dict[str, Any],
    featured_item: Dict[str, Any],
) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    ctx = _build_context(world_state, display)
    protagonist = ctx["protagonist"]
    profile = protagonist.get("character_profile") or {}
    name = profile.get("name") or protagonist.get("label_ja") or "protagonist"
    slug = "".join(ch.lower() if ch.isascii() and ch.isalnum() else "_" for ch in str(name))[:32].strip("_") or "protagonist"
    guide = _portrait_style_guide(ctx, profile)
    entries = [
        _asset_entry(
            asset_id=f"{slug}_portrait",
            label=f"{name} 立ち絵",
            kind="portrait_plate",
            icon_key=f"portrait_{slug}",
            asset_state="queued",
            prompt=_portrait_prompt(ctx=ctx, profile=profile, featured_item=featured_item, crop="full"),
            suggested_filename=f"portrait_{slug}.png",
        ),
        _asset_entry(
            asset_id=f"{slug}_face",
            label=f"{name} 顔アイコン",
            kind="portrait_icon",
            icon_key=f"portrait_{slug}_face",
            asset_state="queued",
            prompt=_portrait_prompt(ctx=ctx, profile=profile, featured_item=featured_item, crop="face"),
            suggested_filename=f"portrait_{slug}_face.png",
        ),
    ]
    return entries, guide


def _asset_entry(
    *,
    asset_id: str,
    label: str,
    kind: str,
    icon_key: str,
    asset_state: str,
    prompt: str,
    suggested_filename: str,
) -> Dict[str, Any]:
    return {
        "assetId": asset_id,
        "label": label,
        "kind": kind,
        "iconKey": icon_key,
        "assetState": asset_state,
        "prompt": prompt,
        "suggestedFilename": suggested_filename,
    }


def _asset_entries(
    *,
    slots: List[Dict[str, Any]],
    relics: List[Dict[str, Any]],
    inventory: Dict[str, Any],
    spells: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for item in slots:
        entries.append(
            _asset_entry(
                asset_id=f"{item['itemId']}_icon",
                label=f"{item['name']} icon",
                kind="equipment_icon",
                icon_key=item["iconKey"],
                asset_state=item.get("assetState", "queued"),
                prompt=item["assetPrompt"],
                suggested_filename=f"{item['iconKey']}.png",
            )
        )
        entries.append(
            _asset_entry(
                asset_id=f"{item['itemId']}_plate",
                label=f"{item['name']} plate art",
                kind="equipment_plate",
                icon_key=f"{item['iconKey']}_plate",
                asset_state=item.get("assetState", "queued"),
                prompt=item["showcasePrompt"],
                suggested_filename=f"{item['iconKey']}-plate.png",
            )
        )

    for item in relics:
        entries.append(
            _asset_entry(
                asset_id=f"{item['itemId']}_icon",
                label=f"{item['name']} icon",
                kind="relic_icon",
                icon_key=item["iconKey"],
                asset_state=item.get("assetState", "queued"),
                prompt=item["assetPrompt"],
                suggested_filename=f"{item['iconKey']}.png",
            )
        )
        entries.append(
            _asset_entry(
                asset_id=f"{item['itemId']}_plate",
                label=f"{item['name']} relic art",
                kind="relic_plate",
                icon_key=f"{item['iconKey']}_plate",
                asset_state=item.get("assetState", "queued"),
                prompt=item["showcasePrompt"],
                suggested_filename=f"{item['iconKey']}-plate.png",
            )
        )

    for group in inventory["groups"]:
        for item in group["items"]:
            entries.append(
                _asset_entry(
                    asset_id=f"{item['itemId']}_icon",
                    label=f"{item['name']} icon",
                    kind=f"{item['category']}_icon",
                    icon_key=item["iconKey"],
                    asset_state=item.get("assetState", "queued"),
                    prompt=item["assetPrompt"],
                    suggested_filename=f"{item['iconKey']}.png",
                )
            )

    for item in spells:
        entries.append(
            _asset_entry(
                asset_id=f"{item['spellId']}_icon",
                label=f"{item['name']} icon",
                kind="spell_icon",
                icon_key=item["iconKey"],
                asset_state=item.get("assetState", "queued"),
                prompt=item["assetPrompt"],
                suggested_filename=f"{item['iconKey']}.png",
            )
        )
        entries.append(
            _asset_entry(
                asset_id=f"{item['spellId']}_sigil",
                label=f"{item['name']} sigil art",
                kind="spell_plate",
                icon_key=f"{item['iconKey']}_plate",
                asset_state=item.get("assetState", "queued"),
                prompt=item["showcasePrompt"],
                suggested_filename=f"{item['iconKey']}-plate.png",
            )
        )

    return entries


def build_player_front_hubs(world_state: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    actor = display.get("actorRail") or {}
    character_profile = world_state.get("resolved_world", {}).get("protagonist", {}).get("character_profile") or {}
    slots = _apply_equipment_overrides(_equipment_slots(world_state, display), character_profile)
    relics = _relics(world_state, display)
    spells = _attuned_spells(world_state, display)
    inventory = _inventory(world_state, display)
    protagonist = _protagonist(world_state)
    equip_load_current = round((float(protagonist.get("skills", {}).get("combat", 50.0)) * 0.34) + 19.0, 1)
    equip_load_max = round(56.0 + float(protagonist.get("skills", {}).get("stewardship", 50.0)) * 0.12, 1)
    featured_item = slots[0]
    asset_entries = _asset_entries(slots=slots, relics=relics, inventory=inventory, spells=spells)
    portrait_entries, portrait_guide = _protagonist_portrait_entries(
        world_state=world_state,
        display=display,
        featured_item=featured_item,
    )
    asset_entries = portrait_entries + asset_entries

    equipment_hub = {
        "screenTitle": "装備",
        "loadoutName": character_profile.get("loadoutLabel") or f"{actor.get('label', '旅人')}の装備",
        "equipLoad": {
            "current": equip_load_current,
            "max": equip_load_max,
            "state": "標準" if equip_load_current / equip_load_max < 0.7 else "重い",
        },
        "slots": slots,
        "featuredItem": featured_item,
        "relics": relics,
        "attunedSpells": spells,
        "flavorNotes": character_profile.get("starterFlavorNotes")
        or [
            f"{character_profile.get('loadoutSummary') or '通行と交渉を通すための装備です。'} 威圧よりも、役割が通る相手だと伝えることを重視しています。",
            "目立つのは印章と補強だけです。戦うためだけの重装ではなく、列と順番を崩さないための旅装として整えています。",
        ],
    }
    if character_profile.get("loadoutNameOverride"):
        equipment_hub["loadoutName"] = character_profile["loadoutNameOverride"]
    inventory_hub = inventory
    asset_prompt_pack = {
        "batchTitle": "人物・装備・所持品の画像",
        "visualDirection": "重厚で落ち着いたダークファンタジー調。人物も装備も同じ筆致と陰影でそろえ、小さく表示しても顔と形が分かることを優先します。",
        "entryCount": len(asset_entries),
        "entries": asset_entries,
        "portraitGuide": portrait_guide,
        "exportCommand": "py -3 scripts/export_front_asset_prompt_pack.py --seed 1729",
    }
    return {
        "equipmentHub": equipment_hub,
        "inventoryHub": inventory_hub,
        "assetPromptPack": asset_prompt_pack,
    }
