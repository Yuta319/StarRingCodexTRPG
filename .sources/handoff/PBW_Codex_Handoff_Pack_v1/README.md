# PBW UI contracts v1

この一式は、PBW.zip の world / node / mythic 層を UI 向け read model に落とすための初版です。

## ねらい
- raw JSON を直接 HUD に流さない
- `player_facing / dramatic_layers / npc_beats / internal` の構造を ScenePacket に固定する
- `active node / institution / world pulse` を右レールの正本にする
- `vessel_points` を主人公の canonical progression とし、HP/MP/EXP は UI ドメインの追加項目として扱う

## 含まれる schema
- `ScenePacketV1.schema.json`
- `ShellSnapshotRM.schema.json`
- `UiEventEnvelope.schema.json`

## 重要な設計判断
1. `ScenePacketV1.playerFacing.lines` は 3〜6 行固定
2. `ShellSnapshotRM.actorRail.vessel` が正本。`exp` は任意
3. `ContextRailRM` は party より `npcFocus / activeNode / institutionAlert / worldPulse` を中心に持つ
4. `UiEventEnvelope` は payload を小さく保ち、再取得は `invalidate` に寄せる
