# Authentication & Security

> **UNSTABLE TARGET — Last verified: 2026-08-25 (26/26 checks passed).**
> Jio AI Cloud has no public API. Endpoints change without notice and can
> break at any time. Features may stop working at any moment — check
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for current status.

## 1. Header Contract (verified against production)

Every request — **including bodiless GETs** — must carry:

| Header | Value | Notes |
|---|---|---|
| `Authorization` | `Basic <base64 session token>` | From your web session |
| `X-User-Id` | 32-char hex user id | Matches the id embedded in the token |
| `X-Device-Key` | UUID | The browser device registration id |
| `X-Device-Type` | `W` | Web |
| `X-Api-Key` | `c153b48e-d8a1-48a0-a40d-293f1dc5be0e` | Public web-app constant (not a secret) |
| `X-App-Secret` | `ODc0MDE2M2EtNGY0MC00YmU2LTgwZDUtYjNlZjIxZGRkZjlj` | Public web-app constant (decodes to a UUID; not per-user) |
| `X-Client-Details` | `clientType:WEB; appVersion:86.0.1` | App version marker |
| `Accept`, `Content-Type` | `application/json; charset=UTF-8` | **Content-Type required even on GETs** (`400 NMSOM0003` / `BRSOM0036` otherwise) |
| `User-Agent`, `Accept-Language` | Browser-like string / `en-US,en;q=0.9` | Missing Accept-Language → `400 NMSOM0001` |

The SDK builds all of this in `jiocloud.auth.JioCloudAuth.get_headers()`.
Contacts endpoints additionally require `X-Offset` / `X-CHUNK-SIZE`
(see [API_REFERENCE.md](API_REFERENCE.md), section 5).

## 2. Extracting Your Own Session Credentials

1. Log in to **your** Jio AI Cloud account in Chrome.
2. Open DevTools → Network tab.
3. Click any request to `*.jioaicloud.com`.
4. Copy from the request headers:
   - `Authorization: Basic …` → `auth_token`
   - `X-User-Id: …` → `user_id`
   - `X-Device-Key: …` → `device_key`
5. Paste into your local `config.json`.

The Basic token decodes (best-effort) to `<userId>#ATK#<payload>`;
`JioCloudAuth.peek_token_identity()` lets you sanity-check that the token
matches your `user_id` locally.

## 3. Token Lifetime & Rotation

Session tokens are long-lived but revocable: logging out of the web session
or re-registering the device invalidates them (SDK then receives `401`,
surfaced as `AuthenticationError`). If a token expires, repeat step 2 above.

## 4. Credential Safety Rules (project policy & yours)

- Credentials are read **only** from local `config.json` or `JIOCLOUD_*`
  environment variables.
- They are transmitted **only** to official `*.jioaicloud.com` hosts over
  TLS (allowlist enforced conceptually by the client's fixed base URLs).
- This project has **zero telemetry** and never writes credentials anywhere
  else.
- Never commit `config.json` (keep it in `.gitignore`), never paste tokens
  into issues, screenshots, or chat logs, and rotate by re-login if leaked.
- Example files contain placeholders only; docs show redacted values.

## 5. Error Semantics

| HTTP | Meaning | SDK exception |
|---|---|---|
| 400 | Bad params/headers/body (see code) | `InvalidRequestError` (+ `.error_code`) |
| 401 | Session expired/invalid | `AuthenticationError` |
| 403 | Operation forbidden | `ForbiddenError` |
| 404 | Unknown object/board key | `ObjectNotFoundError` |
| 429 | Rate limited (auto-retried w/ backoff) | `RateLimitError` |
| 5xx | Server fault (auto-retried) | `ServerError` |
| network | DNS/TLS/reset (auto-retried) | `NetworkError` |

Batch operations additionally surface per-object failures embedded in HTTP
200 responses (`unprocessed[].object.errorCode`) as `InvalidRequestError`
with the server's code attached.
