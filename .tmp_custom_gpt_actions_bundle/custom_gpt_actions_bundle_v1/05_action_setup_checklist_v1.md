# Actions Setup Checklist v1

## 1. Before import
- Confirm the public API host that will actually serve your backend endpoints.
- Decide whether you will use:
  - `https://api.star-ring-codex.com` after that subdomain is fully live, or
  - your hosting provider's public API domain, or
  - `https://star-ring-codex.com` if the API is hosted on the same origin.
- Update `servers.url` in `04_openapi_pbw_actions_v1.yaml` before import.
- Confirm that `GET /api/gpt-read-model?seed=1729` returns `200` from that final host before Actions import.
- Prefer the compact GPT action routes for mutation/load flow:
  - `POST /api/gpt/play`
  - `POST /api/gpt/free-action`
  - `POST /api/gpt/load-session`
  - `POST /api/gpt/next-session`
  This avoids oversized responses in the GPT Actions runtime.

## 2. In the GPT editor
- Open the GPT editor
- Add the system prompt from `01_custom_gpt_system_prompt_v1.md`
- Add conversation starters from `02_custom_gpt_conversation_starters_v1.md`
- In Actions, create a new action and import `04_openapi_pbw_actions_v1.yaml`

## 3. Authentication choice
Use one of these, depending on your backend:
- None (only if the API is intentionally public and safe)
- API key (recommended for server-to-server)
- OAuth (only if user-bound accounts are required)

## 4. Recommended action surface
Minimum recommended actions:
- `getGptReadModel`
- `playChoice`
- `playFreeAction`

Optional but useful:
- `saveSession`
- `loadSession`
- `nextSession`
- `finalizeCharacter`

Character genesis recommended flow:
1. `getGptReadModel`
2. `guidance.openingPackage` を開始演出の核として優先しつつ、`guidance.characterGenesis` を見て導入・初期装備・恩恵・恩寵の案をまとめる
3. 同意後に `finalizeCharacter`
4. 返ってきた `readModel` を正本として開始導入を語る

## 5. Preview flow
Test these prompts in Preview:
1. 「既存キャラをこの世界へ転生させたい。導入と初期装備から決めて」
2. 「見える恩恵と眠る恩寵も含めて、開始案を仕上げて」
3. 「今の節で何が起きているか短く教えて」
4. 「通常行動の候補を比較して」
5. 「自由行動として、夜中に裏帳面を盗みたい」
6. 「この節を保存して」
7. 「次の節へ進めて」

## 6. Failure conditions to check
- GPT does not expose raw free text as if it were canon memory
- GPT does not mutate truth without calling an action
- GPT does not emit internal keys to the player
- GPT does not treat current occupants as immortal unique beings
- GPT does not propose starting equipment or恩恵 that exceed `guidance.characterGenesis.constraints`
- GPT uses `guidance.openingPackage.outputRules` when present
