# GPT Publish Ready Handoff v1

このファイルは、`Star Ring Codex TRPG` を GPT editor へ登録する直前に見る最終 handoff です。

## 1. Current Live Endpoints

- GPT editor  
  `https://chatgpt.com/gpts/editor`
- OpenAI Help: Create a GPT  
  `https://help.openai.com/en/articles/8554397-create-a-gpt`
- OpenAI Help: Building and publishing a GPT  
  `https://help.openai.com/en/articles/8798878-building-and-publishing-a-gpt`
- OpenAI Help: Configuring actions in GPTs  
  `https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts`
- Builder website  
  `https://starringcodextrpg.onrender.com/builder-profile.html`
- Privacy Policy  
  `https://starringcodextrpg.onrender.com/privacy.html`
- Actions server  
  `https://starringcodextrpg.onrender.com`

## 2. Current Bundle Sources

- Publish packet  
  [12_gpt_publish_packet_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/12_gpt_publish_packet_v1)
- Zip archive  
  `c:\Users\quiet\Desktop\myproject\StarRingCodexTRPG\.tmp_custom_gpt_actions_bundle\custom_gpt_actions_bundle_v1\12_gpt_publish_packet_v1.zip`
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
- Preview fixtures  
  [13_gpt_preview_fixtures_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/13_gpt_preview_fixtures_v1)
  - 特に [01_preview_scorecard.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/13_gpt_preview_fixtures_v1/01_preview_scorecard.md) を見ると、Preview の合格ラインが早く分かる

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

公開準備を packet / zip / manifest ごとまとめて作り直す場合:

```powershell
py -3 scripts\prepare_gpt_publish_release.py
```

公開に使うフォルダ、主要ドキュメント、builder / privacy URL をまとめて開く場合:

```powershell
py -3 scripts\open_gpt_publish_workspace.py --open
```

このとき、公開用 dashboard `15_gpt_publish_dashboard_v1.html` が最初に開きます。
dashboard には `Registration Checklist` があり、貼り込み進捗をブラウザの localStorage に保持できます。
また `Actions Setup` パネルで import path / server URL / expected operations / latest smoke を同じ画面で確認できます。
さらに `Preview Test Pack` パネルで、新規開始・通常進行・保存再開の確認文をそのままコピーできます。
`Visibility Guidance` パネルでは、非公開で始めるか、リンク共有へ広げるか、公開前に何を見るかをすぐ確認できます。
`Post-Publish Checks` パネルでは、保存後に最低限通す `新規開始 / 通常進行 / 保存と再開` の3本を短く追えます。
詰まったときは `Editor Troubleshooting` パネルを見ると、import / privacy / finalize の失敗点をすぐ確認できます。
terminal 側で使う `prepare / open / smoke / copy` コマンドは `Quick Commands` パネルからそのまま拾えます。
加えて `Action Examples` パネルで、主要 action の fixture 要約と元 JSON へのリンクも確認できます。

欄ごとのテキストをそのままクリップボードへ送る場合:

```powershell
py -3 scripts\open_gpt_publish_workspace.py --copy instructions
py -3 scripts\open_gpt_publish_workspace.py --copy conversation_starters
py -3 scripts\open_gpt_publish_workspace.py --copy privacy_policy_url
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

## 4.5. Publish Scope Guidance

- 最初は非公開で始めて、action と Preview の通りを確認する
- 次にリンク共有で少人数テストを回す
- 公開範囲を広げる前に、live smoke と Preview Scorecard をもう一度通す

## 5. Fastest Copy Path

参照元を行き来したくない場合は、まず publish packet を開くのが一番速いです。

- まとめ済みパケット  
  [12_gpt_publish_packet_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/12_gpt_publish_packet_v1)
- Preview 比較用  
  [13_gpt_preview_fixtures_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/13_gpt_preview_fixtures_v1)
  - まず見る  
    [01_preview_scorecard.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/13_gpt_preview_fixtures_v1/01_preview_scorecard.md)

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

## 7.5. Official Guardrails To Remember

- 公開前に、Builder website と Privacy Policy URL はどちらも実際に開ける状態にしておく
- Actions を使う場合、OpenAPI の `servers.url` は live の API を指している必要がある
- Preview で成功しても、公開前にもう一度 live smoke を回して URL と operation を確認する
- editor 上で出る説明と実際の応答がずれたら、まず official help の publish / actions 記事を見直す

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
