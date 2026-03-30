# PBW World Simulator Schema v3

## 何を変えたか
元の種族辞書は「見た目・武器・属性・文化モチーフ」辞書として非常に強かった。
この v3 ではそこを壊さず、以下を追加した。

- cosmology: 創造神・神格化・主神暦・輪廻・存在級位
- world_dynamics: 世界変数、演算子、共鳴ベクトル
- era_synthesis: Era の自動生成と自動命名
- race_simulation_profiles: 12種族の歴史反応傾向
- world_simulator_bridges: ミクロ→マクロ→メタ接続
- quest_generation_frame: 問題とクエストの自動生成枠
- sample_generated_eras: 法則から出たEra例

## 中核思想
Era は固定リストではなく、世界の支配的現象クラスタに後付けで与えられる名前である。

## race_simulation_profiles の要点
各種族に以下を追加している。

- ecology_bias
- social_bias
- sacred_bias
- historical_bias
- macro_sensitivity
- micro_conflict_vectors

これにより、同じマナ不足でも種族ごとに違う歴史反応が起きる。

## 使い方
1. 地域ごとに core_variables を更新する
2. 演算子を適用して現象クラスタを作る
3. 種族感受性と残滓で補正する
4. 支配的現象が持続したら Era を生成する
5. 公式名・民間名・異端名・年代記名を並列生成する
6. ミクロ事件と主人公の因果足跡を保存する

## 次にやるとよいこと
- 地域スキーマの追加
- 国家スキーマの追加
- 神格スキーマの追加
- 数式化
- 実際のEra生成アルゴリズム実装
