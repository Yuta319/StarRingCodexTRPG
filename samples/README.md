# Samples

このディレクトリには、release 用の固定サンプルを置く。

## 再生成

```powershell
py -3 scripts/generate_release_samples.py
```

## 代表ファイル

- `bundles/seed1729_opening_bundle.json`
- `bundles/seed2048_opening_bundle.json`
- `saves/seed1729_turn3_save.json`
- `campaigns/seed1729_two_sessions_world.json`
- `gpt/seed1729_two_sessions_read_model.json`
- `manifest.json`

## 用途

- seed 差分の確認
- save/load の動作確認
- archive / nextSessionHook / scene echo の再現確認
- Custom GPT 接続の read model 確認
