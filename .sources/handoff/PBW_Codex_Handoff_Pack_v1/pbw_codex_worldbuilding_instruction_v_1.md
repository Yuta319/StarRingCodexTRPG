# Codex向け指示書：異世界転生PBW/物語生成ゲーム 世界観・文化圏・命名体系 実装仕様 v1

## 0. この指示書の目的

本指示書は、異世界転生を主軸とするPBW/物語生成RPGにおいて、以下の要素を矛盾なく実装可能な形でCodexに渡すための、世界設定・データ構造・命名ルール・実装優先順位を定義するものである。

対象範囲は以下を含む。

- 文化圏、種族、部族、氏族の分離定義
- 成人・洗礼・元服・加入・葬送などの通過儀礼
- 祭礼、祝祭、催事、記念日などの年間イベント
- 人名、地名、称号、武器、防具、道具、薬、魔法、スキル、古代遺物の命名体系
- 量産品と固有名持ち装備の差異
- 真名・古名・伏せ字・覚醒段階のUI仕様
- 種族分類と俗称・蔑称の文化的運用
- 魔族の再分類
- 主人公の周回・介入によって文化や祭りが増える仕組み
- 将来的な生成AI/物語生成システムが参照しやすいデータ構造

本仕様は、単なる雰囲気作りではなく、世界内の命名・文化・社会制度・UI表現・成長システムを一貫させるための基盤仕様である。

---

## 1. 設計理念

### 1-1. 基本方針

このゲームでは、名前や文化は演出要素ではなく、世界構造そのものとして扱うこと。

以下を厳守すること。

1. すべてに固有名を付けないこと
2. 名の有無・重さ自体が世界観や階級差を表すこと
3. 種族と文化圏を同一視しないこと
4. 同一種族でも文化圏により価値観・命名・儀礼・祭礼が変わること
5. 世界内の呼称とUI上の可読性を両立すること
6. 後から文化圏・種族・遺物・流派・祭りを追加しやすいデータ構造にすること

### 1-2. 最重要テーマ

このゲームにおける中心思想は以下の通り。

- 異世界らしさは単語の装飾ではなく、文化・歴史・制度・言語の一貫性から生まれる
- 真名や古名は万能な飾りではなく、神話性・危険性・契約性を背負う特別なレイヤーである
- 主人公の転生・周回・介入によって、世界そのものが儀礼、祭礼、制式名称、俗称を変化させる
- プレイヤーは物語を消費するだけでなく、文化の改変者・神話の発生源となる

---

## 2. 用語定義

### 2-1. 種族

身体的特性、寿命、知覚、再生、魔力適性などの生物学的・存在論的分類。

例：
- 人類種（ヒューマン）
- 長命種（エルフ）
- 小人種（ドワーフ）
- 獣人種（ワービースト）
- 翼人種（バードフォーク）
- 竜鱗種（ドラゴニュート）
- 妖精種（フェイ）
- 魔生種（デモニアン）
- 堕性種（フォールン）

### 2-2. 部族・氏族・家系

血縁、婚姻圏、先祖、紋章、継承、祖霊などに紐づく共同体単位。

例：
- 灰狼氏族
- 白梢家
- 赤冠家
- 潮鴉船団
- 月蝕侯家

### 2-3. 文化圏

宗教、統治、暦、祭礼、通過儀礼、命名規則、社会制度、禁忌などを共有する文化単位。

例：
- 聖暦王国圏
- 灰鉄帝政圏
- 樹海星詠圏
- 北境牙氏族圏
- 潮路商邦圏
- 天幕遊牧圏
- 炉都坑道圏
- 冥契夜界圏

### 2-4. 真名

世界内で本質名・固有存在名・契約名として扱われる名称。単なる読み仮名ではなく、存在・権能・歴史に接続する名であること。

### 2-5. 古名

古代語、神話語、儀礼語、失伝語などによる古層の名称。現代人は完全理解できない場合がある。

### 2-6. 現代解釈名

現代人・現在文明・鑑定機関・冒険者・軍・学者などが便宜上付けた理解用名称。

例：
- 古代黒大剣《終ノ門ヲ啓クモノ》

---

## 3. 表記ルール

### 3-1. 原則

本ゲームでは、漢字のみだと説明性は高いがファンタジー感が弱くなりやすいため、以下の多層表記を採用する。

### 3-2. 種族・概念表記

種族や重要概念は原則として以下の形式。

- 漢字 + 全角括弧内カタカナ/外来語表記

例：
- 長命種（エルフ）
- 獣人種（ワービースト）
- 真名（トゥルーネーム）
- 成人儀礼（イニシエーション）
- 契印（シグナ）

備考：初出では併記し、以後は文脈に応じて漢字・カタカナ・略称のみでも可。

### 3-3. 一般魔法・一般技能

一般魔法・一般戦技・一般技能は原則として以下の形式。

- 漢字《カタカナ語》

例：
- 土壁《アースウォール》
- 火球《ファイアボール》
- 受け流し《パリィ》
- 強撃《パワーストライク》
- 影縫い《シャドウバインド》

### 3-4. 固有名・銘・異名・儀礼名

固有名は原則として以下の形式。

- 詩的和訳・異名・称号句《真名・正式名》

例：
- 傲慢なる水竜王《アクアハーティア》
- 白誓の剣《ルクス・オース》
- 灰冠の断罪剣《グレイ・レクイエム》

### 3-5. 古代遺物

古代遺物は原則として以下の形式。

- 現代解釈名《真名・古名》

例：
- 古代黒大剣《終ノ門ヲ啓クモノ》
- 古代星杖《アストラ・レクイエム》
- 古代祭冠《白キ枝ノ王冠》

### 3-6. 未解放時の表記

真名や古名が未解読・未適合・未契約・未覚醒の場合、以下の伏せ字表記を許可する。

例：
- 古代黒大剣《◼◼◼◼◼◼◼◼◼》
- 古代祭冠《◼◼◼◼◼◼》

### 3-7. 英語名の扱い

英語名は本文の主表記ではなく、補助ラベルとして扱うこと。

使用箇所：
- 図鑑
- 詳細UI
- データベース内部ラベル
- 技一覧
- 設定資料

例：
- 土壁《アースウォール》 / Earth Wall
- 受け流し《パリィ》 / Parry

禁止事項：
- すべての本文表記を英語に寄せないこと
- 世界内の正式言語を無原則に英語化しないこと

---

## 4. 名の階層

世界内における名称は、以下の階層構造を持つこと。

### 4-1. 名の階層一覧

1. 無銘品
2. 工房銘
3. 型式名
4. 通称
5. 儀礼名
6. 固有名
7. 真名・古名

### 4-2. 各階層の定義

#### 無銘品
単なる機能・材質・用途で呼ばれる一般物。

例：
- 鉄剣
- 革鎧
- 治癒薬
- 狩猟弓

#### 工房銘
工房や製作者の刻印・銘が入る中級〜上級品。

例：
- 黒炉工房製鋼短剣
- ベルク鍛鋼の長剣

#### 型式名
軍、国家、工房連盟、学院、神殿などが制式化した規格名。

例：
- 王都歩兵剣三式
- 北辺軽騎兵槍二型
- 地属性防壁術第一位階

#### 通称
兵士、商人、冒険者、庶民などが現場で使う俗称。

例：
- 狼殺し
- 青瓶
- 骨割り

#### 儀礼名
祭祀、継承、奉納、洗礼、神殿認定、王家継承などに伴って与えられる名。

例：
- 灰祓いの冠
- 奉灯剣
- 誓冠の外套

#### 固有名
一点物や歴史的実績を持つ装備・術式・遺物にのみ与えられる正式な個別名。

例：
- 傲慢なる水竜王《アクアハーティア》
- 冬牙の斧《ウルフファング》

#### 真名・古名
神話性、本質、契約、禁忌、古代権能に接続する名称。

例：
- 終ノ門ヲ啓クモノ
- 白キ枝ノ王冠

### 4-3. 実装上の推奨出現比率

- 無銘品：70〜85%
- 工房銘・型式名あり：10〜20%
- 通称持ち：3〜8%
- 儀礼名・継承名あり：1〜3%
- 固有名持ち：0.5〜1%
- 真名級：ごく少数

---

## 5. 命名権

名前は自動で生えるのではなく、誰が付けるかを持たせること。

### 5-1. 命名権者

- 市場
- 工房
- 軍
- 神殿
- 貴族家
- 流派
- 持ち主
- 歴史
- 古代文明

### 5-2. 同一対象の多重名称を許可する

同じ武器でも、複数の名称が共存してよい。

例：
- 市場名：鉄の長剣
- 工房銘：ローデン工房製鋼剣
- 軍型式名：北辺守備隊制式剣二式
- 兵士通称：狼殺し
- 儀礼名：灰祓いの剣
- 後世伝承名：《冬吠》

この多重名称を前提にデータ構造を組むこと。

---

## 6. 種族分類の基本仕様

### 6-1. 原則

種族は「世界内の学術分類」と「一般社会の呼称」を分けること。

### 6-2. プレイアブル候補を含む正式分類

- 人類種（ヒューマン）
- 長命種（エルフ）
- 小人種（ドワーフ）
- 獣人種（ワービースト）
- 翼人種（バードフォーク）
- 竜鱗種（ドラゴニュート）
- 妖精種（フェイ）
- 魔生種（デモニアン）
- 堕性種（フォールン）

備考：解放条件により追加種族を後から増やせる拡張設計にすること。

### 6-3. 一般社会の俗称・蔑称を別持ちにする

例：
- 長耳
- 鳥頭
- 毛人
- 鱗持ち
- 岩チビ
- 夜連中
- 角付き

### 6-4. 蔑称の階層

- 軽口レベル
- 露骨な侮蔑
- 禁句レベル

NPC台詞では関係性、文化圏、時代、戦争史に応じて使い分けること。

---

## 7. 魔族分類の基本仕様

### 7-1. 原則

魔族を単一種族として扱わず、「魔性側に属する存在の上位分類」として扱うこと。

### 7-2. 下位分類

#### 魔生種（デモニアン）

生まれつき魔性圏に属する人型・社会性を持つ種族。国家・文化・家系・法を持つ。プレイアブル向き。

#### 魔獣種（デモンビースト）

魔力汚染・魔界環境に適応した獣型存在。知性幅あり。

#### 魔霊種（インファーナル・スピリット）

霊体、呪詛体、契約体、影存在など。

#### 堕性種（フォールン）

本来別種だったが、堕化・汚染・呪い・変質で魔性化したもの。

#### 古魔種（プライモーディアル / アークデモニアン系）

神話時代・古代文明・深淵的権能に属する高位存在。

### 7-3. 社会的呼称のズレを許可

例：
- 学者：魔生種 / 堕性種 / 古魔種
- 庶民：魔族 / 角付き / 夜の民
- 神殿：異端魔性 / 堕ちし者
- 軍：高脅威魔性群

---

## 8. 文化圏テンプレート

以下の8文化圏を初期実装用テンプレートとする。

1. 聖暦王国圏
2. 灰鉄帝政圏
3. 樹海星詠圏
4. 北境牙氏族圏
5. 潮路商邦圏
6. 天幕遊牧圏
7. 炉都坑道圏
8. 冥契夜界圏

### 8-1. 聖暦王国圏

特徴：王権、神殿、洗礼、騎士、季節祭、農耕共同体

主要要素：
- 命名洗礼
- 成人誓約
- 騎士叙任
- 婚姻祝別
- 葬送灯祷
- 春耕祝祭
- 夏至の光祭
- 秋穣祭
- 冬灯の夜
- 聖人追想日

命名傾向語：
- 光
- 白
- 誓い
- 守護
- 獅子
- 晨
- 花

### 8-2. 灰鉄帝政圏

特徴：軍政、官僚、戸籍、型式、記録、国家祭祀

主要要素：
- 登録命名
- 徴役成年
- 軍印授与
- 昇格式
- 名誉葬
- 建国軍閲祭
- 皇祖記念日
- 戦勝凱旋祭
- 鉄火工廠祭

命名傾向語：
- 灰
- 鉄
- 冠
- 黒陽
- 勲
- 断
- 軍

### 8-3. 樹海星詠圏

特徴：長命種、精霊契約、秘名、歌、月、星、巡礼、森の記憶

主要要素：
- 初夢見
- 月下巡礼
- 真名授受
- 枝継ぎ婚
- 還樹葬
- 新芽祭
- 星降り夜会
- 満月歌会
- 白霧の鎮魂日

命名傾向語：
- 月
- 星
- 露
- 葉
- 水
- 梢
- 薄明

### 8-4. 北境牙氏族圏

特徴：寒冷地、狩猟、氏族、祖霊、功績、戦名

主要要素：
- 初狩り
- 牙結び
- 戦名授与
- 火囲み婚
- 雪送り葬
- 初雪宴
- 狼月の夜
- 祖火祭
- 春狩り競べ

命名傾向語：
- 冬
- 牙
- 嵐
- 狼
- 石
- 炎
- 祖

### 8-5. 潮路商邦圏

特徴：港、交易、商会、契約、混血、商品名、記念市

主要要素：
- 初航海
- 契印授与
- 帳簿名登録
- 連盟婚
- 海送り葬
- 海開き祭
- 帆風市
- 灯舟流し
- 契約更新祭

命名傾向語：
- 潮
- 帆
- 玻璃
- 星
- 路
- 塩
- 青
- 灯

### 8-6. 天幕遊牧圏

特徴：草原、移動生活、天体信仰、弓騎、歌、風名

主要要素：
- 初騎乗
- 弓渡し
- 風名授与
- 幕婚
- 風葬 / 空葬
- 草芽祭
- 星追い夜
- 大競馬祭
- 風歌会

命名傾向語：
- 空
- 風
- 蹄
- 蒼
- 巡り
- 鷹
- 矢

### 8-7. 炉都坑道圏

特徴：鍛冶、坑道、工房、組合、品質保証、刻印文化

主要要素：
- 初打ち
- 炉前誓約
- 工印授与
- 師資継承
- 石室葬
- 炉開き
- 大鍛祭
- 工房競べ
- 鉱脈感謝祭

命名傾向語：
- 炉
- 鋼
- 礎
- 環
- 鉱
- 火
- 鎚
- 石

### 8-8. 冥契夜界圏

特徴：契約、仮面、真名禁忌、代価、影、市、夜の秩序

主要要素：
- 仮面受領
- 契印刻み
- 秘名封じ
- 影婚
- 夜還葬
- 新月契日
- 月蝕の市
- 仮面交換夜会
- 代価清算日

命名傾向語：
- 夜
- 影
- 月蝕
- 深淵
- 契
- 黒
- 棺
- 終

---

