# Deployment Mapping for Current star-ring-codex deployment v1

## Current recommended split
### Public docs / policy / landing
Use the currently published surface:
- `https://policy.star-ring-codex.com`

Recommended contents there:
- Privacy Policy
- How the GPT works
- What the Actions do
- What data is persisted and what is not
- Contact / builder profile website reference

### API host for Actions
Recommended:
- `https://api.star-ring-codex.com` only after it is actually live
- otherwise `https://<actual-public-api-host>`

Why:
- Keeps the public docs surface separate from the mutation-capable API
- Makes CORS, reverse proxy, and backend deployment easier to reason about
- Keeps future migration paths cleaner

## Minimum routing map
- `GET /api/gpt-read-model`
- `POST /api/gpt/play`
- `POST /api/gpt/free-action`
- `POST /api/save-session`
- `POST /api/gpt/load-session`
- `POST /api/gpt/next-session`

Why the GPT-prefixed routes matter:
- the web UI can keep using the full `/api/play` style responses
- the Custom GPT can use the compact `/api/gpt/...` responses
- this keeps the Actions payload small enough for the GPT runtime

## If you later move to the apex domain
If `star-ring-codex.com` later becomes the main public site, you can still:
- move docs/policy there, and
- proxy `/api/*` to your backend,
provided the final deployed host matches the `servers.url` you import into Actions.

## Recommended publication order
1. Public privacy/policy page online
2. API reachable from the final public host
3. OpenAPI spec updated to that host
4. GPT Actions imported
5. Preview tested end-to-end
6. Only then move to sharing/publishing
