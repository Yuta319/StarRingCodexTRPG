# Gameplay Experience

## Goal

- 1 手ごとに world が確実に動き、次 scene の意味が見えるループを作る。
- playable loop を壊さず、体験レイヤーだけを追加する。
- UI は説明と可視化だけを行い、mutation は常に `playable_loop` 経由に固定する。
- 日本語の表示文は `text/text_composer.py` で統一し、運用ルールは `docs/japanese_output_policy.md` に固定する。
- 創造神以外を固定唯一の恒久個体として扱わず、`role slot / occupant` で管理する。

## One Session

- 1 手 = 1 turn
- 6 turn = 1 session
- 2 turn ごとに phase が進む

```text
Session Start
  |
  v
Turn 1-2  偵察局面
  固有イベント候補: 黒封使節の遅着 / 灰杭誓紙の裂け目
  |
  v
Turn 3-4  圧力局面
  固有イベント候補: 環鈴宿の目録欠損 / 灰杭関所の滞列
  |
  v
Turn 5-6  決着局面
  固有イベント候補: 白灰坑路の再鳴動 / 鏡泥封庫の逆照
  |
  v
Next Session
```

各 session は phase ごとの event pool から 1 件ずつ選び、同時に active hub / active dungeon の組も切り替える。schema は変えず、`display.currentEvent / display.hub / display.dungeon` にはその session で前面化した 1 組だけを出す。

## Runtime Flow

```text
seed / world_json
  -> runner.build_bundle()
  -> campaign_state ensure
  -> scene_builder / ui_builder
  -> UI render
  -> choice click
  -> POST /api/play
  -> playable_loop.play_choice()
  -> resolution / mutation
  -> campaign_state advance
  -> runner rebuild
  -> next scene
```

自由入力を使う場合は、`custom action text -> free_action_parser -> free_action_adjudicator -> free_action_recorder -> runner rebuild` の経路を通る。raw text は保存せず、shared schema に沿った structured result だけを `campaign_state.freeActionHistory` へ残す。

## Added Content

### Role Slots And Current Occupants

- 停戦執行官 slot
  街道と停戦の執行役。停戦印の写しや使節経路を追われると糸口が見え、公開の場で責任の所在を詰められると秘密が露見しやすい。交換名簿や負傷兵の列を前にすると情へ寄りやすい。目録官 slot とは、街道維持を優先するか帳簿の穴を塞ぐかで対立する。
- 祈鐘士 slot
  儀礼と記憶の保全役。鐘譜や祈りの手順を確かめられると糸口が見え、聖遺物か鐘譜の処分を迫られると秘密が露見しやすい。聖遺物を前にすると捨てる判断が遅い。坑路案内 slot とは、封印維持と生還優先のどちらを取るかで対立する。
- 目録官 slot
  目録と条文の照合役。荷札と帳面の行を照合されると糸口が見え、公開の場で数字の差分を詰められると秘密が露見しやすい。大勢の前で数字を即答させられると嘘を重ねやすい。停戦執行官 slot とは、責任固定と街道維持のどちらを優先するかで対立する。
- 坑路案内 slot
  白灰坑路の進行役。退路や崩落図を見せられると糸口が見え、退路の出どころを掘り返されると秘密が露見しやすい。崩落音と閉所で判断が狭まる。祈鐘士 slot とは、封印維持と生還路確保のどちらを優先するかで対立する。
- 宿場差配 slot
  寝床と配給の割当役。寝床札と夜番控えを照らされると糸口が見え、配り先を公に突き合わせられると秘密が露見しやすい。空腹と寒さの列を前にすると規則より配布を優先しやすい。目録官 slot とは、列を流すか台帳を合わせるかで対立する。
- 遺物番 slot
  遺物封蔵と封箱管理役。封箱札や鍵穴を照らされると糸口が見え、封箱と中身を公に照合されると秘密が露見しやすい。封箱が割れる気配を前にすると、理屈より抱え込みを優先しやすい。祈鐘士 slot とは、封箱を閉じるか儀礼に使う品を残すかで対立する。

各 slot は current occupant を 1 人だけ持つ。UI の named cast は「この session 時点の current occupants」を出し、`next-session` では死亡・失踪・引退・粛清・継承・昇神・役職剥奪で交代しうる。

### Unique Events

- 黒封使節の遅着
  分岐: 偽印の迂回路 / 人質名簿の怨み / 裏帳面の脅し / 責任線の横流し / 通行印の立て替え
- 環鈴宿の目録欠損
  分岐: 消えた荷札 / 配給切りの噂 / 封鎖票の偽造 / 横流し倉の身代わり / 巡礼路の横抜け
- 白灰坑路の再鳴動
  分岐: 鐘脈の地図 / 崩落迂回の賭け / 聖遺物との取引 / 地上鐘の陽動 / 身代わり封書
- 灰杭誓紙の裂け目
  分岐: 継ぎ札の照合 / 検問列の切り分け / 関印の貸し越し / 夜番の口裏 / 寝床札の先渡し