## 9. 儀礼・祭礼モジュール設計

文化圏ごとに固定値のみで持たず、モジュールとして再利用可能にすること。

### 9-1. 儀礼分類

- 出生儀礼
- 命名儀礼
- 洗礼
- 成人儀礼
- 初狩り / 初航海 / 初騎乗 / 初打ち
- 婚姻儀礼
- 継承儀礼
- 葬送儀礼
- 秘名授受
- 軍務加入
- 流派入門
- 神殿奉仕開始

### 9-2. 祭礼分類

- 農耕祭
- 狩猟祭
- 航海祭
- 市場祭
- 契約祭
- 建国祭
- 鎮魂祭
- 戦勝祭
- 競技祭
- 巡礼祭
- 季節祭
- 復興祭
- 主人公由来の新祭

### 9-3. 周回変化

主人公の行動により以下が増えることを許可する。

- 新しい祝祭日
- 追悼式
- 競技会
- 祭礼名の変更
- 俗称の誕生
- 制式装備名の定着
- 主人公の異名を冠した市場商品
- 本来秘儀だったものの公開化

---

## 10. アイテム命名仕様

### 10-1. カテゴリ別ルール

#### 武器

一般武器は、材質 + 用途 + 種別を基本とする。

例：
- 鉄剣
- 短槍
- 狩猟弓
- 騎兵槍

軍需品は、所属 + 用途 + 型式。

例：
- 王都歩兵剣三式
- 北辺軽騎兵槍二型

工房製は、工房 + 材質 + 種別。

例：
- 黒炉工房製鋼短剣

固有名は一点物、王侯奉納品、継承品、著名戦功品、呪物、神器級に限定する。

#### 防具

武器よりさらに無銘率を高くすること。

一般名：
- 胴鎧
- 鉄靴
- 厚革の外套
- 鎖籠手

名付き防具は象徴性の高いもの中心。

例：
- 灰祓いの冠
- 誓冠の外套
- 白枝の司祭冠

#### 消耗品・薬品

一般流通品は機能名中心。

例：
- 治癒薬
- 解毒薬
- 保存食
- 油布

商業文化が強い地域では商品名・銘柄名を持たせる。

例：
- 青瓶治癒薬
- 山羊印の解熱粉
- 南市香油

#### 魔法

一般魔法は、漢字《カタカナ語》。
学術名は、属性 + 用途 + 位階。流派秘術は流派名併記。禁呪・神話級は固有名付与可。

例：
- 火球《ファイアボール》
- 土壁《アースウォール》
- 地属性防壁術第一位階
- 黒陽断章《グレイ・カタストロフ》

#### スキル・戦技

一般技能は簡潔に。奥義・秘技のみ固有名を持つ。

例：
- 応急手当
- 短剣術
- 受け流し《パリィ》
- 連突《ラッシュスラスト》
- 黒鶴流奥義《雨断ち》

---

## 11. 古代遺物・真名解放システム

### 11-1. 基本方針

古代遺物は現代解釈名と真名を分離して表示すること。

例：
- 古代黒大剣《終ノ門ヲ啓クモノ》

### 11-2. 段階解放

以下の5段階を推奨実装とする。

1. 未鑑定
2. 現代鑑定済み
3. 真名断片表示
4. 真名認識
5. 契約 / 覚醒

### 11-3. 各段階の表示例

#### 未鑑定
- 古びた黒の大剣

#### 現代鑑定済み
- 古代黒大剣

#### 真名断片表示
- 古代黒大剣《◼◼◼◼◼◼◼◼◼》

#### 真名認識
- 古代黒大剣《終ノ門ヲ啓クモノ》

#### 覚醒
- 古代黒大剣《終ノ門ヲ啓クモノ》【覚醒】

### 11-4. 真価反映条件

以下を条件候補として持つこと。

- ステータス値
- 属性適性
- 血統
- 種族
- 信仰
- 深淵感応
- 古代語理解
- 周回記憶
- 特定遺跡の踏破
- 関連イベント完了
- 所有者残響の解放

### 11-5. 未適合時の仕様

真名が見えても、以下の状態を取りうること。

- 潜在補正が表示されるが反映されない
- 固有技能が表示されるが使えない
- 武器説明に「適合不足」と表示される
- 真価解放条件がヒントとして一部開示される

---

## 12. データ構造要件

### 12-1. 基本原則

Codexは文字列生成だけでなく、後からUI・会話・図鑑・戦闘・物語・イベントで再利用できる構造体を生成すること。

単なる表示文字列の固定配列にせず、属性分解したデータ構造にすること。

### 12-2. 文化圏データ例

```json
{
  "culture_id": "holy_kingdom_01",
  "display_name": "聖暦王国圏",
  "environment_tags": ["temperate", "agricultural", "urban"],
  "economy_tags": ["farming", "craft", "pilgrimage_market"],
  "governance_tags": ["monarchy", "temple", "nobility"],
  "religion_tags": ["sacred_light", "oath", "saint_cult"],
  "naming_profile": {
    "phoneme_tendency": ["l", "r", "v", "s", "ia", "el"],
    "semantic_roots": ["光", "白", "誓い", "守護", "獅子", "晨"],
    "uses_baptism_name": true,
    "adult_rename": false,
    "secret_true_name": false
  },
  "rites": [
    "naming_baptism",
    "adult_oath",
    "knighting",
    "marriage_blessing",
    "lamp_funeral"
  ],
  "festivals": [
    "spring_tillage_festival",
    "summer_solstice_light",
    "autumn_harvest_day",
    "winter_lamp_night"
  ],
  "slur_targets": {
    "elf": ["長耳"],
    "dwarf": ["石チビ"]
  },
  "item_naming_rules": {
    "common_items_named": false,
    "craft_marks_common": false,
    "military_pattern_names": true,
    "ritual_items_named": true,
    "heirlooms_named": true
  }
}
```

### 12-3. アイテムデータ例

```json
{
  "item_id": "ancient_black_greatsword_001",
  "category": "weapon",
  "base_type": "greatsword",
  "rarity_tier": "ancient",
  "interpretation_name": "古代黒大剣",
  "true_name": "終ノ門ヲ啓クモノ",
  "masked_true_name": "◼◼◼◼◼◼◼◼◼",
  "display_mode": "modern_plus_true",
  "origin_culture": "night_contract_ancient",
  "maker": null,
  "military_pattern": null,
  "ritual_status": true,
  "has_proper_name": true,
  "nickname": null,
  "unlock_stages": {
    "identified": true,
    "true_name_visible": false,
    "true_effects_visible": false,
    "full_sync": false
  },
  "requirements": {
    "strength": 80,
    "abyss_affinity_rank": "B",
    "event_flags": ["black_gate_ruins_clear"]
  },
  "effects": {
    "base_attack": 42,
    "hidden_attack_bonus": 49,
    "hidden_skills": ["gate_split"],
    "locked_until_sync": true
  }
}
```

### 12-4. 技データ例

```json
{
  "skill_id": "parry_001",
  "display_name": "受け流し",
  "reading_name": "パリィ",
  "full_display": "受け流し《パリィ》",
  "category": "combat_basic",
  "tier": "common",
  "culture_associations": ["holy_kingdom", "empire", "mercenary"],
  "has_proper_name": false
}
```

### 12-5. 種族データ例

```json
{
  "race_id": "elf",
  "display_name": "長命種（エルフ）",
  "formal_name_kanji": "長命種",
  "formal_name_katakana": "エルフ",
  "social_names": ["森の民", "梢の人"],
  "slur_names": ["長耳"],
  "biological_traits": ["long_lived", "high_mana_sense", "light_frame"],
  "default_culture_bias": ["forest_star", "holy_kingdom_minorities"],
  "playable": true
}
```

---

## 13. 命名生成ロジック

命名は以下の順序で生成すること。

1. 文化圏を決定
2. 種族またはカテゴリを決定
3. 身分 / 流通階層 / 希少度を決定
4. 命名権者を決定
5. 語彙源（象徴語）を決定
6. 表示形式を決定
7. 通称・学術名・真名の有無を決定
8. 周回変化・歴史変化を適用

### 13-1. 語彙源の例

#### 聖暦王国圏
- 光
- 誓い
- 白
- 晨
- 守護
- 聖

#### 灰鉄帝政圏
- 灰
- 鉄
- 黒陽
- 勲
- 断
- 冠

#### 樹海星詠圏
- 月
- 星
- 露
- 葉
- 水
- 薄明

#### 北境牙氏族圏
- 冬
- 牙
- 狼
- 祖
- 炎
- 嵐

#### 潮路商邦圏
- 潮
- 帆
- 玻璃
- 星
- 青
- 路

#### 天幕遊牧圏
- 風
- 空
- 蹄
- 鷹
- 蒼
- 矢

#### 炉都坑道圏
- 炉
- 鋼
- 鎚
- 鉱
- 環
- 礎

#### 冥契夜界圏
- 影
- 夜
- 契
- 月蝕
- 深淵
- 終

---

## 14. 周回・主人公介入による世界変化

### 14-1. 基本方針

主人公の行動が文化圏・祭礼・命名体系に影響を与えること。

### 14-2. 変化対象

- 新祭礼の誕生
- 主人公異名を冠した記念行事
- 制式装備化
- 模造品・廉価版の流通
- 市場俗称の定着
- 地名の改称
- 禁忌解除に伴う公開儀礼化
- 流派の新設
- 英雄譚の童話化・大衆化

### 14-3. 実装例

伝説武器《冬吠》が周回後に次のように派生する。

- 《冬吠》：唯一の伝説武器
- 冬吠式長剣：軍・工房が模倣した高級品
- 冬式片刃剣：安価普及型
- 冬牙遊戯剣：子供向け玩具・祭礼用模造具

---

## 15. 実装優先順位

Codexは以下の優先順で実装を進めること。

### Phase 1：基盤データ構造

最優先。

実装対象：
- culture schema
- race schema
- item schema
- skill schema
- naming profile schema
- rite schema
- festival schema
- world mutation schema

目標：
- 各データがJSON/TypeScript interface等で定義されること
- 後から拡張可能であること

### Phase 2：初期辞書と文化圏テンプレート

実装対象：
- 8文化圏の初期データ
- 種族正式分類
- 俗称・蔑称の初期表
- 儀礼モジュール
- 祭礼モジュール
- 語彙源辞書

### Phase 3：命名生成エンジン

実装対象：
- 人名生成
- 地名生成
- 武器名生成
- 魔法名生成
- 古代遺物名生成
- 真名伏せ字生成
- 表記整形ロジック

### Phase 4：古代遺物の段階解放

実装対象：
- 現代解釈名 + 真名構造
- 未解読時表示
- 条件未達時の見えるが反映されない仕様
- UI向けステータスロック表示

### Phase 5：周回変化

実装対象：
- 主人公の行動ログから祭礼や制式名が派生する仕組み
- イベントにより新しい俗称・商品名・記念日を発生させる仕組み

---

## 16. Codexへの実務指示

以下をCodexに対する直接指示として扱うこと。

1. まずはハードコードされた物語文ではなく、構造データを先に定義せよ
2. 命名ロジックは文字列連結だけで作らず、文化圏・カテゴリ・希少度・命名権者を入力に持つ関数として設計せよ
3. 種族と文化圏を分離せよ
4. 魔族を単一種で扱わず、上位分類 + 下位分類で扱え
5. 一般名、型式名、工房銘、通称、固有名、真名の多層表示を可能にせよ
6. 一般魔法・技能は「漢字《カタカナ》」表記を標準化せよ
7. 古代遺物は「現代解釈名《真名》」表記を標準化せよ
8. 真名未解放時は伏せ字表示を可能にせよ
9. 真名が見えても未適合で性能が反映されない状態を実装可能にせよ
10. 主人公の周回・介入により文化データが変異する仕組みを後付けではなく初期設計に含めよ
11. 各データに display_name と internal_id を分離して持たせよ
12. UI表示用フィールドと内部ロジック用フィールドを分けよ
13. 後から文化圏・種族・祭礼・遺物・俗称・蔑称を追加しやすい設計にせよ

---

## 17. 今後の拡張候補

本仕様は初期版であり、将来的には以下を拡張可能とする。

- 文化圏ごとの法律と禁忌
- 婚姻制度の差異
- 食文化と料理名
- 暦と月名
- 神格体系
- 流派・学派・宗派
- 王朝史・戦争史由来の蔑称生成
- 同じ装備の各文化圏での呼び方差分
- 地方方言・訛り
- 本名・通称・儀礼名・秘名の切り替え会話

---

## 18. 最終確認事項

この仕様の核心は次の通り。

- 世界を名付けの密度で作ること
- 名の有無自体を社会構造にすること
- 量産品と伝説品を同じテンションで扱わないこと
- 真名を単なる飾りにせず、システムに接続すること
- 種族、文化、儀礼、祭礼、命名、UI、周回変化を一つの仕様として繋ぐこと

Codexは、この仕様をもとに、まずはデータモデルと命名生成エンジンの骨格を実装し、その後に文化圏データ、種族データ、遺物解放仕様を順次追加すること.

---

## 19. Codex実装開始用 追加仕様（TypeScript / JSON 前提）

以下はCodexが最初に生成すべき実装物の具体案である。まずは Next.js / TypeScript または Node.js / TypeScript を前提に、純粋なデータモデル・辞書・生成ロジックから着手すること。UIは後回しにしてよい。

### 19-1. 推奨ディレクトリ構成

```text
src/
  domain/
    world/
      types/
        culture.ts
        race.ts
        rites.ts
        festivals.ts
        naming.ts
        item.ts
        skill.ts
        relic.ts
        mutation.ts
      generators/
        naming/
          peopleNameGenerator.ts
          placeNameGenerator.ts
          itemNameGenerator.ts
          magicNameGenerator.ts
          relicNameGenerator.ts
      rules/
        cultureRules.ts
        namingRules.ts
        rarityRules.ts
        unlockRules.ts
      services/
        namingService.ts
        relicUnlockService.ts
        worldMutationService.ts
  data/
    cultures/
      holy_kingdom_01.json
      gray_empire_01.json
      forest_star_01.json
      north_clan_01.json
      tide_trade_01.json
      steppe_tent_01.json
      forge_city_01.json
      night_contract_01.json
    races/
      human.json
      elf.json
      dwarf.json
      warbeast.json
      birdfolk.json
      dragonute.json
      fey.json
      demonian.json
      fallen.json
    rites/
      common_rites.json
    festivals/
      common_festivals.json
    vocab/
      semantic_roots.json
      slurs.json
      titles.json
      item_patterns.json
      magic_patterns.json
      relic_patterns.json
```

### 19-2. TypeScript型定義（基礎）

