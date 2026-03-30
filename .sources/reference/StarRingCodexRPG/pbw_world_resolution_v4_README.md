# PBW Quest Resolution + Causal Legacy v4

## 1. 目的

`pbw_world_resolution_v4.py` は v3 の

- 世界生成
- 勢力AI
- 外交更新
- クエスト生成

の上に、**クエスト解決層**を追加したモジュールです。

今回追加したのは次の4点です。

1. **主人公介入の自動選定**
2. **クエスト成否の判定**
3. **world state / diplomacy / faction legitimacy / legacy への反映**
4. **因果足跡 → 存在級位上昇**

これにより、クエストは単なる表示リストではなく、
**季節ごとに本当に世界を変える歴史結節点**として扱われます。

---

## 2. 追加した概念

### 2.1 主人公方針 (`strategy`)
現在は以下の5種を実装しています。

- `balanced`
- `diplomat`
- `delver`
- `devout`
- `shadow`

各方針は以下を持ちます。

- aptitudes
  - `combat`
  - `diplomacy`
  - `ritual`
  - `stealth`
  - `stewardship`
  - `authority`
- source bias
  - `action`
  - `diplomacy`
  - `era`
- tag bias
- `risk`
- `opportunism`
- `mercy`

これにより、同じ世界・同じ seed でも、
**主人公方針を変えるだけで歴史への介入点が変わります。**

### 2.2 クエスト解決結果
現在の結果カテゴリ:

- `大成`
- `成功`
- `部分成功`
- `失敗`
- `惨敗`
- `自力解決`
- `継続小康`
- `放置悪化`
- `収奪的成功`

前4つは主に主人公介入時、
後4つは世界側の自律解決や機会主義的介入で出やすい結果です。

### 2.3 媒体別残滓
各解決は、地域に `LegacyMedium` を残します。

例:
- `制度`
- `建築`
- `信仰`
- `伝承`
- `正史`
- `異端文書`
- `魂`

これらは次季以降の地域状態と、プレイヤーの存在級位に波及します。

### 2.4 因果足跡 / 存在級位
主人公介入は `ProtagonistImpact` に変換され、
`v1.evaluate_protagonist_gain()` に通されます。

評価要素:
- `affected_population`
- `systems_affected_count`
- `impact_tier`
- `persistence_years`
- `sacrifice_cost`
- `law_deformation`
- `media_outputs`

これにより、戦闘勝利だけでなく、
**制度・信仰・外交・Era への介入そのものが主人公を拡張**します。

---

## 3. 季節ごとの処理順

1. `v3.advance_extended_world_one_season()`
   - 勢力行動
   - 外交変動
   - クエスト生成
2. 主人公介入対象を `intervention_budget` 件だけ選定
3. 各クエストを
   - `protagonist`
   - `background`
   のどちらかで解決
4. 地域値更新
5. 外交更新
6. 勢力正統性 / 財政更新
7. 残滓生成
8. 主人公の因果足跡計算

---

## 4. 主要出力

### 4.1 `QuestResolution`
保持項目:

- `outcome`
- `resolution_mode`
- `score`
- `applied_effects`
- `diplomacy_delta`
- `faction_delta`
- `legacies_created`
- `protagonist_gain`

### 4.2 `ProtagonistState`
保持項目:

- `vessel_points`
- `existence_grade`
- `existence_title`
- `media_totals`
- `gain_history`

### 4.3 export JSON
`export_resolved_world()` は以下を返します。

- `protagonist`
- `base_extended_world`
- `last_generated_quests`
- `last_resolutions`
- `resolution_history`
- `season_reports`

---

## 5. 実行方法

```bash
cd /mnt/data
python pbw_world_resolution_v4.py \
  --seed 1729 \
  --regions 20 \
  --seasons 6 \
  --quests 12 \
  --budget 4 \
  --strategy balanced
```

主な出力:

- `pbw_generated_world_seed1729_v3_resolution.json`
- `pbw_generated_world_seed1729_v3_resolution_summary.md`

---

## 6. いま出来ていること

- 世界生成
- 種族ランタイム感受性
- 勢力AI
- 外交変動
- クエスト生成
- **クエスト解決**
- **残滓生成**
- **主人公存在級位の上昇**

---

## 7. 次に自然な拡張

### 7.1 明示的な条約 / 戦争状態
relation score だけでなく、

- 相互不可侵
- 交易盟約
- 宗教同盟
- 聖戦布告
- 封鎖
- 属国化

を明示状態として持たせる段階です。

### 7.2 NPC 会話接続
既存の発話辞書へ、

- `outcome`
- `relation status`
- `era`
- `issuer/counterparty`
- `media residue`

を渡すことで、
クエスト受注時・解決後の会話温度差を自然につなげられます。

### 7.3 主人公の選択 UI
現在は方針ベースの自動介入です。
次段では、

- どのクエストに入るか
- どの立場で入るか
- 誰を切り捨てるか
- 誰の名義で結果を残すか

をプレイヤー入力で分岐させられます。

### 7.4 神格化分岐
媒体別累積と主神派・異端派・民間伝承の比率から、

- 英雄聖人化
- 異端の守護霊化
- 堕した偽神化
- 管理者候補化

へ分岐できるようになります。

---

## 8. 方針

v4 の意図は、

> クエストの成否をその場の報酬に閉じず、
> 地域・制度・外交・神話残滓へ接続すること

です。

つまり、クエストは「終わる」のではなく、
**解決された瞬間から世界史へ変換される**ようにしています。
