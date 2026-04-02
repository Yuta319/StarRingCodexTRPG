# GPT Preview Fixtures v1

このフォルダは、GPT editor の Preview で何が返るべきかを見比べるための実例セットです。

## Included Files

- `initial_gpt_read_model.json`
- `opening_package_excerpt.json`
- `finalize_character_response.json`
- `play_choice_response.json`
- `free_action_response.json`

## What To Check In Preview

1. 新規開始では `guidance.openingPackage` を核にして導入案を組んでいること
2. 確定前は内容を『案』として扱い、同意後に `finalizeCharacter` を呼ぶこと
3. 通常 choice は action 結果を truth として説明していること
4. 自由行動は raw 入力を保存された canon のように扱わず、summary と outcome を基に説明していること

## Suggested Preview Order

1. `opening_package_excerpt.json` を見ながら新規開始を試す
2. `finalize_character_response.json` を見ながら確定後の説明を比べる
3. `play_choice_response.json` と `free_action_response.json` で通常進行を比べる