```ts
export type Id = string;

export type DisplayText = {
  ja: string;
  kana?: string;
  en?: string;
};

export type NamingDisplayMode =
  | "plain"
  | "kanji_katakana"
  | "modern_plus_true"
  | "title_plus_true"
  | "masked_true_name";

export type NameLayer = {
  interpretationName?: string;
  formalName?: string;
  readingName?: string;
  trueName?: string;
  maskedTrueName?: string;
  nickname?: string;
  slangName?: string;
  militaryPatternName?: string;
  workshopName?: string;
  ritualName?: string;
  fullDisplay: string;
  displayMode: NamingDisplayMode;
};

export type SemanticRoot = {
  key: string;
  surface: string;
  tags: string[];
};
```

### 19-3. 文化圏型定義

```ts
export type CultureId = Id;

export type NamingProfile = {
  phonemeTendency: string[];
  semanticRoots: string[];
  usesBaptismName: boolean;
  adultRename: boolean;
  secretTrueName: boolean;
  commonItemNamedRate: number;
  ritualItemNamedRate: number;
  heirloomNamedRate: number;
  properNameRate: number;
  trueNameRate: number;
};

export type Culture = {
  id: CultureId;
  displayName: string;
  shortName?: string;
  environmentTags: string[];
  economyTags: string[];
  governanceTags: string[];
  religionTags: string[];
  namingProfile: NamingProfile;
  rites: Id[];
  festivals: Id[];
  favoredRaces: Id[];
  slurTargets: Record<string, string[]>;
  socialAliases: Record<string, string[]>;
  itemNamingRules: {
    commonItemsNamed: boolean;
    craftMarksCommon: boolean;
    militaryPatternNames: boolean;
    ritualItemsNamed: boolean;
    heirloomsNamed: boolean;
  };
};
```

### 19-4. 種族型定義

```ts
export type Race = {
  id: Id;
  displayName: string;
  formalNameKanji: string;
  formalNameKatakana: string;
  academicCategory: string;
  socialNames: string[];
  slurNames: {
    mild: string[];
    harsh: string[];
    taboo: string[];
  };
  biologicalTraits: string[];
  lifespanClass: "short" | "normal" | "long" | "very_long";
  playable: boolean;
  defaultCultureBias: CultureId[];
  metadata?: {
    notes?: string;
  };
};
```

### 19-5. 儀礼・祭礼型定義

```ts
export type RiteCategory =
  | "birth"
  | "naming"
  | "baptism"
  | "coming_of_age"
  | "guild_entry"
  | "military_entry"
  | "marriage"
  | "succession"
  | "funeral"
  | "true_name"
  | "pilgrimage"
  | "craft_mastery";

export type Rite = {
  id: Id;
  displayName: string;
  category: RiteCategory;
  description: string;
  tags: string[];
  relatedCultures: CultureId[];
  grants?: {
    title?: string[];
    socialStatus?: string[];
    rename?: boolean;
    itemNamingPrivilege?: boolean;
  };
};

export type Festival = {
  id: Id;
  displayName: string;
  category:
    | "seasonal"
    | "market"
    | "military"
    | "religious"
    | "memorial"
    | "competition"
    | "pilgrimage"
    | "hero_origin";
  description: string;
  seasonTags: string[];
  relatedCultures: CultureId[];
  mutationEligible: boolean;
};
```

### 19-6. アイテム・遺物型定義

```ts
export type ItemCategory =
  | "weapon"
  | "armor"
  | "consumable"
  | "tool"
  | "ritual_item"
  | "relic"
  | "magic_focus";

export type NamingTier =
  | "generic"
  | "workshop"
  | "pattern"
  | "slang"
  | "ritual"
  | "proper"
  | "true_name";

export type UnlockStage =
  | "unidentified"
  | "identified"
  | "masked_true_name"
  | "true_name_visible"
  | "awakened";

export type Item = {
  id: Id;
  category: ItemCategory;
  baseType: string;
  rarityTier: "common" | "uncommon" | "rare" | "epic" | "legendary" | "ancient";
  originCulture?: CultureId;
  name: NameLayer;
  namingTier: NamingTier;
  maker?: string | null;
  material?: string | null;
  militaryPattern?: string | null;
  ritualStatus: boolean;
  hasProperName: boolean;
  requirements?: {
    stats?: Record<string, number>;
    traits?: string[];
    eventFlags?: string[];
    raceIds?: string[];
    cultureIds?: string[];
  };
  effects?: {
    visible: Record<string, number | string | boolean>;
    hidden?: Record<string, number | string | boolean>;
    hiddenSkills?: string[];
    lockedUntilSync?: boolean;
  };
};

export type Relic = Item & {
  relicClass: "sealed" | "ancient_weapon" | "ancient_crown" | "gate_relic" | "divine_fragment";
  unlockStage: UnlockStage;
  trueNameVisible: boolean;
  fullSync: boolean;
};
```

### 19-7. 技・魔法型定義

```ts
export type SkillCategory =
  | "combat_basic"
  | "combat_art"
  | "craft"
  | "survival"
  | "social"
  | "magic_basic"
  | "magic_academic"
  | "magic_secret"
  | "magic_taboo";

export type Skill = {
  id: Id;
  displayName: string;
  readingName?: string;
  englishName?: string;
  fullDisplay: string;
  category: SkillCategory;
  tier: "common" | "advanced" | "secret" | "taboo";
  cultureAssociations: CultureId[];
  hasProperName: boolean;
  academicName?: string;
  schoolName?: string;
};
```

### 19-8. 世界変化型定義

```ts
export type WorldMutation = {
  id: Id;
  triggerFlags: string[];
  targetType: "festival" | "item_pattern" | "slang" | "title" | "culture_rule";
  targetId?: Id;
  description: string;
  effects: {
    addFestivalIds?: Id[];
    addNamingPatterns?: string[];
    addSlangNames?: string[];
    upgradePatternToProperName?: boolean;
    unlockPublicRite?: boolean;
  };
};
```

---

## 20. 初期データ投入指示

Codexは以下の初期データを最低限作成すること。

### 20-1. 文化圏データ

8文化圏すべてについて JSON を作成すること。

必須ファイル：
- holy_kingdom_01.json
- gray_empire_01.json
- forest_star_01.json
- north_clan_01.json
- tide_trade_01.json
- steppe_tent_01.json
- forge_city_01.json
- night_contract_01.json

### 20-2. 種族データ

最低9種の種族 JSON を作成すること。

必須ファイル：
- human.json
- elf.json
- dwarf.json
- warbeast.json
- birdfolk.json
- dragonute.json
- fey.json
- demonian.json
- fallen.json

### 20-3. 儀礼・祭礼データ

最低件数目安：
- 儀礼 24件以上
- 祭礼 32件以上

### 20-4. 語彙辞書

以下の辞書 JSON を作成すること。

- semantic_roots.json
- slurs.json
- titles.json
- item_patterns.json
- magic_patterns.json
- relic_patterns.json

辞書には cultureId と tags を持たせること。

---

## 21. 命名生成関数の仕様

Codexは以下の関数を実装すること。

### 21-1. 人名生成

```ts
generatePersonName(input: {
  cultureId: string;
  raceId: string;
  genderStyle?: "masculine" | "feminine" | "neutral";
  socialTier?: "commoner" | "noble" | "priest" | "warrior" | "merchant";
  hasSecretTrueName?: boolean;
}): NameLayer
```

### 21-2. 地名生成

```ts
generatePlaceName(input: {
  cultureId: string;
  placeType: "city" | "village" | "fortress" | "forest" | "port" | "ruin" | "holy_site";
  ancient?: boolean;
}): NameLayer
```

### 21-3. 一般アイテム名生成

```ts
generateItemName(input: {
  cultureId: string;
  category: ItemCategory;
  baseType: string;
  rarityTier: string;
  namingTier?: NamingTier;
  maker?: string;
  militaryPattern?: string;
  ritual?: boolean;
}): NameLayer
```

### 21-4. 魔法名生成

```ts
generateMagicName(input: {
  cultureId: string;
  tier: "common" | "advanced" | "secret" | "taboo";
  elementTags: string[];
  functionTags: string[];
}): Skill
```

### 21-5. 古代遺物名生成

```ts
generateRelicName(input: {
  interpretationBase: string;
  originCultureId: string;
  relicClass: string;
  ancientTone?: "sacred" | "abyssal" | "royal" | "sealed";
  masked?: boolean;
}): NameLayer
```

### 21-6. 真名マスク処理

```ts
maskTrueName(trueName: string, visibleRatio?: number): string
```

仕様：
- 原則は ◼ で伏せる
- 一部のみ可視化する設定も許可
- UI側で段階開示できる設計にする

---

## 22. 初期実装における禁止事項

Codexは以下を避けること。

1. すべての装備に固有名を付けること
2. すべての魔法を詩的名称にすること
3. 種族と文化圏を一対一対応させること
4. 魔族を単一種として雑に処理すること
5. 表示文字列だけでシステムを構成すること
6. UI表示名と内部IDを同一にすること
7. 俗称・蔑称を単なるランダム悪口リストにすること
8. 真名をただのフリガナとして扱うこと
9. 古代遺物の解放条件を一種類だけに固定すること
10. 周回変化を後付け機能として設計すること

---

## 23. 受け入れ基準（Definition of Done）

Phase 1 完了条件：
- 型定義が存在する
- 8文化圏 JSON が存在する
- 9種族 JSON が存在する
- 儀礼と祭礼の初期辞書が存在する
- 命名辞書が存在する

Phase 2 完了条件：
- 人名・地名・一般装備・魔法・古代遺物の命名関数が呼び出せる
- 文化圏ごとに命名傾向が明確に変わる
- 一般アイテムは大半が無銘 / 型式 / 工房銘止まりである
- 固有名の出現率が低く保たれる

Phase 3 完了条件：
- 古代黒大剣《◼◼◼◼◼◼◼◼◼》 のような表示が可能
- 条件不足時に「見えるが反映されない」状態が再現できる
- 真名解放後に特殊スキルと補正が解禁される

Phase 4 完了条件：
- 主人公の周回・イベントフラグで新祭礼や新命名が追加される
- 一つの伝説装備が、後世に模造品・制式化・市場化される挙動が再現できる

---

## 24. 次段階の実装候補

この仕様書を土台に、次にCodexへ追加依頼すべきものは以下。

1. TypeScript の interface / zod schema 実装
2. 初期 JSON データ一式の自動生成
3. 命名生成ユニットテスト
4. 古代遺物の段階解放ロジック実装
5. 文化圏・種族・祭礼を参照する会話生成補助ロジック
6. UI用図鑑表示モデル
7. 周回時文化変異シミュレータ

以上を、実装順に分割してPR単位でCodexに作業させること。

---

## 25. Codex向け 初回実装タスク分割書（PR単位）

以下は、Codexに順番に依頼するための実装タスク分割である。各PRはなるべく責務を限定し、レビューしやすく、ロールバックしやすい単位で区切ること。

### PR-001: 世界観基盤の型定義とディレクトリ作成

**目的**
- 今後の全実装の土台となる型とフォルダ構成を用意する

**実装内容**
- `src/domain/world/types/` 以下に型定義ファイルを作成
- `culture.ts`
- `race.ts`
- `rites.ts`
- `festivals.ts`
- `naming.ts`
- `item.ts`
- `skill.ts`
- `relic.ts`
- `mutation.ts`
- `src/data/` 以下に空ディレクトリを作成
- 必要なら zod schema も併設

**成果物**
- TypeScript interface / type 一式
- 必須ディレクトリ構成

**受け入れ条件**
- ビルドエラーが出ない
- 型だけで各データの責務が見える
- 表示名と内部IDが分離されている

---

### PR-002: 8文化圏の初期JSONデータ投入

**目的**
- 命名・儀礼・祭礼の基礎となる文化圏データを投入する

**実装内容**
- 以下のJSONを作成
  - `holy_kingdom_01.json`
  - `gray_empire_01.json`
  - `forest_star_01.json`
  - `north_clan_01.json`
  - `tide_trade_01.json`
  - `steppe_tent_01.json`
  - `forge_city_01.json`
  - `night_contract_01.json`
- 各ファイルに以下を格納
  - 基本表示名
  - 環境タグ
  - 経済タグ
  - 統治タグ
  - 宗教タグ
  - namingProfile
  - rites
  - festivals
  - slurTargets
  - itemNamingRules

**成果物**
- 8文化圏の初期データ

**受け入れ条件**
- JSONの構造が共通化されている
- 文化圏ごとの差が明確に見える
- namingProfile に出現率・命名傾向が含まれている

---

### PR-003: 種族分類・俗称・蔑称データ投入

**目的**
- プレイアブル種族と社会的呼称の基盤を作る

**実装内容**
- 以下のJSONを作成
  - `human.json`
  - `elf.json`
  - `dwarf.json`
  - `warbeast.json`
  - `birdfolk.json`
  - `dragonute.json`
  - `fey.json`
  - `demonian.json`
  - `fallen.json`
- 各種族に以下を持たせる
  - 正式名称
  - 学術分類
  - socialNames
  - slurNames（mild/harsh/taboo）
  - biologicalTraits
  - lifespanClass
  - defaultCultureBias
  - playable

**成果物**
- 9種族分のJSONデータ

**受け入れ条件**
- 種族と文化圏が分離されている
- 魔族系が単一種扱いになっていない
- 蔑称がランダム悪口ではなく関係史を感じさせる

---

### PR-004: 儀礼・祭礼モジュール辞書投入

**目的**
- 文化イベント生成・物語分岐・周回変化の基盤を作る

**実装内容**
- `common_rites.json`
- `common_festivals.json`
- 儀礼24件以上、祭礼32件以上を投入
- category / tags / relatedCultures / grants / mutationEligible を定義

**成果物**
- 儀礼・祭礼辞書

**受け入れ条件**
- 出生、成人、婚姻、継承、葬送、加入、真名授受などが揃っている
- 季節祭、市場祭、軍事祭、鎮魂祭、主人公由来祭が揃っている

---

### PR-005: 語彙辞書の整備

**目的**
- 命名生成に必要な象徴語・型式・通称・古代遺物語彙を準備する

**実装内容**
- `semantic_roots.json`
- `slurs.json`
- `titles.json`
- `item_patterns.json`
- `magic_patterns.json`
- `relic_patterns.json`
- cultureId, category, tags, rarityWeight などを定義

**成果物**
- 命名辞書一式

**受け入れ条件**
- 文化圏ごとに語彙の癖が違う
- 一般語と固有名語彙が分かれている
- 真名・古名向け語彙が別管理されている

---

### PR-006: 命名整形ユーティリティ実装

**目的**
- 表記ルールをコード化する

