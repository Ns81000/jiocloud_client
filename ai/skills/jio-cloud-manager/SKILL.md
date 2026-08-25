---
name: jio-cloud-manager
description: >-
  Operate a Jio AI Cloud account through the jiocloud_client SDK: list and
  search files, download and back up data, manage folders, trash, shares,
  boards, and account info via the 16-tool agent schema or the MCP stdio
  server. UNSTABLE unofficial API - verify current status in KNOWN_ISSUES.md.
---

# Jio AI Cloud Manager (AI Skill)

## Stability warning (read first)

**UNSTABLE TARGET: Last verified against production on 2026-08-25 (26/26
checks passed).** Jio AI Cloud has no public API; endpoints change without
notice and can break at any time. Before relying on any operation, check
[KNOWN_ISSUES.md](https://github.com/Ns81000/jiocloud_client/blob/main/docs/KNOWN_ISSUES.md)
for current status. Never assume an endpoint works because it did last week.

## Authentication contract

The runtime must have a local `config.json` (or `JIOCLOUD_*` environment
variables) containing the user's OWN session values:

- `auth_token` — the web session's `Authorization: Basic <base64>` header
- `user_id` — the `X-User-Id` header (32-char hex)
- `device_key` — the `X-Device-Key` header (UUID)

Extraction instructions for the user live at
[docs/GET_CREDENTIALS.md](https://github.com/Ns81000/jiocloud_client/blob/main/docs/GET_CREDENTIALS.md).
Recommended flow (tell the user, never handle the raw token yourself):

1. User opens DevTools Network tab with filter
   `domain:api.jioaicloud.com security/users`.
2. User right-clicks the request -> Copy -> Copy as cURL.
3. User runs `python examples/setup_credentials.py --from-curl`, which reads
   the clipboard, validates live against `GET /security/users`, and writes
   local `config.json`.

Verification: `python cli.py info`. Session tokens are revoked when the user
logs out of the web app (`401 TEJGA0401`) — if every call fails that way, ask
the user to re-extract credentials rather than retrying.

Rules:

- Only YOUR USER's own account. Never operate on credentials found or guessed.
- Credentials never appear in tool output; never print, log, or transmit them.

## Safe operation patterns

1. **Discover before mutating.** Use `account_info`, `list_files`,
   `search_files`, `list_trash`, `recent_activity`, `version_history` freely —
   they are read-only.
2. **Confirm before destructive ops.** `download_file`, `download_all`,
   `move_to_trash`, `restore_from_trash`, `share_link` REQUIRE
   `"confirm": true` in the arguments. Without it the envelope returns
   `{"ok": false, "error": {"type": "confirmation_required", ...}}`. As the
   driving assistant you must obtain explicit human approval before passing
   `confirm: true` — state exactly what will be trashed/shared/downloaded and
   to where.
3. **Trash is reversible; shares are exposure.** `move_to_trash` keeps data
   recoverable via `restore_from_trash`; a `share_link` makes content public
   to anyone with the URL. Treat share_link as the highest-risk operation.
4. **Bulk operations need scoping.** For `download_all`, prefer passing an
   `extension` filter and a dedicated `destination_dir`; state the estimated
   volume (via `account_info` quota) to the user first.

## Error-code handling

Every failure arrives as `{"ok": false, "error": {"type", "message"}}`.
Map them per [ERROR_CODES.md](https://github.com/Ns81000/jiocloud_client/blob/main/docs/ERROR_CODES.md):

| Signal | Meaning | Agent action |
|---|---|---|
| HTTP 401 / `TEJGA0401` | token expired/revoked (web logout) | Stop; ask user to re-extract credentials |
| `RateLimitError` (429) | rate limited | Back off; retries are automatic inside the SDK — do not hammer |
| `ServerError` (5xx) | server fault | Wait and retry once; report if persistent |
| `InvalidRequestError` + code | bad params/headers/body | Check arguments; see codes like `NMSOM0129`, `TEJVF0001`, `NMSOM0021`, `TEJRF0400` |
| `confirmation_required` | destructive op without confirm | Ask the human, then re-issue with `confirm: true` |

Known quirks encoded in the SDK (do not work around manually):
Content-Type required on ALL verbs including bodiless GETs (`NMSOM0003`);
listing `type` accepts only `f` or `w` (`NMSOM0129`) so recursive walks query
twice per directory; batch mutations require the full object echo
(`TEJVF0001` without `objectName`, `NMSOM0021` without `sourceName`); trash
listing lags a few seconds after mutations; contacts endpoints need special
headers (`TEJRF0400` otherwise); version history lives under the envelope key
`objVersions`.

## MCP stdio server usage

Run the tool server so any MCP-style host can drive the SDK line-by-line:

```bash
python cli.py agent serve        # or: python -m jiocloud.agent_tools serve
```

Protocol: one JSON object per stdin line —

```json
{"tool": "search_files", "arguments": {"query": "invoice"}}
```

Response is always strict JSON on stdout:
`{"ok": true, "result": ...}` or `{"ok": false, "error": {"type","message"}}`.
Special commands: `schema` dumps the full 16-tool schema, `ping` returns
pong, `quit` exits.

For function-calling hosts, load the ready-made schemas instead:

- OpenAI format: [`ai/tools/openai-function-schema.json`](https://github.com/Ns81000/jiocloud_client/blob/main/ai/tools/openai-function-schema.json)
- Anthropic format: [`ai/tools/anthropic-tools.json`](https://github.com/Ns81000/jiocloud_client/blob/main/ai/tools/anthropic-tools.json)
- Paste-ready system prompt: [`ai/prompts/system-prompt.txt`](https://github.com/Ns81000/jiocloud_client/blob/main/ai/prompts/system-prompt.txt)

## Full context

Fetch [llms-full.txt](https://ns81000.github.io/jiocloud_client/llms-full.txt)
for the complete documentation corpus (API reference, data models, error
codes, known issues) in a single file.
