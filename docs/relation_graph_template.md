# Relation Graph Template

## 目的

- 人物、組織、事件、制度の関係を、色だけに頼らず読み取れる graph として定義する。
- `mfugu` のような「中央に焦点、周囲に関係、右に詳細」の分かりやすさと、Black Desert 的な discovery 感を両立させる。
- 実装時に edge 表現がぶれないよう、線種テンプレートを先に固定する。

## 推奨スタック

### 第一候補: Cytoscape.js

理由:

- plain JS でも扱いやすい
- edge の色、太さ、破線、矢印、ラベルを細かく制御できる
- node の画像表示と compound node に対応しやすい
- 相関図の「意味のある線」を表現する用途に向いている

### 第二候補: vis-network

理由:

- ring っぽい配置を素早く作りやすい
- 画像ノードと簡易な矢印付きネットワークが軽い

使い分け:

- semantic edge を重視するなら `Cytoscape.js`
- 最初に BDO 的な輪っかを手早く作るなら `vis-network`

この repo では、最終的には `Cytoscape.js` を推奨する。

## 表示モード

### Focus Ring

- デフォルト
- 選択中の人物か node を中央に置く
- 1 hop の関係だけ表示する
- Codex から開く最初の画面に向く

### Local Web

- 2 hop まで広げる
- 関係の密度を見たいときに使う

### Institution Weave

- 組織、active node、人物を混ぜて表示する
- quest 側から相関を見るときに使う

### Full Graph

- debug / GM 用
- 通常プレイでは初期表示にしない

## 基本レイアウト

```text
+──────────────────────── Relation Graph ────────────────────────+
| Filters | Legend | Layout Switch | Search                     |
+──────────────────── Graph Canvas ───────────────────+──────── Detail Pane ───────+
|                                                   | 名称                       |
|                 Focus Node                         | 肩書き                     |
|             /      |      \\                       | 要約                       |
|          NPC    Institution   Node                 | 関係一覧                   |
|                                                   | 関連クエスト               |
+────────────────────────────────────────────────────+─────────────────────────────+
```

## ノード種別

| 種別 | 形 | 基本色 | 備考 |
| --- | --- | --- | --- |
| 主人公 | 二重円 | 金 | 常に中央候補 |
| NPC | 円 | 生成 portrait / 中立灰 | 人物図鑑から開く主対象 |
| 組織 | 六角形 | 群青 | 評議会、騎士団、修道会など |
| active node | 菱形 | 朱色 | 事件、争点、クエスト |
| 地域 | 横長 capsule | 青灰 | 港、街、森、辺境 |
| 遺物 | 四角丸 | 紫灰 | 指輪、聖印、鍵など |
| 未発見 | 霧付き円 | 薄灰 | `???` と弱いアイコンだけ見せる |

## エッジ種別テンプレート

色だけではなく、太さ、破線、矢印、記号、ラベルを組み合わせる。

| 関係 | 色 | 線 | 太さ | 矢印 | 補助記号 | ラベル例 |
| --- | --- | --- | --- | --- | --- | --- |
| 信頼 / 協力 | 緑 | 実線 | 太 | なし | 小さな盾 | `信頼` `協力` |
| 命令 / 保護 | 金 | 実線 | 中 | 片矢印 | 王冠 / 盾 | `命令` `庇護` |
| 敵対 / 警戒 | 赤 | 破線 | 太 | 両端なし | 亀裂 | `敵対` `警戒` |
| 借り / 義務 | 青 | 点線 | 中 | 片矢印 | 鎖 | `借り` `義務` |
| 好意 / 親愛 | 桃 | 曲線 | 中 | なし | ハート | `好意` `親愛` |
| 執着 / 依存 | 紫赤 | 曲線破線 | 太 | なし | 割れたハート | `執着` `依存` |
| 秘密 / 隠蔽 | 紫 | 細点線 | 細 | なし | 鍵穴 / 目隠し | `秘匿` `隠し事` |
| 事件関与 | 象牙 | 実線 | 細 | なし | 旗 | `関与` `現場` |

## 未発見要素の見せ方

- node 名は `???`
- edge の詳細も完全には出さない
- ただし種別だけは薄く示してよい
  - 人物
  - 組織
  - 遺物
- 発見が進むほど
  - シルエット
  - 名前
  - 関係ラベル
  - 詳細説明
  の順で開放する

## 詳細ペイン

右ペインには次を出す。

- 主表示
- 補助表示
- 一言要約
- 現在の関係一覧
- 関連 quest / node
- `Codex を開く`
- `1 hop を展開`

## interaction rules

- click で焦点化
- double click で 1 hop 展開
- legend click で edge 種別を filter
- search で node を focus
- active node と焦点人物は常に highlight

## ラベル設計

- edge ラベルは短くする
- 名詞 1〜2 語まで
- 例:
  - `信頼`
  - `借り`
  - `警戒`
  - `命令`
  - `秘匿`

説明文は detail pane に逃がす。

## アニメーション

- 初期表示は穏やかに fade-in
- 新規解放 node は pulse
- 新しい edge は線を trace するように現す
- ただし常時動かし続けない

## accessibility

- 色だけで意味を区別しない
- 線種、太さ、ラベル、記号を併用する
- 赤緑色覚特性でも区別しやすいよう、dash pattern と矢印を必ず変える

## 推奨テンプレート

### Template A: Focus Ring

- 中央に選択ノード
- 外周に 1 hop
- 右に詳細
- もっとも扱いやすい

### Template B: Split Panel Network

- 左 70% graph
- 右 30% detail pane
- 管理しやすく、ラベルも見やすい

### Template C: Institution Weave

- 左に人物群
- 右に組織 / node 群
- 縦方向に責任や命令の流れを見せる

今の拡張では `Template B` を先に実装し、`人物` カテゴリだけ `Template A` を追加するのが自然。

## read model

```text
RelationGraphRM
- focusNodeId
- layoutMode
- nodes[]
- edges[]
- legend[]
- filters
```

```text
RelationNodeRM
- nodeId
- entityType
- uiLabel
- uiSubtitle
- discoveryState
- iconUrl?
- portraitUrl?
- emphasis
```

```text
RelationEdgeRM
- edgeId
- sourceId
- targetId
- relationType
- intensity
- direction
- label
- discovered
```

## 実装メモ

- root HUD の右レールには full graph を出さない
- Codex overlay 内で開く
- 最初は `namedCast + trust/stress/conflict + activeNode` から projector を作る
- 画像がなくても node は描けるよう、icon fallback を必ず持つ

## 参照

- Cytoscape.js  
  https://js.cytoscape.org/
- vis-network  
  https://visjs.github.io/vis/docs/network/
- React Flow examples  
  https://reactflow.dev/examples
- Primer: Progressive disclosure  
  https://primer.style/product/ui-patterns/progressive-disclosure/
- mfugu technical artificial intelligence  
  https://mfugu.com/technical-artificialIntelligence.html
- Chrome Extension UI Blueprint  
  [chrome_extension_ui_blueprint.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/chrome_extension_ui_blueprint.md)
