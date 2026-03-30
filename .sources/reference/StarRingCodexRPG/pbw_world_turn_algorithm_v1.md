# PBW World Turn Algorithm v1

## 0. 目的

この文書は `pbw_world_simulator_schema_v3.json` を実際に回すための、**季節ターン基準の更新アルゴリズム** を定義する。

ここでの目的は次の3つ。

1. 世界変数がプレイヤー抜きでも自律更新されること。
2. Era が固定カテゴリではなく、**世界状態のクラスタ**として抽出されること。
3. 主人公のミクロ行動が、地域・国家・宗教・神話へと伝播し、**存在級位**の上昇へ接続されること。

本仕様は以下の既存前提を維持する。

- 創造神は存在する。
- 主神が存在し、暦名は主神の名を取る。
- 神は創造神に召し上げられることで増減しうる。
- マナと魔素は別概念である。
- 12属性は戦闘属性であると同時に、地域・種族・神格・Eraの共鳴ベクトルでもある。
- 主人公は例外的な魂であり、輪廻を超えて因果足跡を蓄積する。

---

## 1. 時間構造

世界は4つの時計で動く。

### 1.1 場面時計
- 単位: 会話、買い物、移動、短休憩
- 用途: 日常パート
- 変化: 昼→夕→夜など

### 1.2 行動時計
- 単位: 戦闘ラウンド、探索手番、儀式進行
- 用途: ダンジョン、戦闘、神事
- 変化: 非常に遅い

### 1.3 季節時計
- 単位: **1シミュレーションターン = 1季節**
- 用途: 地域更新、国家更新、宗教更新、資源更新、人口更新
- 本仕様の中心

### 1.4 歴史時計
- 単位: 複数年〜複数十年
- 用途: Era抽出、主神交代、文明残滓、100年後評価

> 実装上は、場面時計と行動時計の結果を `micro_outcome_buffer` に蓄積し、
> 季節ターンの終わりにマクロへ注入する。

---

## 2. 状態モデル

## 2.1 RegionState

各地域は以下を持つ。全数値は基本的に `0..100` 正規化。

```text
RegionState
- id
- biome_tags[]
- adjacency[]
- resonance[12]                  # 火/水/風/地/光/闇/爆発/氷/雷/金/回復/精神
- dominant_races[]
- active_factions[]
- core_values:
    food
    water
    housing
    timber
    metal_stock
    medicine
    trade_routes
    labor_force
    population
    birth_rate
    death_rate
    age_structure
    refugee_flow
    monster_density
    plague_load
    legitimacy
    faith_density
    class_gap
    slavery_rate
    succession_stability
    law_order
    recordkeeping
    racial_tension
    mana_level
    miasma_level
    divine_interference
    interworld_intrusion
    dungeon_density
    cycle_stability
    soul_residue
- history_window[last 8 turns]
- legacy_media[]
- current_regional_phases[]
- pending_micro_deltas[]
```

## 2.2 FactionState

```text
FactionState
- id
- type (state / religion / guild / demon_domain / divine_faction / tribe)
- regions[]
- doctrine_tags[]
- resource_stock
- legitimacy
- militarization
- policy_profile
- hostility_map{}
- calendar_loyalty(main_god)
```

## 2.3 WorldState

```text
WorldState
- current_main_god
- calendar_year
- world_eras[]
- global_pulses[]
- regions[]
- factions[]
- era_memory[]
```

## 2.4 ProtagonistImpactBuffer

```text
ProtagonistImpactBuffer
- affected_regions[]
- affected_population
- affected_systems[]
- affected_factions[]
- medium_outputs: law/song/ritual/architecture/curse/soul_residue/place_name/etc.
- sacrifice_cost
- law_deformation
- persistence_estimate_years
- moral_polarity
- action_tags[]
```

---

## 3. 季節ターンの更新順序

### Step 0. ミクロ結果の集約
場面時計・行動時計で起きた出来事を、地域差分へ集約する。

例:
- 水路修復 → `food +6, housing +2, law_order +1`
- 異端神官救出 → `faith_density +2, legitimacy -1, heretical_seed +1`
- 深層封印破壊 → `dungeon_density +8, miasma_level +6, soul_residue +4`

### Step 1. 外因パルス適用
その季節に入る前に、世界外・世界上位・偶発的なパルスを入れる。

