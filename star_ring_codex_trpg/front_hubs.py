from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List
import json
import random

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


def _build_context(world_state: Dict[str, Any], display: Dict[str, Any]) -> Dict[str, Any]:
    lexicon = _equipment_lexicon()
    race_id = _race_id(world_state)
    naming = _race_naming_profile(race_id)
    design = _race_design_profile(race_id)
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
        "palette": palette,
        "materials": materials,
        "motifs": motifs,
        "event_terms": _event_terms(display),
        "rng": _seed_rng(world_state, "front_hubs"),
    }


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
        "Scene/backdrop: isolated item on a transparent or near-black background\n"
        "Style/medium: painterly high-fidelity dark fantasy item art, austere sacred motifs, original game icon, not branded\n"
        "Composition/framing: centered square icon, full silhouette visible, readable at small size\n"
        "Lighting/mood: moody warm rim light, bronze and ash atmosphere\n"
        f"Color palette: {palette_text}\n"
        f"Materials/textures: {material_text}\n"
        f"Constraints: include motifs {motif_text}; no text; no watermark; preserve a clear icon silhouette\n"
        "Avoid: clutter, extra hands, UI frames, duplicate objects\n"
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


def _equipment_slots(world_state: Dict[str, Any], display: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = _build_context(world_state, display)
    protagonist = ctx["protagonist"]
    naming = ctx["naming"]
    attr_cfg = ctx["attr_cfg"]
    weapon_cfg = ctx["weapon_cfg"]
    materials = ctx["materials"]
    palette = ctx["palette"]
    rng = ctx["rng"]

    race_prefix = rng.choice(naming["prefixes"])
    race_motif = rng.choice(naming["motifs"])
    race_title = rng.choice(naming["artifact_titles"])
    oath = rng.choice(naming["oaths"])
    event_term = rng.choice(ctx["event_terms"])
    offhand_term = f"{event_term}の封灯" if event_term.endswith("検札") else f"{event_term}検札の封灯"
    attr_motif = rng.choice(attr_cfg["motifs"])
    combat = round(float(protagonist.get("skills", {}).get("combat", 50.0)), 1)
    ritual = round(float(protagonist.get("skills", {}).get("ritual", 50.0)), 1)
    authority = round(float(protagonist.get("skills", {}).get("authority", 50.0)), 1)

    return [
        _equipment_item(
            slot_id="main_hand",
            slot_label="右手武器",
            name=f"{race_prefix}の{rng.choice(attr_cfg['epithets'])}{rng.choice(weapon_cfg['formal'])}《{race_title}》",
            subtitle=f"{weapon_cfg['label_ja']} / {attr_cfg['label_ja']}",
            rarity="royal",
            rarity_label=_rarity_label(rng, "royal"),
            stats=[f"攻撃 {int(92 + combat)}", f"信仰補正 {int(28 + ritual / 2)}", "戦技: 誓約の返し"],
            flavor=f"{event_term}の列が崩れぬよう、抜くべき時だけ抜かれる誓剣。刃の曇りは所有者の躊躇を映す。",
            materials=materials,
            motifs=[race_motif, event_term, attr_motif],
            palette=palette,
            kind="weapon",
        ),
        _equipment_item(
            slot_id="off_hand",
            slot_label="左手聖具",
            name=offhand_term,
            subtitle="聖具 / 灯具",
            rarity="sacred",
            rarity_label=_rarity_label(rng, "sacred"),
            stats=[f"防御 {int(38 + authority / 2)}", f"詠唱補助 {int(20 + ritual / 2)}", "固有: 露見抑制"],
            flavor="灯火を掲げると、誓紙と検札の筋だけが白く浮く。隠し事まで暴く代わりに、持ち手の迷いも照らす。",
            materials=materials,
            motifs=["灯", "十字", event_term],
            palette=palette,
            kind="focus",
        ),
        _equipment_item(
            slot_id="head",
            slot_label="頭防具",
            name=f"{race_prefix}の旅冠",
            subtitle="頭防具 / 旅装",
            rarity="crafted",
            rarity_label=_rarity_label(rng, "crafted"),
            stats=["物理 21", "精神 26", "発見力 +8"],
            flavor="王都仕立ての冠というには質素だが、正面の刻印は門をくぐる者の身分を曖昧にしない。",
            materials=materials,
            motifs=[race_motif, "冠", event_term],
            palette=palette,
            kind="armor",
        ),
        _equipment_item(
            slot_id="body",
            slot_label="胴防具",
            name=f"{event_term}渡りの外套",
            subtitle="胴防具 / 外套",
            rarity="crafted",
            rarity_label=_rarity_label(rng, "crafted"),
            stats=["物理 42", "信仰 36", "耐候 +14"],
            flavor="潮気と灰を吸って色を変える外套。背の紋は所属ではなく、通してよい者を示すために縫われた。",
            materials=materials,
            motifs=[event_term, race_motif, "外套"],
            palette=palette,
            kind="armor",
        ),
        _equipment_item(
            slot_id="arms",
            slot_label="腕防具",
            name=f"{oath}の手甲",
            subtitle="腕防具 / 手甲",
            rarity="uncommon",
            rarity_label=_rarity_label(rng, "uncommon"),
            stats=["物理 18", "器用 12", "手順補正 +6"],
            flavor="誓紙を扱う手が震えないよう、内側に細い補強が仕込まれている。約定を破ると先に冷たくなる。",
            materials=materials,
            motifs=["鍵", "誓約", race_motif],
            palette=palette,
            kind="armor",
        ),
        _equipment_item(
            slot_id="legs",
            slot_label="脚防具",
            name=f"{event_term}渡靴",
            subtitle="脚防具 / 旅靴",
            rarity="mundane",
            rarity_label=_rarity_label(rng, "mundane"),
            stats=["機動 24", "静歩 18", "湿地適性 +10"],
            flavor="泥と板橋の境目で音を殺すため、踵の革だけが異様に柔らかい。逃げ足ではなく踏みとどまりのための靴。",
            materials=materials,
            motifs=["舟", "波紋", event_term],
            palette=palette,
            kind="armor",
        ),
    ]


def _relics(world_state: Dict[str, Any], display: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = _build_context(world_state, display)
    palette = ctx["palette"]
    materials = ctx["materials"]
    event_term = ctx["event_terms"][0]
    return [
        {
            "itemId": "relic_white_oath",
            "name": "白き誓環",
            "subtitle": "Relic / covenant",
            "rarity": "sacred",
            "rarityLabel": "Consecrated",
            "flavorText": f"{event_term}の場で誓いを立てた者の吐息を閉じ込めた環。嘘には光らず、保留には鈍く応じる。",
            "iconKey": "relic_white_oath",
            "assetState": "queued",
            "assetPrompt": _icon_prompt(
                label="白き誓環",
                category="relic icon",
                materials=materials,
                motifs=[event_term, "環", "十字"],
                palette=palette,
                flavor="誓いの熱と白金の冷たさが同居する遺物",
            ),
            "showcasePrompt": _showcase_prompt(
                label="白き誓環",
                category="relic illustration",
                materials=materials,
                motifs=[event_term, "環", "十字"],
                palette=palette,
                flavor=f"{event_term}の場で誓いを立てた者の吐息を閉じ込めた環。",
            ),
        },
        {
            "itemId": "relic_marsh_key",
            "name": "澱舟の鍵印",
            "subtitle": "Relic / passage",
            "rarity": "royal",
            "rarityLabel": "Warden-kept",
            "flavorText": "渡し場の優先を決める古い鍵印。門そのものではなく、人が譲った順番を覚えている。",
            "iconKey": "relic_marsh_key",
            "assetState": "queued",
            "assetPrompt": _icon_prompt(
                label="澱舟の鍵印",
                category="relic icon",
                materials=materials,
                motifs=["鍵", "舟", event_term],
                palette=palette,
                flavor="湿地の塩気を帯びた、古い通行印の遺物",
            ),
            "showcasePrompt": _showcase_prompt(
                label="澱舟の鍵印",
                category="relic illustration",
                materials=materials,
                motifs=["鍵", "舟", event_term],
                palette=palette,
                flavor="渡し場の優先を決める古い鍵印。",
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
            "name": "検塩小瓶",
            "category": "consumable",
            "quantity": 4,
            "rarity": "common",
            "description": "札と印泥の筋を見分けるための塩液。光にかざすと偽装の継ぎ目が浮く。",
            "motifs": ["塩", "瓶", "白滴"],
        },
        {
            "itemId": "consumable_heal_broth",
            "name": "白粥の湯筒",
            "category": "consumable",
            "quantity": 2,
            "rarity": "common",
            "description": "負傷者列に配るための薄い回復湯。戦場より避難列で価値がある。",
            "motifs": ["湯", "粥", "布巻き"],
        },
        {
            "itemId": "tool_ledger_lens",
            "name": "帳面透写レンズ",
            "category": "tool",
            "quantity": 1,
            "rarity": "rare",
            "description": "上書きされた帳面の筆圧差を見るためのレンズ。急いで消した数字ほどよく見える。",
            "motifs": ["帳面", "レンズ", "線刻"],
        },
        {
            "itemId": "quest_ferry_ticket",
            "name": current_event.get("label", "渡し札の写し"),
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
        {"groupId": "consumables", "label": "Consumables", "items": [item for item in items if item["category"] == "consumable"]},
        {"groupId": "tools", "label": "Tools", "items": [item for item in items if item["category"] == "tool"]},
        {"groupId": "quest", "label": "Quest Items", "items": [item for item in items if item["category"] == "quest_item"]},
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
    slots = _equipment_slots(world_state, display)
    relics = _relics(world_state, display)
    spells = _attuned_spells(world_state, display)
    inventory = _inventory(world_state, display)
    protagonist = _protagonist(world_state)
    equip_load_current = round((float(protagonist.get("skills", {}).get("combat", 50.0)) * 0.34) + 19.0, 1)
    equip_load_max = round(56.0 + float(protagonist.get("skills", {}).get("stewardship", 50.0)) * 0.12, 1)
    featured_item = slots[0]
    asset_entries = _asset_entries(slots=slots, relics=relics, inventory=inventory, spells=spells)

    equipment_hub = {
        "screenTitle": "Equipment",
        "loadoutName": f"{actor.get('label', '旅人')}の旅装",
        "equipLoad": {
            "current": equip_load_current,
            "max": equip_load_max,
            "state": "medium" if equip_load_current / equip_load_max < 0.7 else "heavy",
        },
        "slots": slots,
        "featuredItem": featured_item,
        "relics": relics,
        "attunedSpells": spells,
        "flavorNotes": [
            "誓約と通行のために整えた旅装。正面から威圧するより、秩序がまだ残っていると信じさせるための装い。",
            "金属の光り方を抑え、印章と縫い目だけを目立たせる。敵を屠るためではなく、順番を崩さないための装備構成。",
        ],
    }
    inventory_hub = inventory
    asset_prompt_pack = {
        "batchTitle": "equipment-and-item-icons",
        "visualDirection": "somber dark fantasy item rendering, restrained sacred motifs, readable icon silhouettes, codex plate art for key gear",
        "entryCount": len(asset_entries),
        "entries": asset_entries,
        "exportCommand": "py -3 scripts/export_front_asset_prompt_pack.py --seed 1729",
    }
    return {
        "equipmentHub": equipment_hub,
        "inventoryHub": inventory_hub,
        "assetPromptPack": asset_prompt_pack,
    }