**実装内容**
- `formatKanjiKatakanaName()`
- `formatTitlePlusTrueName()`
- `formatModernPlusTrueName()`
- `maskTrueName()`
- `buildFullDisplayName()`

**成果物**
- 名前表記ユーティリティ関数群

**受け入れ条件**
- `土壁《アースウォール》` を正しく生成できる
- `古代黒大剣《◼◼◼◼◼◼◼◼◼》` を生成できる
- `傲慢なる水竜王《アクアハーティア》` を生成できる

---

### PR-007: 一般命名生成エンジン実装

**目的**
- 人名、地名、一般アイテム名を生成できるようにする

**実装内容**
- `generatePersonName()`
- `generatePlaceName()`
- `generateItemName()`
- culture + race + socialTier + namingTier を入力に取る
- generic / workshop / pattern / slang の各層を生成できるようにする

**成果物**
- 命名生成関数群

**受け入れ条件**
- 同一文化圏で音と語彙に一貫性がある
- 無銘品が大半を占める
- 工房銘・型式名・通称の差が表現できる

---

### PR-008: 魔法・技能命名生成エンジン実装

**目的**
- 一般魔法、学術魔法、秘術、技能、奥義の命名差を実装する

**実装内容**
- `generateMagicName()`
- `generateSkillDisplay()`
- common / advanced / secret / taboo を分岐
- 漢字《カタカナ》 と 学術名・流派名を両立

**成果物**
- 魔法・技能命名ロジック

**受け入れ条件**
- 一般魔法は説明的
- 禁呪や秘術だけが重い名を持つ
- すべての魔法が詩的名称になっていない

---

### PR-009: 古代遺物命名と段階解放ロジック実装

**目的**
- 現代解釈名 + 真名 + 覚醒段階をシステム化する

**実装内容**
- `generateRelicName()`
- `relicUnlockService.ts`
- UnlockStage の遷移
- 真名伏せ字
- 条件不足時の「見えるが反映されない」状態
- hidden effects / hidden skills / fullSync の実装

**成果物**
- 遺物生成と解放ロジック

**受け入れ条件**
- `古代黒大剣《終ノ門ヲ啓クモノ》` 形式が扱える
- 真名未解放時は伏せ字表示になる
- 条件不足時に hidden bonus が反映されない
- 覚醒後に特殊スキルが解禁される

---

### PR-010: 世界変化・周回変異システム実装

**目的**
- 主人公の行動が文化や命名体系を変える仕組みを入れる

**実装内容**
- `worldMutationService.ts`
- `mutation.ts` 型利用
- triggerFlags に応じた festival / naming / slang / title の追加
- 伝説装備の模造品、制式化、商品化への派生

**成果物**
- 世界変異ロジック

**受け入れ条件**
- 1つの伝説装備から模造品派生ができる
- 新祭礼が追加される
- 主人公異名が市場名・記念行事に変換される

---

### PR-011: テスト実装

**目的**
- 今後の拡張で命名体系やデータ整合性が壊れないようにする

**実装内容**
- unit test
- snapshot test
- fixture data test
- JSON schema validation test

**重点テスト項目**
- 表記ルールが崩れない
- 文化圏差が出る
- 無銘率が高く維持される
- 真名マスクが正しく動く
- 解放条件未達時の hidden effect が反映されない

**成果物**
- テスト一式

**受け入れ条件**
- テストが自動実行可能
- 主要な命名出力がスナップショットで確認できる

---

### PR-012: サンプル出力とデバッグ用図鑑データ生成

**目的**
- 実装内容を人間が確認しやすくする

**実装内容**
- 各文化圏ごとのサンプル人名 20件
- 各文化圏ごとの地名 20件
- 一般装備 / 工房装備 / 制式装備 / 固有装備のサンプル
- 一般魔法 / 学術魔法 / 秘術 / 禁呪のサンプル
- 古代遺物の未解放 / 部分解放 / 覚醒済みサンプル

**成果物**
- デバッグ用JSONまたはmdレポート

**受け入れ条件**
- 人間レビューで世界観差が確認できる
- 表記ルールと命名階層が視覚的に確認できる

---

## 26. Codexへの最初の依頼文テンプレート

以下をCodexへの最初の依頼文テンプレートとして使うこと。

```md
このプロジェクトでは、異世界転生PBW/物語生成RPG向けの世界観データ基盤を構築します。
まずはUIではなく、TypeScriptとJSONによるデータモデル、初期データ、命名生成ロジックから実装してください。

最初のPRでは以下を実装してください。
- src/domain/world/types/ 以下の型定義作成
- src/data/ 以下の基礎ディレクトリ作成
- display_name と internal_id の分離
- culture, race, rite, festival, naming, item, relic, skill, mutation の型定義

要件:
- 種族と文化圏は分離すること
- 魔族は単一種族でなく上位分類として扱えるようにすること
- 名前は一般名、型式名、工房銘、通称、固有名、真名の多層構造を持てること
- 古代遺物は現代解釈名《真名》を扱えること
- 真名未解放時の伏せ字表示を扱えること

実装後、どの型を作ったか、今後どのJSONを入れる想定かをREADMEまたはPR説明にまとめてください。
```

---

## 27. PR-001 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、最初の実装を依頼すること。

```md
# 依頼内容

異世界転生PBW/物語生成RPG向けの世界観データ基盤を構築したいです。
今回は **PR-001: 世界観基盤の型定義とディレクトリ作成** のみを実装してください。

目的は、後続の文化圏データ、種族データ、儀礼・祭礼辞書、命名生成ロジック、古代遺物解放システムを安全に追加できる土台を作ることです。

UI実装は不要です。まずは **TypeScript の型定義、必要ディレクトリ、最小限の README / 説明** に集中してください。

---

# 実装範囲

以下を実装してください。

## 1. ディレクトリ作成

次の構成を作成してください。

```text
src/
  domain/
    world/
      types/
        culture.ts
        race.ts
        rites.ts
        festivals.ts
        naming.ts
        item.ts
        skill.ts
        relic.ts
        mutation.ts
  data/
    cultures/
    races/
    rites/
    festivals/
    vocab/
```

必要なら将来拡張しやすいように `index.ts` やエクスポート整理を入れて構いません。

---

## 2. 型定義作成

以下の責務を持つ TypeScript の型定義を作成してください。

### `naming.ts`
含めたいもの:
- `Id`
- `DisplayText`
- `NamingDisplayMode`
- `NameLayer`
- `SemanticRoot`

`NameLayer` は少なくとも以下を扱えるようにしてください。
- interpretationName
- formalName
- readingName
- trueName
- maskedTrueName
- nickname
- slangName
- militaryPatternName
- workshopName
- ritualName
- fullDisplay
- displayMode

目的:
- 一般名、型式名、工房銘、通称、固有名、真名の多層表記を扱えるようにする
- `土壁《アースウォール》`
- `傲慢なる水竜王《アクアハーティア》`
- `古代黒大剣《終ノ門ヲ啓クモノ》`
- `古代黒大剣《◼◼◼◼◼◼◼◼◼》`
のような表示を将来組める構造にする

### `culture.ts`
含めたいもの:
- `CultureId`
- `NamingProfile`
- `Culture`

`Culture` には少なくとも以下を持たせてください。
- id
- displayName
- shortName
- environmentTags
- economyTags
- governanceTags
- religionTags
- namingProfile
- rites
- festivals
- favoredRaces
- slurTargets
- socialAliases
- itemNamingRules

`NamingProfile` には少なくとも以下を持たせてください。
- phonemeTendency
- semanticRoots
- usesBaptismName
- adultRename
- secretTrueName
- commonItemNamedRate
- ritualItemNamedRate
- heirloomNamedRate
- properNameRate
- trueNameRate

目的:
- 種族と文化圏を分離する
- 文化圏ごとに命名傾向と命名率を分ける

### `race.ts`
含めたいもの:
- `Race`

`Race` には少なくとも以下を持たせてください。
- id
- displayName
- formalNameKanji
- formalNameKatakana
- academicCategory
- socialNames
- slurNames（mild / harsh / taboo）
- biologicalTraits
- lifespanClass
- playable
- defaultCultureBias
- metadata

目的:
- プレイアブル種族と学術分類を扱えるようにする
- 種族と文化圏を一対一対応させない
- 蔑称や俗称をデータとして持てるようにする

### `rites.ts`
含めたいもの:
- `RiteCategory`
- `Rite`

カテゴリには少なくとも以下を含めてください。
- birth
- naming
- baptism
- coming_of_age
- guild_entry
- military_entry
- marriage
- succession
- funeral
- true_name
- pilgrimage
- craft_mastery

`Rite` には以下を持たせてください。
- id
- displayName
- category
- description
- tags
- relatedCultures
- grants

### `festivals.ts`
含めたいもの:
- `Festival`

カテゴリには少なくとも以下を含めてください。
- seasonal
- market
- military
- religious
- memorial
- competition
- pilgrimage
- hero_origin

`Festival` には以下を持たせてください。
- id
- displayName
- category
- description
- seasonTags
- relatedCultures
- mutationEligible

### `item.ts`
含めたいもの:
- `ItemCategory`
- `NamingTier`
- `Item`

カテゴリには少なくとも以下を含めてください。
- weapon
- armor
- consumable
- tool
- ritual_item
- relic
- magic_focus

命名階層には少なくとも以下を含めてください。
- generic
- workshop
- pattern
- slang
- ritual
- proper
- true_name

`Item` には以下を含めてください。
- id
- category
- baseType
- rarityTier
- originCulture
- name
- namingTier
- maker
- material
- militaryPattern
- ritualStatus
- hasProperName
- requirements
- effects

目的:
- 一般品から伝説品まで同一構造で扱う
- すべてのアイテムに固有名を付けない前提を型で支える

### `relic.ts`
含めたいもの:
- `UnlockStage`
- `Relic`

`UnlockStage` は少なくとも以下。
- unidentified
- identified
- masked_true_name
- true_name_visible
- awakened

`Relic` は `Item` を拡張し、少なくとも以下を持たせてください。
- relicClass
- unlockStage
- trueNameVisible
- fullSync

目的:
- 古代遺物の現代解釈名 + 真名 + 覚醒段階を扱う
- 真名未解放時の伏せ字や、見えるが反映されない状態の実装土台にする

### `skill.ts`
含めたいもの:
- `SkillCategory`
- `Skill`

カテゴリには少なくとも以下。
- combat_basic
- combat_art
- craft
- survival
- social
- magic_basic
- magic_academic
- magic_secret
- magic_taboo

`Skill` には以下を持たせてください。
- id
- displayName
- readingName
- englishName
- fullDisplay
- category
- tier
- cultureAssociations
- hasProperName
- academicName
- schoolName

目的:
- 一般技能と秘術・禁呪を同じカテゴリに押し込めず区別する
- `受け流し《パリィ》` のような表記に対応する

### `mutation.ts`
含めたいもの:
- `WorldMutation`

`WorldMutation` には以下を持たせてください。
- id
- triggerFlags
- targetType
- targetId
- description
- effects

`targetType` には少なくとも以下。
- festival
- item_pattern
- slang
- title
- culture_rule

目的:
- 主人公の周回やイベントによって祭り・俗称・制式名・文化ルールが変化する余地を初期設計に含める

---

## 3. export 整理

型定義は今後使いやすいように、必要なら `src/domain/world/types/index.ts` を作成して再エクスポートしてください。

---

## 4. README または説明ファイル

PR内で、今回作成した型定義が何を担当するのかを短くまとめた md ファイルを1つ追加してください。

内容:
- 今回作成した型の一覧
- どのような後続実装を想定しているか
- 文化圏、種族、命名、遺物、世界変化がどう分かれているか

長文でなくてよいですが、レビュー側が意図を追えるようにしてください。

---

# 必須要件

- TypeScript で実装してください
- 表示名と内部IDは分離してください
- 種族と文化圏は分離してください
- 魔族は単一種族前提で閉じないようにしてください
- 名前は一般名、型式名、工房銘、通称、固有名、真名の多層構造を持てるようにしてください
- 古代遺物は `現代解釈名《真名》` を扱える構造にしてください
- 真名未解放時の伏せ字表示を扱える構造にしてください
- 後続PRで JSON を投入しやすいようにしてください

---

# 今回はやらないこと

以下は今回のPRでは不要です。

- 実データJSONの投入
- 命名生成ロジックの実装
- UIコンポーネント
- DB接続
- APIルート
- テストの本格実装
- 古代遺物の解放ロジック本体

ただし、将来拡張しやすいように設計するのは必要です。

---

# 期待する成果物

- 上記ファイル群が作成されている
- 型定義が整理されている
- 今後のPR-002 以降で JSON と生成ロジックを安全に追加できる
- 世界観の重要ルール（文化圏と種族の分離、多層命名、遺物段階解放、世界変異）が型レベルで表現されている

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 作成したファイル一覧
2. 各型の役割
3. 後続PRで追加すべきもの
4. 設計上の懸念点があればその指摘
```

## 28. PR-002 以降の依頼文作成方針

次回以降も同じ形式で、各PRごとに以下を含む完全版プロンプトを作ること。

- 目的
- 実装範囲
- 変更対象ファイル
- 必須要件
- 今回やらないこと
- 期待成果物
- 最後に出してほしい報告内容

これにより、Codexへの依頼が曖昧化しないようにする。

---

## 29. PR-002 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-002 を依頼すること。

