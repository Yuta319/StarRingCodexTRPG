# PBW Custom GPT + Actions Bundle v1

このバンドルは、`Star Ring Codex TRPG` を **Custom GPT + Actions** として公開・運用するための最小構成です。

## 前提
- 現在の公開ポリシー面: `https://starringcodextrpg.onrender.com/builder-profile.html`
- 現在の公開プライバシーページ候補: `https://starringcodextrpg.onrender.com/privacy.html`
- Actions API: `api.star-ring-codex.com` が未開通なら、**実際に到達できる公開 API ホスト** を使う

## 推奨構成
- 公開説明・ポリシー:
  - `https://starringcodextrpg.onrender.com/builder-profile.html`
- Actions API:
  - `https://api.star-ring-codex.com` を使うなら、DNS / TLS / backend 公開が完了してから
  - それまでは `https://<actual-public-api-host>` を OpenAPI の `servers.url` に入れる

## 同梱ファイル
- `01_custom_gpt_system_prompt_v1.md`
- `02_custom_gpt_conversation_starters_v1.md`
- `03_custom_gpt_builder_fields_v1.json`
- `04_openapi_pbw_actions_v1.yaml`
- `05_action_setup_checklist_v1.md`
- `06_deployment_mapping_star_ring_codex_v1.md`
- `07_privacy_policy_and_publish_checklist_v1.md`

## 使い方
1. `01_custom_gpt_system_prompt_v1.md` の内容を GPT の Instructions に貼る
2. `02_custom_gpt_conversation_starters_v1.md` から会話スターターを設定する
3. `04_openapi_pbw_actions_v1.yaml` を Actions にインポートする
4. `servers.url` を**実際に 200 を返す API ホスト**へ合わせる
5. `07_privacy_policy_and_publish_checklist_v1.md` に従って Privacy Policy URL と Builder Profile を整える
6. 実際の登録直前は `11_gpt_publish_ready_handoff_v1.md` を見て、live URL と貼り込み順を確認する
7. 手元でそのまま使う最終パケットが必要なら `12_gpt_publish_packet_v1` を開く
8. 一発で公開準備をやり直すなら次を実行する

```powershell
py -3 scripts\prepare_gpt_publish_release.py
```

公開に使うファイルと URL をまとめて開く場合:

```powershell
py -3 scripts\open_gpt_publish_workspace.py --open
```

## この版の方針
- `01_custom_gpt_system_prompt_v1.md` は Builder にそのまま貼りやすい圧縮版です
- 詳しい設計意図や補足は `docs/` 側の文書を参照します
- 新規開始時は `getGptReadModel -> finalizeCharacter` の順で主人公導入を固めます

## 重要原則
- Truth mutation は必ず backend API 経由
- GPT は narrator / guide / adjudication assistant であり、truth engine ではない
- raw free text は保存しない
- role slot 原則を壊さない
