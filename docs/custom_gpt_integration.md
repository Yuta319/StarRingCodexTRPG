# Custom GPT Integration

## 目的

Custom GPT は語り手・GM・会話補助としてだけ接続する。  
truth は常に backend 側の `world_state / structured result` に置き、GPT は状態更新をしない。

## 設計ロック

- `engine / resolution / schema` は変更しない
- GPT は `world_state` を直接変更しない
- GPT は save を直接編集しない
- free action の raw text は保存しない
- 主語は個人ではなく `role slot`
- GPT が扱うのは narration / NPC 会話 / free action の narrative surface のみ

## Read Model Export

API:

```text
GET /api/gpt-read-model?seed=1729
GET /api/gpt-read-model?world_json=C:\path\to\world.json
```

返却内容:

- `contracts`
  truth mutation が backend only であることを明示
- `scene`
  current scene の headline、opening lines、dramatic layers、choice surface
- `guidance`
  `sessionOpeningGuide`、`storyGuide`、`actionGuide`
- `world`
  `worldSpine`、`worldPulse`、`currentEvent`、`activeNode`、`institutionAlert`、`hub`、`dungeon`
- `cast`
  current occupant の short reaction surface
- `memory`
  `archiveSummary`、`nextSessionHook`、`sessionEnding`
- `freeActionSurface`
  直近の自由行動 summary と narration rule

## GPT の責務

### narration

- `scene.openingLines` と `guidance.storyGuide` から 2〜4 文の導入を作る
- `memory.archiveSummary` と `memory.nextSessionHook` を見て、持ち越しの因果を短く混ぜる

### NPC dialogue

- `cast` の current occupant を使って台詞や短い応答を作る
- `traceText / conflictText / secretText / weaknessText` を踏まえる
- ただし truth を新規確定しない

### free action narrative surface

- backend が返した `structuredResult` と、この read model を合わせて語りの表面を作る
- outcome は backend の裁定をそのまま使う
- GPT は free action の raw text を保存しない

## してはいけないこと

- success / failure / exposed / backlash を GPT が決める
- `world_state`、`campaign_state`、`sessionArchive` を GPT が編集する
- role slot を飛ばして unique individual を truth 主語にする
- raw free text を log や archive に保存する

## 推奨フロー

1. backend で `/api/bundle` または `/api/gpt-read-model` を取得する
2. narration が必要なら `readModel` を GPT に渡す
3. choice / free action は必ず backend API に送る
4. backend が更新した結果を再度 `readModel` として GPT に渡す

## 期待する分離

- backend: truth / mutation / persistence / validation
- GPT: narration / dialogue / presentation

この分離を守れば、GPT 層を外してもゲーム本体は壊れない。