候補:
- 気候異常
- 主神の神託/沈黙
- 異界断裂
- 魔王の進軍
- ダンジョン噴出
- 疫病波
- 豊作/凶作
- 主神紀の儀礼年

### Step 2. 平衡点への引力
地域は、地形・共鳴・種族構成・制度残滓に応じて、固有の平衡点へ少しずつ戻ろうとする。

```text
delta_equilibrium(v) = pull_v * (target_v(region) - current_v)
```

`target_v(region)` は biome + resonance + race profile + legacy により決まる。

### Step 3. 相互作用マトリクス更新
各変数は他変数から影響を受ける。これを疎な係数行列で処理する。

```text
norm(x) = (x - 50) / 50

delta_cross(v) = scale_v * Σ( coeff[src -> v] * norm(src) )
```

### Step 4. 勢力方針更新
国家・宗教・ギルド・魔王領・神派閥が、その時点の圧力に応じて方針を変える。

例:
- 飢饉圧高 → 配給、略奪、輸入、徴税強化のどれか
- 神託過剰 → 異端審問、巡礼徴発、神殿増築
- 魔素過剰 → 封鎖、狩猟、利用、密輸

### Step 5. 種族反応補正
各地域の支配種族構成に応じて、同じ現象の増減が変わる。

例:
- 魚人種比率高 + 食料不足 → 海上輸送で一部緩和
- 小人種比率高 + マナ不足 + 地/金共鳴 → 鍛造衰退が加速
- 妖精種比率高 + マナ過剰 + 精神共鳴 → 夢害・幻視が増幅

### Step 6. 超常生態更新
マナ・魔素・輪廻安定・神意干渉・ダンジョン密度・異界侵食をまとめて更新する。

ここでは **マナ** と **魔素** を別に扱う。

- マナ: 文明・術式・祝福・工芸・神殿回路
- 魔素: 魔物・呪い・変異・怪異・ダンジョン・世界の傷

### Step 7. 人口・移民・衝突更新
- 難民移動
- 奴隷流入/逃亡
- 種族摩擦
- 疫病による死
- 出生回復
- 強制移住

### Step 8. 圧力計算
現象候補のための圧力値を計算する。

例:
- food_stress
- housing_stress
- plague_pressure
- legitimacy_crisis
- faith_runaway
- mana_crisis
- miasma_bloom
- dungeon_fixation
- demon_lord_pressure
- interworld_bleed

### Step 9. 現象候補抽出
各地域で、`変数 × 演算子` の組み合わせから現象候補を作る。

### Step 10. Era合成
現象候補が複数地域・複数勢力・複数季節にまたがって持続した場合、
`regional_phase` または `world_era` へ昇格させる。

### Step 11. 残滓堆積と主人公評価
- 法、歌、儀礼、建築、呪い、地名、魂残滓に変換
- 主人公の因果足跡を媒体別に記録
- 存在級位ポイントを増加

---

## 4. 基本演算子

Era を固定の種類で増やすのではなく、以下の演算子を世界変数へ作用させる。

- scarcity（欠乏）
- surplus（過剰）
- imbalance（偏在）
- contamination（汚染）
- stagnation（停滞）
- acceleration（加速）
- rupture（断絶）
- runaway（暴走）
- resonance（共鳴）
- inversion（反転）
- fixation（固着）
- collapse（崩落）

### 4.1 演算子の基本式

`x_t` を今ターン値、`x_prev` を前ターン値とする。

```text
scarcity(x; low)      = clamp((low - x) / low, 0, 1)
surplus(x; high)      = clamp((x - high) / (100 - high), 0, 1)
imbalance(a, b)       = abs(a - b) / 100
acceleration(x)       = clamp(abs(x_t - x_prev) / 20, 0, 1)
rupture(x)            = clamp(max(0, x_prev - x_t) / 25, 0, 1)
collapse(x)           = scarcity(x; 35) * clamp((x_prev - x_t) / 15, 0, 1)
fixation(x)           = surplus(x; 70) * clamp(1 - abs(x_t - x_prev) / 10, 0, 1)
runaway(x)            = surplus(x; 70) * clamp(max(0, x_t - x_prev) / 15, 0, 1)
stagnation(x)         = clamp(1 - abs(x_t - x_prev) / 8, 0, 1) * clamp(x_t / 100, 0, 1)
contamination(pure, pollute) = clamp(pollute / (pure + pollute + 1), 0, 1)
```

