# KNOWN ISSUES & SERVER BEHAVIOR NOTES

This project practices **radical honesty**: everything below was discovered by
live testing against production Jio AI Cloud servers (2026-08-25) and is
documented so contributors know exactly where the gaps are.
**Anyone can contribute a fix** — see "How to help" under each issue.

Status legend: ✅ verified working · ⚠️ works with caveats · ❌ broken / server-rejected

---

## ✅ ISSUE-001 (RESOLVED): Move-to-trash requires `TRASH` op + `status:"T"`

**History**
The original traffic capture (2026-08-24 19:20) showed deletes working via:

```
PUT /nms/metadata/delete   body: {"objectKeys": ["<key>"]}
```

By the time of live verification (2026-08-25), that endpoint **silently
rejected every key** — HTTP 200 but the op landed in an empty-detail
`unprocessed[]` array, for new folders and old files alike, regardless of
headers or payload shape.

**Resolution:** a second capture (2026-08-24 21:16, contributed by the
project owner) revealed the web client had switched to:

```
PUT /nms/metadata/1.0
body: {"objects": [{"operation": "TRASH",
                    "correlationId": "<userId>",
                    "object": { ...FULL object echo..., "status": "T" }}]}
```

The decisive detail was `"status": "T"` pre-set in the request object.
With the full echo plus `status:"T"`, items land in trash within seconds;
`restore_from_trash` (`PUT /nms/metadata/restore`, unchanged contract) then
verifiably restores them. The full create→rename→favorite→trash→restore→trash
cycle now passes in `tests/live_verify.py`.

**Lesson for contributors**: Jio's web client evolves its contracts without
notice; when an endpoint starts failing, capture fresh traffic before
assuming breakage. The SDK's `_metadata_op()` also surfaces per-object
errors from `unprocessed[].object.errorMessage / errorCode` as typed
exceptions instead of pretending success.

---

## ✅ ISSUE-002 (RESOLVED): Restore-from-trash verified

Depends on ISSUE-001's flow. Verified end-to-end: trash → visible in
`GET /nms/trash` → restore → gone from trash → re-trash → lands again.

---

## ⚠️ ISSUE-003: `type` query param only accepts `f` or `w`

`GET /nms/metadata*?type=…` rejects anything except `f` (files) / `w`
(folders) with `400 NMSOM0129`. There is **no "list everything at once"**
mode, so recursive walks issue two queries per directory. Handled internally
by `stream_all_files()`.

---

## ⚠️ ISSUE-004: Batch mutations require the FULL object echo

`PUT /nms/metadata/1.0` operations (`SETFAV`, `UNSETFAV`, `RENAME`, `MOVE`,
`TRASH`) fail constraint validation unless the object patch carries fields
like `objectName` / `sourceName`:

- missing `objectName` → `TEJVF0001`
- missing `sourceName` → `NMSOM0021 "Source name is null or empty"`

The SDK handles this by resolving current server state before mutating.
Failure detail is returned inside `unprocessed[].object.errorMessage /
errorCode`; `_metadata_op()` raises `InvalidRequestError` with that code.

---

## ⚠️ ISSUE-005: Contacts service requires undocumented headers/params

`GET /amiko/cab/contacts` fails without BOTH:
- `X-Offset: <n>` request header (error `TEJRF0400`)
- `nextPageDate=yyyy-MM-dd HH:mm:ss.SSSSSS` query param (same error)

`get_contacts()` sends both defaults; paging uses `X-CHUNK-SIZE`.
Accounts with zero contacts return `{}` — behavior with many contacts is
inferred from the pagination contract, not yet observed live. **Contributor
with a populated address book: please verify page-walk works end-to-end.**

---

## ⚠️ ISSUE-006: Content-Type mandatory on bodiless GETs

All Jio endpoints reject GETs without a `Content-Type` header
(`NMSOM0003`, `BRSOM0036`). The SDK always sends it. Keep this in mind when
adding new endpoints.

---

## ⚠️ ISSUE-007: Trash/listing eventual consistency (~2s)

Newly created items may take a second or two to appear in listings;
mutations can lag similarly. Tests use short settle delays. If you see flaky
results in scripts, add small sleeps between mutate→list sequences.

---

## 📝 Not implemented (endpoints exist in captures but lack verified contracts)

These appeared only as CORS preflights or were not exercised live; payloads
are unknown, so we deliberately did NOT guess them:

- Upload (the web app uploads via a different authenticated flow we have not
  captured yet)
- Board file add/remove, board edit/delete, board invite flows
- Folder copy/duplicate operations
- Manual tag create/delete (`GET` variants are implemented & verified)
- Permanent (non-trash) deletion

**Contributors welcome**: capture the traffic for any of these from the web
UI and open an issue with the (redacted) request shape.

---

## Verification environment

Findings above reproduced 2026-08-25 against production with a free-tier
account (~39 GB used of 100 GB), Chrome 147 web-client header profile.
Run `python tests/live_verify.py` yourself to reproduce the matrix locally.

> **Note on token expiry:** session tokens are revocable and expire when the
> web session is logged out or refreshed. A run against an expired token
> shows every check failing with `AuthenticationError: 401 TEJGA0401` — that
> is the SDK working correctly (typed errors, no silent retries). Refresh
> `config.json` per [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) §2 and re-run.
