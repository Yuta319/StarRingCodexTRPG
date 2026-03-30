# Chrome Extension UI Blueprint

## 目的

- Phase 10 の完成版プレイヤー UI を、Chrome 拡張 front として固定する。
- 既存の `read_only_ui` を「開発中の全体表示画面」と明示的に切り分ける。
- すでにある read model / display payload を最大限再利用しつつ、不足している front domain を追加する。
- Quest のクライマックスで発生する画像生成も、UI 契約に含めて最初から扱う。

## この文書の位置づけ

- この文書は、完成版プレイヤー UI の正本である。
- quoted spec で合意した shell 構造を採用する。
- `engine / resolution / schema` は壊さない。
- UI は world state を直接変更しない。
- 物語の truth は backend に残し、front は read model と event contract を読む。

## 先に固定する結論

### 1. ルート shell

```text
+────────────────────────────── World Spine ──────────────────────────────+
| Region | Era | Year / Season | Main God | Active Chain | Sync          |
+────────────── Actor Rail ──────────────+──── Narrative Core ───────────+──────────── Context Rail ───────────+
| Portrait                               | Scene Header                  | NPC Focus                           |
| HP / MP / EXP→Vessel                   | Event Card                    | Active Node                         |
| Existence Title                        | Custom GPT Chat               | Institution Risk                    |
| 6 Skill Vectors                        | Choice Chips                  | World Pulse                         |
| Status / Blessings / Quick Skills      | Dice Tray                     | Party / Companions                  |
+────────────────────────────────────────+───────────────────────────────+──────────────────────────────────────+
| Hotbar: Character | Inventory | Skills | Quest | Codex | Journal | World | Dice | Assets | Settings |
+────────────────────────────────────────────────────────────────────────────────────────────────────────────+
```

### 2. 優先順位

- 中央は常に `Scene Packet + Custom GPT + Choice Chips`
- 左は常に主人公の身体性
- 右は常に世界との接点
- 右レールの優先順位は次の順に固定する
  - 現在の会話相手 / 焦点 NPC
  - current active node / quest
  - institution risk
  - world pulse
  - party / companions

### 3. 深い画面

- 深い画面は `Menu Hub` に集約する
- 常時表示しない
- 主要 Hub は次で固定する
  - `Character`
  - `Inventory`
  - `Skills`
  - `Quest`
  - `Codex`
  - `Journal`
  - `World`
  - `Dice`
  - `Assets`
  - `Settings`

### 4. 関係図の扱い

- 相関図は常時表示しない
- 右レールは「現在の焦点」を出す
- full の相関図は `Codex` または `World` Hub に置く
- 初期表示は「焦点 NPC / 焦点 node の 1〜2 hop」までに絞る

### 5. クライマックス画像生成

- Quest のクライマックスでは画像生成を前提にする
- ただし画像は truth ではなく asset layer とする
- 中央には `Cinematic Card` として直近の生成状態を出し、完全な一覧は `Assets` Hub に置く
- 画像生成の状態は `queued -> silhouette -> revealed -> canonical` で扱う

## HCI / GUI の根拠

この UI は、見た目の好みではなく次の原則で最適化する。

### 概要を先に見せ、深掘りは後で開く

Ben Shneiderman の Information Visualization Mantra は「overview first, zoom and filter, then details-on-demand」と整理されている。  
この PBW では、`World Spine + Actor Rail + Context Rail` が overview、`Menu Hub` と `Drawer` が details-on-demand にあたる。  
そのため、装備・所持品・相関図・詳細履歴を常時出しっぱなしにはしない。  
参照: https://www.cs.umd.edu/~ben/about.html

### 階層は深くしすぎない

Jacko / Salvendy (1996) は、階層メニューの depth が深くなるほど、知覚される複雑さが有意に増えると報告している。  
このため、Hotbar からの遷移は shallow に保ち、`常設 shell -> Hub -> Tab` の 3 層までを原則にする。  
参照: https://www.research.ed.ac.uk/en/publications/hierarchical-menu-design-breadth-depth-and-task-complexity-percep

### Progressive disclosure は文脈を壊さない形で使う

GitHub Primer の progressive disclosure 指針は、情報を隠すときもユーザーの焦点を失わせないこと、アイコンには説明テキストを添えることを勧めている。  
このため、下部 Hotbar はアイコンのみではなくラベル付きにし、`NPC Drawer` や `Intervention Overlay` も「現在の場面」を背後に残したまま開く。  
参照: https://primer.style/product/ui-patterns/progressive-disclosure/

### Chrome 拡張の UI 役割は分ける