```md
# 依頼内容

今回は **PR-002: 8文化圏の初期JSONデータ投入** を実装してください。

前提として、PR-001 で世界観基盤の型定義がすでに存在している想定です。今回はその型に沿って、まずは命名・儀礼・祭礼・文化差の土台となる **8文化圏の初期データ** を JSON で投入してください。

今回はロジック実装よりも、文化圏ごとの差が明確に見えること、後続の種族・儀礼・祭礼・命名辞書と結びつけやすいことを重視してください。

---

# 実装範囲

以下を実装してください。

## 1. 文化圏JSONの作成

`src/data/cultures/` 以下に、少なくとも次の8ファイルを作成してください。

- `holy_kingdom_01.json`
- `gray_empire_01.json`
- `forest_star_01.json`
- `north_clan_01.json`
- `tide_trade_01.json`
- `steppe_tent_01.json`
- `forge_city_01.json`
- `night_contract_01.json`

---

## 2. 各文化圏に必ず含める内容

各 JSON には、PR-001 の `Culture` 型に沿って少なくとも以下を入れてください。

- id
- displayName
- shortName
- environmentTags
- economyTags
- governanceTags
- religionTags
- namingProfile
- rites
- festivals
- favoredRaces
- slurTargets
- socialAliases
- itemNamingRules

---

## 3. namingProfile に必ず含める内容

各文化圏の `namingProfile` には最低限以下を持たせてください。

- phonemeTendency
- semanticRoots
- usesBaptismName
- adultRename
- secretTrueName
- commonItemNamedRate
- ritualItemNamedRate
- heirloomNamedRate
- properNameRate
- trueNameRate

### 重要方針

- 文化圏ごとに音の傾向が違うこと
- 文化圏ごとに象徴語が違うこと
- 文化圏ごとに「一般品にどの程度名が付くか」が違うこと
- 冥契夜界圏や樹海星詠圏では真名文化が強く、聖暦王国圏や灰鉄帝政圏では相対的に制度名・型式名・洗礼名が強い、などの差を反映すること

---

## 4. 8文化圏の内容要件

以下の設定意図を反映してください。

### 1. 聖暦王国圏
特徴:
- 王権と神殿権威の並立
- 洗礼、誓約、騎士、農耕共同体
- 季節祭が多い
- 命名は比較的気品と信仰寄り

象徴語の方向性:
- 光
- 白
- 誓い
- 守護
- 獅子
- 晨

### 2. 灰鉄帝政圏
特徴:
- 軍政、官僚、戸籍、制式化、功績主義
- 記録文化が強い
- 命名は短く硬い
- 個人名より所属や型式が強くなりやすい

象徴語の方向性:
- 灰
- 鉄
- 冠
- 黒陽
- 勲
- 断
- 軍

### 3. 樹海星詠圏
特徴:
- 長命種、森の民、精霊契約、月と星
- 秘名・真名文化が強い
- 文字より歌や記憶も重要
- 名は流麗で詩的

象徴語の方向性:
- 月
- 星
- 露
- 葉
- 水
- 梢
- 薄明

### 4. 北境牙氏族圏
特徴:
- 寒冷地、狩猟、氏族、祖霊、戦名
- 成人儀礼と戦功が重い
- 本名より戦名が有名になりやすい

象徴語の方向性:
- 冬
- 牙
- 狼
- 祖
- 炎
- 嵐
- 石

### 5. 潮路商邦圏
特徴:
- 港、交易、契約、商会、混血、多文化接触
- 商品名や商号文化が発達
- 実利と祝祭性が共存

象徴語の方向性:
- 潮
- 帆
- 玻璃
- 星
- 路
- 塩
- 青
- 灯

### 6. 天幕遊牧圏
特徴:
- 草原、移動生活、弓騎、風、空、歌
- 風名や成人後の改名文化がある
- 文字より口承が強い

象徴語の方向性:
- 空
- 風
- 蹄
- 蒼
- 巡り
- 鷹
- 矢

### 7. 炉都坑道圏
特徴:
- 鍛冶、坑道、組合、工房、品質保証、刻印文化
- 工房銘や工印が強い
- 人名以上に工房名が目立つこともある

象徴語の方向性:
- 炉
- 鋼
- 礎
- 環
- 鉱
- 火
- 鎚
- 石

### 8. 冥契夜界圏
特徴:
- 契約、仮面、秘名、真名禁忌、代価、夜の秩序
- 真名や秘名の重要性が非常に高い
- 社会人格と本質名が分かれている文化

象徴語の方向性:
- 夜
- 影
- 月蝕
- 深淵
- 契
- 黒
- 棺
- 終

---

## 5. rites / festivals の参照ID

今回は rites / festivals の実ファイルがまだ空でも構いませんが、後続PRで接続できるように **参照予定IDを先に入れてください**。

例:
- `naming_baptism`
- `adult_oath`
- `knighting`
- `lamp_funeral`
- `spring_tillage_festival`
- `summer_solstice_light`

重要:
- 文化圏ごとに rites / festivals の候補が違うこと
- 同じ儀礼カテゴリでも文化圏によってIDや意味が違ってよいこと

---

## 6. slurTargets / socialAliases の扱い

各文化圏ごとに、特定種族や他文化圏集団に対する社会的呼称の雛形を入れてください。

注意:
- 今回は過激な罵倒語を大量に作ることが目的ではない
- 文化差・歴史差が見える軽口〜侮蔑レベルの雛形を少数入れる
- ランダム悪口ではなく、身体特徴・生活様式・信仰・歴史関係が反映されていること

例の方向性:
- 長耳
- 石チビ
- 港ネズミ
- 角付き
- 夜連中

---

## 7. itemNamingRules の作り分け

各文化圏で次の差を出してください。

- 一般品が無銘中心か
- 工房銘が一般的か
- 軍や国家の型式名が強いか
- 儀礼品に名前が付くか
- 家宝や継承品に名前が付きやすいか

たとえば:
- 灰鉄帝政圏 → militaryPatternNames が強い
- 炉都坑道圏 → craftMarksCommon が強い
- 樹海星詠圏 → ritualItemsNamed / heirloomsNamed が強い
- 冥契夜界圏 → proper / true name が相対的に強い

---

## 8. README または説明ファイルの追加

今回追加した8文化圏について、レビュー用に短い説明 md を追加してください。

内容:
- 8文化圏の一覧
- それぞれの主題
- 命名・儀礼・祭礼・装備名の違いがどこに出る想定か

長文でなくて構いませんが、差分がレビューしやすい形にしてください。

---

# 必須要件

- JSON の構造は 8文化圏で統一してください
- 文化圏ごとの差が namingProfile と itemNamingRules に現れていること
- 種族と文化圏は分離した設計のままにしてください
- rites / festivals は今後の接続を見越した参照IDで構いません
- displayName と internal id を混同しないでください
- 後続PRで辞書や命名生成ロジックを追加しやすいようにしてください

---

# 今回はやらないこと

- 種族JSONの投入
- 儀礼JSON / 祭礼JSONの実体投入
- 命名生成ロジックの実装
- テスト本体
- UI
- API

今回はあくまで、文化圏の初期データ投入に集中してください。

---

# 期待する成果物

- 8文化圏の JSON ファイル
- 構造が揃ったデータ
- 文化圏ごとの命名傾向と命名率差
- 後続PRで種族、儀礼、祭礼、語彙辞書を接続しやすい状態
- 文化圏差がレビューしやすい説明ファイル

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 作成した JSON ファイル一覧
2. 各文化圏の差分の要点
3. rites / festivals にどういう参照IDを入れたか
4. 後続PRで追加すべきもの
5. データモデリング上の懸念点があればその指摘
```

---

## 30. PR-003 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-003 を依頼すること。

```md
# 依頼内容

今回は **PR-003: 種族分類・俗称・蔑称データ投入** を実装してください。

前提として、PR-001 で型定義、PR-002 で文化圏 JSON が存在している想定です。今回は、プレイアブル種族と社会的呼称の基盤となる **種族JSONデータ** を投入してください。

目的は、種族を身体的・学術的分類として定義しつつ、文化圏や社会による俗称・蔑称・バイアスを表現できる土台を作ることです。

---

# 実装範囲

`src/data/races/` 以下に、少なくとも次のファイルを作成してください。

- `human.json`
- `elf.json`
- `dwarf.json`
- `warbeast.json`
- `birdfolk.json`
- `dragonute.json`
- `fey.json`
- `demonian.json`
- `fallen.json`

---

## 1. 各種族に必ず含める内容

PR-001 の `Race` 型に沿って、少なくとも以下を入れてください。

- id
- displayName
- formalNameKanji
- formalNameKatakana
- academicCategory
- socialNames
- slurNames
  - mild
  - harsh
  - taboo
- biologicalTraits
- lifespanClass
- playable
- defaultCultureBias
- metadata

---

## 2. 種族定義の基本方針

### 人類種（ヒューマン）
- 基準種として広く分布
- 文化圏の分化が最も大きい
- 種族差より文化差が目立つ場合が多い

### 長命種（エルフ）
- 長寿、魔力感応、軽量、森や星詠み文化との相性が高い
- ただし特定文化圏専属にはしない
- 社会的には「森の民」「梢の人」などの別名もありうる

### 小人種（ドワーフ）
- 工房、鍛造、坑道、耐久性、職能共同体と相性が高い
- ただし全員が鍛冶屋である必要はない

### 獣人種（ワービースト）
- 亜種が多い前提でよい
- 嗅覚、感覚、身体能力、牙・爪・毛皮などの生物的特徴を持ちうる
- 氏族文化と都市文化の両方に適応しうる余地を残す

### 翼人種（バードフォーク）
- 滑空・飛行・高所適性・視認性などの特徴候補
- 天幕遊牧圏や沿岸圏との接続余地あり
- 一般社会では「鳥頭」系の軽口が生じうる

### 竜鱗種（ドラゴニュート）
- 鱗、熱耐性、威圧感、血統意識、誇りなどの要素候補
- 文化圏によっては尊敬と恐れが混ざる

### 妖精種（フェイ）
- 小型に限定しない
- 精霊・妖異・気まぐれ・自然親和・時間感覚差などを候補にする
- 人間社会から見ると理解しづらい存在でもよい

### 魔生種（デモニアン）
- いわゆるプレイアブル寄りの「魔族」の中核
- 社会、法、契約、家系、文化を持つ
- 単なる魔物ではない
- 冥契夜界圏と相性が高いが固定しない

### 堕性種（フォールン）
- 生得種ではなく、変質・呪い・堕化・汚染由来の分類として扱う
- 一般社会からの偏見や危険視を受けやすい
- 条件付きプレイアブルでもよいように設計する

---

## 3. 学術分類と社会的呼称を分けること

各種族には、正式名だけでなく `socialNames` を持たせてください。

例:
- 長命種（エルフ） → 森の民 / 梢の人
- 小人種（ドワーフ） → 炉の民 / 岩の手
- 魔生種（デモニアン） → 夜の民 / 契りの民

目的:
- 世界内で学者・神殿・庶民が異なる呼び方をする余地を持たせる

---

## 4. slurNames の方針

各種族に mild / harsh / taboo の3段階を持たせてください。

注意:
- ランダムな悪口集にしないこと
- 身体特徴、文化差、歴史的対立、誤解を反映すること
- 過度に現実の差別語に寄せないこと

方向性の例:
- 長命種 → 長耳
- 小人種 → 石チビ / 岩チビ
- 翼人種 → 鳥頭
- 竜鱗種 → 鱗持ち
- 魔生種 → 角付き / 夜連中
- 堕性種 → 堕ちもの / 汚れ血 などの強い偏見語の候補

ただし taboo は件数少なめでよいです。無理にすべての層を大量に埋める必要はありません。

---

## 5. 魔族系の扱い

今回の PR では、少なくともプレイアブル分類としては `demonian` と `fallen` を投入してください。

重要:
- 魔族を「単一種族」として雑に閉じないこと
- `demonian` は社会性を持つ魔生種として扱うこと
- `fallen` は別種からの変質・堕化系統として扱うこと
- 将来的に `demon_beast` `infernal_spirit` `primordial` などを追加できる余地を metadata や academicCategory に残してよい

---

## 6. defaultCultureBias の方針

各種族に「相性が良い / 多く見られる」文化圏候補を持たせてください。ただし、固定所属にはしないでください。

例:
- 長命種 → forest_star, holy_kingdom_minorities など
- 小人種 → forge_city, gray_empire
- 獣人種 → north_clan, steppe_tent, tide_trade
- 魔生種 → night_contract

目的:
- 後続の生成ロジックで自然な組み合わせを出しやすくする
- しかし例外個体は十分ありうる世界にする

---

## 7. metadata / notes

各種族に簡単な補足を書いてください。

内容候補:
- 実装メモ
- 今後増やしたい亜種
- 文化圏差の余地
- 偏見や禁忌の注意点

---

## 8. README または説明ファイル

レビュー用に短い md ファイルを追加してください。

内容:
- 今回投入した 9 種族の一覧
- 各種族の主な特徴
- 学術分類と社会的呼称の違い
- 魔生種 / 堕性種をどう切り分けたか

---

# 必須要件

- 種族と文化圏を一対一対応させないでください
- displayName と formalNameKanji / formalNameKatakana を整理してください
- socialNames と slurNames を分けてください
- 魔族系を単一の雑な一項目で終わらせないでください
- 後から亜種や上位分類を足しやすい形にしてください

---

# 今回はやらないこと

- 命名生成ロジック
- 儀礼JSON / 祭礼JSONの実体投入
- 語彙辞書投入
- UI
- API
- テスト本体

今回はあくまで、種族分類データ投入に集中してください。

---

# 期待する成果物

- 9種族分のJSONデータ
- 学術分類と社会的呼称が分かれた構造
- 俗称・蔑称を含むが、雑な悪口リストになっていないデータ
- 文化圏バイアスを持ちつつ固定化しない種族データ
- 魔生種 / 堕性種の切り分けが明確な状態

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 作成した JSON ファイル一覧
2. 各種族の要点
3. socialNames / slurNames の設計方針
4. demonian / fallen をどう分けたか
5. 後続PRで追加すべきもの
```

---

## 31. PR-004 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-004 を依頼すること。

