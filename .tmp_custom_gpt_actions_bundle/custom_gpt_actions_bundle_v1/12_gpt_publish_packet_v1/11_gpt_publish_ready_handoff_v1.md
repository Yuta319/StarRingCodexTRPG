# GPT Publish Ready Handoff v1

このファイルは、`Star Ring Codex TRPG` を GPT editor へ登録する直前に見る最終 handoff です。

## 1. Current Live Endpoints

- Builder website  
  `https://starringcodextrpg.onrender.com/builder-profile.html`
- Privacy Policy  
  `https://starringcodextrpg.onrender.com/privacy.html`
- Actions server  
  `https://starringcodextrpg.onrender.com`

## 2. Current Bundle Sources

- Publish packet  
  [12_gpt_publish_packet_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/12_gpt_publish_packet_v1)
- Instructions source  
  [01_custom_gpt_system_prompt_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/01_custom_gpt_system_prompt_v1.md)
- Conversation starters source  
  [02_custom_gpt_conversation_starters_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/02_custom_gpt_conversation_starters_v1.md)
- OpenAPI import file  
  [04_openapi_pbw_actions_v1.yaml](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/04_openapi_pbw_actions_v1.yaml)
- Paste-ready pack  
  [09_gpt_editor_paste_ready_pack_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/09_gpt_editor_paste_ready_pack_v1.md)
- Field fragments  
  [10_gpt_editor_field_fragments_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/10_gpt_editor_field_fragments_v1)

## 3. Live Validation Status

2026-04-03 JST 時点で、次の smoke は通過済みです。

- Builder website: `200`
- Privacy Policy: `200`
- `GET /health`: `200`
- `GET /api/front/snapshot?seed=1729`: `200`
- `GET /api/gpt-read-model?seed=1729`: `200`
- `POST /api/gpt/finalize-character`: `200`

使った確認コマンド:

```powershell
py -3 scripts\run_custom_gpt_publish_smoke.py
```

## 4. Recommended Editor Flow

1. GPT editor の `Configure` を開く
2. `Name` に `Star Ring Codex TRPG` を入れる
3. `Description` を入れる
4. `Instructions` を貼る
5. `Conversation Starters` を貼る
6. `Actions` へ [04_openapi_pbw_actions_v1.yaml](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/04_openapi_pbw_actions_v1.yaml) を import する
7. `Builder website` と `Privacy Policy URL` を入れる
8. Preview で新規開始と通常進行を試す
9. 問題なければ Save / Publish へ進む

## 5. Fastest Copy Path

参照元を行き来したくない場合は、まず publish packet を開くのが一番速いです。

- まとめ済みパケット  
  [12_gpt_publish_packet_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/12_gpt_publish_packet_v1)

- まとめて見る  
  [09_gpt_editor_paste_ready_pack_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/09_gpt_editor_paste_ready_pack_v1.md)
- 欄ごとに貼る  
  [10_gpt_editor_field_fragments_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/10_gpt_editor_field_fragments_v1)

特に使うファイル:

- `name.txt`
- `description.txt`
- `instructions.txt`
- `conversation_starters.txt`
- `builder_website.txt`
- `privacy_policy_url.txt`

## 6. Preview Prompts

新規開始:

- `既存キャラをこの世界へ転生させたい。導入と初期装備から一緒に決めて。`
- `見える恩恵と眠る恩寵も含めて、開始案を仕上げて。`
- `その内容で確定して。`

通常進行:

- `現在の場面で何が起きているか、まず短く説明して。`
- `この場面で選べる通常行動を比較して。`
- `自由行動として、夜中に裏帳面を盗み見たい。`
- `このセッションを保存して。`
- `前回の続きから再開して。`
- `次のセッションへ進めて。`

## 7. What Good Looks Like

- 新規開始時に `getGptReadModel` を読んで、`guidance.characterGenesis` と `guidance.openingPackage` を使って導入案を組む
- 同意後に `finalizeCharacter` を呼ぶ
- 通常進行では `world_json` を優先する
- internal key や raw debug 情報を出さない
- truth を GPT が直接決めない
- 装備や恩恵の提案が backend constraints を超えない

## 8. Current Code State

- live smoke pass: 済み
- main branch pushed: 済み
- local worktree: clean

## 9. If Something Fails In Editor

- Action import で失敗したら  
  `servers.url` が `https://starringcodextrpg.onrender.com` になっているか確認する
- Privacy URL で失敗したら  
  `https://starringcodextrpg.onrender.com/privacy.html` がそのまま開くか確認する
- Preview で新規開始が弱い場合は  
  `guidance.openingPackage` を使っているか、開始案を確定前の「案」として扱っているかを見る
- `finalizeCharacter` が失敗したら  
  `world_json` が request に入っているか確認する
