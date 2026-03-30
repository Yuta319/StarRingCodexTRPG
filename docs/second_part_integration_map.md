# Second Part Integration Map

## Canonical Reading Order

1. `00_READ_FIRST_codex_handoff_v1.md`
2. `02_execution_order_v1.md`
3. `03_canonical_sources_v1.json`
4. `pbw_world_mythic_integration_v9.py`
5. `pbw_generated_world_seed1729_v9_mythic_integration.json`
6. `pbw_ui_contracts_v1/*.schema.json`
7. `pbw_style_engine_v1.json`
8. `pbw_scene_output_schema_v1.json`
9. `pbw_npc発話辞書_v_1_0.md`

## Current Integrated State

- Truth engine の実体は `world v9 mythic integration`。
- 第二部の read model 契約は `ScenePacketV1 / ShellSnapshotRM / UiEventEnvelope`。
- scene 出力の正本は `pbw_scene_output_schema_v1.json`。
- 文体制御は `pbw_style_engine_v1.json` と `pbw_npc発話辞書_v_1_0.md`。
- 参照用 `PBW_SecondPart_Integration_Report_v10.md` は、この接続方向を確認するためだけに利用し、正本には昇格させていない。

## Connection Diagram

```text
canonical v9 world engine
  pbw_world_mythic_integration_v9.py
          |
          | generate/load world_state
          v
pbw_generated_world_seed*_v9_mythic_integration.json
          |
          | reads resolved_world.active_nodes / institutions / factions / cycle_state
          v
scene builder
  + pbw_style_engine_v1.json
  + pbw_npc発話辞書_v_1_0.md
  + pbw_scene_output_schema_v1.json
          |
          v
scene_output
          |
          | map to UI contract
          v
ScenePacketV1
          |
          | embed scene + protagonist + context
          v
ShellSnapshotRM
          |
          | derive latest event from resolution_history
          v
UiEventEnvelope
          |
          | validate against canonical UI schemas
          v
JSON bundle for CLI / UI handoff
```

## Field-Level Wiring

- `world -> scene`
  `resolved_world.active_nodes` から焦点ノードを選び、`regions / factions / institutions / cycle_state` を scene 要約へ落とす。
- `style -> scene`
  `pbw_style_engine_v1.json` の `場→焦点→差異→反応→余波` と `第一声→二言目→三言目` を scene 文と NPC beat に適用する。
- `scene -> ScenePacketV1`
  `player_facing` を `playerFacing` に、dramatic layer を UI 用の `place / focus / discrepancy / reaction / aftermath` に変換する。
- `world + scene -> ShellSnapshotRM`
  `world` と `protagonist` を `worldSpine / actorRail` に、焦点ノードを `contextRail.activeNode` に埋め込む。
- `world -> UiEventEnvelope`
  `resolved_world.resolution_history` の最新項目から UI 再取得用 event を作る。

## Runtime Supplement Policy

- handoff は唯一の正本であり、world / scene / UI contracts / style の仕様判断は必ず handoff に戻る。
- reference は canonical v9 engine を実行するために handoff に欠けている依存ファイルを補完する時だけ使う。
- `.runtime/` は実行時コピーであり、仕様正本ではない。
- `.tmp_engine/` はローカル検証で一時的に作られる場合があっても、仕様正本ではない。
- `.runtime/` や `.tmp_engine/` の中で仕様変更してはいけない。
- 仕様変更が必要な場合は handoff の canonical source を見直し、reference や runtime 側で吸収しない。

## Planned Responsibility Split

- `scene planner`
  world state から焦点 node / region / institution / scene objective / involved factions を選ぶ責務に限定する。
- `text composer`
  planner が決めた事実と `pbw_style_engine_v1.json`、`pbw_npc発話辞書_v_1_0.md` を使って `scene_output` の本文と NPC beats を組み立てる。
- `ui mapper`
  canonical scene model を `ScenePacketV1 / ShellSnapshotRM / UiEventEnvelope` に写像し、表示都合の派生値だけを扱う。
- 分離の狙い
  world facts の決定、文章生成、UI 変換を切り離し、将来の UI 実装で scene text の変更が truth selection に波及しないようにする。

## Explicit Non-Goals

- UI を先に作らない。
- handoff の schema や world 仕様を書き換えない。
- reference 側の v10 manifest / sample を新しい正本として扱わない。
- active node が存在しない世界に対して、事実のない scene を捏造しない。