Chrome の公式 docs では、Side Panel は「persistent experiences that complement the user's browsing journey」とされる。一方、content scripts は page DOM を読んで変更できるが、service worker は 30 秒の非活動で停止しうる。  
このため、主 UI shell は content script overlay、Side Panel は設定 / debug / GM 管理、service worker は event routing と reconnect に限定する。  
参照:
- https://developer.chrome.com/docs/extensions/reference/api/sidePanel
- https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts
- https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle

### 相関図は overview と details-on-demand の間に置く

ManyNets は network visualization を tabular overview と details-on-demand で扱っている。  
この PBW の相関図も、常時フル graph を出すのではなく、まず焦点 NPC / 焦点 node の summary を右レールに出し、full graph は Hub で開く形にする。  
参照: https://www.cs.umd.edu/projects/hcil/manynets/

## 情報アーキテクチャ

### Level 0: 常設 shell

- `World Spine`
- `Actor Rail`
- `Narrative Core`
- `Context Rail`
- `Hotbar`

### Level 1: Hub

- `Character`
- `Inventory`
- `Skills`
- `Quest`
- `Codex`
- `Journal`
- `World`
- `Dice`
- `Assets`
- `Settings`

### Level 2: Hub 内タブ / Drawer / Overlay

- `Character`
  - `Status`
  - `Equipment`
  - `Relics`
  - `Blessings`
- `Inventory`
  - `Consumables`
  - `Quest Items`
  - `Resources`
  - `Key Assets`
- `Quest`
  - `Node Board`
  - `Interventions`
  - `Institution Risk`
- `World`
  - `Institutions`
  - `Chains`
  - `Pantheon`
  - `Final Branch`
- `Codex`
  - `NPC`
  - `Relics`
  - `Regions`
  - `Factions`
  - `Relation Graph`
- `Assets`
  - `Climax Gallery`
  - `NPC Portraits`
  - `Relic Art`
  - `World Keyframes`

## 画面定義

### Narrative Mode

- 常時表示する基本形
- 中央の主タスクは「現在の場面を理解して選ぶ」こと
- 中央に置くもの
  - scene header
  - event card
  - choice chips
  - GPT 会話
  - dice tray
- 中央に置かないもの
  - full inventory
  - full relation graph
  - archive 全件

### Intervention Overlay

- active node に対する介入方針を明示する画面
- `suppress / reconcile / divine_judgement / restructure` を意図ボタンとして出す
- このボタンは canonical truth を直接変えず、まず GPT / backend に構造化意図を送る

### Character Hub

- 身体性と build の確認場所
- 最低限のタブ
  - `Status`
  - `Equipment`
  - `Relics`
  - `Skills`
  - `Blessings`

### Inventory Hub

- 現在は未実装
- 新設する最小 domain
  - `itemId`
  - `displayName`
  - `category`
  - `quantity`
  - `rarity`
  - `equippableSlots`
  - `consumableEffect`
  - `narrativeTags`
  - `assetState`

### Quest Hub

- `Node Board` を主役にする
- generic な quest list ではなく、PBW の active node / chain / institution risk に沿う
- ここに相関図の quest 側入口も置く

### Codex Hub

- NPC / relic / god / institution / region の詳細
- 命名レイヤー
  - market
  - workshop
  - formal
  - ritual
  - proper
  - true_name
- `Relation Graph` はここに置く

### Journal Hub

- 履歴、持ち越し、archive echo を読む場所
- 既存 `archiveInspector` を移植ベースにする

### Assets Hub

- 画像生成のホーム
- クライマックス時の生成結果を一覧化する
- NPC portrait / relic art / climax scene を一元管理する
- 右レールや中央 card では最新 1 件のみ要約し、full history はここに送る

## クライマックス画像生成の扱い

### UI 原則

- 画像生成は「最後に思いついた演出」ではなく、Quest 終盤の正式導線として扱う
- 画像は物語の truth を決めない
- 画像が未生成でも session は継続できる
- 生成待ちでも UI 全体は止めない

### 発火条件

- `activeNode.stage >= 5` かつ `questClimaxEligible = true`
- あるいは `sessionEnding` / `node.resolution.committed` が `climaxAssetPrompt` を返した場合

### 表示位置

- 中央 `Narrative Core`
  - `Cinematic Card`
  - 生成状況、短い説明、開くボタン
- `Assets Hub`
  - 生成履歴
  - variation
  - canonical 採用状態

### 状態

- `none`
- `queued`
- `rendering`
- `silhouette`
- `revealed`
- `canonical`
- `failed`

### 追加 read model

```text
AssetGalleryRM
- latestClimaxAsset
- assetEntries[]
- queueState
- revealState
- canonicalAssetId
```

### 追加イベント

- `asset.job.queued`
- `asset.job.updated`
- `asset.ready`
- `asset.canonicalized`

## read model 設計

### 既存を再利用するもの

- `WorldSpineRM`
  - 既存 `display.worldSpine`
