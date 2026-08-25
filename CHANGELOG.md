# Changelog

All notable changes to this project are documented here.
The project uses semantic versioning for the SDK surface (client methods,
tool schemas, CLI commands).

> **Why this file exists:** Jio AI Cloud has no public API and changes its
> contracts without notice. Between two traffic captures taken one day apart
> (2026-08-24), the delete endpoint silently changed its entire contract —
> see [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) ISSUE-001. This changelog
> tracks what was verified, against which server behavior, and when.

## UNSTABLE TARGET NOTICE

**Last verified against production: 2026-08-25 (26/26 checks passed).**
Jio AI Cloud endpoints change without notice and can break at any time.
Check [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for current status.

## [2.0.0] - 2026-08-25

First public release. Everything below was verified live against production
(26-check matrix in `tests/live_verify.py`).

### Added — SDK (`jiocloud/`)

- `JioCloudClient`: streaming recursive account cataloging (2200+ files
  tested), directory listings, full-text search across names and backup
  source paths
- Chunked atomic downloads with progress callbacks; MD5 verified against the
  server hash; multi-threaded bulk sync with skip-existing
- Mutations: create folder, rename, move, favorite/unfavorite, move-to-trash,
  restore from trash; multi-object public share links; version history
- Boards/albums: list, create, detail, members, leave
- Account: profile, quota breakdown, devices, promotions, app settings;
  feeds: recent objects, spotlights, shared-by-me, DigiLocker linked-app
  objects, manual tags; contacts
- Retry with exponential backoff on 429/5xx/network errors; typed exception
  taxonomy; per-object error surfacing from batch `unprocessed[]`
- Zero dependencies: Python 3.8+ standard library only

### Added — CLI (`cli.py`)

- 20 commands: info, list, tree, search, download, sync, mkdir, rename, move,
  favorite, trash, restore, trash-list, share, versions, recent, boards,
  contacts, promotions, agent

### Added — AI agent layer

- `AGENT_TOOLS_SCHEMA`: 16-tool JSON schema in OpenAI/Anthropic
  function-calling format
- Strict JSON envelope dispatcher (`{"ok": true/false, ...}`) with a
  destructive-op confirmation guard (`confirm === true` required)
- MCP-style stdio server via `python cli.py agent serve`
- Published assets under `ai/`: installable skill, exported OpenAI + Anthropic
  tool schemas, paste-ready system prompt, example conversation

### Added — Tooling & docs

- Interactive credential validator (`examples/setup_credentials.py`) that
  live-validates session headers against `GET /security/users`
- One-paste browser console credential extractor
  (`examples/browser_console_extractor.js`) plus full walkthrough
  (`docs/GET_CREDENTIALS.md`)
- MkDocs Material documentation site deployed to GitHub Pages:
  <https://ns81000.github.io/jiocloud_client/>
- `llms.txt` / `llms-full.txt` LLM-oriented documentation indexes
- GitHub Actions workflow deploying the docs site on push to main

### Verified protocol facts (see docs/)

- Content-Type header required on ALL verbs including bodiless GETs
  (`400 NMSOM0003` / `BRSOM0036` otherwise); Accept-Language required
  (`NMSOM0001`)
- Listing `type` param accepts only `"f"` / `"w"` — no combined mode
  (`400 NMSOM0129`)
- Batch mutations require the FULL object echo (`TEJVF0001` without
  `objectName`; `NMSOM0021` without `sourceName`)
- Move-to-trash requires the TRASH batch op with `status:"T"` pre-set; legacy
  `PUT /nms/metadata/delete` silently rejects all keys (ISSUE-001)
- Contacts endpoints need both `X-Offset` header and `nextPageDate` query
  param (`400 TEJRF0400`)
- Trash listing lags several seconds after mutations
- Version history envelope key is `objVersions`

[2.0.0]: https://github.com/Ns81000/jiocloud_client/releases/tag/v2.0.0