```md
# 依頼内容

今回は **PR-004: 儀礼・祭礼モジュール辞書投入** を実装してください。

前提として、PR-001 で型定義、PR-002 で文化圏 JSON、PR-003 で種族 JSON が存在している想定です。今回は、文化イベント生成・物語分岐・周回変化の基盤となる **儀礼辞書** と **祭礼辞書** を JSON で投入してください。

目的は、単なるフレーバーではなく、成人、洗礼、婚姻、葬送、加入、巡礼、記念祭、市場祭、戦勝祭などを、後で会話・イベント・世界変化ロジックから参照できる構造にすることです。

---

# 実装範囲

以下を実装してください。

- `src/data/rites/common_rites.json`
- `src/data/festivals/common_festivals.json`

---

## 1. 儀礼データの件数目安

`common_rites.json` に、少なくとも **24件以上** の儀礼を入れてください。

カテゴリは PR-001 の `RiteCategory` に沿って、最低でも以下を含めてください。

- birth
- naming
- baptism
- coming_of_age
- guild_entry
- military_entry
- marriage
- succession
- funeral
- true_name
- pilgrimage
- craft_mastery

可能なら各カテゴリ2件以上あると望ましいです。

---

## 2. 祭礼データの件数目安

`common_festivals.json` に、少なくとも **32件以上** の祭礼を入れてください。

カテゴリは PR-001 の `Festival` に沿って、最低でも以下を含めてください。

- seasonal
- market
- military
- religious
- memorial
- competition
- pilgrimage
- hero_origin

可能なら各カテゴリ3〜4件程度あると望ましいです。

---

## 3. 儀礼の設計方針

各儀礼には少なくとも以下を入れてください。

- id
- displayName
- category
- description
- tags
- relatedCultures
- grants

`grants` には必要に応じて以下を入れてください。
- title
- socialStatus
- rename
- itemNamingPrivilege

### 儀礼の方向性例

- 命名洗礼
- 成人誓約
- 初狩り
- 月下巡礼
- 牙結び
- 工印授与
- 契印刻み
- 仮面受領
- 枝継ぎ婚
- 火囲み婚
- 海送り葬
- 還樹葬
- 石室葬
- 真名授受
- 師資継承

重要:
- 同じ category でも文化圏ごとに内容が違うこと
- 儀礼が改名、称号付与、所属変化、工房銘の権利獲得などに結びつく余地を持つこと

---

## 4. 祭礼の設計方針

各祭礼には少なくとも以下を入れてください。

- id
- displayName
- category
- description
- seasonTags
- relatedCultures
- mutationEligible

### 祭礼の方向性例

- 春耕祝祭
- 夏至の光祭
- 秋穣祭
- 冬灯の夜
- 建国軍閲祭
- 戦勝凱旋祭
- 新芽祭
- 星降り夜会
- 初雪宴
- 狼月の夜
- 海開き祭
- 帆風市
- 大競馬祭
- 炉開き
- 大鍛祭
- 新月契日
- 月蝕の市
- 亡名追悼の灯

重要:
- 季節祭、市場祭、軍事祭、宗教祭、競技祭、巡礼祭、記念祭が混ざること
- 一部は `mutationEligible: true` にして、主人公由来の変化対象にできること

---

## 5. relatedCultures の扱い

各儀礼・祭礼には、関連文化圏を 1つ以上設定してください。

重要:
- 完全専用でもよい
- 複数文化圏共有でもよい
- 同名異義よりも、まずは ID の一意性を優先してください

---

## 6. hero_origin カテゴリについて

祭礼カテゴリ `hero_origin` は、主人公や英雄、救国、悲劇、再建などの出来事から後天的に生まれる祭りを想定したカテゴリです。

今回は、少なくとも 4件以上の雛形を用意してください。

例の方向性:
- 帰還祭
- 救国祈祷日
- 無名兵追想祭
- 黒門封鎖記念日

重要:
- まだ具体的主人公がいなくても、後からフラグで接続できる雛形として定義すること

---

## 7. README または説明ファイル

レビュー用に短い md ファイルを追加してください。

内容:
- 儀礼と祭礼の件数
- カテゴリ別の内訳
- 改名・称号付与・所属変化に繋がる儀礼の例
- 周回変化で増やしやすい祭礼の例

---

# 必須要件

- 儀礼24件以上、祭礼32件以上を満たしてください
- category, tags, relatedCultures を必ず入れてください
- 儀礼は単なる説明文で終わらず、社会的効果の余地を持たせてください
- 祭礼は文化圏と季節・市場・宗教・戦争・巡礼などの性質が見えるようにしてください
- 後続PRで命名や世界変化と接続しやすいデータ構造にしてください

---

# 今回はやらないこと

- 命名生成ロジック
- 語彙辞書投入
- UI
- API
- テスト本体
- 世界変異ロジックの実装本体

今回はあくまで、辞書データ投入に集中してください。

---

# 期待する成果物

- 儀礼辞書 JSON
- 祭礼辞書 JSON
- 文化圏差が見えるイベントデータ
- 後続PRで会話生成、命名、世界変異に接続しやすい辞書

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 儀礼と祭礼の件数
2. カテゴリ別内訳
3. 代表的な儀礼・祭礼の例
4. mutationEligible を付けた祭礼の例
5. 後続PRで追加すべきもの
```

---

## 32. 次に作成すべき完全版プロンプト

次は以下の順で、同じ粒度の完全版プロンプトを追加していくこと。

1. PR-005 語彙辞書整備
2. PR-006 命名整形ユーティリティ実装
3. PR-007 一般命名生成エンジン実装
4. PR-008 魔法・技能命名生成エンジン実装
5. PR-009 古代遺物命名と段階解放ロジック実装
6. PR-010 世界変化・周回変異システム実装
7. PR-011 テスト実装
8. PR-012 サンプル出力とデバッグ用図鑑データ生成

この順で作ると、Codexに順送りで渡せる。

---

## 33. PR-005 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-005 を依頼すること。

```md
# 依頼内容

今回は **PR-005: 語彙辞書の整備** を実装してください。

前提として、PR-001 で型定義、PR-002 で文化圏 JSON、PR-003 で種族 JSON、PR-004 で儀礼・祭礼辞書が存在している想定です。今回は、後続の命名生成エンジンが参照するための **語彙辞書 JSON 一式** を投入してください。

目的は、文化圏ごとの命名傾向を文字列生成でなく辞書参照ベースで安定化させること、一般語と固有名語彙、俗称と真名語彙、制式名と詩的名を混ぜずに扱えるようにすることです。

---

# 実装範囲

`src/data/vocab/` 以下に、少なくとも次のファイルを作成してください。

- `semantic_roots.json`
- `slurs.json`
- `titles.json`
- `item_patterns.json`
- `magic_patterns.json`
- `relic_patterns.json`

---

## 1. semantic_roots.json

目的:
- 文化圏ごとの象徴語・意味語根を管理する

最低限持たせたい項目:
- id
- surface
- cultureIds
- tags
- weight
- usageDomains

`usageDomains` の例:
- person_name
- place_name
- title
- weapon_name
- armor_name
- ritual_name
- magic_name
- relic_name

重要:
- 文化圏ごとの差が見えるようにすること
- 同じ語でも文化圏によって weight を変えてよい
- 一般語と真名語彙を混ぜないこと

文化圏ごとの方向性例:
- 聖暦王国圏 → 光、白、誓い、守護、獅子、晨
- 灰鉄帝政圏 → 灰、鉄、冠、黒陽、勲、断、軍
- 樹海星詠圏 → 月、星、露、葉、水、梢、薄明
- 北境牙氏族圏 → 冬、牙、狼、祖、炎、嵐、石
- 潮路商邦圏 → 潮、帆、玻璃、星、路、塩、青、灯
- 天幕遊牧圏 → 空、風、蹄、蒼、巡り、鷹、矢
- 炉都坑道圏 → 炉、鋼、礎、環、鉱、火、鎚、石
- 冥契夜界圏 → 夜、影、月蝕、深淵、契、黒、棺、終

件数目安:
- 全体で 120件以上
- 各文化圏で最低 12〜15件程度は関連語を持つ

---

## 2. slurs.json

目的:
- 俗称・軽口・侮蔑語を、文化差や関係史を踏まえて辞書化する

最低限持たせたい項目:
- id
- surface
- sourceCultureIds
- targetRaceIds
- severity
- tags
- notes

`severity` の例:
- mild
- harsh
- taboo

重要:
- 種族 JSON に入れた slurNames と矛盾しないこと
- 身体特徴、生活様式、宗教差、歴史対立などが感じられること
- ランダム悪口集にしないこと
- 過剰に現実差別に寄せないこと

件数目安:
- 全体で 40件以上

---

## 3. titles.json

目的:
- 称号、位階、二つ名、役職、儀礼称号を分けて管理する

最低限持たせたい項目:
- id
- surface
- cultureIds
- category
- tags
- weight

`category` の例:
- noble_title
- military_rank
- ritual_title
- heroic_epithet
- craft_rank
- priestly_title
- clan_title

例の方向性:
- 白暁の騎士
- 灰冠監察官
- 星梢の巫子
- 狼喰い
- 深脈鍛匠
- 月蝕侯

件数目安:
- 全体で 80件以上

---

## 4. item_patterns.json

目的:
- 一般装備、工房銘、制式装備、通称、儀礼品の命名テンプレートを管理する

最低限持たせたい項目:
- id
- category
- cultureIds
- namingTier
- patternType
- template
- tags
- weight

`namingTier` の例:
- generic
- workshop
- pattern
- slang
- ritual
- proper

`patternType` の例:
- material_plus_type
- region_plus_type
- workshop_plus_material_plus_type
- group_plus_pattern_number
- symbolic_plus_type

テンプレート例:
- `{material}{baseType}`
- `{region}{baseType}`
- `{workshop}工房製{material}{baseType}`
- `{group}{baseType}{patternNumber}`
- `{symbolicRoot}の{baseType}`

件数目安:
- 全体で 60件以上

---

## 5. magic_patterns.json

目的:
- 一般魔法、学術魔法、流派秘術、禁呪の命名テンプレートを管理する

最低限持たせたい項目:
- id
- cultureIds
- tier
- patternType
- template
- tags
- weight

`tier` の例:
- common
- advanced
- secret
- taboo

`patternType` の例:
- kanji_katakana
- academic_formula
- school_secret
- title_plus_true

テンプレート例:
- `{kanjiName}《{readingName}》`
- `{element}属性{function}術{rank}`
- `{school}秘術《{secretName}》`
- `{poeticTitle}《{trueName}》`

件数目安:
- 全体で 50件以上

---

## 6. relic_patterns.json

目的:
- 古代遺物の現代解釈名、真名、古名、伏せ字名の構築に使うテンプレートを管理する

最低限持たせたい項目:
- id
- cultureIds
- relicClass
- patternType
- template
- tags
- weight

`relicClass` の例:
- ancient_weapon
- ancient_crown
- gate_relic
- divine_fragment
- sealed_artifact

`patternType` の例:
- interpretation_name
- modern_plus_true
- title_plus_true
- masked_true_name
- archaic_true_name

テンプレート例:
- `古代{color}{baseType}`
- `{interpretationName}《{trueName}》`
- `{interpretationName}《{maskedTrueName}》`
- `{poeticTitle}《{archaicTrueName}》`

件数目安:
- 全体で 40件以上

---

## 7. README または説明ファイル

レビュー用に短い md ファイルを追加してください。

内容:
- 6ファイルの役割
- 文化圏差がどの辞書にどう出るか
- 一般語と固有名語彙をどう分けたか
- 真名・古名向け語彙をどう扱ったか

---

# 必須要件

- 辞書は文化圏や用途で参照可能な構造にしてください
- 一般用語と固有名用語を混ぜないでください
- 種族 JSON や文化圏 JSON と矛盾しないようにしてください
- 真名や古名は relic_patterns や semantic_roots 側で特別扱いできるようにしてください
- 後続PRで命名生成関数から使いやすい構造にしてください

---

# 今回はやらないこと

- 命名生成ロジック本体
- UI
- API
- テスト本体
- 古代遺物の解放ロジック本体

今回は辞書データ整備に集中してください。

---

# 期待する成果物

- 6種類の語彙辞書 JSON
- 文化圏差が命名に反映できる辞書構造
- 一般名 / 固有名 / 真名 / 蔑称 / 制式名を分けて扱える土台

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 作成した辞書ファイル一覧
2. 各辞書の件数
3. 文化圏差をどう表現したか
4. 真名・古名語彙をどう分離したか
5. 後続PRで使う想定をどう置いたか
```

---

## 34. PR-006 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-006 を依頼すること。

```md
# 依頼内容

今回は **PR-006: 命名整形ユーティリティ実装** を実装してください。

前提として、PR-001〜PR-005 により型定義、文化圏データ、種族データ、儀礼・祭礼辞書、語彙辞書が揃っている想定です。今回は、命名生成本体の前段として、**表記ルールをコード化する整形ユーティリティ関数群** を実装してください。

目的は、世界観ルールとして決めた表記形式を、今後の全命名出力で一貫して使えるようにすることです。

---

# 実装範囲

次のような責務を持つユーティリティを実装してください。

想定配置:
- `src/domain/world/generators/naming/formatters.ts`
- または同等の適切な場所

必要に応じて補助ファイルを追加して構いません。

---

## 1. 実装したい関数

少なくとも以下を実装してください。

### `formatKanjiKatakanaName()`
目的:
- 一般魔法・一般技能の `漢字《カタカナ》` 表記を作る

例:
- `土壁《アースウォール》`
- `受け流し《パリィ》`

### `formatTitlePlusTrueName()`
目的:
- 固有名・異名・称号句 + 真名 の表記を作る

例:
- `傲慢なる水竜王《アクアハーティア》`
- `白誓の剣《ルクス・オース》`

### `formatModernPlusTrueName()`
目的:
- 古代遺物の `現代解釈名《真名》` 表記を作る

例:
- `古代黒大剣《終ノ門ヲ啓クモノ》`

### `maskTrueName()`
目的:
- 真名や古名を伏せ字化する

例:
- `終ノ門ヲ啓クモノ` → `◼◼◼◼◼◼◼◼◼`

要件:
- 完全伏せ字だけでなく、一部可視化の余地がある設計でも可
- ただし今回の標準出力は全伏せ字でよい

### `buildFullDisplayName()`
目的:
- NameLayer から `fullDisplay` を組み立てる
- displayMode に応じて適切な形式を返す

対応したい displayMode 例:
- plain
- kanji_katakana
- modern_plus_true
- title_plus_true
- masked_true_name

---

## 2. 実装方針

- 単純な文字列連結ではなく、空文字や未定義に耐えること
- 将来的に UI 側で詳細表示用と一覧表示用を分けられるような拡張余地を残すこと
- `NameLayer` を入力にして `fullDisplay` を返せる構造を優先すること
- 不正な入力時の最低限の防御を入れてよい

---

## 3. 期待する出力例

最低限、次のようなケースを正しく扱えるようにしてください。

- 一般魔法
  - 入力: `displayName=土壁, readingName=アースウォール`
  - 出力: `土壁《アースウォール》`

- 一般技能
  - 入力: `displayName=受け流し, readingName=パリィ`
  - 出力: `受け流し《パリィ》`

- 固有武器
  - 入力: `formalName=傲慢なる水竜王, trueName=アクアハーティア`
  - 出力: `傲慢なる水竜王《アクアハーティア》`

- 古代遺物（解放済み）
  - 入力: `interpretationName=古代黒大剣, trueName=終ノ門ヲ啓クモノ`
  - 出力: `古代黒大剣《終ノ門ヲ啓クモノ》`

- 古代遺物（未解放）
  - 入力: `interpretationName=古代黒大剣, maskedTrueName=◼◼◼◼◼◼◼◼◼`
  - 出力: `古代黒大剣《◼◼◼◼◼◼◼◼◼》`

---

## 4. README または説明ファイル

短い md を追加してください。

内容:
- 実装した関数一覧
- 各関数の責務
- `NameLayer` と `displayMode` の関係
- 後続PRの命名生成エンジンがどう利用する想定か

---

# 必須要件

- 表記ルールを世界観仕様通りに反映してください
- `《》` を標準表記として扱ってください
- 古代遺物の `現代解釈名《真名》` と `現代解釈名《伏せ字真名》` の両方を扱えるようにしてください
- 一般名、固有名、真名を同じテンションで混ぜない構造にしてください
- 今後の命名生成本体から再利用しやすい関数設計にしてください

---

# 今回はやらないこと

- 文化圏ごとの語彙選定ロジック
- 命名生成本体
- 古代遺物の解放条件判定ロジック
- UI
- API

今回はあくまで、整形ロジックに集中してください。

---

# 期待する成果物

- 命名整形ユーティリティ関数群
- 代表例を正しく出力できるコード
- 後続PRで naming engine から直接使える関数構造

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 作成した関数一覧
2. 各関数の役割
3. 想定した displayMode 一覧
4. 表記ルール上の注意点
5. 後続PRでどう使う前提か
```

