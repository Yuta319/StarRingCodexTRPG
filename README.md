# StarRingCodexTRPG

`PBW_Codex_Handoff_Pack_v1.zip` を正本として扱い、`StarRingCodexRPG.zip` は不足依存の補完と第二部統合状態の参照に限定した実装です。  
現在は、world 生成、Playable Loop、save/load/next-session、free action、archive memory、Custom GPT read model まで一通り揃っています。

## Canonical Priority

1. `.sources/handoff/PBW_Codex_Handoff_Pack_v1/`
2. handoff 内の world / scene / UI contracts
3. `.sources/reference/StarRingCodexRPG/` は不足依存と参照専用

`.runtime/` は実行時コピーであり正本ではありません。runtime 補完方針は [second_part_integration_map.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/second_part_integration_map.md) を参照してください。

## 最短の起動

### 1. 依存導入

```powershell
py -3 -m pip install -r requirements.txt
```

### 2. bundle 生成

```powershell
py -3 -m star_ring_codex_trpg --seed 1729 --output generated/seed1729_bundle.json
```

### 3. ローカル UI

```powershell
py -3 -m star_ring_codex_trpg.read_only_ui --host 127.0.0.1 --port 8765
```

ブラウザ:

```text
http://127.0.0.1:8765
```

## 主な実行方法

### 既存 world state を読む

```powershell
py -3 -m star_ring_codex_trpg --world-json .sources/handoff/PBW_Codex_Handoff_Pack_v1/pbw_generated_world_seed1729_v9_mythic_integration.json
```

### 通常 choice を 1 手進める

```powershell
py -3 -m star_ring_codex_trpg.play_loop --seed 1729 --choice-id observe --output generated/play_loop_seed1729_observe.json
```

### テスト

```powershell
py -3 -m unittest discover -s tests -v
```

## 保存と継続

- UI から:
  - `この session を保存`
  - `前回の続きから読む`
  - `次の session へ進む`
- sample save を直接読む場合:
  - `world_json` または `savePath` を使う

## Samples

release 用サンプルの再生成:

```powershell
py -3 scripts/generate_release_samples.py
```

主なサンプル:

- `samples/bundles/seed1729_opening_bundle.json`
- `samples/bundles/seed2048_opening_bundle.json`
- `samples/saves/seed1729_turn3_save.json`
- `samples/campaigns/seed1729_two_sessions_world.json`
- `samples/gpt/seed1729_two_sessions_read_model.json`
- `samples/manifest.json`

## Runtime Cleanup

dry-run:

```powershell
py -3 scripts/cleanup_runtime.py
```

適用:

```powershell
py -3 scripts/cleanup_runtime.py --apply
```

既定では `.runtime/session_saves` の新しい 40 件、`.runtime/ui_sessions` の新しい 120 件を残します。

## Custom GPT Read Model

Custom GPT は narration / NPC 会話 / free action の表面演出にだけ接続します。truth mutation は backend のみです。

```text
GET /api/gpt-read-model?seed=1729
GET /api/gpt-read-model?world_json=C:\path\to\world.json
```

設計方針は [custom_gpt_integration.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/custom_gpt_integration.md)、プロンプトたたき台は [custom_gpt_narrator_prompt.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/prompts/custom_gpt_narrator_prompt.md) を参照してください。

## Chrome Extension Shell

Chrome 拡張の shell は [chrome_extension/README.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/chrome_extension/README.md) を参照してください。  
これは `read_only_ui` の代替ではなく、ChatGPT 上に重ねる完成版プレイヤー UI の最初の実装です。

## Docs

- [index.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/index.md)
- [read_only_ui.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/read_only_ui.md)
- [playable_loop.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/playable_loop.md)
- [gameplay_experience.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/gameplay_experience.md)
- [release_guide.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/release_guide.md)
- [design_lock_alignment.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/design_lock_alignment.md)
- [japanese_output_policy.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/japanese_output_policy.md)