### 4.2 共鳴増幅

```text
resonance_amp(region, signature) = 1 + 0.5 * dot(norm_resonance(region), signature)
```

- `signature` は現象ごとの12属性重みベクトル
- 値域は概ね `0.5..1.5`

### 4.3 種族感受性増幅

```text
race_amp(region, issue_tag) = weighted_mean( race_sensitivity[race][issue_tag], population_share )
```

出力は `0.7..1.4` を想定。

### 4.4 残滓増幅

```text
legacy_amp(region, issue_tag) = 1 + 0.15 * matching_legacy_count
```

例:
- かつての飢饉税が残る地域では `food_scarcity` が増幅
- かつての神戦巡礼路が残る地域では `divine_war` が増幅

---

## 5. キー圧力の計算式

以下は最小構成。全て `0..1` に正規化して使う。

### 5.1 食料圧

```text
food_stress =
  0.35 * scarcity(food; 40)
+ 0.20 * rupture(trade_routes)
+ 0.15 * surplus(population; 65)
+ 0.15 * (plague_load / 100)
+ 0.15 * (refugee_flow / 100)
```

### 5.2 住居圧

```text
housing_stress =
  0.40 * scarcity(housing; 45)
+ 0.20 * surplus(population; 65)
+ 0.20 * (refugee_flow / 100)
+ 0.10 * rupture(law_order)
+ 0.10 * contamination(housing, miasma_level)
```

### 5.3 正統性危機

```text
legitimacy_crisis =
  0.30 * collapse(legitimacy)
+ 0.20 * (class_gap / 100)
+ 0.15 * food_stress
+ 0.15 * scarcity(succession_stability; 45)
+ 0.10 * (slavery_rate / 100)
+ 0.10 * faith_schism
```

### 5.4 信仰分裂 / 信仰暴走

```text
faith_schism =
  0.30 * runaway(faith_density)
+ 0.20 * (divine_interference / 100)
+ 0.20 * legitimacy_crisis
+ 0.15 * scarcity(recordkeeping; 40)
+ 0.15 * imbalance(faith_density, law_order)
```

### 5.5 マナ危機

```text
mana_crisis =
  0.40 * scarcity(mana_level; 40)
+ 0.20 * rupture(cycle_stability)
+ 0.20 * (interworld_intrusion / 100)
+ 0.20 * imbalance(mana_level, population)
```

### 5.6 マナ過飽和

```text
mana_surge =
  0.35 * surplus(mana_level; 70)
+ 0.20 * runaway(divine_interference)
+ 0.15 * imbalance(mana_level, cycle_stability)
+ 0.15 * (faith_density / 100)
+ 0.15 * resonance(light/water/mind signature)
```

### 5.7 魔素繁茂

```text
miasma_bloom =
  0.35 * surplus(miasma_level; 70)
+ 0.20 * fixation(dungeon_density)
+ 0.15 * rupture(cycle_stability)
+ 0.15 * (monster_density / 100)
+ 0.15 * (soul_residue / 100)
```

### 5.8 ダンジョン固着

```text
dungeon_fixation =
  0.35 * fixation(dungeon_density)
+ 0.20 * surplus(miasma_level; 70)
+ 0.20 * (soul_residue / 100)
+ 0.15 * rupture(cycle_stability)
+ 0.10 * imbalance(dungeon_density, law_order)
```

### 5.9 異界浸出

```text
interworld_bleed =
  0.40 * runaway(interworld_intrusion)
+ 0.20 * rupture(cycle_stability)
+ 0.15 * surplus(mana_level; 70)
+ 0.15 * surplus(miasma_level; 70)
+ 0.10 * scarcity(recordkeeping; 40)
```

### 5.10 魔王圧

```text
demon_lord_pressure =
  0.30 * miasma_bloom
+ 0.20 * legitimacy_crisis
+ 0.20 * faith_schism
+ 0.15 * scarcity(law_order; 40)
+ 0.15 * (monster_density / 100)
```

> 重要なのは、Era をこの圧力の最大値だけで直決めしないこと。
> まず現象候補を作り、その後クラスタリングする。

---

