# PBW Diplomacy + Quest Generation v3

## 1. 目的

`pbw_world_diplomacy_quests_v3.py` は、既存の world bootstrap / faction AI v2 に対して、次の2本を**直接接続**した拡張です。

- 勢力行動 → 外交関係の変動
- 勢力行動 + 種族ごとの `micro_conflict_vectors` → クエスト自動生成

これにより、世界はプレイヤーが不在でも季節ごとに動き、
その時点で本当に起きている摩擦からクエストが立ち上がります。

---

## 2. 何を追加したか

### 2.1 外交層
各勢力ペアごとに `DiplomacyRelation` を生成します。

保持項目:
- `score` (-100..100)
- `status` （盟約 / 協調 / 友好 / 中立 / 緊張 / 敵対 / 戦争前夜）
- `axes`
  - `territory`
  - `trade`
  - `theology`
  - `security`
  - `legitimacy`
- `shared_regions`
- `border_regions`
- `last_delta`

初期値は以下から合成します。

- 勢力タイプ同士の基本相性
- 共有地域 / 隣接地域
- 教義タグの重なり
- 種族の order / trade / zeal / corruption などの駆動値
- demon_domain のような危険勢力補正

### 2.2 季節ごとの外交更新
1季節ごとに、

1. 現在の地域状態から外交ベースラインを再計算
2. その季節に実行された faction action を relation に反映

します。

たとえば:
- `grain_distribution` は周辺の state / religion / guild / tribe との関係を改善しやすい
- `raid_caravans` は state / guild と強く悪化する
- `inquisition` は高 heresy_risk の種族・勢力と悪化しやすい
- `spread_miasma` は demon_domain 以外のほぼ全勢力と悪化する
- `seal_rift` は religion / state と改善しやすいが、delver 利権と衝突することもある

### 2.3 クエスト自動生成
クエストは3種類を同時に生成します。

#### action quest
各勢力行動から1件ずつ。

- issuer = 行動した勢力
- region = 行動対象地域
- race hook = issuer 種族の `micro_conflict_vectors`
- stakes = 地域圧力 + 行動内容 + 近隣勢力の反応

例:
- 配給護衛
- 巡礼路の偽神託調査
- 開拓境界の測量交渉
- 裂け目封印の祭具回収
- 深層探索隊の救出

#### diplomacy quest
外交スコア変動や敵対/協調の強いペアから生成。

例:
- 停戦書の仲裁
- 共同勅許の護衛
- 境界衝突の火消し
- 交易盟約の裏切り調査

#### era quest
その季節の world era が強く成立している場合に生成。

例:
- 飢饉 Era なら種子・配給・播種をめぐる大局介入
- 魔素氾濫 Era なら瘴核破壊・浄化・避難政策
- 境界侵食 Era なら門閉鎖か開放かの判断

---

## 3. クエストに入る情報

各 `QuestOffer` には次が入っています。

- `source_kind` (`action` / `diplomacy` / `era`)
- `quest_type`
- `title_ja`
- `summary_ja`
- `issuer_faction_*`
- `counterparty_faction_*`
- `urgency`
- `difficulty`
- `objective_tags`
- `race_hooks`
- `pressure_hooks`
- `dialogue_mood`
- `impact_projection`
- `potential_success_effects`
- `potential_failure_effects`

特に `impact_projection` は、将来的に主人公の**因果足跡 / 存在級位**へ直結させる前提で設計しています。

---

## 4. 実行方法

```bash
cd /mnt/data
python pbw_world_diplomacy_quests_v3.py --seed 1729 --regions 20 --seasons 6 --quests 12
```

出力:
- `pbw_generated_world_seed1729_v2_diplomacy_quests.json`
- `pbw_generated_world_seed1729_v2_diplomacy_quests_summary.md`

---

## 5. いま出来ていること

- 世界生成
- 種族感受性
- 勢力生成
- 勢力AI
- Era合成
- **外交関係の数値更新**
- **クエストの自動生成**

---

## 6. 次に自然な拡張

### 6.1 クエスト解決
今は「生成」までです。次は、

- 成功
- 部分成功
- 失敗
- 裏切り成功

を region / relation / legacy に反映する層が必要です。

### 6.2 条約と戦争状態
relation score だけでなく、

- 相互不可侵
- 交易条約
- 宗教同盟
- 聖戦布告
- 封鎖
- 属国化

のような明示状態を持たせる段階です。

### 6.3 NPC 会話接続
すでに持っている発話辞書へ、

- issuer_faction
- race_hooks
- dialogue_mood
- relation status
- era name

を渡すと、クエスト発注者の第一声・二言目・三言目まで自然につながります。

### 6.4 主人公の因果足跡
`impact_projection` をそのまま使って、

- 影響人口
- 影響した制度数
- 残存媒体
- 局地/地域/世界/神話級の波及

を集計できます。

---

## 7. 方針

この v3 の重要点は、クエストをテンプレートから選ぶのではなく、

- その季節に
- その地域で
- その勢力が
- その種族性と摩擦を持って
- 本当に起こしていること

から立ち上げている点です。

つまり、クエストはシナリオ表ではなく、**世界の副産物**です。