- `ActorRailRM`
  - 既存 `display.actorRail`
- `ScenePacketV1`
  - 既存 `display.scenePacket`
- `ContextRailRM`
  - 既存 `display.activeNode`
  - 既存 `display.institutionAlert`
  - 既存 `display.worldPulse`
  - 既存 `display.namedCast`
  - 既存 `display.npcBeats`
- `JournalRM`
  - 既存 `display.archiveInspector`
  - 既存 `display.nextSessionHook`
  - 既存 `display.sessionEnding`

### 追加するもの

- `EquipmentRM`
- `InventoryRM`
- `RelationGraphRM`
- `QuestHubRM`
- `AssetGalleryRM`
- `DiceTrayRM`

### ShellSnapshotRM の完成形

```text
ShellSnapshotRM
- sessionId
- shellMode
- worldSpine
- actorRail
- scenePacket
- contextRail
- hotbar
- overlays
- drawers
- badges
- lastSeq
```

### 既存 payload との対応

| 完成版 UI | 既存 source |
| --- | --- |
| World Spine | `display.worldSpine` |
| Actor Rail | `display.actorRail`, `display.playCycle`, `display.namedCast` |
| Narrative Core | `display.scenePacket`, `display.storyGuide`, `display.currentEvent` |
| Context Rail | `display.npcBeats`, `display.activeNode`, `display.institutionAlert`, `display.worldPulse` |
| Journal | `display.archiveInspector`, `display.nextSessionHook`, `display.sessionEnding` |
| Quest | `display.currentEvent.branchPreview`, `display.activeNodeGuide` |
| Assets | 新設 |
| Inventory | 新設 |
| Equipment | 新設 |
| Relation Graph | `namedCast + conflictText + trust/stress + active node references` から projector を新設 |

## 相関図の仕様

### 常設しない理由

- full node-link graph は narrative core を圧迫する
- 右レールの仕事は「現在の焦点を伝える」ことであり、全関係を常時描くことではない
- overview first の原則に合わせ、まず summary を見せる

### 最小仕様

- graph node 種別
  - protagonist
  - npc
  - role slot
  - institution
  - active node
- edge 種別
  - trust
  - stress
  - conflict
  - debt
  - vice/taboo residue
  - quest involvement
- 初期表示
  - focus NPC 中心
  - 1 hop
  - 2 hop は手動展開

## Chrome 拡張の構成

### 主 shell

- `content script overlay`
- 理由
  - ChatGPT 上に常設しやすい
  - page DOM を読んで上に shell を重ねられる
  - narrative core と会話面の距離が最短になる

### Side Panel

- `Settings`
- `Debug`
- `GM / diagnostics`
- `archive full view`
- `asset queue monitor`

### Service Worker

- event relay
- reconnect
- alarm / cache / storage coordination
- UI の主 state store にはしない

## 実装順

### Step 1

- `ShellSnapshotRM` をこの文書どおりに固定
- `EquipmentRM / InventoryRM / AssetGalleryRM / RelationGraphRM` を新設

### Step 2

- Chrome 拡張 shell
  - manifest
  - content script overlay
  - side panel
  - runtime messaging

### Step 3

- `Narrative Mode`
- `Intervention Overlay`

### Step 4

- `Character Hub`
- `Inventory Hub`
- `Quest Hub`

### Step 5

- `Codex Hub`
- `Relation Graph`
- `Journal Hub`

### Step 6

- `Assets Hub`
- クライマックス画像生成導線

## 非目標

- 既存 `read_only_ui` をそのまま完成版 UI と呼ばない
- 常時フル graph を出さない
- 画像生成を truth source にしない
- UI から直接 canonical world state を mutation しない

## 既存実装との関係

- [read_only_ui.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/read_only_ui.md)
  は開発中の全体表示画面の設計であり、完成版プレイヤー UI ではない
- [gameplay_experience.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/gameplay_experience.md)
  は loop と runtime state の基礎
- [design_lock_alignment.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/design_lock_alignment.md)
  の lock は継続する

## 参照

- Ben Shneiderman, overview first / details-on-demand  
  https://www.cs.umd.edu/~ben/about.html
- Hierarchical Menu Design: Breadth, Depth, and Task Complexity  
  https://www.research.ed.ac.uk/en/publications/hierarchical-menu-design-breadth-depth-and-task-complexity-percep
- GitHub Primer: Progressive disclosure  
  https://primer.style/product/ui-patterns/progressive-disclosure/
- Chrome Side Panel API  
  https://developer.chrome.com/docs/extensions/reference/api/sidePanel
- Chrome content scripts  
  https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts
- Chrome extension service worker lifecycle  
  https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle
- ManyNets  
  https://www.cs.umd.edu/projects/hcil/manynets/