## 6. 現象候補の生成

各地域において、`変数 × 演算子` から現象候補を作る。

例:
- `mana_level × surplus`
- `food × scarcity`
- `interworld_intrusion × runaway`
- `legitimacy × collapse`
- `dungeon_density × fixation`

### 6.1 候補スコア

```text
phenomenon_score =
  base_operator_score
* family_affinity
* resonance_amp
* race_amp
* legacy_amp
* duration_amp
* severity_amp
```

#### 各項目
- `base_operator_score`: 演算子の出力値
- `family_affinity`: その変数にその演算子がどれだけ自然か
- `resonance_amp`: 地域共鳴との一致
- `race_amp`: 主要種族構成との一致
- `legacy_amp`: 過去残滓の一致
- `duration_amp`: 直近数ターン継続しているか
- `severity_amp`: 圧力値や被害人口から導く強度

### 6.2 タグ生成

候補にはタグを付与する。

例:

```text
mana_level × surplus
-> [mana, surplus, miracle, overload, dream, sanctification]

food × scarcity
-> [food, scarcity, famine, migration, hoarding]

miasma_level × surplus
-> [miasma, corruption, monster, mutation, dungeon]
```

タグが Era 命名・クエスト生成・勢力反応の橋になる。

---

## 7. Era 合成

## 7.1 Regional Phase

同一地域または隣接地域で、類似タグを持つ現象候補が2〜4季節継続したら `regional_phase` 候補になる。

```text
regional_phase_score =
  mean(phenomenon_score)
* adjacency_coverage
* duration_factor
* faction_involvement
```

しきい値目安: `>= 0.55`

## 7.2 World Era

複数の `regional_phase` が、

- 共通タグを持ち
- 複数勢力に跨り
- 大陸規模に広がり
- 少なくとも 6 季節以上継続

した場合、`world_era` に昇格する。

```text
world_era_score =
  0.30 * regional_phase_mean
+ 0.25 * geographic_coverage
+ 0.20 * duration_factor
+ 0.15 * meta_structure_involvement
+ 0.10 * historical_inertia
```

しきい値目安: `>= 0.68`

## 7.3 歴史慣性

旧Eraが消えても、以下が高ければ移行相を残す。

- 制度残滓
- 物流習慣
- 祭礼
- 怨霊/魂残滓
- 神話記録
- 建築残存

```text
historical_inertia = min(1.0, 0.15 * legacy_media_count + 0.25 * average_remaining_intensity)
```

---

## 8. Era命名アルゴリズム

Era 名は単一ではなく、**公式名 / 民間名 / 異端名 / 年代記名** を並列生成する。

## 8.1 命名材料

### 主因辞書
- food scarcity → 灰麦 / 施穀 / 配給 / 痩灯
- mana surplus → 星脈 / 奇跡 / 過飽和 / 白潮夢
- miasma surplus → 瘴 / 深穴 / 黒胞子 / 灰角
- legitimacy collapse → 断冠 / 簒奪 / 裂印 / 空位
- dungeon fixation → 深層 / 穴城 / 固洞 / 封鎖
- interworld bleed → 異界 / 裂境 / 向こう側 / 逆潮

### 社会相辞書
- 再編 / 戦役 / 令 / 期 / 歳月 / 年 / 時代 / 乱

### 感覚辞書（popular）
- 燃えた / 溢れた / 痩せた / 眠らぬ / 黒い / 白い / 泣く / 鳴る

## 8.2 文法

```text
official   = [主因名詞] + [再編/統制/戦役/期/令]
popular    = [色/自然物/日用品/身体感覚] + [痩せた/燃えた/溢れた/眠らぬ] + [年/時代]
heretical  = [偽/断/逆/穢] + [光/契約/潮/輪/冠] + [期/暦/禍]
chronicle  = （主神名）暦[年数]年より続く[原因+社会相+期]
```

## 8.3 例

現象クラスタ:
- mana surplus
- water/mind resonance
- faith runaway
- elf/fey prevalence

生成名:
- 公式名: `星脈再誦期`
- 民間名: `白く眠らぬ年`
- 異端名: `偽潮禍`
- 年代記名: `ミレイア暦三一二年より続く星脈祈誦期`

---

## 9. 主人公の因果足跡と存在級位

