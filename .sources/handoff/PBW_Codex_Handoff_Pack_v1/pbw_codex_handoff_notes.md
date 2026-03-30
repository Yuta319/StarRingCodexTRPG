# PBW Codex handoff

## Files
- pbw_style_engine_v1.json : 文体ルール本体。CustomGPTのsystem instructionsやActionsの前処理に使う。
- pbw_scene_output_schema_v1.json : Actions出力のJSON schema。

## Recommended use
1. Codex側で NPC profile を保持する。
2. リクエストごとに role / personality / relation / emotion / suppression を与える。
3. pbw_style_engine_v1.json の scene_generation_algorithm に沿って player_facing / dramatic_layers / npc_beats / internal を生成する。
4. internal はHUDでは折りたたむか別タブに送る。

## Minimum renderer order
- GM: 場→焦点→差異→反応→余波
- NPC: 第一声=役割 / 二言目=関係 / 三言目=感情
- Rupture: stable → micro_leak → local_break → clear_break