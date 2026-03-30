# Local UI

## Goal

- runner の出力をそのまま可視化する。
- UI は world state を直接変更しない。
- UI 層は runner だけを呼ぶ。
- 操作は `playable_loop` 経由だけで行う。
- 説明文と session 進行は `display` payload を読むだけで描画する。
- 表示文の統治は `text/text_composer.py` と `docs/japanese_output_policy.md` に従う。

## Directory Layout

```text
star_ring_codex_trpg/
├─ read_only_ui/
│  ├─ __main__.py
│  ├─ controller.py
│  ├─ server.py
│  └─ static/
│     ├─ index.html
│     ├─ app.js
│     └─ styles.css
```

## Backend Boundary

- `controller.py`
  query / JSON body を正規化し、`runner.build_bundle()`、`playable_loop.play_choice()`、`playable_loop.play_free_action()`、session save / load / next-session helper を呼ぶ。
- `server.py`
  静的 UI と `/api/bundle`、`/api/play`、`/api/free-action`、`/api/save-session`、`/api/load-session`、`/api/next-session`、`/api/gpt-read-model` を配信する。
- UI backend は `runner` と `playable_loop` 以外の world / scene / ui builder を直接呼ばない。

## Screen Layout

```text
+--------------------------------------------------------------------------------------+
| Toolbar: seed / seasons / archetype / world_json / save / reload / next session     |
+--------------------------------------------------------------------------------------+
| Actor Rail                                                    |
+----------------------+-------------------------+--------------+
| World Rail           | Scene Pane              | Node Rail    |
| left                 | center                  | right        |
| - worldSpine         | - scenePacket           | - activeNode |
| - worldPulse         | - choice chips          | - institution|
| - event / hub / dng  | - story guide           |              |
|                      | - npcBeats              |              |
+----------------------+-------------------------+--------------+
```

## Display Mapping

- Actor 上段
  `shell_snapshot.actorRail`
- World 左段
  `shell_snapshot.worldSpine`
  `shell_snapshot.contextRail.worldPulse`
  `display.currentEvent`
  `display.hub`
  `display.dungeon`
- Scene 中央
  `shell_snapshot.scenePacket`
  `shell_snapshot.scenePacket.npcBeats`
  `display.storyGuide`
- Node 右段
  `shell_snapshot.contextRail.activeNode`
  `shell_snapshot.contextRail.institutionAlert`
- Actor 上段の追加表示
  `display.playCycle`
  `display.namedCast`

## API

### `GET /api/bundle`

- 入力
  `seed` または `world_json`
- 処理
  `runner.build_bundle()` を呼ぶ
- 出力
  `bundle`
  `display`
  `playSource`

### `POST /api/play`

- 入力
```json
{
  "choiceId": "observe",
  "seed": 1729,
  "world_json": null
}
```
- 処理
  `playable_loop.play_choice()` を呼ぶ
- 出力
  `after.bundle`
  `display`
  `playSource`
  `transition`

### `POST /api/free-action`

- 入力
```json
{
  "actionText": "夜中に宿の裏から入り、裏帳面を盗み出す",
  "seed": 1729,
  "world_json": null
}
```
- 処理
  `playable_loop.play_free_action()` を呼ぶ。
  backend 側で parser -> adjudicator -> recorder を通す。
- 出力
  `after.bundle`
  `display`
  `playSource`
  `structuredResult`
  `transition`

### `POST /api/save-session`

- 入力
```json
{
  "world_json": "C:\\...\\.runtime\\ui_sessions\\world_xxx.json"
}
```
- 代替入力
  `world_state`
- 処理
  現在の world state を `.runtime/session_saves/` へ保存する。
- 出力
  `saveId`
  `savePath`
  `savedAt`
  `sessionSummary`

### `POST /api/load-session`

- 入力
```json
{
  "saveId": "save_20260328T120000_abcd1234"
}
```
- 代替入力
  `savePath`
  空 body の場合は最新 save を読む。
