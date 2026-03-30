# PBW World Historical Nodes v7

この層は、条約条項や制度の破綻を「関係値の悪化」では終わらせず、  
**世界史を動かす事件ノード** として昇格させるための standalone 実装です。

## 目的

- 穀物関税違反
- 巡礼路襲撃
- 共同採掘権侵害
- 人質交換破綻
- 朝貢停止
- 非武装境界破り
- 聖遺物保管争奪

のような事態を、単なる外交ペナルティではなく

1. 条項違反の検出  
2. 制度破綻リスクの集計  
3. **HistoricalEventNode** への昇格  
4. 事件連鎖 (**EventChain**) への接続  
5. 専用クエストへの変換  
6. Era 推進力 (`era_impetus`) の付与  

として扱う。

---

## コア構造

### RegionState
地域単位の生活・治安・信仰・魔素状態を持つ。

### FactionState
国家、宗教勢力、ギルド、魔王 / 魔族勢力など。

### TreatyClause
個別条項。  
`support / strain / intensity / status / last_tension` を持つ。

### InstitutionState
条約・封鎖・聖戦・属国化盟約など。  
複数の条項を束ねる。

### HistoricalEventNode
条項違反や制度破綻が昇格した、世界史上の事件ノード。

### EventChain
同系統の事件が継続・再燃・連鎖した痕跡。

---

## 流れ

1. 世界側の季節ドリフトを適用
2. 各条項の tension を計算
3. violated になった条項を事件ノード化
4. breach_risk が高すぎる制度は制度崩壊ノード化
5. 同系統の事件を chain に束ねる
6. 各ノードに専用クエストを1本生成

---

## 事件ファミリー

- `food_crisis`
- `pilgrimage_conflict`
- `mining_conflict`
- `deep_delving_conflict`
- `succession_conflict`
- `frontier_militarization`
- `religious_schism`
- `tributary_revolt`
- `hostage_breakdown`
- `relic_dispute`
- `institutional_breakdown`

---

## 今回の意味

ここまでで、世界は

- 条約を結ぶ
- 条項が軋む
- その違反が火種になる
- 火種が歴史事件へ昇格する
- 事件が専用クエストになる
- 事件が連鎖し、Era を押す

ところまで来ています。

つまり、もはや「クエストが世界に影響する」だけでなく、  
**世界の制度そのものが、プレイヤーに介入を要求する歴史事件を生む** 段階です。

---

## 次段

この次に自然なのは 2 方向です。

### A. 事件ノードの解決層
- 事件クエストの成否
- 条項修復 / 新条項追加
- 制度再編
- 鎮圧 / 和解 / 神罰 / 聖戦化
- 歴史媒体への固定

### B. 神々・主神暦・輪廻接続
- 神託で事件が拡大・収束する
- 昇神英雄が事件ノードを奪う
- 主神交代が制度外交を再編する
- 輪廻の歪みが同じ事件を別時代に再発させる

A を先にやるとゲームループが強くなり、  
B まで入れると設計第一部の最終段に入れます。