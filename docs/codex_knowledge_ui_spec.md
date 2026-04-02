# Codex Knowledge UI Spec

## 目的

- 人物図鑑を、Black Desert の `Knowledge` に近い収集体験で再設計する。
- `???` が徐々に埋まる快感を front の正式導線にする。
- root HUD を重くせず、深い情報は Codex Hub に集約する。

## この文書の結論

- 人物図鑑は `Codex Hub` の中核機能にする。
- 初期表示は `カテゴリ -> サブカテゴリ -> 未解放を含む一覧 -> 詳細` の 4 面構成にする。
- 未発見エントリは最初から全部見せない。カテゴリも discovery に応じて開く。
- 相関図は人物図鑑の中の 1 ビューとして扱う。

## 参照元として採る体験

Black Desert の Knowledge UI から次の要素を採る。

- 大カテゴリと中カテゴリの段階的な開放
- `???` が埋まっていく収集感
- 進捗数の可視化
- 右ペインの詳細表示
- いま見ている対象と、その周辺情報の関係が分かる構成

## 置き場所

- 常設 HUD には置かない
- `Codex` ボタンから開く full overlay に置く
- 同一画面内 overlay で開き、背面の ChatGPT と文脈を切らない

## 画面構成

```text
+────────────────────────── Codex / Knowledge ──────────────────────────+
| Search | Filters | Category Progress                                  |
+──────────── Category Rail ───────────+──── Entry Field ─────+──────── Detail Pane ───────+
| 人物                                   | ???  ○  ○  ?         | 立ち絵 / 肩書き             |
| 組織                                   | ○  ○  ?  ?           | 説明                        |
| 地域                                   | ○  ?  ?              | 関連人物                    |
| 遺物                                   | ?  ?  ?              | 関連組織                    |
| 技法 / 魔法                            |                      | 相関図を開く                |
| 神話 / 神格                            |                      | 取得条件 / 由来             |
| 歴史 / 事件                            |                      |                              |
+──────────────────────────────────────+──────────────────────+──────────────────────────────+
```

## 情報アーキテクチャ

### Level 1

- `人物`
- `組織`
- `地域`
- `遺物`
- `技法 / 魔法`
- `神話 / 神格`
- `歴史 / 事件`
- `怪物 / 異形`

### Level 2

人物の例:

- 港町の人々
- 修道会の人々
- 灰の辺境の旅人
- 焦点人物

組織の例:

- 騎士団
- 修道会
- 評議会
- 商会

### Level 3

- 各カテゴリ内の個別エントリ
- 未発見は `???`
- 断片しか分かっていないものは silhouette と短いヒントだけ出す

## 発見状態

### `hidden`

- カテゴリ自体が見えない
- 何も表示しない

### `hinted`

- カテゴリは見える
- エントリは `???`
- ツールチップに「街道筋で噂を聞く」などの曖昧なヒントだけ出す

### `discovered`

- 主表示と短い説明が見える
- ただし詳細は未完成

### `linked`

- 関係人物や所属組織、関連 node が見える
- 相関図からジャンプできる

### `mastered`

- 背景、由来、関係、取得条件がすべて揃う
- 図鑑としての完成状態

## 表示ルール

### カテゴリ一覧

- カテゴリ名
- 取得数 / 総数
- 進捗バー
- 新規取得バッジ

### 一覧エリア

- grid でも ring でもよいが、初期実装は grid を推奨する
- `???` が多い段階でも視認しやすい
- 特定カテゴリだけ、後で ring 表示へ切り替えてよい

### 詳細ペイン

- portrait か emblem
- `ui_label`
- `ui_subtitle`
- 2〜3 文の要約
- 関連人物
- 関連組織
- 関連 node
- `相関図を見る` ボタン

## 人物カテゴリの特別ルール

- 焦点人物は一覧の先頭に pin する
- 現在の active node に関与している人物は強調する
- 初回取得時は toast と codex badge を出す
- 同じ人物でも `噂だけ`, `名前判明`, `立場判明`, `関係判明` のように段階解放してよい

## 相関図との接続

- 詳細ペインから `相関図を見る` を押す
- 相関図は同じ Codex overlay 内でタブ切替する
- full graph を最初から出さず、選択中人物を中心に 1 hop で開く

## UI トーン

- 未発見は blank ではなく「存在しているが未解放」と分かる見せ方にする
- `???` に加えて、輪郭、家紋色、カテゴリ記号などの弱い手がかりを出す
- ただし答えは出しすぎない

## 推奨レイアウト

### 初期実装

- 左: category rail
- 中央: entry grid
- 右: detail pane

### 拡張実装

- `人物` カテゴリだけ `ring view` を追加する
- ring は Black Desert 的な収集感を強く出したいときに使う
- 他カテゴリは grid のままでよい

## read model

```text
KnowledgeHubRM
- categories[]
- selectedCategoryId
- selectedSubcategoryId
- selectedEntryId
- progress
- featuredEntry
- recentUnlocks[]
```

```text
KnowledgeCategoryRM
- categoryId
- label
- unlocked
- discoveredCount
- totalCount
- subcategories[]
```

```text
KnowledgeEntryRM
- entryId
- entityType
- uiLabel
- uiSubtitle
- discoveryState
- portraitUrl?
- iconUrl?
- summary
- relatedEntryIds[]
- relatedNodeIds[]
- revealHints[]
```

## event contract

- `codex.entry.unlocked`
- `codex.entry.updated`
- `codex.category.unlocked`
- `codex.progress.changed`
- `codex.relation.focused`

## 初期の実装範囲

- `人物`
- `組織`
- `地域`
- `遺物`

まずこの 4 つで十分。`技法 / 魔法`, `神話 / 神格`, `歴史 / 事件` は次段で足す。

## 実装メモ

- plain JS の現状でも十分実装可能
- overlay で描く場合は、中央一覧と右詳細を先に作る
- ring 表示やアニメーションは後段でよい
- まずは `???` とカテゴリ進捗が効いていることを優先する

## 参照

- Black Desert Console Wiki: Knowledge  
  https://blackdesert.pearlabyss.com/Console/en-US/Game/Wiki?_masterWikiNo=320
- Black Desert NAEU Wiki: Knowledge  
  https://www.naeu.playblackdesert.com/fr-fr/Wiki?wikiNo=10
- Primer: Progressive disclosure  
  https://primer.style/product/ui-patterns/progressive-disclosure/
- Chrome Extension UI Blueprint  
  [chrome_extension_ui_blueprint.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/chrome_extension_ui_blueprint.md)
