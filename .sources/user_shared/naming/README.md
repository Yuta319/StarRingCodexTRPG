# Naming Import Folder

このフォルダは、外部から受け取った命名辞典を置く場所です。

## 基本

- `Fantasy_Naming_System_Core.json`
  生成器のコア辞典です。
- それ以外の `*.json`
  外部辞典として自動読込されます。

外部から受け取った JSON を取り込むときは、まず importer を使います。

```powershell
py -3 scripts\import_naming_dictionary.py C:\path\to\dictionary.json
```

## 外部辞典の形式

- ひな形:
  [External_Naming_Lexicon.template.json](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.sources/user_shared/naming/External_Naming_Lexicon.template.json)
- バッチ計画のひな形:
  [Batch_Generation_Plan.template.json](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/.sources/user_shared/naming/Batch_Generation_Plan.template.json)

最低限必要なキー:

- `surface_name`
- `category`

使えるキー:

- `surface_name`
- `display_text`
- `category`
- `race`
- `ui_only`
- `source_terms`
- `semantic_tags`
- `annotation`
- `item_type`
- `priority`
- `source_label`

## category

- `city`
- `place`
- `person`
- `item`
- `equipment`

補足:

- `equipment` は内部では `item` として扱います
- `place` は地名・拠点・遺跡などの表示差し替えに使えます

## 読み込みルール

- category は必須です
- race は空でも構いません
- `source_terms` を入れると、既存 canonical 名から UI 表示名への差し替えに使えます
- `display_text` を入れると、UI 表示だけ `セルカ〈停戦執行官〉` のように整えられます
- `ui_only: true` を入れると、生成候補には使わず UI 差し替え専用にできます
- item の場合、`item_type` があると一致度が上がります
- `priority` が高いエントリほど優先されます
- `ui_only: true` のファイルは validate / compile の対象外です

## 注意

- ここに置いた辞典は候補語の供給源です
- UI 主表示へそのまま出すかどうかは
  [fantasy_naming_guide.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/fantasy_naming_guide.md)
  の可読性基準で判断します

## 単発生成

```powershell
py -3 scripts\generate_fantasy_names.py --race human --category city --count 3 --seed 1729
```

## 一括生成

```powershell
py -3 scripts\generate_fantasy_name_batches.py `
  --plan .sources\user_shared\naming\Batch_Generation_Plan.template.json `
  --out generated\naming\batches\default_seed1729.json
```

## 辞典の検証

外部辞典を置いたら、取り込み前にまずこれを通します。

```powershell
py -3 scripts\validate_naming_lexicons.py
```

JSON で結果を残したい場合:

```powershell
py -3 scripts\validate_naming_lexicons.py `
  --json-out generated\naming\validation\latest.json
```

主に見る項目:

- 必須キー欠落
- category の不整合
- 同一キー重複
- annotation 形式
- 英語そのままの surface_name
- 不自然な繰り返し語感

## 辞典の compile

検証が通ったら、複数の外部辞典を1本にまとめられます。

```powershell
py -3 scripts\compile_naming_lexicons.py
```

出力先の既定値:

```text
generated/naming/compiled/external_lexicon_compiled.json
```

この compile では:

- 外部辞典を正規化
- 同一キーの候補を priority で解決
- source_file / source_label を保持
- 取り込み用の1本に集約

## source_terms の書き出し

現在の canonical 名をまとめて書き出すには:

```powershell
py -3 scripts\export_canonical_naming_sources.py
```

既定の出力先:

```text
generated/naming/source_terms/canonical_sources_seed1729.json
```

## 編集用ドラフトの作成

canonical 名から、そのまま編集できる外部辞典ドラフトを作るには:

```powershell
py -3 scripts\scaffold_external_naming_lexicon.py
```

既定の出力先:

```text
generated/naming/drafts/canonical_ui_naming_lexicon_seed1729.json
```

このドラフトでは:

- `source_terms` を canonical 名で自動入力
- 人名は `surface_name` を素の名前、`display_text` を `名前〈役職〉` に整形
- place / equipment / item には編集の足場になる短い annotation を付与
- 生成結果は `generated/` 配下へ出すので、自動読込はされません

## 初期反映版の作成

第一弾の UI 用見せ名辞典を自動生成して、そのまま自動読込位置へ置くには:

```powershell
py -3 scripts\build_initial_ui_naming_lexicon.py
```

既定の出力先:

```text
.sources/user_shared/naming/canonical_ui_naming_lexicon.json
```

この初期反映版では:

- 人名は `名前〈役職〉` を有効化
- 装備と所持品は現在の分かりやすい主表示を固定
- 地名は第一弾として、固有名 + 短い異名の形へ置換
