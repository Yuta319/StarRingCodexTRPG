# 05 Risk register v1

## 高リスク
- 方針書が v10 正本を前提としているが、現物は v9 系までしかない
- UI schema が root と pbw_ui_contracts_v1/ で重複している
- magic system が JSON ではなく Python script 形式で配布されている
- README と実コードのズレが存在しうる

## 対応
- 現物優先の canonical list を固定する
- UI は pbw_ui_contracts_v1/ に統一する
- magic system は JSON 正規化してから読む
- 挙動判断は sample json と code を優先する