---

## 35. PR-007 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-007 を依頼すること。

```md
# 依頼内容

今回は **PR-007: 一般命名生成エンジン実装** を実装してください。

前提として、PR-001〜PR-006 により型定義、文化圏データ、種族データ、儀礼・祭礼辞書、語彙辞書、表記整形ユーティリティが揃っている想定です。今回は、**人名・地名・一般アイテム名** を生成する基礎命名エンジンを実装してください。

目的は、文化圏・種族・社会階層・命名階層を入力として、雰囲気だけでない一貫した名前を返せるようにすることです。

---

# 実装範囲

想定配置:
- `src/domain/world/generators/naming/peopleNameGenerator.ts`
- `src/domain/world/generators/naming/placeNameGenerator.ts`
- `src/domain/world/generators/naming/itemNameGenerator.ts`
- 必要に応じて `namingService.ts`

---

## 1. 実装したい関数

### `generatePersonName()`

想定シグネチャ:

```ts
generatePersonName(input: {
  cultureId: string;
  raceId: string;
  genderStyle?: "masculine" | "feminine" | "neutral";
  socialTier?: "commoner" | "noble" | "priest" | "warrior" | "merchant";
  hasSecretTrueName?: boolean;
}): NameLayer
```

目的:
- 文化圏の音傾向と象徴語を反映した人名を生成する
- 種族は生物的傾向や defaultCultureBias に影響するが、文化圏と同一視しない
- socialTier により名前の長さや格調差が出てもよい

---

### `generatePlaceName()`

想定シグネチャ:

```ts
generatePlaceName(input: {
  cultureId: string;
  placeType: "city" | "village" | "fortress" | "forest" | "port" | "ruin" | "holy_site";
  ancient?: boolean;
}): NameLayer
```

目的:
- 地名の文化圏差を出す
- placeType により語尾やテンプレート差が出せると望ましい
- ancient=true の場合は古層の名前寄りにしてもよい

---

### `generateItemName()`

想定シグネチャ:

```ts
generateItemName(input: {
  cultureId: string;
  category: ItemCategory;
  baseType: string;
  rarityTier: string;
  namingTier?: NamingTier;
  maker?: string;
  militaryPattern?: string;
  ritual?: boolean;
}): NameLayer
```

目的:
- 一般装備の名前を生成する
- generic / workshop / pattern / slang / ritual / proper を扱える基礎を作る
- ただし今回は主に generic / workshop / pattern / slang あたりを優先でよい

---

## 2. 実装方針

### 人名
- cultureId を最優先に参照
- semantic_roots と phonemeTendency を組み合わせる
- noble / priest などはやや格調高めでもよい
- 長命種や魔生種などは必要なら補助バイアスをかけてよいが、文化圏支配を崩さないこと

### 地名
- placeType によってテンプレートを切り替える
- 港なら潮路商邦圏の語彙が出やすい、砦なら灰鉄帝政圏や北境牙氏族圏の語彙が出やすい、などの自然な差を作る

### 一般アイテム名
- すべてに固有名を付けないこと
- generic は材質 + 種別などの説明的名称を優先
- workshop は工房名や地域名を足す
- pattern は制式名・型式名を使う
- slang は通称・俗称寄りにする

---

## 3. 期待する挙動例

### 人名
- 聖暦王国圏 + 人類種 + noble → やや格調高い名
- 樹海星詠圏 + 長命種 → 流麗で星や月の語感を持つ名
- 北境牙氏族圏 + 獣人種 → 短く力強い名、または戦名向きの響き

### 地名
- 潮路商邦圏 + port → 港や航路を感じる名前
- 炉都坑道圏 + city → 炉・鉱・環などを含みやすい名前
- 冥契夜界圏 + ruin → 夜や影や終を感じる古い響き

### 一般アイテム名
- generic → `鋼短剣` `狩猟弓` `厚革外套`
- workshop → `黒炉工房製鋼短剣`
- pattern → `王都歩兵剣三式`
- slang → `狼殺し` `青瓶`

---

## 4. README または説明ファイル

短い md を追加してください。

内容:
- 実装したジェネレータ一覧
- cultureId / raceId / namingTier の使い分け
- 一般品に固有名を乱発しないための方針
- 今回時点での制限事項

---

# 必須要件

- 文化圏ごとの差が出ること
- 種族と文化圏を混同しないこと
- 無銘品が大半になる設計であること
- 工房銘・型式名・通称の差が表現できること
- 表記整形は PR-006 のユーティリティを利用すること

---

# 今回はやらないこと

- 魔法・技能の命名生成
- 古代遺物の命名生成
- 真名解放ロジック
- 世界変異ロジック
- UI
- API

今回は人名・地名・一般アイテムに集中してください。

---

# 期待する成果物

- 人名生成関数
- 地名生成関数
- 一般アイテム名生成関数
- 文化圏差と命名階層差が出る実装

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 実装したジェネレータ一覧
2. 文化圏差をどう反映したか
3. namingTier をどう扱ったか
4. 一般品と上位品の差をどう出したか
5. 残る制約や今後の拡張点
```

---

## 36. PR-008 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-008 を依頼すること。

```md
# 依頼内容

今回は **PR-008: 魔法・技能命名生成エンジン実装** を実装してください。

前提として、PR-001〜PR-007 により型定義、文化圏・種族・儀礼・祭礼・語彙辞書・表記整形ユーティリティ・一般命名エンジンが存在している想定です。今回は、**一般魔法、学術魔法、流派秘術、禁呪、一般技能、戦技、奥義** の命名生成を実装してください。

目的は、すべてを同じテンションの必殺技名にせず、一般呪文は説明的に、秘術や禁呪だけが重い名前を持つようにすることです。

---

# 実装範囲

想定配置:
- `src/domain/world/generators/naming/magicNameGenerator.ts`
- `src/domain/world/generators/naming/skillNameGenerator.ts`
- 必要に応じて `namingService.ts` に統合可

---

## 1. 実装したい関数

### `generateMagicName()`

想定シグネチャ:

```ts
generateMagicName(input: {
  cultureId: string;
  tier: "common" | "advanced" | "secret" | "taboo";
  elementTags: string[];
  functionTags: string[];
}): Skill
```

目的:
- 一般魔法から禁呪まで、階層差を持った名前を生成する

---

### `generateSkillDisplay()` または同等の関数

想定シグネチャ例:

```ts
generateSkillDisplay(input: {
  cultureId: string;
  category: "combat_basic" | "combat_art" | "craft" | "survival" | "social";
  tier: "common" | "advanced" | "secret";
  functionTags: string[];
  schoolName?: string;
}): Skill
```

目的:
- 一般技能、戦技、奥義の差を出す
- 一般技能は簡潔、奥義や秘伝だけ固有名寄りにする

---

## 2. 命名方針

### 一般魔法
- 説明的な名前を優先
- 原則 `漢字《カタカナ》`
- 例: `火球《ファイアボール》`, `土壁《アースウォール》`, `治癒《ヒール》`

### 学術魔法
- 学院、帝国、神殿などで使う体系名
- 属性 + 用途 + 位階 のような構造を許可
- 例: `地属性防壁術第一位階`

### 流派秘術
- 流派名や学校名が前に出る
- 例: `黒鶴流秘術《雨断ち》`

### 禁呪
- 重く、詩的・儀礼的・禁忌的でよい
- 例: `黒陽断章《グレイ・カタストロフ》`
- ただし乱発しないこと

### 一般技能・戦技
- 一般技能は簡潔
- 戦技は少しカタカナ読みを付けてもよい
- 例: `受け流し《パリィ》`, `連突《ラッシュスラスト》`

### 奥義・秘伝
- 流派名や異名を許可
- 例: `黒鶴流奥義《雨断ち》`

---

## 3. 期待する挙動例

### 一般魔法
- `火球《ファイアボール》`
- `土壁《アースウォール》`
- `影縫い《シャドウバインド》`

### 学術魔法
- `地属性防壁術第一位階`
- `治癒光循環法第二段`

### 秘術
- `星梢秘術《月糸》`
- `黒鶴流秘術《雨断ち》`

### 禁呪
- `黒陽断章《グレイ・カタストロフ》`
- `終末門儀《ラスト・ゲート》`

### 一般技能・戦技
- `受け流し《パリィ》`
- `強撃《パワーストライク》`
- `応急手当`
- `採掘`

---

## 4. 実装方針

- magic_patterns.json と semantic_roots.json を参照すること
- PR-006 の整形ユーティリティを使うこと
- `tier` により命名の重さを切り替えること
- 一般魔法や一般技能に固有名テンションを乱発しないこと
- cultureId により語彙傾向差が出ること

---

## 5. README または説明ファイル

短い md を追加してください。

内容:
- 実装した魔法・技能ジェネレータ一覧
- 一般魔法と禁呪の命名差
- 一般技能と奥義の命名差
- cultureId と tier をどう使ったか

---

# 必須要件

- 一般魔法は説明的であること
- 秘術・禁呪だけが重くなること
- 一般技能は簡潔であること
- 奥義や秘伝だけが流派名や固有名を持ちやすいこと
- 表記ルールは世界観仕様に従うこと

---

# 今回はやらないこと

- 古代遺物の命名生成
- 真名解放ロジック
- 世界変異ロジック
- UI
- API
- 本格テスト

今回は魔法・技能の命名生成に集中してください。

---

# 期待する成果物

- 魔法命名ジェネレータ
- 技能・戦技命名ジェネレータ
- 一般 / 学術 / 秘術 / 禁呪 の命名差が見える実装
- 一般技能 / 戦技 / 奥義 の命名差が見える実装

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 実装した関数一覧
2. tier ごとの命名差をどう出したか
3. cultureId の反映方法
4. 一般系と上位系をどう切り分けたか
5. 今後の拡張候補
```

---

## 37. 次に作成すべき完全版プロンプト

次は以下の順で続けること。

1. PR-009 古代遺物命名と段階解放ロジック実装
2. PR-010 世界変化・周回変異システム実装
3. PR-011 テスト実装
4. PR-012 サンプル出力とデバッグ用図鑑データ生成

ここまで作れば、Codexへ一連の順送り依頼がほぼ完成する。

---

## 38. PR-009 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-009 を依頼すること。

```md
# 依頼内容

今回は **PR-009: 古代遺物命名と段階解放ロジック実装** を実装してください。

前提として、PR-001〜PR-008 により型定義、文化圏・種族・儀礼・祭礼・語彙辞書・表記整形・一般命名・魔法技能命名が揃っている想定です。今回は、**古代遺物の命名生成** と **真名・覚醒の段階解放ロジック** を実装してください。

目的は、古代遺物を「現代解釈名 + 真名」で扱い、未解放時の伏せ字表示、条件不足時の“見えるが反映されない”状態、覚醒後の特殊効果解禁をシステムとして扱えるようにすることです。

---

# 実装範囲

想定配置:
- `src/domain/world/generators/naming/relicNameGenerator.ts`
- `src/domain/world/services/relicUnlockService.ts`
- 必要に応じて `src/domain/world/rules/unlockRules.ts`

必要に応じて補助ファイルを追加して構いません。

---

## 1. 実装したい関数・責務

### `generateRelicName()`

想定シグネチャ:

```ts
generateRelicName(input: {
  interpretationBase: string;
  originCultureId: string;
  relicClass: string;
  ancientTone?: "sacred" | "abyssal" | "royal" | "sealed";
  masked?: boolean;
}): NameLayer
```

目的:
- 現代解釈名と真名を組み合わせた古代遺物名を生成する
- masked=true の場合は伏せ字真名を使う

例:
- `古代黒大剣《終ノ門ヲ啓クモノ》`
- `古代黒大剣《◼◼◼◼◼◼◼◼◼》`
- `古代祭冠《白キ枝ノ王冠》`

---

### `relicUnlockService` または同等のサービス

最低限扱いたいこと:
- 未鑑定 → 鑑定済み
- 真名伏せ字表示
- 真名可視化
- 覚醒
- 条件未達時のロック維持
- hidden effects / hidden skills の制御

想定する UnlockStage:
- unidentified
- identified
- masked_true_name
- true_name_visible
- awakened

---

## 2. 段階解放仕様

以下の段階を少なくとも扱ってください。

### 1. 未鑑定
表示例:
- `古びた黒の大剣`

状態:
- 現代解釈名未確定でもよい
- 効果は最低限のみ
- 真名不明

### 2. 現代鑑定済み
表示例:
- `古代黒大剣`

状態:
- 武器種や大まかな分類が分かる
- 真名は不明
- 一部基本性能は見える

### 3. 真名断片 / 伏せ字表示
表示例:
- `古代黒大剣《◼◼◼◼◼◼◼◼◼》`

状態:
- 何か本質名があることは分かる
- hidden effect は見えても反映されない場合がある
- 固有技能は表示のみ、または封印中扱いでもよい

### 4. 真名認識
表示例:
- `古代黒大剣《終ノ門ヲ啓クモノ》`

状態:
- 真名が見える
- 特殊効果や技能の存在が開示される
- ただし完全適合でない限り full effect は反映されない場合がある

### 5. 覚醒
表示例:
- `古代黒大剣《終ノ門ヲ啓クモノ》【覚醒】`

状態:
- hidden effect 反映
- hidden skill 解禁
- trueNameVisible = true
- fullSync = true

---

## 3. 条件不足時の仕様

特に重要:
- **真名が見えていても、性能が反映されない状態** を扱えるようにしてください
- **特殊スキルが見えていても使用不能** を扱えるようにしてください

想定条件:
- ステータス値
- raceId
- cultureId
- trait
- 属性適性
- eventFlags
- relic 由来イベント完了

例:
- 筋力 80 未満では hiddenAttackBonus が反映されない
- `black_gate_ruins_clear` が無いと特殊スキルが封印されたまま
- 深淵感応 trait が無いと fullSync 不可

---

## 4. データとの接続

PR-001 の `Relic` / `Item` 型、PR-005 の `relic_patterns.json`、PR-006 の整形ユーティリティを利用してください。

期待すること:
- interpretationName と trueName を分離して扱う
- maskedTrueName を NameLayer に載せる
- hidden effect と visible effect を分離する

---

## 5. 期待する挙動例

### 未解放
- 表示: `古代黒大剣《◼◼◼◼◼◼◼◼◼》`
- baseAttack: 42
- hiddenAttackBonus: 49
- hiddenSkill: `gate_split`
- ただし hidden は反映されない

### 真名可視・未適合
- 表示: `古代黒大剣《終ノ門ヲ啓クモノ》`
- hiddenSkill の存在は見える
- ただし使用不可
- `lockedUntilSync: true`

### 覚醒
- 表示: `古代黒大剣《終ノ門ヲ啓クモノ》【覚醒】`
- hiddenAttackBonus 反映
- `gate_split` 使用可能
- fullSync = true

---

## 6. README または説明ファイル

短い md を追加してください。

内容:
- 古代遺物の段階一覧
- 真名表示と覚醒の違い
- hidden effect / hidden skill をどう扱ったか
- 後続PRで図鑑や UI からどう見せられる想定か

---

# 必須要件

- `現代解釈名《真名》` を標準表記として扱ってください
- 真名伏せ字表示を扱ってください
- 真名可視と fullSync を分けてください
- 条件不足時に“見えるが反映されない”状態を扱ってください
- 古代遺物だけを特別扱いしつつ、既存の Item / NameLayer 構造を壊さないでください

---

# 今回はやらないこと

- UIコンポーネント
- API
- 本格テスト
- 世界変異ロジック
- サンプル図鑑生成

今回は古代遺物命名と段階解放ロジックに集中してください。

---

# 期待する成果物

- relicNameGenerator
- relicUnlockService
- 古代遺物の段階解放ロジック
- 真名表示、伏せ字、hidden effect の制御

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 実装したファイル一覧
2. 段階解放の扱い方
3. hidden effect / hidden skill の扱い方
4. fullSync 条件の設計方針
5. 今後のUI接続で必要になりそうな点
```

