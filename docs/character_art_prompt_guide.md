# Character Art Prompt Guide

## Goal

`Star Ring Codex` の人物画は、主人公も NPC も同じ画風と陰影でそろえる。
参照画像やゲームのスクリーンショットを使う場合も、そのまま写すのではなく、
この世界の素材感と意匠へ再解釈する。

## Default outputs

- `portrait_plate`: 立ち絵。全身 3/4 立ち、顔と手元、主装備が読める構図。
- `portrait_icon`: 顔アイコン。胸上の bust crop。髪型、目元、色が分かる構図。

## House style

- painterly dark fantasy character illustration
- restrained realism
- readable face design
- shared brushwork and shadow density across the whole cast
- calm 3/4 pose as the default
- low-key lighting with warm rim light and cool fill

## What to preserve from references

参照画像やスクリーンショットがあるときは、次を優先して拾う。

- 顔立ちの印象
- 髪型の輪郭
- 年齢感
- 体格
- 主な配色
- 印象的な装飾
- 武器や道具のシルエット

## What to reinterpret

次はそのまま持ち込まず、この世界に合わせて置き換える。

- 服の素材
- 模様
- 金具
- 紋章
- 装備の表面処理
- スクリーンショット固有の UI / HUD / ロゴ
- 作品固有の記号

## Hard bans

- UI / HUD / ロゴ / 文字を残す
- 他作品の衣装や紋章をそのまま複製する
- 現代服
- SF 装備
- 過剰な露出
- 極端なデフォルメ
- chibi 比率
- cel-shaded MMO screenshot look
- 顔が見えない構図
- 武器や髪で顔を隠す構図
- 複数人物
- 過剰な bloom

## Prompt skeleton

```text
Use case: stylized-concept
Asset type: protagonist standing portrait / protagonist face icon
Primary request: original dark fantasy portrait of <character name>
Scene/backdrop: subtle dark fantasy studio backdrop with faint ash, shrine smoke, or weathered stone atmosphere only
Subject: <race>, <style>, <origin>, equipped in <loadout>, signature item <item>
Style/medium: painterly dark fantasy character illustration, restrained realism, original game art, unified house style shared with all NPC portraits
Composition/framing: <full-body 3:4 standing> or <bust portrait for face icon>
Lighting/mood: low-key solemn lighting, warm rim light and cool fill
Color palette: <palette>
Materials/textures: <materials>
Constraints: preserve facial impression, hairstyle silhouette, age impression, body type, signature colors, and key accessory silhouette from references; redesign materials and ornament into this world's motifs
Avoid: text, watermark, UI, HUD, logos, copied franchise insignia, modern zippers, sci-fi panels, chibi proportions, cel-shaded MMO screenshot look
Character notes: <summary>
Appearance notes: <appearance notes>
Reinterpretation notes: <keep-these notes>
```

## Workflow

1. キャラクリで `初期装備` と `転生元` を決める。
2. `appearanceNotes` と `reinterpretationNotes` に、残したい印象だけを短く書く。
3. 参照画像がある場合は、顔・髪・体格・色・武器シルエットだけを拾う前提で使う。
4. 立ち絵と顔アイコンは同じ prompt family から作る。
5. 主人公と主要 NPC を同じ negative prompt で回し、画風のずれを抑える。