- 灰杭関所の滞列
  分岐: 釜場の割り直し / 寝床札の繰り上げ / 病列の隔て布 / 通行銭の立て替え / 積荷列の夜送り
- 鏡泥封庫の逆照
  分岐: 遮り布の張り直し / 封箱の移し替え / 泥鏡の覆い鐘 / 退路灯の吊り替え / 反照遺物の借り出し

各イベントは `success / partial_success / failure` に加えて、別方向の展開を selector 付き branch として持つ。ここでいう別方向とは、事件そのものは抑えても別の場所に負担が流れる、NPC 関係だけが悪化する、秘密が先に露見する、といった横ずれの結果を指す。

### Location Content

- 拠点: 環鈴宿《カンレイ》
  `stability / supply / heat` を持つ。流通と停戦の綱渡りが主題になる。
- 拠点: 灰杭関所《エンショウ》
  `stability / supply / heat` を持つ。検問、寝床、通行権の優先順位が主題になる。
- 簡易ダンジョン: 白灰坑路
  `depth / sealIntegrity / threat` を持つ。退路と封印の両立が主題になる。
- 簡易ダンジョン: 鏡泥封庫
  `depth / sealIntegrity / threat` を持つ。遺物封蔵と持ち出し判断が主題になる。

## World-State Impact

- `campaign_state.session`
  turn, session, phase を保持する。
- `campaign_state.events`
  current event, pressure, history を保持する。
- `campaign_state.hub`
  stability, supply, heat を保持する。
- `campaign_state.dungeon`
  depth, sealIntegrity, threat を保持する。
- `campaign_state.hubCatalog / dungeonCatalog`
  session ごとに切り替わる拠点・ダンジョン候補を保持する。
- `campaign_state.sessionLoadout`
  その session の active hub / active dungeon / phase event ids を保持する。
- `campaign_state.npcs`
  `roleSlotId` を主キーに、trust, stress, affiliation, secret, weakness, conflict, memory を保持する。slot ごとに current occupant を持ち、秘密と弱みには trigger を持たせ、`hidden -> hinted -> exposed` の進行理由を追えるようにする。
- `campaign_state.choiceHistory / choiceStats`
  過去の選択と手癖を保持する。
- `campaign_state.freeActionHistory / lastFreeAction`
  自由入力の structured result と直近の裁定を保持する。保存するのは summary と hash、normalized intent、adjudication、logs だけで、raw free text は残さない。
- `campaign_state.viceTrace / tabooTrace`
  悪徳と禁忌の痕を session log と nextSessionHook に持ち越す。
- `campaign_state.vicePressure / tabooPressure / moralCorrosion / publicInfamy / hiddenCrimes / ritualPollution`
  悪徳と禁忌の世界構造を表す派生値。`cycle_state` にも同期するが、engine の正本仕様は書き換えない。
- `campaign_state.sessionEndings / lastEnding`
  6 turn 終端の小結末と legacy を保持する。小結末は `keyRoleSlotId` で role slot を記録し、表示には current occupant 名を使う。

これらは `world_state` の拡張キーであり、canonical schema の正本ではない。`world_engine` の仕様を書き換えずに、UI と session 運用のための runtime state としてのみ使う。

## UI Additions

- What Is Happening
  今の phase, current event, current objective を説明する。
- Why It Matters
  なぜこの choice が重要か、failure でも何が動くかを説明する。
- World State
  hub / dungeon / world pulse を一文で要約する。
- Actor Rail
  session progress と role slot ごとの current occupant を表示する。
- World Rail
  current event / hub / dungeon をカード表示する。
- Player Trace
  最近の choice、発覚した秘密、露見した弱点、world marks を表示する。
- Session Ending
  現在の forecast と、発生済みの小結末を表示する。

## Branch Semantics

- success だけを正解にしない。
- partial_success は「前進するが借りが残る」結果として扱う。
- failure は「圧力が増す代わりに秘密・弱点・世界 mark が露出する」結果として扱う。
- 追加 branch は「拠点は守れたが坑路が悪化する」「事件は収まるが NPC 関係が悪化する」など、別の損失を明示する。

## Session Ending

- turn 6 の choice 解決後に `lastEnding` を生成する。
- ending は `summary / whatRemained / protected / lost / carriedForward / keyNpcAftertaste` を持つ。
- ending は `hub / dungeon / event pressure / npc trust/stress` に legacy を与える。
- 次 session は turn 1 に戻るが、前 session の legacy を抱えたまま始まる。
- ending tone は `steady / mixed / grim` の 3 段で、6 手の選び方によって分かれる。

## Boundary Rules

- `world_engine / resolution / mutation` は変更しない。
- schema は変更しない。
- UI は `display` を描画するだけで、world mutation を実行しない。
- runtime 拡張は `campaign_state` に閉じ、canonical source を書き換えない。