- 処理
  保存済み world state を読み、`runner.build_bundle()` で再開 bundle を返す。
- 出力
  `bundle`
  `display`
  `playSource`
  `saveMeta`

### `POST /api/next-session`

- 入力
```json
{
  "world_json": "C:\\...\\.runtime\\ui_sessions\\world_xxx.json"
}
```
- 処理
  直近の `lastEnding` を `sessionArchive` へ退避し、`nextSessionHook` を campaign_state へ追加したうえで、次 session の開始 bundle を返す。
- 出力
  `bundle`
  `display`
  `playSource`
  `nextSessionHook`
  `sessionArchiveSize`

### `GET /api/gpt-read-model`

- 用途:
  Custom GPT へ渡す narration / dialogue 用の read-only surface を返す
- 入力:
  `GET /api/gpt-read-model?seed=1729`
  または `GET /api/gpt-read-model?world_json=...`
- 処理:
  `build_bundle()` で現在 state を組み立て、truth を変更せずに GPT 用 read model へ変換する
- 出力:
  `readModel`
  `playSource`

この endpoint は presentation 専用で、world state を更新しない。

### `display` additions

- `playCycle`
  6 turn session の進行状態
- `storyGuide`
  What Is Happening / Why It Matters / World State
- `currentEvent`
  現在の固有イベント
- `hub`
  拠点状態
- `dungeon`
  簡易ダンジョン状態
- `namedCast`
  role slot ごとの current occupant 一覧
- `playerTrace`
  最近の選択、発覚した秘密、露見した弱点、world mark
- `viceTaboo`
  悪徳圧、禁忌圧、悪名、隠れた罪、儀礼の汚れ、直近 trace
- `endingForecast`
  現セッションの小結末予測
- `sessionEnding`
  6 turn 終端に生成された小結末
- `lastFreeAction`
  直近の自由行動 summary / adjudication / logs
- `nextSessionHook`
  次 session に持ち越す主事件候補、圧力、NPC 関係、残る傷、守れたもの
- `saveMeta`
  直近 save の metadata

## UI Operation Flow

1. 初回ロードで `GET /api/bundle` を呼ぶ。
2. server が world state snapshot を `.runtime/ui_sessions/` に保存し、次回用の `playSource.world_json` を返す。
3. choice chip クリックで `POST /api/play` を呼ぶ。
4. server が `playable_loop.play_choice()` を実行する。
5. response の `display` を `renderDisplay(payload.display)` で再描画する。
6. response の `playSource.world_json` を次回クリック用の source に更新する。
7. custom action textbox 送信時は `POST /api/free-action` を呼び、同じく `display` だけで再描画する。

## Session Continuation Flow

1. session 終了後に `POST /api/save-session` で現在の world state を保存する。
2. `POST /api/load-session` で保存済み state から再開する。
3. `POST /api/next-session` で `sessionArchive` を 1 件追加し、`nextSessionHook` を campaign_state に積む。
4. backend は更新後 state を runtime snapshot に保存し、次 session の `bundle / display / playSource` を返す。
5. UI は返ってきた `display` をそのまま描画し、次の choice から継続する。

## Startup

1. `py -3 -m pip install -r requirements.txt`
2. `py -3 -m star_ring_codex_trpg.read_only_ui --host 127.0.0.1 --port 8765`
3. ブラウザで `http://127.0.0.1:8765`

## UI Rules

- UI は choice を送るだけで、state mutation を自分で行わない。
- custom action も text を backend に送るだけで、UI 側では parser / adjudicator / mutation を持たない。
- save / reload / next-session も UI では state を触らず、backend API の結果だけを描画する。
- choice chip は `POST /api/play` の trigger であり、ロジック実行場所ではない。
- schema や truth engine の仕様を UI 側で吸収しない。
- choice の重要性説明や current event 表示は `display` に含まれた派生情報を読むだけにする。
- 内部指標名や英語の設計ラベルを見出しや説明文へ直出ししない。
