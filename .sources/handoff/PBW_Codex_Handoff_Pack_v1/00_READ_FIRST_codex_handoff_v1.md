# 00 READ FIRST / Codex handoff v1

このパックは、Codex が PBW 全体実装を開始するときの **現物ベースの正本整理** である。

## まず重要なこと
- `pbw_development_policy_v1.md` には「第二部統合版 v10 を正本」とある。
- しかし、今回アップロードされている実体には **v10 ファイル群は存在しない**。
- したがって、Codex は **存在する現物** を基準に実装を開始する必要がある。

## 現実的な正本
1. `/mnt/data/pbw_development_policy_v1.md`  ← 制作統治ルール
2. ZIP 内 `pbw_world_mythic_integration_v9.py`  ← 現物の世界 engine 最終段階
3. ZIP 内 `pbw_generated_world_seed1729_v9_mythic_integration.json`  ← 現物の世界 runtime 見本
4. ZIP 内 `pbw_ui_contracts_v1/`  ← UI 契約の唯一正本
5. `/mnt/data/pbw_npc発話辞書_v_1_0.md` + ZIP 内 `pbw_style_engine_v1.json` + `pbw_scene_output_schema_v1.json`  ← narrative / scene 正本

## 進め方
- v10 を仮定せず、v9 系現物を土台に進める。
- ただし制作方針の優先順位・品質基準・正本管理ルールは `pbw_development_policy_v1.md` に従う。
- 矛盾したら、**方針書 > この handoff > 現物 code/json > 旧 readme** の順で解決する。

## 何を作れば開始できるか
- World inventory
- UI inventory
- Truth Engine / Read Model / Playable Loop の最小実装計画
- 変更管理 / schema validation / fallback の明文化

## 禁止
- root 直下と `pbw_ui_contracts_v1/` の schema を混在させる
- 旧版 readme の説明だけで挙動を決める
- “v10 がある前提” で勝手に補完する
