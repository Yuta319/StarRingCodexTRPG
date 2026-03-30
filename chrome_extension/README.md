# Star Ring Codex Shell

## 目的

- ChatGPT 上に `World Spine / Actor Rail / Narrative Core / Context Rail / Hotbar` を重ねる Chrome 拡張 shell
- Phase 10 の最初の実装
- 既存の `read_only_ui` とは別物

## いま入っているもの

- MV3 manifest
- service worker
- content script overlay
- side panel
- front 用 compact API を読む接続
  - `GET /api/front/snapshot`
  - `POST /api/front/play`
  - `POST /api/front/free-action`
  - `POST /api/save-session`
  - `POST /api/front/load-session`
  - `POST /api/front/next-session`

## まだ未接続のもの

- EquipmentRM
- InventoryRM
- RelationGraphRM
- AssetGalleryRM の実データ
- クライマックス画像生成ジョブの実連携

## ローカル読み込み

1. Chrome で `chrome://extensions` を開く
2. `デベロッパーモード` を有効にする
3. `パッケージ化されていない拡張機能を読み込む`
4. このフォルダを選ぶ

```text
C:\Users\quiet\Desktop\myproject\StarRingCodexTRPG\chrome_extension
```

## 使い方

1. ChatGPT を開く
2. 拡張アイコンを押して side panel を開く
3. 必要なら `ChatGPT を開く` でタブを用意する
4. `API 疎通確認` で `/health` と `/api/front/snapshot?seed=1729` を確認する
5. `shell を開く`
6. 必要なら `API Base URL / seed / world_json` を変更する
7. `再読込`

## 既定接続先

- `https://starringcodextrpg.onrender.com`

ローカル UI backend を使う場合は、side panel で次を指定する。

- `http://127.0.0.1:8765`
- または `http://localhost:8765`
