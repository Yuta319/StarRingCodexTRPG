from __future__ import annotations

from typing import Any, Iterable, Mapping
import re

from .copy_checks import ensure_copy_quality
from .terminology_registry import natural_phrase, ui_label


def _text(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _sentence(text: object, fallback: str) -> str:
    normalized = _text(text, fallback)
    if normalized[-1] not in "。！？":
        normalized = f"{normalized}。"
    return normalized


def _trim_terminal(text: object, fallback: str = "") -> str:
    normalized = _text(text, fallback)
    return normalized.rstrip("。！？").strip()


def _soften_weakness_copy(text: object, fallback: str = "") -> str:
    normalized = _trim_terminal(text, fallback)
    normalized = normalized.replace(" 火がつくのは ", " 起きやすいのは ")
    normalized = normalized.replace("火がつくのは ", "起きやすいのは ")
    normalized = normalized.replace("弱みの発火", "弱みが表に出た")
    return normalized


def _join_sentences(parts: Iterable[object], fallback: str) -> str:
    cleaned = _dedupe_sentence_chunks(_trim_terminal(part) for part in parts if _text(part))
    if not cleaned:
        return _sentence(fallback, fallback)
    return _sentence("。".join(cleaned), fallback)


def _value(value: object) -> float:
    return round(float(value or 0.0), 1)


_LEAD_IN_RE = re.compile(r"^(放置すると|このままでは|ここで(?:誤る|見誤る)と|いま強く戻ってきているのは|前節の因果として|隠れた不正の痕として)\s*")


def _normalize_sentence_key(text: object) -> str:
    normalized = _trim_terminal(text)
    normalized = _LEAD_IN_RE.sub("", normalized)
    return normalized.replace("　", " ").strip()


def _dedupe_sentence_chunks(parts: Iterable[object]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = _trim_terminal(part)
        if not text:
            continue
        key = _normalize_sentence_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def choice_label(choice_id: str) -> str:
    return ensure_copy_quality(ui_label(choice_id, choice_id), "status")


def outcome_label(outcome: str) -> str:
    return ensure_copy_quality(ui_label(outcome, outcome), "status")


def outcome_phrase(outcome: str) -> str:
    return ensure_copy_quality(_sentence(natural_phrase(outcome, outcome), outcome), "afterglow")


def compose_event_copy(event: Mapping[str, Any]) -> dict[str, Any]:
    status_key = _text(event.get("status"), "contained")
    status_label = ensure_copy_quality(ui_label(status_key, "進行中"), "status")
    summary_text = ensure_copy_quality(_sentence(event.get("summary"), "状況を確認している。"), "explanation")
    importance_text = ensure_copy_quality(
        _sentence(
            f"{_trim_terminal(event.get('stakes'), 'この事件は次の交渉にも響く')}。"
            f"{_trim_terminal(event.get('whyImportant'), '放置すると後手に回る')}",
            "この事件は放置できない。",
        ),
        "explanation",
    )
    last_outcome_text = ensure_copy_quality(
        _sentence(event.get("lastOutcomeText"), "まだ決定的な結果は出ていない。"),
        "afterglow",
    )

    branch_preview: list[dict[str, Any]] = []
    for branch in event.get("branches", []):
        summary = ensure_copy_quality(_sentence(branch.get("summary"), "手がかりを追っている。"), "explanation")
        result_text = ensure_copy_quality(_sentence(branch.get("notes", {}).get("success"), "うまく収められそうだ。"), "afterglow")
        risk_text = ensure_copy_quality(
            _sentence(
                f"この筋が崩れると、{_trim_terminal(branch.get('notes', {}).get('failure'), '事態が悪い方向へ転ぶ')}",
                "この筋が崩れると事態が悪化する。",
            ),
            "explanation",
        )
        branch_preview.append(
            {
                **branch,
                "summaryText": summary,
                "resultText": result_text,
                "riskText": risk_text,
                "preferredChoiceLabels": [choice_label(intent) for intent in branch.get("preferredIntents", [])],
            }
        )

    return {
        **event,
        "statusLabel": status_label,
        "statusText": ensure_copy_quality(_sentence(natural_phrase(status_key, status_label), status_label), "afterglow"),
        "summaryText": summary_text,
        "importanceText": importance_text,
        "lastOutcomeText": last_outcome_text,
        "recommendedChoiceLabels": [choice_label(choice_id) for choice_id in event.get("recommendedChoices", [])],
        "branchPreview": branch_preview,
    }


def compose_hub_copy(hub: Mapping[str, Any]) -> dict[str, Any]:
    stability = _value(hub.get("stability"))
    supply = _value(hub.get("supply"))
    heat = _value(hub.get("heat"))
    supply_text = "補給はひとまず保たれている" if supply >= 60 else "補給に余裕が少ない" if supply >= 42 else "補給がかなり乱れている"
    heat_text = "場の空気はまだ荒れきっていない" if heat < 50 else "場の緊張が高まっている" if heat < 72 else "人心がかなり荒れている"
    stability_text = "拠点はまだ持ちこたえている" if stability >= 55 else "拠点の足元が揺らいでいる" if stability >= 40 else "拠点の支えが崩れかけている"
    status_key = _text(hub.get("status"), "holding")
    return {
        **hub,
        "statusLabel": ensure_copy_quality(ui_label(status_key, "様子見"), "status"),
        "statusText": ensure_copy_quality(_sentence(natural_phrase(status_key, "まだ持ちこたえている"), "まだ持ちこたえている。"), "afterglow"),
        "supportText": ensure_copy_quality(
            _sentence(f"{hub['label']}では{stability_text}。{supply_text}。{heat_text}", "拠点の状況を見極めている。"),
            "explanation",
        ),
    }


def compose_dungeon_copy(dungeon: Mapping[str, Any]) -> dict[str, Any]:
    seal = _value(dungeon.get("sealIntegrity"))
    threat = _value(dungeon.get("threat"))
    depth = int(dungeon.get("depth", 0))
    max_depth = max(1, int(dungeon.get("maxDepth", 1)))
    seal_text = "封印はまだ働いている" if seal >= 62 else "封印の効きが弱まり始めている" if seal >= 42 else "封印がかなり弱っている"
    threat_text = "坑路の危険はまだ抑えられている" if threat < 52 else "坑路の危険が増している" if threat < 72 else "坑路はかなり危険だ"
    depth_text = "まだ入口近くで様子を見ている" if depth == 0 else "奥へ踏み込んで道筋を確かめている" if depth < max_depth else "奥まで道筋は見えている"
    status_key = _text(dungeon.get("status"), "sealed")
    return {
        **dungeon,
        "statusLabel": ensure_copy_quality(ui_label(status_key, "探索中"), "status"),
        "statusText": ensure_copy_quality(_sentence(natural_phrase(status_key, "封印はまだ働いている"), "封印はまだ働いている。"), "afterglow"),
        "supportText": ensure_copy_quality(
            _sentence(f"{dungeon['label']}では{seal_text}。{threat_text}。{depth_text}", "坑路の状況を見極めている。"),
            "explanation",
        ),
    }


def compose_world_pulse_copy(cycle_state: Mapping[str, Any]) -> dict[str, Any]:
    distortion = _value(cycle_state.get("distortion"))
    apotheosis = _value(cycle_state.get("apotheosis_flux"))
    succession = _value(cycle_state.get("succession_pressure"))
    divine = _value(cycle_state.get("divine_war_pressure"))
    distortion_text = "世界のゆらぎはまだ抑えられている" if distortion < 48 else "世界のゆらぎが目立ち始めている" if distortion < 70 else "世界の綻びがかなり広がっている"
    divine_text = "神々の対立はまだ局地的だ" if divine < 52 else "神々の対立が表ににじんでいる" if divine < 72 else "神々の対立が強く噴き出している"
    succession_text = "継承争いはまだ散発的だ" if succession < 48 else "継承争いが各地で表に出始めている"
    apotheosis_text = "昇神をめぐる気配は静かだ" if apotheosis < 48 else "昇神をめぐる気配が濃くなっている"
    status_text = "世界のゆらぎが強い" if distortion >= 60 else "世界はまだ踏みとどまっている"
    return {
        "statusLabel": ensure_copy_quality(status_text, "status"),
        "summaryText": ensure_copy_quality(
            _sentence(f"{distortion_text}。{divine_text}。{succession_text}。{apotheosis_text}", "世界の気配を観測している。"),
            "explanation",
        ),
        "detailRows": [
            [ui_label("distortion"), distortion],
            [ui_label("apotheosis_flux"), apotheosis],
            [ui_label("succession_pressure"), succession],
            [ui_label("divine_war_pressure"), divine],
        ],
    }


def compose_session_opening_guide(
    session: Mapping[str, Any],
    opening_summary: object,
    archive_review: Mapping[str, Any] | None,
    next_session_hook: Mapping[str, Any] | None,
) -> dict[str, Any]:
    lines = _dedupe_sentence_chunks(
        [
            opening_summary,
            archive_review.get("resurfacingSpark") if archive_review else "",
            archive_review.get("hiddenWound") if archive_review else "",
            (next_session_hook.get("carriedPressures") or [""])[0] if isinstance(next_session_hook, Mapping) else "",
        ]
    )
    if not lines:
        lines = ["前のセッションから、いま強く引きずっている問題はまだない"]
    return {
        "headline": ensure_copy_quality(f"第{session['sessionNumber']}セッションの入り口", "ui"),
        "lines": [ensure_copy_quality(_sentence(line, "セッションの始まりを確認している。"), "explanation") for line in lines[:3]],
    }


def compose_action_mode_guide(
    current_event: Mapping[str, Any],
    story_guide: Mapping[str, Any],
) -> dict[str, str]:
    recommended = list(current_event.get("recommendedChoiceLabels") or story_guide.get("recommendedChoiceLabels") or [])
    first_choice = recommended[0] if recommended else "周囲の様子を見る"
    return {
        "choiceMode": ensure_copy_quality(
            _sentence(
                f"まずは通常の選択で場面を進める。迷ったら「{first_choice}」から始めると流れをつかみやすい",
                "通常の選択から始める。",
            ),
            "explanation",
        ),
        "freeActionMode": ensure_copy_quality(
            _sentence(
                "自由行動は、選択肢にない手を試したいときだけ使う。通っても露見や反動が残ることがある",
                "自由行動は慎重に使う。",
            ),
            "explanation",
        ),
        "sessionFlow": ensure_copy_quality(
            _sentence(
                "途中で区切るなら保存する。6手を終えたら次のセッションへ進み、持ち越しを見てから一手目を選ぶ",
                "保存と継続の流れを確認する。",
            ),
            "explanation",
        ),
    }


def compose_world_pulse_panel_copy(world_pulse: Mapping[str, Any], world_pulse_guide: Mapping[str, Any]) -> dict[str, str]:
    metrics = [
        ("世界のゆらぎ", _value(world_pulse.get("cycleDistortion"))),
        ("神々の対立", _value(world_pulse.get("divineWarPressure"))),
        ("継承争い", _value(world_pulse.get("successionPressure"))),
        ("昇神のうねり", _value(world_pulse.get("apotheosisFlux"))),
    ]
    label, score = max(metrics, key=lambda item: item[1])
    if score >= 70:
        focus = f"いま特に強いのは「{label}」だ。局地の事件にもその圧が表へにじみやすい"
    elif score >= 55:
        focus = f"いま目立ってきているのは「{label}」だ。場面の裏でじわじわ効いている"
    else:
        focus = "いまは局地の事件が先に見えやすいが、世界の圧も静かに積み上がっている"
    return {
        "summary": ensure_copy_quality(_sentence(world_pulse_guide.get("summaryText"), "世界の気配を見ている。"), "explanation"),
        "focus": ensure_copy_quality(_sentence(focus, "強い圧を見ている。"), "explanation"),
        "read": ensure_copy_quality(
            _sentence("数字が高い項目ほど、その場面の判断や事件の空気に割り込んできやすい", "数字の見方を確認している。"),
            "explanation",
        ),
    }


def compose_active_node_panel_copy(active_node: Mapping[str, Any]) -> dict[str, str]:
    severity = _value(active_node.get("severity"))
    urgency = _value(active_node.get("urgency"))
    stage = int(active_node.get("stage") or 0)
    vectors = [ui_label(vector, vector) for vector in active_node.get("recommendedVectors", [])]
    if urgency >= 72 or severity >= 72:
        summary = "先送りしにくい局面だ。次の一手で被害や対立の広がり方が決まりやすい"
    elif urgency >= 56 or severity >= 56:
        summary = "手順を選ぶ余地はあるが、ここで鈍ると後手に回りやすい"
    else:
        summary = "まだ状況を読み切る余地がある。急がず筋を見定めたい"
    if stage >= 4:
        timing = "流れはかなり固まりつつある。大きくひっくり返すより、損を減らす判断が重くなる"
    elif stage >= 2:
        timing = "事件は途中段階だ。ここで選んだ向きが、後の分岐を決めやすい"
    else:
        timing = "まだ入口だ。観察や聞き取りで責任の流れをつかみやすい"
    action = (
        f"向いているのは {', '.join(vectors[:3])} だ。"
        if vectors
        else "まずは状況を見て、無理に踏み込みすぎない。"
    )
    return {
        "summary": ensure_copy_quality(_sentence(summary, "この局面を見ている。"), "explanation"),
        "action": ensure_copy_quality(_sentence(action, "向いている動きを見ている。"), "explanation"),
        "timing": ensure_copy_quality(_sentence(timing, "いまの進みを見ている。"), "explanation"),
    }


def compose_institution_alert_panel_copy(
    institution_alert: Mapping[str, Any],
    current_event: Mapping[str, Any],
) -> dict[str, str]:
    label = _text(institution_alert.get("label"))
    status = _text(institution_alert.get("status"), "none")
    breach_risk = _value(institution_alert.get("breachRisk"))
    if not label or status == "none":
        summary = "この場面で前面に出ている取り決めはまだ少ない。まずは事件側の筋を読む"
        consequence = "ただし、裏で支えている約定が崩れると、交渉や配分が急に止まりやすい"
    else:
        if breach_risk >= 72 or status == "broken":
            summary = f"「{label}」はかなり危うい。このまま崩れると、{current_event.get('label', '事件')}の収め方まで細くなる"
        elif breach_risk >= 52 or status == "strained":
            summary = f"「{label}」には綻びが出ている。事件だけでなく、文言や手順のほころびも見たい"
        else:
            summary = f"「{label}」はまだ保っているが、油断すると事件の圧で崩れやすい"
        consequence = "取り決めが崩れると、次の交渉、補給、通行のどれかが止まりやすい"
    return {
        "summary": ensure_copy_quality(_sentence(summary, "取り決めの状態を見ている。"), "explanation"),
        "consequence": ensure_copy_quality(_sentence(consequence, "崩れたときの影響を見ている。"), "explanation"),
    }


def compose_player_trace(
    dominant_choice: str,
    recent_entries: Iterable[Mapping[str, Any]],
    npcs: Iterable[Mapping[str, Any]],
    world_marks: Iterable[str],
) -> dict[str, Any]:
    dominant_label = choice_label(dominant_choice)
    recent_choices = [
        ensure_copy_quality(
            _sentence(
                f"{entry.get('turnInSession', '?')}手目: {choice_label(_text(entry.get('intentType') or entry.get('choiceId')))}で"
                f"「{_text(entry.get('branchLabel'), 'この筋')}」へ踏み込み、"
                f"{_trim_terminal(entry.get('outcomeText'), outcome_label(_text(entry.get('outcome'), 'unknown')))}"
                f"{' 残った痕跡は ' + _text((entry.get('marksAdded') or [''])[0]) if entry.get('marksAdded') else ''}",
                "最近の行動を整理している。",
            ),
            "afterglow",
        )
        for entry in recent_entries
    ]

    discovered_secrets: list[str] = []
    known_weaknesses: list[str] = []
    for npc in npcs:
        secret_state = _text(npc.get("secretState"), "hidden")
        if secret_state == "hinted":
            discovered_secrets.append(ensure_copy_quality(f"{npc['displayName']}: {npc['secretHint']}", "afterglow"))
        elif secret_state == "exposed":
            discovered_secrets.append(ensure_copy_quality(f"{npc['displayName']}: {npc['secret']}", "afterglow"))
        if npc.get("knownWeakness"):
            known_weaknesses.append(ensure_copy_quality(f"{npc['displayName']}: {npc['knownWeakness']}", "afterglow"))

    marks = [ensure_copy_quality(_sentence(mark, "痕跡が残った。"), "afterglow") for mark in list(world_marks)[-4:]]
    afterglow_text = marks[-1] if marks else "まだ世界に大きな爪痕は残っていない。"
    return {
        "dominantChoice": dominant_choice,
        "dominantChoiceLabel": dominant_label,
        "dominantChoiceText": ensure_copy_quality(
            _sentence(f"最近は「{dominant_label}」を選ぶことが多い", "最近の傾向を見ている。"),
            "explanation",
        ),
        "recentChoices": recent_choices,
        "discoveredSecrets": discovered_secrets,
        "knownWeaknesses": known_weaknesses,
        "worldMarks": marks,
        "afterglowText": ensure_copy_quality(afterglow_text, "afterglow"),
        "summary": ensure_copy_quality(
            _sentence(
                f"最近は「{dominant_label}」で動くことが多い。{_trim_terminal(afterglow_text, 'まだ大きな爪痕は残っていない')}",
                "最近の選択傾向を整理している。",
            ),
            "explanation",
        ),
    }


def compose_story_guide_copy(
    scene_title: str,
    session: Mapping[str, Any],
    event: Mapping[str, Any],
    hub: Mapping[str, Any],
    dungeon: Mapping[str, Any],
    world_pulse: Mapping[str, Any],
    trace: Mapping[str, Any],
    forecast: Mapping[str, Any],
) -> dict[str, Any]:
    now = ensure_copy_quality(
        _sentence(
            f"第{session['sessionNumber']}セッションの{session['phaseLabel']}だ。いま前面に出ているのは「{event['label']}」で、場面の焦点は「{scene_title}」にある",
            "いまの局面を整理している。",
        ),
        "explanation",
    )
    stakes = ensure_copy_quality(
        _sentence(
            f"{_trim_terminal(event['summaryText'], '事態が動いている')}。{_trim_terminal(event['importanceText'], '放置すると後手に回る')}",
            "この局面の重要性を整理している。",
        ),
        "explanation",
    )
    world_state = ensure_copy_quality(
        _sentence(
            f"{_trim_terminal(hub['supportText'], '拠点を見ている')}。{_trim_terminal(dungeon['supportText'], '坑路を見ている')}。{_trim_terminal(world_pulse['summaryText'], '世界の気配を見ている')}",
            "世界の状態を整理している。",
        ),
        "explanation",
    )
    trace_text = ensure_copy_quality(
        _sentence(
            f"{_trim_terminal(trace['dominantChoiceText'], '選択の傾向を見ている')}。{_trim_terminal(trace['afterglowText'], 'まだ大きな爪痕は残っていない')}",
            "選択の傾向を整理している。",
        ),
        "explanation",
    )
    forecast_text = ensure_copy_quality(
        _sentence(
            f"{_trim_terminal(forecast.get('title'), '結末はまだ読めない')}。{_trim_terminal(forecast.get('summary'), '次の手で重みが決まる')}",
            "結末の見立てを整理している。",
        ),
        "explanation",
    )
    return {
        "now": now,
        "stakes": stakes,
        "worldState": world_state,
        "trace": trace_text,
        "forecast": forecast_text,
        "recommendedChoices": list(event.get("recommendedChoices", [])),
        "recommendedChoiceLabels": list(event.get("recommendedChoiceLabels", [])),
        "objective": ensure_copy_quality(_sentence(event.get("objective"), "次の一手を定める。"), "explanation"),
    }


def compose_npc_copy(npc: Mapping[str, Any]) -> dict[str, Any]:
    trust = _value(npc.get("trust"))
    stress = _value(npc.get("stress"))
    if trust >= 62:
        trust_text = "まだこちらに賭ける余地がある。"
    elif trust >= 48:
        trust_text = "協力の余地はあるが、全面的には任せていない。"
    else:
        trust_text = "助けは欲していても、簡単には腹を割らない。"

    if stress >= 68:
        stress_text = "かなり追い詰められている。"
    elif stress >= 52:
        stress_text = "平静を装っているが余裕は薄い。"
    else:
        stress_text = "まだ判断の余白を残している。"

    secret_state = _text(npc.get("secretState"), "hidden")
    if secret_state == "exposed":
        secret_text = _sentence(
            f"{_trim_terminal(npc.get('secret'), '秘密が表に出ている')} 露見のきっかけは {_trim_terminal(npc.get('lastSecretTrigger') or npc.get('exposeTrigger'), '責任の所在を公に問われたことだ')}",
            "秘密が表に出ている。",
        )
    elif secret_state == "hinted":
        secret_text = _sentence(
            f"{_trim_terminal(npc.get('secretHint'), '秘密の気配が見えている')} さらに {_trim_terminal(npc.get('exposeTrigger'), 'もう一押しで露見する')}",
            "秘密の気配が見えている。",
        )
    else:
        secret_text = _sentence(
            f"まだ腹の底は見せていない。糸口は {_trim_terminal(npc.get('hintTrigger'), 'まだ表に出ていない')}",
            "まだ腹の底は見せていない。",
        )

    weakness_text = _sentence(
        f"{_soften_weakness_copy(npc.get('knownWeakness') or npc.get('weakness'), '弱みはまだ見えていない')} "
        f"起きやすいのは {_trim_terminal(npc.get('lastWeaknessTrigger') or npc.get('weaknessTrigger'), '追い込まれたときだ')}",
        "弱みはまだ見えていない。",
    )
    conflict_text = _sentence(npc.get("conflictDetail") or f"{npc['conflictsWithLabel']}と利害がぶつかっている", "利害の衝突を抱えている。")
    trace_text = _join_sentences(
        [npc.get("archiveReactionText"), npc.get("lastReaction")],
        "まだこちらの出方を測っている。",
    )
    return {
        **npc,
        "trustText": ensure_copy_quality(trust_text, "afterglow"),
        "stressText": ensure_copy_quality(stress_text, "afterglow"),
        "secretText": ensure_copy_quality(secret_text, "afterglow"),
        "weaknessText": ensure_copy_quality(weakness_text, "afterglow"),
        "conflictText": ensure_copy_quality(conflict_text, "afterglow"),
        "traceText": ensure_copy_quality(trace_text, "afterglow"),
    }


def compose_npc_role_line(npc: Mapping[str, Any], event: Mapping[str, Any]) -> str:
    return ensure_copy_quality(
        _join_sentences(
            [
                f"{npc['role']}として「{event['label']}」の火元を見張っている。{npc['conflictsWithLabel']}とは利害が噛み合っていない",
                npc.get("archiveRoleText"),
            ],
            "この人物は現場を見張っている。",
        ),
        "explanation",
    )


def compose_npc_relation_line(npc: Mapping[str, Any]) -> str:
    return ensure_copy_quality(
        _join_sentences(
            [
                compose_npc_copy(npc)["trustText"],
                npc.get("archiveRelationText"),
                npc.get("lastReaction"),
            ],
            "こちらとの距離を測っている。",
        ),
        "explanation",
    )


def compose_npc_emotion_line(npc: Mapping[str, Any]) -> str:
    copy = compose_npc_copy(npc)
    return ensure_copy_quality(
        _join_sentences(
            [
                copy["stressText"],
                npc.get("archiveEmotionText"),
                copy["weaknessText"],
            ],
            "感情の揺れを見ている。",
        ),
        "explanation",
    )


def compose_transition_message(transition: Mapping[str, Any], outcome: str) -> str:
    branch_label = _text(transition.get("branchLabel"), "この一手")
    outcome_text = _trim_terminal(transition.get("branchOutcomeText"), natural_phrase(outcome, outcome_label(outcome)))
    movements: list[str] = []

    event_delta = _value(transition.get("eventPressureAfter")) - _value(transition.get("eventPressureBefore"))
    heat_delta = _value(transition.get("hubHeatAfter")) - _value(transition.get("hubHeatBefore"))
    seal_delta = _value(transition.get("dungeonSealAfter")) - _value(transition.get("dungeonSealBefore"))
    depth_delta = int(transition.get("dungeonDepthAfter", 0)) - int(transition.get("dungeonDepthBefore", 0))

    if event_delta >= 0.8:
        movements.append("責任争いがさらに重くなった")
    elif event_delta <= -0.8:
        movements.append("責任争いが少しほどけた")
    if heat_delta >= 0.8:
        movements.append("宿の空気が荒れた")
    elif heat_delta <= -0.8:
        movements.append("宿の空気が少し落ち着いた")
    if seal_delta <= -0.8:
        movements.append("坑路の封印が弱まった")
    elif seal_delta >= 0.8:
        movements.append("坑路の封印が持ち直した")
    if depth_delta > 0:
        movements.append("坑路の奥へ一歩進んだ")

    if not movements:
        movements.append("局面は次の一手待ちになった")

    ending_title = _text(transition.get("endingTitle"))
    body = f"「{branch_label}」では{outcome_text}。{'。'.join(movements[:2])}。"
    if ending_title:
        body = f"{body} {ending_title}でこのセッションが締めくくられた。"
    return ensure_copy_quality(body, "explanation")
