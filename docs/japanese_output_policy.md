# Japanese Output Policy

## Goal

- engine / resolution / schema を変えず、表示層と文章層だけで自然な日本語を作る。
- 内部指標名、設計ラベル、世界観用語、地の文を混ぜない。
- 情緒より先に意味を伝え、一読で状況が分かる文を優先する。

## Terminology Layers

- `internal_key`
  実装や計算で使う識別子。UI にそのまま出さない。
- `ui_label`
  画面に短く置く表示語。短く、説明不要で読める語にする。
- `natural_phrase`
  状況説明や補助文に使う自然文。誰が、何が、どうなっているかを入れる。

## Forbidden Expressions

- 指標名の直訳
  例: `distortion`, `breach_risk`, `sealIntegrity`
- 名詞を並べただけの文
  例: 「世界圧危機波形増大」
- 抽象的だが状況が読めない比喩
  例: 「夜がさらに濃く鳴る」
- 主語、対象、危険が読めない文
- 英語の設計ラベルを UI 見出しへ流すこと
  例: `Play Cycle`, `Named Cast`, `Current Event`
- 「それっぽい」だけで意味を補えない雰囲気文

## Recommended Principles

- 誰が / 何が / どうなっているかを先に書く。
- 危険、利得、変化を先に明示する。
- 雰囲気は意味が通ったあとにだけ足す。
- 数値は補足として使い、状況説明の代わりにしない。
- 1 文 1 役割を基本にする。

## UI Text Rules

- ステータス表示文は短くする。
  例: 「安定している」「補給が乱れている」「封印が弱まっている」
- 見出しは日本語で統一する。
- ボタン文は動作が分かる言い方にする。
  例: 「関係者に話を聞く」
- 内部の outcome 名や status 名をそのまま出さない。

## Explanation Rules

- 2〜3 文で「状況」と「放置した時の意味」を分けて書く。
- 1 文目で状況、2 文目で危険や重要性を書く。
- 比喩は補助に留める。
- 同じ文に内部語と世界観語を混在させない。

## Scene Support Rules

- 最初の数行で場所、争点、危険を読めるようにする。
- 数値より前に意味を書く。
- 事件文は「何が揉めているか」を明示する。
- scene 補助文は UI と同じ用語を使う。

## NPC Short Text Rules

- 役割文: 何を担当し、誰とぶつかっているかを示す。
- 反応文: こちらの行動をどう受け取ったかを示す。
- 弱点文: 条件と揺らぎを具体的に書く。
- 秘密文: hidden / hinted / exposed の差を文で表す。

## Item And Event Naming Rules

- 名詞を重ねるだけで重さを出そうとしない。
- 事件名は争点が読める形にする。
- アイテム名や地名は固有性を持たせつつ、初見でも用途や危険が推測できる語を選ぶ。

## Quality Gate

- `text/terminology_registry.py`
  internal / UI / natural の対応表を持つ。
- `text/text_composer.py`
  player-facing text を一箇所で組み立てる。
- `text/copy_checks.py`
  internal key の漏出、長すぎる UI 文、不自然な名詞連結を軽く検査する。
