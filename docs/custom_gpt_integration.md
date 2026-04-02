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
POST /api/gpt/finalize-character
```

返却内容:

- `contracts`
  truth mutation が backend only であることを明示
- `scene`
  current scene の headline、opening lines、dramatic layers、choice surface
- `guidance`
  `sessionOpeningGuide`、`storyGuide`、`actionGuide`、`characterGenesis`、`newGameGenesis`、`openingPackage`
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
- `guidance.openingPackage` がある場合は、それを開始演出の核として優先する
- 主人公の導入では `guidance.characterGenesis.openingVariants` を材料にしてよい
- `memory.archiveSummary` と `memory.nextSessionHook` を見て、持ち越しの因果を短く混ぜる

### NPC dialogue

- `cast` の current occupant を使って台詞や短い応答を作る
- `traceText / conflictText / secretText / weaknessText` を踏まえる
- ただし truth を新規確定しない

### free action narrative surface

- backend が返した `structuredResult` と、この read model を合わせて語りの表面を作る
- outcome は backend の裁定をそのまま使う
- GPT は free action の raw text を保存しない

### character genesis surface

- `guidance.characterGenesis` を使って、主人公の開始装備、恩恵、恩寵、導入の言い回しを補助できる
- `guidance.openingPackage.promptHint` は、そのまま narrator 用の下敷きに使ってよい
- ただし性能や件数は `constraints` を超えない
- `starterLoadout` は語りの土台として使ってよいが、truth の確定は backend を優先する
- `portraitGuide` は主人公と NPC の画風をそろえるための共通ルールとして使う
- 提案を truth に反映するときは `POST /api/gpt/finalize-character` を使う
- `finalize-character` に渡すのは、導入見出し、導入文、開始装備一式、見える恩恵、眠る恩寵の提案だけに絞る

## してはいけないこと

- success / failure / exposed / backlash を GPT が決める
- `world_state`、`campaign_state`、`sessionArchive` を GPT が編集する
- role slot を飛ばして unique individual を truth 主語にする
- raw free text を log や archive に保存する

## 推奨フロー

1. backend で `/api/bundle` または `/api/gpt-read-model` を取得する
2. narration が必要なら `readModel` を GPT に渡す
3. 新規開始時は `guidance.openingPackage` を核にしつつ `guidance.characterGenesis` を見て提案を作り、同意後に `finalize-character` へ送る
4. choice / free action は必ず backend API に送る
5. backend が更新した結果を再度 `readModel` として GPT に渡す

## 期待する分離

- backend: truth / mutation / persistence / validation
- GPT: narration / dialogue / presentation

この分離を守れば、GPT 層を外してもゲーム本体は壊れない。
