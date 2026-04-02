from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from .custom_gpt_bundle_support import validate_custom_gpt_bundle
from .read_only_ui.controller import (
    build_front_snapshot_payload,
    build_gpt_finalize_character_payload,
    build_gpt_free_action_payload,
    build_gpt_play_payload,
    build_gpt_read_model_payload,
    finalize_character_request_from_body,
    free_action_request_from_body,
    play_request_from_body,
    viewer_request_from_query,
)


@dataclass
class CustomGptPreviewFixtures:
    bundle_root: str
    output_dir: str
    files: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


def export_custom_gpt_preview_fixtures(
    bundle_root: Path,
    *,
    seed: int = 1729,
    output_dir: Path | None = None,
) -> CustomGptPreviewFixtures:
    root = Path(bundle_root)
    report = validate_custom_gpt_bundle(root)
    if not report.ok:
        raise ValueError("bundle validation failed: " + "; ".join(report.errors))

    out_dir = output_dir or (root / "13_gpt_preview_fixtures_v1")
    out_dir.mkdir(parents=True, exist_ok=True)

    initial_snapshot = build_front_snapshot_payload(viewer_request_from_query({"seed": [str(seed)]}))
    initial_read_model = build_gpt_read_model_payload(viewer_request_from_query({"seed": [str(seed)]}))
    world_json = initial_snapshot["playSource"]["world_json"]

    finalize_payload = build_gpt_finalize_character_payload(
        finalize_character_request_from_body(
            {
                "world_json": world_json,
                "proposal": {
                    "openingHeadline": "灰の関所で始まる旅",
                    "openingLines": [
                        "ルアカイの渡し場からカルドルンの関所へ向かう街道で、旅は始まる。",
                        "停戦のきしみと渡し場の検札違いが、最初の火種として立ち上がっている。",
                    ],
                    "starterBoonSeed": {
                        "visibleBoon": {
                            "label": "旅路の加護",
                            "summary": "迷いかけた道で、進むべき筋をひとつだけ照らす。",
                        },
                        "dormantGrace": {
                            "label": "まだ名を持たない恩寵",
                            "summary": "危うい局面でだけ、遠い世界の勘が薄く戻る。",
                        },
                    },
                },
            }
        )
    )
    finalized_world_json = finalize_payload["playSource"]["world_json"]

    choice_payload = build_gpt_play_payload(
        play_request_from_body(
            {
                "choiceId": "observe",
                "world_json": finalized_world_json,
            },
            prefer_world_json_when_both=True,
        )
    )

    free_action_payload = build_gpt_free_action_payload(
        free_action_request_from_body(
            {
                "actionText": "夜中に裏帳面を盗み見し、封鎖の名目を探る。",
                "world_json": finalized_world_json,
            },
            prefer_world_json_when_both=True,
        )
    )

    files = {
        "initial_read_model": out_dir / "initial_gpt_read_model.json",
        "opening_package": out_dir / "opening_package_excerpt.json",
        "finalize_response": out_dir / "finalize_character_response.json",
        "choice_response": out_dir / "play_choice_response.json",
        "free_action_response": out_dir / "free_action_response.json",
        "summary": out_dir / "00_preview_summary.md",
        "scorecard": out_dir / "01_preview_scorecard.md",
    }

    files["initial_read_model"].write_text(json.dumps(initial_read_model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files["opening_package"].write_text(
        json.dumps(
            {
                "openingPackage": initial_read_model["readModel"]["guidance"]["openingPackage"],
                "characterGenesis": initial_read_model["readModel"]["guidance"]["characterGenesis"],
                "newGameGenesis": initial_read_model["readModel"]["guidance"]["newGameGenesis"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    files["finalize_response"].write_text(json.dumps(finalize_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files["choice_response"].write_text(json.dumps(choice_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files["free_action_response"].write_text(json.dumps(free_action_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# GPT Preview Fixtures v1",
        "",
        "このフォルダは、GPT editor の Preview で何が返るべきかを見比べるための実例セットです。",
        "",
        "## Included Files",
        "",
        "- `initial_gpt_read_model.json`",
        "- `opening_package_excerpt.json`",
        "- `finalize_character_response.json`",
        "- `play_choice_response.json`",
        "- `free_action_response.json`",
        "",
        "## What To Check In Preview",
        "",
        "1. 新規開始では `guidance.openingPackage` を核にして導入案を組んでいること",
        "2. 確定前は内容を『案』として扱い、同意後に `finalizeCharacter` を呼ぶこと",
        "3. 通常 choice は action 結果を truth として説明していること",
        "4. 自由行動は raw 入力を保存された canon のように扱わず、summary と outcome を基に説明していること",
        "",
        "## Suggested Preview Order",
        "",
        "1. `opening_package_excerpt.json` を見ながら新規開始を試す",
        "2. `finalize_character_response.json` を見ながら確定後の説明を比べる",
        "3. `play_choice_response.json` と `free_action_response.json` で通常進行を比べる",
    ]
    files["summary"].write_text("\n".join(summary_lines).strip() + "\n", encoding="utf-8")

    opening_package = initial_read_model["readModel"]["guidance"]["openingPackage"]
    opening_anchors = opening_package.get("anchors") or {}
    finalize_read_model = finalize_payload.get("readModel") or {}
    finalize_guidance = finalize_read_model.get("guidance") or {}
    choice_read_model = choice_payload.get("readModel") or {}
    choice_scene = choice_read_model.get("scene") or {}
    free_action_result = free_action_payload.get("structuredResult") or {}
    free_story_guide = ((free_action_payload.get("readModel") or {}).get("guidance") or {}).get("storyGuide") or {}

    scorecard_lines = [
        "# Preview Scorecard v1",
        "",
        "このファイルは、GPT editor の Preview で返答を確認するときの合格ラインです。",
        "",
        "## 1. 新規開始の開始案",
        "",
        "次の要素が説明に入っていれば正常です。",
        "",
        f"- 導入見出しの核: `{opening_package.get('headline') or ''}`",
        f"- 最初の火種: `{opening_anchors.get('incitingIncidentLabel') or ''}`",
        f"- 拠点: `{opening_anchors.get('hubLabel') or ''}`",
        f"- 坑路: `{opening_anchors.get('dungeonLabel') or ''}`",
        "- 最初に関わる主要人物 2〜3 人",
        "",
        "この段階では、導入・装備・恩恵を確定事項ではなく『案』として扱っている必要があります。",
        "",
        "最初に関わる人物:",
        *(f"- `{item.get('displayName')}` / {item.get('agenda')}" for item in (opening_anchors.get("castLabels") or [])[:3]),
        "",
        "## 2. 確定後の説明",
        "",
        "次の要素が見えていれば正常です。",
        "",
        f"- 確定した導入見出し: `{(finalize_guidance.get('sessionOpeningGuide') or {}).get('headline') or ''}`",
        f"- 見える恩恵: `{(((finalize_guidance.get('characterGenesis') or {}).get('starterBoonSeed') or {}).get('visibleBoon') or {}).get('label') or ''}`",
        f"- 眠る恩寵: `{(((finalize_guidance.get('characterGenesis') or {}).get('starterBoonSeed') or {}).get('dormantGrace') or {}).get('label') or ''}`",
        "",
        "この段階では、確定後の内容として話してよく、`finalizeCharacter` を通っている前提です。",
        "",
        "## 3. 通常 choice の説明",
        "",
        "次の要素が見えていれば正常です。",
        "",
        f"- 現在の場面: `{choice_scene.get('headline') or ''}`",
        f"- 場面の焦点: `{choice_scene.get('title') or ''}`",
        "- 推奨 choice を比較して説明する",
        "",
        "推奨 choice の例:",
        *(f"- `{item.get('label')}`" for item in (choice_scene.get("choiceSurface") or []) if item.get("recommended")),
        "",
        "## 4. 自由行動の説明",
        "",
        "次の要素が見えていれば正常です。",
        "",
        f"- 自由行動 summary: `{free_action_result.get('summary') or ''}`",
        f"- outcome: `{free_action_result.get('outcome') or ''}`",
        f"- 物語上の現在位置: `{free_story_guide.get('now') or ''}`",
        "",
        "この段階では、raw の自由入力をそのまま保存済み canon のように扱わず、summary と outcome を基に語っている必要があります。",
        "",
        "## 5. NG 例",
        "",
        "- internal key や debug 用語を出す",
        "- 返っていない truth を勝手に増やす",
        "- 確定前の開始案を既成事実として言い切る",
        "- 自由行動の raw テキストをそのまま保存された事実として扱う",
        "- backend constraints を無視した強すぎる装備や恩恵を断定する",
    ]
    files["scorecard"].write_text("\n".join(scorecard_lines).strip() + "\n", encoding="utf-8")

    return CustomGptPreviewFixtures(
        bundle_root=str(root),
        output_dir=str(out_dir),
        files={key: str(path) for key, path in files.items()},
    )