---

## 39. PR-010 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-010 を依頼すること。

```md
# 依頼内容

今回は **PR-010: 世界変化・周回変異システム実装** を実装してください。

前提として、PR-001〜PR-009 により世界基盤、文化圏・種族・辞書・命名生成・古代遺物解放が存在している想定です。今回は、**主人公の行動や周回フラグによって文化・祭礼・俗称・装備名・制式名が変化する仕組み** を実装してください。

目的は、主人公が単に物語を体験するだけでなく、世界の文化や命名体系そのものに影響を与える存在として機能するようにすることです。

---

# 実装範囲

想定配置:
- `src/domain/world/services/worldMutationService.ts`
- `src/domain/world/rules/cultureRules.ts`
- `src/domain/world/rules/rarityRules.ts`
- 必要に応じて mutation 関連補助ファイル

---

## 1. 実装したい責務

### `worldMutationService`
最低限扱いたいこと:
- triggerFlags を受け取る
- mutation 定義を評価する
- festival の追加
- slang / title / naming pattern の追加
- 伝説装備の模造・制式化・商品化派生
- 公開儀礼化 / 禁忌解除の反映

---

## 2. 想定する変化対象

### 祭礼
- 新祭礼の誕生
- 記念日化
- 鎮魂祭の追加
- 地方祭の全国化

### 命名体系
- 主人公の異名が商品名になる
- 伝説装備が制式名になる
- 俗称が一般化する
- 模造品や廉価版の命名パターンが増える

### 儀礼
- 本来秘儀だったものが公開祭礼化する
- 特定文化圏でのみ行われていた儀礼が他文化へ波及する

### 社会語彙
- 蔑称や呼称が変質する
- 英雄名が尊称や地名に転化する

---

## 3. 最低限扱いたい mutation 例

以下のような雛形を少なくとも扱えるようにしてください。

### 例1: 伝説武器の派生
- trigger: 主人公が《冬吠》を使って大戦功を上げる
- effect:
  - `冬吠式長剣` という pattern name が追加
  - `冬式片刃剣` という廉価型 pattern が追加
  - `冬牙遊戯剣` という祭礼・玩具名が追加

### 例2: 新祭礼の誕生
- trigger: `black_gate_sealed`
- effect:
  - `black_gate_memorial_day` 追加
  - 関連文化圏に追悼祭や祈祷日追加

### 例3: 秘儀の公開化
- trigger: 主人公が特定文化圏の秘儀を再建
- effect:
  - `unlockPublicRite: true`
  - 関連祭礼を追加
  - 古名の一部が一般公開される

---

## 4. データ構造との接続

- `WorldMutation` 型を利用すること
- triggerFlags ベースで評価できるようにすること
- mutation の結果を festival, slang, title, naming pattern に反映できるようにすること

理想:
- 元データを破壊せず、派生差分として管理できる
- 複数周回や複数フラグの組み合わせに耐えられる

---

## 5. 期待する挙動例

### 伝説装備の派生
入力:
- triggerFlags: `["hero_winterhowl_legend"]`

出力例:
- 追加 pattern: `冬吠式長剣`
- 追加 pattern: `冬式片刃剣`
- 追加 festival: `winterhowl_commemoration`

### 黒門封鎖由来祭礼
入力:
- triggerFlags: `["black_gate_sealed"]`

出力例:
- festival 追加: `black_gate_memorial_day`
- title 追加: `黒門封じ`

---

## 6. README または説明ファイル

短い md を追加してください。

内容:
- mutation の適用単位
- triggerFlags の扱い方
- 祭礼 / 命名 / 儀礼への影響の違い
- 伝説装備が模造・制式化される流れの例

---

# 必須要件

- 主人公の行動で文化・命名が変わる構造にしてください
- 祭礼・俗称・制式名・商品名の派生を扱ってください
- 元データを壊さず派生差分として扱える設計にしてください
- 単なるフラグ一覧ではなく、文化世界への反映を意識してください

---

# 今回はやらないこと

- UI
- API
- 本格テスト
- サンプル図鑑生成

今回は世界変異ロジックに集中してください。

---

# 期待する成果物

- worldMutationService
- mutation 適用ロジック
- 祭礼・命名・俗称・儀礼の派生例

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 実装したファイル一覧
2. どの targetType を扱えるようにしたか
3. triggerFlags からどう派生させたか
4. データ破壊を避けるための設計方針
5. 今後増やしやすい mutation の形
```

---

## 40. PR-011 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-011 を依頼すること。

```md
# 依頼内容

今回は **PR-011: テスト実装** を実装してください。

前提として、PR-001〜PR-010 により型定義、データ、命名生成、古代遺物ロジック、世界変異ロジックが存在している想定です。今回は、**命名体系とデータ整合性が今後壊れないようにするためのテスト** を実装してください。

目的は、文化圏差・表記ルール・真名マスク・一般品比率・世界変異などの仕様が、今後の拡張で崩れないようにすることです。

---

# 実装範囲

想定内容:
- unit test
- snapshot test
- fixture data test
- JSON schema validation test

テストフレームワークはプロジェクト方針に合わせて選定してください（例: Vitest / Jest）。

---

## 1. 最低限欲しいテスト観点

### 型・データ整合性
- 文化圏 JSON が schema に適合する
- 種族 JSON が schema に適合する
- 儀礼 / 祭礼 / 辞書 JSON が schema に適合する

### 表記ルール
- `土壁《アースウォール》` を正しく整形できる
- `受け流し《パリィ》` を正しく整形できる
- `古代黒大剣《終ノ門ヲ啓クモノ》` を正しく整形できる
- `古代黒大剣《◼◼◼◼◼◼◼◼◼》` を正しく整形できる

### 文化圏差
- 同じカテゴリでも cultureId が違えば出力傾向が変わる
- 例: 聖暦王国圏と冥契夜界圏で人名や地名の雰囲気差がある

### 命名階層差
- 一般アイテムは generic が優勢である
- 固有名が乱発されない
- 工房銘 / 型式名 / 通称の整形が壊れない

### 古代遺物
- 真名マスクが効く
- trueNameVisible と fullSync が別概念として扱われる
- 条件未達では hidden effect が反映されない

### 世界変異
- triggerFlags に応じて mutation が適用される
- 元データを壊さず派生差分を返せる

---

## 2. テスト実装方針

- 単純な 1ケースだけでなく、文化圏差や tier 差が見える fixture を使う
- スナップショットは代表例に絞る
- ランダム生成を使う場合は seed 固定か fixture 化を行う

---

## 3. 最低限ほしい代表ケース

### 表記整形
- 一般魔法
- 一般技能
- 固有武器
- 古代遺物（解放済み）
- 古代遺物（伏せ字）

### 命名生成
- 人名 文化圏差 2〜3件
- 地名 文化圏差 2〜3件
- 一般アイテム generic / workshop / pattern / slang
- 魔法 common / taboo

### 世界変異
- 伝説武器の模造派生
- 黒門封鎖記念祭の追加

---

## 4. README または説明ファイル

短い md を追加してください。

内容:
- テスト対象の一覧
- snapshot を取った対象
- seed 固定や fixture の扱い方
- 今後増やすべきテスト観点

---

# 必須要件

- データ整合性テストを入れてください
- 表記ルールテストを入れてください
- 文化圏差テストを入れてください
- 古代遺物と世界変異の主要ロジックに最低限のテストを入れてください
- 将来の拡張で壊れやすい箇所を優先してください

---

# 今回はやらないこと

- UIテスト
- API統合テスト
- E2Eテスト

今回は世界基盤のロジックとデータのテストに集中してください。

---

# 期待する成果物

- テスト一式
- fixture / snapshot / validation の整備
- 今後の拡張で壊れやすい箇所を守る土台

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 追加したテストの一覧
2. 主要なテスト観点
3. snapshot 対象
4. まだ弱いテスト領域
5. 今後追加したいテスト
```

---

## 41. PR-012 用：Codexへそのまま貼る完全版プロンプト

以下を Codex にそのまま貼り付けて、PR-012 を依頼すること。

```md
# 依頼内容

今回は **PR-012: サンプル出力とデバッグ用図鑑データ生成** を実装してください。

前提として、PR-001〜PR-011 により世界基盤、データ、命名生成、古代遺物、世界変異、テストが揃っている想定です。今回は、**人間レビュー用のサンプル出力** と **デバッグ・図鑑確認用のデータ** を生成してください。

目的は、コードの正しさだけでなく、実際に出力された世界観の質・命名の差・文化差・階層差を人間が確認できるようにすることです。

---

# 実装範囲

想定内容:
- サンプル JSON 生成
- レビュー用 md レポート生成
- デバッグ用 fixture 生成

必要に応じて以下のような出力先を作って構いません。
- `src/data/debug/`
- `docs/world-sample-output.md`

---

## 1. 最低限出したいサンプル

### 人名
- 各文化圏ごとに 20件ずつ
- 可能なら socialTier を数種類混ぜる

### 地名
- 各文化圏ごとに 20件ずつ
- city / village / fortress / forest / port / ruin / holy_site を適度に混ぜる

### 一般アイテム
- generic 10件以上
- workshop 10件以上
- pattern 10件以上
- slang 10件以上
- ritual / proper は数件でよい

### 魔法・技能
- common 魔法 20件以上
- advanced / secret / taboo をそれぞれ複数
- 一般技能 / 戦技 / 奥義の差が見えるサンプル

### 古代遺物
- 未鑑定
- 現代鑑定済み
- 伏せ字真名
- 真名可視
- 覚醒済み
を含むサンプルを複数

### 世界変異後サンプル
- 伝説武器 → 模造品 / 制式品 / 商品名派生
- 新祭礼追加例
- 主人公異名由来の称号や俗称例

---

## 2. 出力形式

少なくとも次のどちらか、できれば両方を用意してください。

### JSON
- 機械的に比較しやすい
- fixture として再利用しやすい

### Markdown レポート
- 人間がレビューしやすい
- 文化圏差や命名差を一覧で見やすい

---

## 3. レポートで見たい観点

以下が人間に一目で分かるようにしてください。

- 文化圏ごとの音と語彙の差
- 種族と文化圏が分離していること
- 一般品と固有名持ち装備の差
- 一般魔法と禁呪の差
- 古代遺物の段階差
- 周回・変異後の命名派生

---

## 4. README または説明ファイル

短い md を追加してください。

内容:
- サンプル生成方法
- 生成に使った固定条件や seed
- レビュー時に見るべきポイント
- 今後サンプルを増やす方法

---

# 必須要件

- 人間レビューに使える出力を作ってください
- 文化圏差と命名階層差が確認できること
- 古代遺物の段階差が確認できること
- 世界変異後の派生命名が確認できること
- 後で fixture や回帰確認に使いやすい形にしてください

---

# 今回はやらないこと

- UIコンポーネント本体
- API
- 本格的な図鑑画面実装

今回はサンプル出力とレビュー用データに集中してください。

---

# 期待する成果物

- サンプル JSON
- レビュー用 markdown
- デバッグ・図鑑確認用 fixture

---

# 実装後に出してほしい内容

最後に、以下を簡潔にまとめてください。

1. 生成したサンプルの種類
2. 件数
3. 文化圏差がよく見える出力例
4. 古代遺物段階差がよく見える出力例
5. 今後レビューすべき観点
```

---

## 42. Codex依頼セット完成後の運用方針

この文書の PR-001 〜 PR-012 を順番に Codex へ渡す際は、以下を守ること。

1. 一度に複数PRを混ぜて依頼しない
2. 各PRごとにレビューしてから次へ進む
3. 命名や文化差に違和感が出た場合は、ロジック修正前に辞書や culture JSON を見直す
4. 表記崩れが出た場合は generator より先に formatter を修正する
5. 真名や古代遺物の違和感は relic_patterns と unlock rules を優先的に見直す
6. 周回変異の違和感は mutation 定義を増減して調整する
7. まずはデータ基盤を安定させ、UI や会話生成統合はその後に進める

---

## 43. 次に人間側で行うべきレビュー

Codexにこの一式を渡した後、人間側では以下を優先してレビューすること。

1. 8文化圏の差が本当に読み分けられるか
2. 種族が文化圏に固定されていないか
3. 一般品に固有名が付きすぎていないか
4. 一般魔法と禁呪の差が十分あるか
5. 真名が飾りで終わらずシステム的意味を持っているか
6. 周回変異で世界が変わった感じが出るか
7. サンプル出力が「読んで面白い」水準に届くか

必要に応じて、この後は以下の追加文書を作る。

- 会話生成用ルールブック
- イベント生成用ルールブック
- 種族関係図テンプレート
- 宗教・神格・禁忌データ仕様
- 暦・月名・季語辞書
- 武器種・装備種の詳細辞書
- 学派・流派・宗派データ仕様

ここまでで、Codexへ渡す世界観・文化・命名基盤の依頼セットは完成とみなしてよい。

