# Playable Loop

## Goal

- choice を intent に正規化する。
- intent を resolution に渡す。
- resolution に応じて world state を mutation する。
- mutation 後の world から次の scene を再生成する。

## Flow

```text
choiceId
  |
  v
intent layer
  choiceId -> intentType
  choiceId -> skill/tendency vector
  |
  v
resolution layer
  capability vs difficulty
  -> success / partial_success / failure
  |
  v
mutation layer
  node
  institution
  worldPulse
  protagonist.vessel_points
  resolution_history append
  campaign_state advance
  |
  v
runner bundle rebuild
  scene_builder
  ui_builder
  validation
  |
  v
next scene
```

## Determinism Rules

- 新しい random は使わない。
- outcome は `seed` ではなく current world state と choice からのみ決まる。
- 同一 seed + 同一 choice + 同一 world_json なら同一結果になる。

## Observable Mutation Rules

- 毎回 `node` は変わる。
- `institution` がある場合は `breach_risk / support / status` を更新する。
- `worldPulse` は `distortion / divine_war_pressure / notes` を更新する。
- `resolution_history` は必ず 1 件増える。
- `campaign_state` は毎回 1 turn 進む。

## Failure Semantics

- failure でも `resolution_history` は増える。
- failure でも `worldPulse` は変化する。
- failure では node / institution の圧が増し、次 scene の緊張が上がる。

## CLI

```powershell
py -3 -m star_ring_codex_trpg.play_loop --seed 1729 --choice-id observe --output generated/play_loop_seed1729_observe.json
```
