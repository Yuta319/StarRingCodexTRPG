# PBW Institutional Diplomacy v5

## 1. 目的

`pbw_world_institutions_v5.py` は v4 の

- 世界生成
- 勢力AI
- 外交変動
- クエスト生成
- クエスト解決
- 残滓生成
- 主人公存在級位

の上に、**明示的な制度外交**を追加したモジュールです。

relation score をそのまま「同盟」や「戦争」と見なすのではなく、
**条約・戦争状態・属国化・宗教同盟・封鎖** を別レイヤーで保持します。

これにより、外交は「雰囲気の良し悪し」ではなく、
世界に継続的効果を持つ制度として回ります。

---

## 2. 追加した制度種別

### 平時制度
- `non_aggression_pact` : 相互不可侵条約
- `trade_compact` : 通商盟約
- `religious_concordat` : 宗教同盟 / 教義裁定協約
- `defensive_alliance` : 防衛同盟

### 断続的戦時制度
- `truce` : 停戦条約

### 戦争制度
- `open_war` : 戦争状態
- `holy_war` : 聖戦布告
- `blockade` : 封鎖令

### 階層制度
- `vassalage` : 属国化盟約

---

## 3. 何を見て制度が成立するか

各 faction pair について、以下を毎季節評価します。

- 現在の relation score
- relation axes
  - `territory`
  - `trade`
  - `theology`
  - `security`
  - `legitimacy`
- 直近の faction action
  - 協調行動
  - 攻撃行動
  - 経済行動
  - 信仰行動
- 直近の quest resolution
  - 調停成功
  - 信仰裁定成功/失敗
  - 契約解決成功/失敗
  - 惨敗や収奪的成功
- pair 周辺圧力
  - 食料危機
  - 瘴気繁茂
  - 異界浸出
  - 魔王圧
  - 正統性危機

これらから制度ごとの **formation score** を計算し、
閾値を超えたものが成立します。

---

## 4. 制度は毎季節、世界へどう作用するか

### 相互不可侵条約
- 接触地域の `trade_routes`, `housing`, `law_order` を微増
- relation を少し押し上げる

### 通商盟約
- `trade_routes`, `food`, `recordkeeping` を上げる
- 両勢力 treasury を増やす

### 宗教同盟
- `faith_density`, `recordkeeping`, `cycle_stability` を上げる
- 宗教勢力の legitimacy を補強

### 防衛同盟
- `law_order` を高め、`monster_density` を少し抑える
- treasury を消費して militarization を上げる

### 停戦条約
- `housing`, `trade_routes` を少し回復
- `refugee_flow` をやや抑える

### 戦争状態 / 聖戦布告
- `food`, `housing`, `trade_routes` を削る
- `refugee_flow` を増やす
- militarization を高める
- 聖戦ではさらに `faith_density` を高め、`cycle_stability` を削る

### 封鎖令
- 対象側の `trade_routes`, `food`, `housing` を削る
- 封鎖側 treasury を微増、封鎖される側 treasury を減らす

### 属国化盟約
- tribute に応じて senior / junior の treasury を移す
- junior 側に秩序は入るが、class gap や legitimacy の歪みも溜まる

---

## 5. 維持・破綻・遷移

制度は成立したら固定ではなく、毎季節

- `support`
- `breach_risk`
- `strength`

を更新します。

### 例
- 停戦が安定 → 不可侵条約へ移行
- 戦争が宗教動員を帯びる → 聖戦へ転化
- 聖戦が調停により鈍化 → 停戦へ移行
- 属国が力を取り戻す → 反乱して戦争化
- 通商盟約が raid や blockade で崩れる

このため、外交は static なフラグではなく、
**制度そのものが歴史の中で変質**します。

---

## 6. 残滓化

制度は成立時・破綻時に地域へ legacy を残します。

例:
- 通商盟約 → `制度`, `伝承`
- 宗教同盟 → `信仰`, `正史`
- 聖戦 → `信仰`, `正史`, `魂`, `異端文書`
- 属国化 → `制度`, `正史`

これにより、外交制度も
**100年後に残る痕跡** になります。

---

## 7. 季節処理順

1. active institution の preseason effect を適用
2. v4 の季節進行
   - faction action
   - diplomacy drift
   - quest generation
   - quest resolution
   - legacy / protagonist gain
3. 既存制度の維持判定
4. 新制度の成立判定
5. relation tags へ institution 情報を反映

---

## 8. 主な出力

### `DiplomaticInstitution`
- `institution_id`
- `kind`
- `category`
- `faction_a`, `faction_b`
- `status`
- `strength`
- `support`
- `breach_risk`
- `terms`
- `tags`
- `history`

### `InstitutionalWorldState`
- `resolved`
- `institutions`
- `institution_history`
- `last_institution_events`
- `season_reports`

### export JSON
- `resolved_world`
- `institutions`
- `institution_history`
- `last_institution_events`
- `season_reports`

---

## 9. 実行例

```bash
cd /mnt/data
python pbw_world_institutions_v5.py \
  --seed 1729 \
  --regions 20 \
  --seasons 8 \
  --quests 12 \
  --budget 4 \
  --strategy balanced
```

出力:
- `pbw_generated_world_seed1729_v5_institutions.json`
- `pbw_generated_world_seed1729_v5_institutions_summary.md`

---

## 10. 今回できるようになったこと

- relation score と制度状態を分離
- 条約 / 戦争 / 属国化 / 宗教同盟 / 封鎖の明示
- 制度の維持・破綻・遷移
- 制度が world state に継続効果を及ぼす
- 制度自体が legacy として残る

---

## 11. 次に自然な段階

1. **条約条文の細分化**
   - 穀物関税
   - 巡礼路保護
   - 共同採掘権
   - 婚姻条約
   - 人質提供

2. **正式な戦争目的 / 講和条項**
   - 領土割譲
   - 朝貢義務
   - 奴隷返還
   - 聖地管理権
   - 封印管理権

3. **NPC会話直結**
   - 停戦直後の口調
   - 属国民の怨嗟
   - 通商景気の浮つき
   - 聖戦期の熱狂や倦み

4. **プレイヤー選択による条約介入**
   - 誰の名義で締結するか
   - 誰を裏切るか
   - 文言をどう捻じ曲げるか
   - どの媒体に残すか