存在級位は戦闘勝利数ではなく、**世界に残した因果足跡** で上昇する。

schema にある成長軸をそのまま使用する。

- 影響人口
- 影響層の数
- 継続年数
- 残った媒体
- 払った代償
- 既存法則の変形量

### 9.1 因果足跡スコア

```text
impact_tier:
  micro = 1
  local = 2
  regional = 4
  macro = 8
  meta = 13
  mythic = 21
```

```text
causal_footprint =
  sqrt(affected_population + 1)
* impact_tier
* (0.6 + 0.2 * systems_affected_count)
* (0.5 + persistence_years / 20)
* (1.0 + sacrifice_cost)
* (1.0 + law_deformation)
```

### 9.2 媒体重み

```text
law          1.30
architecture 1.15
ritual       1.20
song         0.90
chronicle    1.00
curse        1.10
soul_residue 1.35
place_name   0.85
```

```text
vessel_gain = Σ( causal_footprint * medium_weight * medium_intensity )
```

### 9.3 ランクしきい値例

```text
R0: 凡魂        0
R1: 余燼         120
R2: 影刻         300
R3: 史触         650
R4: 国脈         1200
R5: 神話辺縁     2200
R6: 召し上げ候補 4000
R7: 神格接続     7000
```

> これにより、村一つを救う、飢饉を遅らせる、宗派を残す、主神の解釈を変える、といった行為が、
> すべて異なる経路で魂の器を拡張できる。

---

## 10. クエスト生成への接続

Era と現象タグは、そのままクエスト生成の上位入力になる。

## 10.1 上位入力
- 現在の regional_phase
- 現在の world_era
- 地域の macro pressure 上位3つ
- 支配種族の micro_conflict_vectors
- 勢力対立
- 残滓媒体

## 10.2 生成パターン

例:
- `food scarcity + debt + family + human`
  - 穀物護送
  - 配給簿改竄
  - 子売り阻止/斡旋

- `mana surplus + dream + fey + faith runaway`
  - 予言依存者の捜索
  - 偽神託の暴露
  - 夢から帰れない子供の救出

- `dungeon fixation + dwarf + gemfolk + law decline`
  - 深層封鎖設備の修復
  - 鉱晶核の奪還
  - 遺物流通を巡るギルド抗争

---

## 11. 1ターン疑似コード

```python
for season in world.seasons:
    collect_micro_outcomes(world)
    apply_global_pulses(world)

    for region in world.regions:
        apply_equilibrium_pull(region)
        apply_cross_influences(region)
        apply_faction_policies(region, world.factions)
        apply_racial_modifiers(region)
        update_supernatural_ecology(region)
        update_population_and_migration(region)
        compute_pressures(region)
        region.phenomena = generate_phenomena(region)

    world.regional_phases = cluster_regional_phases(world.regions)
    world.world_era = synthesize_world_era(world.regional_phases)
    apply_era_inertia(world)
    deposit_legacies(world)
    evaluate_protagonist_footprint(world)
```

---

## 12. 生成されうる Era はどう無限化されるか

厳密な意味での数学的無限ではないが、以下の直積で非常に大きな多様性を持てる。

- 変数 30種前後
- 演算子 12種
- 12属性共鳴ベクトル
- 12種族の感受性
- 地域差
- 勢力差
- 旧Era残滓
- 命名辞書の差

つまり、Era の種類を列挙するのではなく、
**有限の法則系から、際限なく新しい時代が立ち上がる** 設計にする。

---

## 13. 実装優先順位

### Phase 1
- RegionState
- 季節ターン
- 外因パルス
- 基本圧力 6種
- 現象候補生成
- regional_phase 抽出

### Phase 2
- FactionState
- 種族感受性増幅
- world_era 合成
- 命名アルゴリズム
- 残滓媒体

### Phase 3
- 主神交代
- 神格化
- 主人公存在級位
- 100年後評価
- 自動年代記生成

---

## 14. 実装上の重要原則

1. Era はイベントリストから選ばない。**状態クラスタから抽出する。**
2. マナと魔素を混ぜない。
3. 種族を職業テンプレにしない。**歴史反応傾向として使う。**
4. 主人公の価値を戦闘力だけで測らない。**因果足跡で測る。**
5. 旧Eraの残滓を必ず残す。そうしないと世界が薄くなる。

