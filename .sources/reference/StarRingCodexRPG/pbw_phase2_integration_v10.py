from __future__ import annotations

import ast
import copy
import json
import math
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Tuple
from zipfile import ZipFile

from jsonschema import Draft202012Validator

ZIP_PATH = Path('/mnt/data/StarRingCodexRPG.zip')
OUTPUT_DIR = Path('/mnt/data/PBW_SecondPart_Integrated_v10')
PROJECT_ROOT = OUTPUT_DIR / '_project' / 'StarRingCodexRPG'


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def ensure_project_root() -> Path:
    if PROJECT_ROOT.exists():
        return PROJECT_ROOT
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    extract_root = OUTPUT_DIR / '_project'
    extract_root.mkdir(parents=True, exist_ok=True)
    with ZipFile(ZIP_PATH, 'r') as zf:
        zf.extractall(extract_root)
    if PROJECT_ROOT.exists():
        return PROJECT_ROOT
    dirs = [p for p in extract_root.iterdir() if p.is_dir()]
    if len(dirs) == 1:
        return dirs[0]
    raise FileNotFoundError('project root not found after extraction')


def slugify(text: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in text).strip('_')


def normalize_magic_asset(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'data':
                    return ast.literal_eval(node.value)
    raise ValueError('data assignment not found')


def relation_stage_from_breach(breach: float) -> str:
    if breach >= 85: return 'S6'
    if breach >= 70: return 'S5'
    if breach >= 55: return 'S4'
    if breach >= 40: return 'S3'
    if breach >= 25: return 'S2'
    if breach >= 10: return 'S1'
    return 'S0'


def rupture_stage_from_node(node: Dict[str, Any]) -> str:
    score = float(node.get('severity', 0))*0.6 + float(node.get('urgency', 0))*0.4
    if score >= 92: return 'clear_break'
    if score >= 75: return 'local_break'
    if score >= 55: return 'micro_leak'
    return 'stable'


def faction_role_label(faction_type: str) -> str:
    return {
        'state': '行政代表',
        'religion': '宗務代表',
        'guild': '利権代表',
        'tribe': '氏族代表',
        'demon_domain': '魔域代行',
    }.get(faction_type, '代表')


def rep_name(label: str, faction_type: str) -> str:
    suffix = {
        'state': 'の執達吏',
        'religion': 'の神官',
        'guild': 'の帳場頭',
        'tribe': 'の使者',
        'demon_domain': 'の代行者',
    }.get(faction_type, 'の代表')
    return f'{label}{suffix}'


def merge_race_codex(design: Dict[str, Any], background: Dict[str, Any], sim_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    bg_index = {r['id']: r for r in background['races']}
    sim_index = {}
    for rp in sim_schema.get('race_simulation_profiles', []):
        rid = rp.get('race_id') or rp.get('id')
        if rid:
            sim_index[rid] = rp
    merged = []
    for race in design['races']:
        rid = race['id']
        merged.append({
            'id': rid,
            'label_ja': race.get('label_ja', rid),
            'primary_attribute': race.get('primary_attribute'),
            'secondary_affinities': race.get('secondary_affinities', []),
            'primary_weapon': race.get('primary_weapon'),
            'visual_identity': {
                'culture_reference': race.get('culture_reference'),
                'motif_design_rules': race.get('motif_design_rules'),
                'visual_design_rules': race.get('visual_design_rules'),
            },
            'world_background': {
                'short_pitch': bg_index.get(rid, {}).get('short_pitch'),
                'biology': bg_index.get(rid, {}).get('biology'),
                'ecology': bg_index.get(rid, {}).get('ecology'),
                'philosophy': bg_index.get(rid, {}).get('philosophy'),
                'society': bg_index.get(rid, {}).get('society'),
                'culture': bg_index.get(rid, {}).get('culture'),
                'settlements': bg_index.get(rid, {}).get('settlements'),
                'economy': bg_index.get(rid, {}).get('economy'),
                'relations': bg_index.get(rid, {}).get('relations'),
                'adventuring_motives': bg_index.get(rid, {}).get('adventuring_motives'),
            },
            'simulation_overlay': (sim_index.get(rid, {}).get('simulation_genome')
                                   or sim_index.get(rid, {}).get('social_structure')
                                   or {}),
            'continuity_note': 'visual / background / simulation の三層統合',
        })
    return merged


def build_codex_registry(project_root: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    design = load_json(project_root / 'TRPG_Race_Attribute_Culture_Motif_Design.json')
    background = load_json(project_root / 'race_background_bible_v3_1.json')
    sim_schema = load_json(project_root / 'pbw_world_simulator_schema_v3.json')
    naming = load_json(project_root / 'trpg_naming_codex_pack.json')
    equipment = load_json(project_root / 'equipment_name_lexicon_v1.json')
    magic = normalize_magic_asset(project_root / 'trpg_magic_system_for_codex.json')
    style_engine = load_json(project_root / 'pbw_style_engine_v1.json')
    scene_schema = load_json(project_root / 'pbw_scene_output_schema_v1.json')

    registry = {
        'schema_version': '10.0',
        'project': 'PBW_SecondPart_Integrated',
        'purpose': '第二部向けの統合 Codex / UI / 体験設計レジストリ',
        'canonical_authorities': {
            'world_engine': 'pbw_generated_world_seed1729_v9_mythic_integration.json',
            'ui_contracts': 'pbw_ui_contracts_v1/*.schema.json',
            'scene_output_schema': 'pbw_scene_output_schema_v1.json',
            'style_engine': 'pbw_style_engine_v1.json',
            'race_visual_design': 'TRPG_Race_Attribute_Culture_Motif_Design.json',
            'race_background_bible': 'race_background_bible_v3_1.json',
            'world_simulation_schema': 'pbw_world_simulator_schema_v3.json',
            'naming_pack': 'trpg_naming_codex_pack.json',
            'equipment_lexicon': 'equipment_name_lexicon_v1.json',
            'magic_system_normalized': 'trpg_magic_system_for_codex.normalized.json',
        },
        'integration_decisions': [
            'UI 契約は pbw_ui_contracts_v1/ 配下を正本とする',
            'scene 出力は pbw_scene_output_schema_v1.json を正本とする',
            '魔法資産は Python script だったため AST 抽出で正規 JSON 化した',
            '種族は visual / background / simulation の三層統合とした',
            '世界史サンプルは v9 mythic integration を現時点の正本とした',
        ],
        'merged_races': merge_race_codex(design, background, sim_schema),
        'magic_system': magic,
        'naming_system': naming,
        'equipment_lexicon': equipment,
        'style_contract_summary': {
            'gm_rules': style_engine.get('gm_rules'),
            'npc_rules': style_engine.get('npc_rules'),
            'scene_generation_algorithm': style_engine.get('scene_generation_algorithm'),
            'scene_output_contract': style_engine.get('scene_output_contract'),
            'scene_schema_required': scene_schema.get('required', []),
        },
    }
    return registry, magic


def build_scene_output(world_data: Dict[str, Any], ui_examples: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    rw = world_data['resolved_world']
    world = rw['world']
    regions = rw['regions']
    factions = rw['factions']
    institutions = rw['institutions']
    nodes = rw['active_nodes']
    chains = rw['chains']
    cycle_state = world_data['cycle_state']

    focus_node = max(nodes.values(), key=lambda n: float(n.get('severity', 0))*0.7 + float(n.get('urgency', 0))*0.3)
    region_id = (focus_node.get('regions') or [next(iter(regions))])[0]
    region = regions[region_id]
    region_label = region.get('label_ja', region_id)

    institution = None
    institution_label = None
    if focus_node.get('source_institution_id') and focus_node['source_institution_id'] in institutions:
        institution = institutions[focus_node['source_institution_id']]
        institution_label = institution.get('label_ja', focus_node['source_institution_id'])

    faction_ids = [fid for fid in focus_node.get('factions', []) if fid in factions][:2]
    faction_labels = [factions[fid]['label_ja'] for fid in faction_ids]
    chapter_title = f"{world['calendar_name']} {world['calendar_year']}年 / {world['current_world_era']}"
    scene_title = focus_node.get('title', '事件')
    desc = focus_node.get('description', '違約の積み重ねが表面化している')
    headline = f"{region_label}で、{scene_title}の気配が表へにじみ出ている。"
    lines = [
        f"{region_label}では、{scene_title}をめぐるざわめきが、もう奥に隠れきっていない。",
        f"{'と'.join(faction_labels) if faction_labels else '複数勢力'}のあいだで責任の押し付け合いが始まり、見張りも通行人も視線を落ち着けられずにいる。",
        f"{desc}",
        f"{('もともとの約定は「' + institution_label + '」だが、その文言はもう現場を縛りきれていない。') if institution_label else '小さなほころびが、いまや一つの事件として姿を持ち始めていた。'}",
        '聞き流して通れる気配ではない。手を入れるなら、今のうちだ。',
    ]
    lines = lines[:5]
    choices_output = [
        {'id': 'observe', 'label': '現場を観察する', 'risk_hint': 'low'},
        {'id': 'speak_issuer', 'label': '代表に話す', 'relation_hint': 'issuer'},
        {'id': 'inspect_terms', 'label': '条文を確かめる', 'risk_hint': 'medium'},
        {'id': 'trace_pressure', 'label': '火種を探る', 'risk_hint': 'high'},
    ]

    npc_beats_output = []
    npc_beats_scene = []
    breach = float(institution.get('breach_risk', focus_node.get('severity', 50.0))) if institution else float(focus_node.get('severity', 50.0))
    relation_stage = relation_stage_from_breach(breach)
    rupture_stage = rupture_stage_from_node(focus_node)
    for idx, fid in enumerate(faction_ids):
        faction = factions[fid]
        display = rep_name(faction['label_ja'], faction.get('faction_type', 'state'))
        role = faction_role_label(faction.get('faction_type', 'state'))
        if idx == 0:
            first = 'こちらの出方を量るように、先に文言だけを整えてくる。'
            second = '譲歩を口にする前に、どこまで責任を切り離せるかを探っている。'
            third = 'ほんの一瞬だけ、失うものの大きさが声の底に落ちた。'
            motion = '書板を持つ指先が一度だけ止まった。'
            role_beat = '場を仕切るつもりで、一歩だけ前へ出る。'
            relation_beat = 'こちらを値踏みしながらも、追い返しきれずにいる。'
            emotion_beat = '平静を装っているが、息の継ぎ目がわずかに浅い。'
        else:
            first = '返答の前に、門と人の流れを見比べている。'
            second = 'こちらへ近づく気配はあるが、決定的な言葉だけを飲み込んだ。'
            third = '怒りよりも、長引く面倒への疲れが先ににじむ。'
            motion = '肩口の力を抜きかけて、すぐに戻した。'
            role_beat = '列の外側から、崩れた均衡を見張っている。'
            relation_beat = '介入を期待しつつも、先に頼るのは避けたがっている。'
            emotion_beat = '苛立ちより疲労が先に見える。'
        npc_beats_output.append({
            'npc_id': f'npc_{slugify(fid)}',
            'display_name': display,
            'role': role,
            'relation_stage': relation_stage,
            'rupture_stage': rupture_stage,
            'motion_cue': motion,
            'first_line': first,
            'second_line': second,
            'third_line_or_null': third,
            'subsurface_note': f"{faction['label_ja']}側の利害と保身が交錯している。",
        })
        npc_beats_scene.append({
            'npcId': f'npc_{slugify(fid)}',
            'displayName': display,
            'roleBeat': role_beat,
            'relationBeat': relation_beat,
            'emotionBeat': emotion_beat,
            'suppression': 'high' if rupture_stage != 'clear_break' else 'medium',
            'ruptureState': rupture_stage,
        })

    scene_output = {
        'player_facing': {
            'chapter_title': chapter_title,
            'scene_title': scene_title,
            'scene_record': '\n'.join(lines),
            'current_objective': ((focus_node.get('quest_offers') or [{}])[0].get('title') or f'{scene_title}への介入'),
            'choices': choices_output,
        },
        'dramatic_layers': {
            'scene_pulse': f'{region_label}で事件の熱が表面化している',
            'human_drama': {
                'label': '言い逃れと保身',
                'subtext': desc,
                'cannot_say': '誰が先に約定を食い破ったか',
            },
            'relation_cost': f"{institution_label or '既存制度'}の傷みが人間関係の負債として噴き出している",
            'memory_echo': '過去の違約や見逃しが、いまの空気を重くしている',
            'world_echo': 'この局地のほころびが、Era の圧力へ再接続されている',
        },
        'npc_beats': npc_beats_output,
        'internal': {
            'style_checks': [
                '場→焦点→差異→反応→余波の順で構成',
                '第一声=役割 / 二言目=関係 / 三言目=感情 の骨格を維持',
                '抽象語を抑え、行動と視線を先に置いた',
            ],
            'violations': [],
        },
    }

    scene_packet = {
        'sceneId': f"scene_{region_id}_{slugify(focus_node['node_id'])}",
        'locationLabel': region_label,
        'focusLabel': scene_title,
        'playerFacing': {
            'headline': headline,
            'lines': lines[:6],
            'choiceChips': [
                {'choiceId': 'observe', 'label': '現場を観察する', 'intentType': 'observe', 'emphasis': 'primary'},
                {'choiceId': 'speak', 'label': '代表に話しかける', 'intentType': 'speak'},
                {'choiceId': 'inspect', 'label': '条文を確かめる', 'intentType': 'inspect'},
                {'choiceId': 'intervene', 'label': '介入方針を決める', 'intentType': 'intervene', 'emphasis': 'risky'},
            ],
        },
        'dramaticLayers': {
            'place': region_label,
            'focus': scene_title,
            'discrepancy': desc,
            'reaction': '関係者が互いの顔色を見ながら言葉を選んでいる',
            'aftermath': '介入の仕方次第で制度・関係・Era圧まで動きうる',
        },
        'npcBeats': npc_beats_scene,
        'linkedNodeIds': [focus_node['node_id']],
        'internalFoldCount': 3,
        'renderHints': {'preferredMode': 'intervention', 'showDiceTray': True, 'highlightNodeId': focus_node['node_id']},
    }

    return scene_output, scene_packet, {
        'focus_node': focus_node,
        'focus_region': region,
        'focus_institution': institution,
        'focus_chain': chains.get(focus_node.get('chain_id')) if focus_node.get('chain_id') else None,
        'world': world,
        'cycle_state': cycle_state,
        'factions': factions,
    }


def infer_bar(base: float, bonus: float) -> Dict[str, int]:
    max_v = int(round(base + bonus))
    cur = int(round(max_v * 0.82))
    return {'current': cur, 'max': max_v}


def build_shell_snapshot(world_data: Dict[str, Any], scene_packet: Dict[str, Any], ctx: Dict[str, Any], examples: Dict[str, Any]) -> Dict[str, Any]:
    rw = world_data['resolved_world']
    world = rw['world']
    protagonist = rw['protagonist']
    cycle = world_data['cycle_state']
    final_branch = world_data['final_branch_history'][-1] if world_data.get('final_branch_history') else {}
    pantheon = world_data.get('pantheon', [])
    focus_node = ctx['focus_node']
    institution = ctx['focus_institution']
    focus_chain = ctx['focus_chain']

    shell = copy.deepcopy(examples['shellSnapshotExample'])
    shell['sessionId'] = f"sess_{world['seed']}"
    shell['generatedAt'] = f"{int(world['calendar_year']):04d}-01-01T00:00:00+09:00"
    shell['shellMode'] = 'intervention'
    shell['worldSpine'] = {
        'worldName': world['world_name'],
        'calendarName': world['calendar_name'],
        'year': int(world['calendar_year']),
        'seasonIndex': int(world['season_index']),
        'eraLabel': world['current_world_era'],
        'mainGodLabel': world['main_god_name'],
        'activeChainLabel': (focus_chain or {}).get('label_ja', '局地事件'),
        'cycleDistortion': round(float(cycle.get('distortion', 0.0)), 1),
        'divineWarPressure': round(float(cycle.get('divine_war_pressure', 0.0)), 1),
        'dominantBranch': final_branch.get('dominant_branch', '未確定'),
        'topNotes': (cycle.get('notes') or ['世界圧は推移中'])[:3],
        'syncState': 'synced',
    }
    skills = {k: round(float(v), 1) for k, v in protagonist.get('skills', {}).items()}
    tendencies = {k: round(float(v), 1) for k, v in protagonist.get('tendencies', {}).items()}
    shell['actorRail'] = {
        'actorId': 'protagonist_main',
        'label': protagonist.get('label_ja', '旅人'),
        'hp': infer_bar(90, float(skills.get('combat', 40))*0.9),
        'mp': infer_bar(40, float(skills.get('ritual', 40))*0.7),
        'exp': {'current': int(float(protagonist.get('vessel_points', 0))) % 1000, 'next': round(float(protagonist.get('vessel_points', 0)) + 320.0, 1), 'label': 'Vessel換算'},
        'vessel': round(float(protagonist.get('vessel_points', 0.0)), 1),
        'existenceTitle': protagonist.get('existence_title', '無銘の旅人'),
        'skills': skills,
        'tendencies': tendencies,
        'statuses': [
            {'statusId': 'era_pressure', 'label': world['current_world_era'], 'tone': 'warning'},
            {'statusId': 'cycle_distortion', 'label': '輪廻歪み', 'tone': 'warning'},
        ],
        'blessings': [
            {'blessingId': 'main_god_mark', 'label': f"{world['main_god_name']}の徴", 'tier': 'major', 'tone': 'holy'},
        ] + ([{'blessingId': f"pantheon_{slugify(str(pantheon[0].get('name', 'god')))}", 'label': pantheon[0].get('name', '神意'), 'tier': 'minor', 'tone': 'seal'}] if pantheon else []),
        'quickSlots': [
            {'slotIndex': 0, 'slotType': 'skill', 'label': '観察', 'actionRef': 'skill.observe'},
            {'slotIndex': 1, 'slotType': 'skill', 'label': '交渉', 'actionRef': 'skill.negotiate'},
            {'slotIndex': 2, 'slotType': 'skill', 'label': '調査', 'actionRef': 'skill.inspect'},
            {'slotIndex': 3, 'slotType': 'skill', 'label': '介入', 'actionRef': 'skill.intervene'},
        ],
    }
    beat = (scene_packet.get('npcBeats') or [{}])[0]
    shell['scenePacket'] = scene_packet
    shell['contextRail'] = {
        'companions': [{'companionId': 'cmp_record', 'label': '記録役', 'role': '観測補佐'}],
        'npcFocus': {
            'npcId': beat.get('npcId', 'npc_focus'),
            'displayName': beat.get('displayName', '代表者'),
            'role': '焦点人物',
            'relationSummary': '利害の均衡を崩さぬよう距離を取っている',
            'emotionSummary': '疲れを隠して手順を守ろうとしている',
            'suppression': beat.get('suppression', 'high'),
            'ruptureState': beat.get('ruptureState', 'micro_leak'),
        },
        'activeNode': {
            'nodeId': focus_node['node_id'],
            'title': focus_node.get('title', '事件'),
            'chainLabel': (focus_chain or {}).get('label_ja', '局地連鎖'),
            'institutionLabel': institution.get('label_ja', '') if institution else '',
            'questTitle': ((focus_node.get('quest_offers') or [{}])[0].get('title') or f"{focus_node.get('title', '事件')}への介入"),
            'severity': round(float(focus_node.get('severity', 0.0)), 1),
            'urgency': round(float(focus_node.get('urgency', 0.0)), 1),
            'stage': int(focus_node.get('stage', 1)),
            'status': focus_node.get('status', 'active'),
            'recommendedVectors': ((focus_node.get('quest_offers') or [{}])[0].get('recommended_vectors') or ['observe']),
            'projectedLegacies': focus_node.get('projected_legacies', []),
        },
        'institutionAlert': {
            'institutionId': institution.get('institution_id', '') if institution else '',
            'label': institution.get('label_ja', '') if institution else '',
            'status': institution.get('status', 'none') if institution else 'none',
            'breachRisk': round(float(institution.get('breach_risk', 0.0)), 1) if institution else 0.0,
        },
        'worldPulse': {
            'cycleDistortion': round(float(cycle.get('distortion', 0.0)), 1),
            'apotheosisFlux': round(float(cycle.get('apotheosis_flux', 0.0)), 1),
            'successionPressure': round(float(cycle.get('succession_pressure', 0.0)), 1),
            'divineWarPressure': round(float(cycle.get('divine_war_pressure', 0.0)), 1),
            'topNote': (cycle.get('notes') or ['世界圧は推移中'])[0],
        },
    }
    shell['hotbar'] = examples['shellSnapshotExample']['hotbar']
    shell['badges'] = [{'badgeId': 'quest_badge', 'target': 'node_board', 'label': '介入候補あり', 'tone': 'warn', 'count': min(9, len(rw.get('active_nodes', {})))}]
    shell['overlays'] = [{'overlayId': 'olv_intervention', 'type': 'intervention', 'state': 'hidden'}]
    shell['lastSeq'] = 2000 + int(world['season_index'])
    return shell


def build_ui_event(world_data: Dict[str, Any], shell: Dict[str, Any], examples: Dict[str, Any]) -> Dict[str, Any]:
    rw = world_data['resolved_world']
    latest = rw['resolution_history'][-1] if rw.get('resolution_history') else None
    event = copy.deepcopy(examples['uiEventExample'])
    event['seq'] = shell['lastSeq']
    event['sessionId'] = shell['sessionId']
    event['occurredAt'] = shell['generatedAt']
    if latest:
        event['eventId'] = f"evt_{slugify(latest['node_id'])}_{latest['year']}_{latest['season']}"
        event['type'] = 'node.resolution.committed'
        event['payload'] = {
            'nodeId': latest['node_id'],
            'approach': latest.get('approach', 'observe'),
            'outcome': latest.get('outcome', 'unknown'),
            'vesselDelta': round(float(latest.get('vessel_gain', 0.0)), 1),
            'realizedMedia': latest.get('realized_media', []),
        }
        event['invalidate'] = ['actorRail', 'contextRail', 'worldSpine', 'journal']
        event['uiHints'] = [
            {'type': 'toast', 'key': 'node-updated', 'level': 'success'},
            {'type': 'fx.vessel_gain', 'amount': round(float(latest.get('vessel_gain', 0.0)), 1)},
            {'type': 'highlight.hotbar', 'target': 'journal'},
        ]
    else:
        event['eventId'] = 'evt_snapshot_generated'
        event['type'] = 'snapshot.generated'
        event['payload'] = {'message': 'snapshot generated'}
        event['invalidate'] = ['worldSpine', 'contextRail']
        event['uiHints'] = [{'type': 'toast', 'key': 'snapshot-ready', 'level': 'info'}]
    return event


def validate(instance: Any, schema: Dict[str, Any]) -> List[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, err.absolute_path)) or '<root>'}: {err.message}" for err in errors]


def build_manifest(root: Path) -> Dict[str, Any]:
    return {
        'schema_version': '10.0',
        'project_root': str(root),
        'used_assets': [
            'pbw_generated_world_seed1729_v9_mythic_integration.json',
            'pbw_ui_contracts_v1/ScenePacketV1.schema.json',
            'pbw_ui_contracts_v1/ShellSnapshotRM.schema.json',
            'pbw_ui_contracts_v1/UiEventEnvelope.schema.json',
            'pbw_scene_output_schema_v1.json',
            'pbw_style_engine_v1.json',
            'race_background_bible_v3_1.json',
            'TRPG_Race_Attribute_Culture_Motif_Design.json',
            'trpg_naming_codex_pack.json',
            'equipment_name_lexicon_v1.json',
            'trpg_magic_system_for_codex.json',
            'event_display_template_checklist_codex.md',
            'pbw_codex_handoff_notes.md',
            'pbw_codex_worldbuilding_instruction_v_1.md',
        ],
        'canonical_conflict_resolution': {
            'duplicate_ui_contract_examples': 'pbw_ui_contracts_v1/pbw_ui_contracts_examples.json を優先',
            'duplicate_summaries_with_(1)': '語尾 (1) 付き summary は重複とみなし無視',
            'magic_asset_format': 'Python script を正規 JSON に変換して採用',
        },
    }


def write_report(path: Path, manifest: Dict[str, Any], validation: Dict[str, Any]) -> None:
    text = f'''# PBW 第二部統合レポート v10

## 何を統合したか
- 世界史エンジン: v1〜v9 の到達点を前提に、現時点の正本を v9 mythic integration に固定
- UI 契約: ScenePacket / ShellSnapshot / UiEventEnvelope
- Scene 出力: `pbw_scene_output_schema_v1.json`
- 文体: `pbw_style_engine_v1.json`
- 種族: visual design + background bible + world simulation overlay
- 命名: naming codex + equipment lexicon
- 魔法: Python script 資産を正規 JSON 化

## 反映した更新差分
- `pbw_ui_contracts_v1/` を HUD / read model の正本として採用
- `pbw_scene_output_schema_v1.json` を Actions 出力の正本として採用
- `race_background_bible_v3_1.json` により、種族の文化・資源依存・共存軸を統合
- `trpg_naming_codex_pack.json` / `equipment_name_lexicon_v1.json` を Codex 命名層へ統合
- `trpg_magic_system_for_codex.json` を正規化して魔法カタログとして統合

## 調整内容
- UI schema は example 構造に合わせて ScenePacket / ShellSnapshot を生成
- active node / institution / world pulse を context rail の中核に固定
- protagonist の canonical progression は vessel_points を採用
- scene 文は style engine の `場→焦点→差異→反応→余波` と NPC 三段構成へ合わせた

## バリデーション
- Scene Output: {'OK' if not validation['scene_output'] else 'NG'}
- Scene Packet: {'OK' if not validation['scene_packet'] else 'NG'}
- Shell Snapshot: {'OK' if not validation['shell_snapshot'] else 'NG'}
- UI Event Envelope: {'OK' if not validation['ui_event'] else 'NG'}

## 現時点の第二部の意味
第二部は、世界を作る段階から、世界を **UI / Codex / 出力契約 / プレイヤー体験** に接続する段階へ移った。
これにより、世界史エンジンの出力をそのまま HUD / ジャーナル / ノードボード / Codex に流し込める。

## 使った正本
{json.dumps(manifest['used_assets'], ensure_ascii=False, indent=2)}
'''.strip()
    path.write_text(text, encoding='utf-8')


def main() -> None:
    root = ensure_project_root()
    registry, normalized_magic = build_codex_registry(root)
    save_json(OUTPUT_DIR / 'trpg_magic_system_for_codex.normalized.json', normalized_magic)
    save_json(OUTPUT_DIR / 'pbw_codex_registry_v10.json', registry)

    world_data = load_json(root / 'pbw_generated_world_seed1729_v9_mythic_integration.json')
    ui_examples = load_json(root / 'pbw_ui_contracts_v1' / 'pbw_ui_contracts_examples.json')
    scene_output, scene_packet, ctx = build_scene_output(world_data, ui_examples)
    shell = build_shell_snapshot(world_data, scene_packet, ctx, ui_examples)
    ui_event = build_ui_event(world_data, shell, ui_examples)

    save_json(OUTPUT_DIR / 'pbw_scene_output_sample_v10.json', scene_output)
    save_json(OUTPUT_DIR / 'pbw_scene_packet_sample_v10.json', scene_packet)
    save_json(OUTPUT_DIR / 'pbw_shell_snapshot_sample_v10.json', shell)
    save_json(OUTPUT_DIR / 'pbw_ui_event_sample_v10.json', ui_event)

    validation = {
        'scene_output': validate(scene_output, load_json(root / 'pbw_scene_output_schema_v1.json')),
        'scene_packet': validate(scene_packet, load_json(root / 'pbw_ui_contracts_v1' / 'ScenePacketV1.schema.json')),
        'shell_snapshot': validate(shell, load_json(root / 'pbw_ui_contracts_v1' / 'ShellSnapshotRM.schema.json')),
        'ui_event': validate(ui_event, load_json(root / 'pbw_ui_contracts_v1' / 'UiEventEnvelope.schema.json')),
    }
    save_json(OUTPUT_DIR / 'pbw_validation_report_v10.json', validation)
    manifest = build_manifest(root)
    save_json(OUTPUT_DIR / 'pbw_phase2_bundle_manifest_v10.json', manifest)
    write_report(OUTPUT_DIR / 'PBW_SecondPart_Integration_Report_v10.md', manifest, validation)

if __name__ == '__main__':
    main()
