# GPT Editor Final Input Pack v1

このファイルは、`Star Ring Codex TRPG` を ChatGPT の GPT editor に登録するための最終入力セットです。

## 1. Name

```text
Star Ring Codex TRPG
```

## 2. Description

```text
局所の介入が制度を裂き、時代を動かし、やがて神話そのものを書き換えるダークファンタジー歴史生成TRPG。新規開始時は主人公の導入・初期装備・恩恵を相談しながら組み、その後は通常選択と自由行動の両方で進行できます。
```

## 3. Instructions

貼り付け元:
- [01_custom_gpt_system_prompt_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/01_custom_gpt_system_prompt_v1.md)

## 4. Conversation Starters

貼り付け元:
- [02_custom_gpt_conversation_starters_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/02_custom_gpt_conversation_starters_v1.md)

推奨 starter:
- 既存キャラをこの世界へ転生させたい。導入と初期装備から一緒に決めて。
- 主人公の恩恵と恩寵を相談しながら決めて、開始導入まで仕上げて。
- 現在の場面で何が起きているか、まず短く説明して。
- この場面で選べる通常行動を比較して。
- 自由行動を試したい。状況に合う形に整理して実行して。
- このセッションの終わりで、何を守れて何を失ったか整理して。
- 前のセッションの因果が、今どこに再燃しているか教えて。
- 保存済みの続きから再開して、状況を要約して。

## 5. Actions

Import file:
- [04_openapi_pbw_actions_v1.yaml](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/04_openapi_pbw_actions_v1.yaml)

Current `servers.url`:

```text
https://starringcodextrpg.onrender.com
```

Expected operations:
- `getGptReadModel`
- `playChoice`
- `playFreeAction`
- `saveSession`
- `loadSession`
- `nextSession`
- `finalizeCharacter`

## 6. Website / Privacy

Builder Profile website:

```text
https://policy.star-ring-codex.com
```

Privacy Policy URL:

```text
https://policy.star-ring-codex.com/privacy.html
```

## 7. Recommended Configure Flow

1. Name に `Star Ring Codex TRPG` を入れる
2. Description に上の文を入れる
3. Instructions に [01_custom_gpt_system_prompt_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/01_custom_gpt_system_prompt_v1.md) を貼る
4. Conversation Starters に [02_custom_gpt_conversation_starters_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/02_custom_gpt_conversation_starters_v1.md) の行を入れる
5. Actions に [04_openapi_pbw_actions_v1.yaml](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/04_openapi_pbw_actions_v1.yaml) を import する
6. Privacy Policy URL を入れる
7. Save して Preview へ進む

## 8. Preview Check

新規開始:
1. `既存キャラをこの世界へ転生させたい。導入と初期装備から一緒に決めて。`
2. `見える恩恵と眠る恩寵も含めて、開始案を仕上げて。`
3. `その内容で確定して。`

通常進行:
1. `現在の場面で何が起きているか、まず短く説明して。`
2. `この場面で選べる通常行動を比較して。`
3. `自由行動として、夜中に裏帳面を盗み見たい。`
4. `このセッションを保存して。`
5. `前回の続きから再開して。`
6. `次のセッションへ進めて。`

## 9. What Good Looks Like

- 新規開始時に `getGptReadModel` を見て、`guidance.characterGenesis` を踏まえた開始案を出す
- `guidance.openingPackage` があれば、それを開始演出の核として優先する
- 同意後に `finalizeCharacter` を使う
- 通常進行では `world_json` を優先して follow-up する
- internal key を出さない
- raw free text を canon memory のように扱わない
- 装備や恩恵の提案が `constraints` を超えない

## 10. Validation

公開前の最終確認:

```powershell
py -3 scripts\validate_custom_gpt_bundle.py
```

期待:
- `ok: true`
- `finalizeCharacter` を含む expected operations が揃っている
- `guidance.openingPackage` を使う前提が system prompt と input pack の両方で確認できる

## 11. Paste-Ready Export

参照元を行き来せず、展開済みの `Instructions` と `Conversation Starters` を 1 ファイルで出したい時:

```powershell
py -3 scripts\export_gpt_editor_paste_pack.py
```

出力先:
- [09_gpt_editor_paste_ready_pack_v1.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/09_gpt_editor_paste_ready_pack_v1.md)

## 12. Field Fragments

各入力欄ごとに個別ファイルを出したい時:

```powershell
py -3 scripts\export_gpt_editor_field_fragments.py
```

出力先:
- [10_gpt_editor_field_fragments_v1](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.tmp_custom_gpt_actions_bundle/custom_gpt_actions_bundle_v1/10_gpt_editor_field_fragments_v1)

主なファイル:
- `name.txt`
- `description.txt`
- `instructions.txt`
- `conversation_starters.txt`
- `builder_website.txt`
- `privacy_policy_url.txt`
- `actions_import_path.txt`
- `actions_server_url.txt`
- `manifest.json`

## 13. Live Smoke Test

公開前または公開直後に、live の policy / privacy / API が通るか確認したい時:

```powershell
py -3 scripts\run_custom_gpt_publish_smoke.py
```

確認内容:
- Builder website
- Privacy Policy URL
- `GET /health`
- `GET /api/front/snapshot?seed=1729`
- `GET /api/gpt-read-model?seed=1729`
- `POST /api/gpt/finalize-character`
