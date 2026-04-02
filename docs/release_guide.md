# Release Guide

## 目的

Codex がいなくても、ローカルで起動、保存、継続、読み返し、GPT 接続まで再現できる状態を保つ。

## 標準の起動導線

### 1. bundle を生成する

```powershell
py -3 -m star_ring_codex_trpg --seed 1729 --output generated/seed1729_bundle.json
```

### 2. ローカル UI を開く

```powershell
py -3 -m star_ring_codex_trpg.read_only_ui --host 127.0.0.1 --port 8765
```

### 3. 保存と継続

- UI の `この session を保存`
- UI の `前回の続きから読む`
- UI の `次の session へ進む`

## サンプル資産

release 用の再生成コマンド:

```powershell
py -3 scripts/generate_release_samples.py
```

生成される主なサンプル:

- `samples/bundles/seed1729_opening_bundle.json`
- `samples/bundles/seed2048_opening_bundle.json`
- `samples/saves/seed1729_turn3_save.json`
- `samples/campaigns/seed1729_two_sessions_world.json`
- `samples/gpt/seed1729_two_sessions_read_model.json`
- `samples/manifest.json`

## save cleanup policy

`.runtime/` は実行キャッシュであり、正本ではない。  
長期保管したい world は `samples/` または別ディレクトリへ退避する。

dry-run:

```powershell
py -3 scripts/cleanup_runtime.py
```

適用:

```powershell
py -3 scripts/cleanup_runtime.py --apply
```

既定値:

- `session_saves`: 新しい 40 件を保持
- `ui_sessions`: 新しい 120 件を保持

## GPT 接続の位置づけ

- backend が truth を確定する
- GPT は narration / dialogue / free action surface だけを担当する
- 接続先は `GET /api/gpt-read-model`

現時点で含まれている front は、開発中の全体表示画面である。  
完成版プレイヤー UI、HUD、装備画面、所持品画面はまだこの release に含まれていない。  
次フェーズでは Chrome 拡張を配布 front として追加し、現行 web UI とは役割を分ける。

## release checklist

- `py -3 -m unittest discover -s tests -v` が通る
- `py -3 scripts/generate_release_samples.py` が通る
- `samples/manifest.json` が更新される
- `README.md` と `docs/index.md` から主要導線に辿れる
- `/api/bundle` と `/api/gpt-read-model` が動く
- raw free text が save / archive / GPT read model に残っていない
- role slot 原則が崩れていない
- `.runtime/` を正本扱いしていない
