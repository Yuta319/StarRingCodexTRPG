# Design Lock Alignment

`c:\Users\quiet\Downloads\pbw_design_lock_memo_v1.md` をこの時点の設計ロックとして扱い、現行実装との差分をここで吸収する。

## Locked Principles

- 創造神以外は有限存在として扱う。
- 世界が記憶する主語は個人ではなく `role slot` を優先する。
- `engine / resolution / schema` は当面の正本として大きく壊さない。
- UI は state を直接変更せず、`runner / playable_loop / save-load` 経路だけを使う。
- 1 choice = 1 turn、6 turn = 1 session、2 turn ごとに phase を進める。
- failure にも意味を持たせ、必ず observable mutation を残す。
- save は world state を正本とし、同一 state + 同一 choice の再現性を守る。
- 自由入力の raw text は正本にせず、保存するのは structured result のみとする。
- 悪徳と禁忌は flavor ではなく、`campaign_state` に残る世界構造として扱う。

## Current Implementation Mapping

- [campaign_content.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/campaign_content.py)
  `ROLE_SLOT_BLUEPRINTS` を正本にし、`occupantTemplates` は slot ごとの継承候補として管理する。
- [gameplay_experience.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/gameplay_experience.py)
  `campaign_state["npcs"]` を `roleSlotId` 主体で保持し、`prepare_next_session()` で occupant 交代を進める。
- [read_only_ui/controller.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/read_only_ui/controller.py)
  UI からの操作を `runner / playable_loop / save-load` に集約し、直接 mutation を行わない。
- [read_only_ui.md](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/docs/read_only_ui.md)
  save / load / next-session の UI 導線を backend 呼び出しとして固定する。
- [vice_taboo.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/vice_taboo.py)
  shared catalog を runtime へ固定し、vice / taboo の派生値を `campaign_state` と `cycle_state` に同期する。
- [free_action_parser.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/free_action_parser.py)
  raw free text をそのまま保存せず、role slot / institution / region を含む structured intent に落とす。
- [free_action_adjudicator.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/free_action_adjudicator.py)
  shared schema に従った structured result を deterministic に返す。
- [free_action_recorder.py](/c:/Users/quiet/Desktop/myproject/StarRingCodexTRPG/star_ring_codex_trpg/free_action_recorder.py)
  structured result を既存 loop と両立する patch として world/campaign に落とす。

## Role Slot Rule

- primary key は current occupant 名ではなく `roleSlotId`
- `displayName` はその session の occupant 名
- history / summary は必要に応じて role 名と occupant 名の両方を出してよい
- `next-session` 後は同じ role slot でも occupant が変わりうる

## Era Boundary

- gameplay layer は Era の固定一覧を持たない
- UI / display は `world_state` 由来の `current_world_era` を読むだけに留める
- Era の合成規則そのものは handoff world 側の責務として扱う

## Compatibility

- 旧 save の固定 NPC key は load 時に role slot key へ migration する
- ending / archive は `keyRoleSlotId` を保持し、表示用に occupant 名を併記する
- 既存の `keyNpcId` は互換用 alias として残すが、値は role slot id である
- vice / taboo / free action の追加は `campaign_state` と補助層に閉じ、scene/ui contract schema は変更しない
