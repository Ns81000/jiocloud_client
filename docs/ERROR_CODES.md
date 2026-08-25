# Error Codes — Production Taxonomy

> **UNSTABLE TARGET — Last verified: 2026-08-25 (26/26 checks passed).**
> Jio AI Cloud has no public API. Endpoints change without notice and can
> break at any time. Features may stop working at any moment — check
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for current status.

All codes below were **observed live** (2026-08-25) or present in verified
captures. The SDK maps HTTP status to typed exceptions and, for batch
operations, extracts the per-object `errorCode` from `unprocessed[]`.

---

## HTTP-level mapping

| HTTP | Exception | Trigger | Handling |
|---|---|---|---|
| 400 | `InvalidRequestError` | bad params/headers/body | surfaced; `.error_code` carries server code |
| 401 | `AuthenticationError` | expired/invalid session token | re-extract credentials |
| 403 | `ForbiddenError` | operation not permitted | check account permissions |
| 404 | `ObjectNotFoundError` | unknown object/board key | verify key via listing |
| 429 | `RateLimitError` | throttled | **auto-retried** w/ exponential backoff |
| 5xx | `ServerError` | upstream fault | **auto-retried** |
| net | `NetworkError` | DNS/TLS/reset/timeout | **auto-retried** |

Retry policy: `max_retries=3`, backoff `1.5 × 2^attempt` seconds
(configurable in `JioCloudClient.__init__`). Non-retryable: 400/401/403/404.

---

## Server error codes (verified)

| Code | Message (abridged) | Cause → Fix |
|---|---|---|
| `NMSOM0001` | "Accept language is null or empty." | Missing `Accept-Language` header → SDK always sends it |
| `NMSOM0003` | "Content type is null or empty." | GET without `Content-Type` → SDK always sends it |
| `NMSOM0021` | "Source name is null or empty." | Batch op (`RENAME`/`MOVE`/…) without `sourceName` in object echo → SDK resolves full state first |
| `NMSOM0129` | "Kindly provide valid value for folder(W) or file(F) Search." | `type` query param ≠ `f`/`w` → only those values exist |
| `NMSOM0135` | "Request is not proper" | Malformed batch op shape (e.g. unknown operation name) |
| `TEJVF0001` | "constraint validation on objectName for value null" | Batch op missing `objectName` → full object echo required |
| `TEJRF0400` | "Missing or Invalid value of X-Offset" / "nextPageDate must be a valid time…" | Contacts endpoints require `X-Offset` header AND `nextPageDate` param (`yyyy-MM-dd HH:mm:ss.SSSSSS`) → handled by `get_contacts()` |
| `BRSOM0036` | "Content-Type header is not available in the request." | Boards service variant of NMSOM0003 |

## Silent rejection pattern (important)

Batch mutations return **HTTP 200** even when individual ops fail; failures
appear inside:

```jsonc
{ "objects": [],   // succeeded ops
  "unprocessed": [ { "operation": "TRASH",
                     "correlationId": "…",
                     "object": { "objectKey": "…",
                                 "errorMessage": "…",   // may be absent!
                                 "errorCode": "…" } } ] }
```

Note: some rejections carry **no error message at all** — just the bare
object key. The SDK treats any entry in `unprocessed[]` as an
`InvalidRequestError` and never reports silent failure as success.
Historical example: the legacy `PUT /nms/metadata/delete` endpoint began
rejecting every key this way after 2026-08-24 (see docs/KNOWN_ISSUES.md
ISSUE-001); the fix routes deletes through the `TRASH` batch op with
`status:"T"`.

---

## Client-side exceptions

Defined in `jiocloud.exceptions`:

```
JioCloudError                      # base
├── AuthenticationError            # 401
├── ForbiddenError                 # 403
├── ObjectNotFoundError            # 404 (+ local key resolution misses)
├── InvalidRequestError            # 400 + batch unprocessed[] errors
├── QuotaExceededError             # storage full (reserved)
├── RateLimitError                 # 429
├── ConflictError                  # 409
├── PayloadTooLargeError           # 413
├── ServerError                    # 5xx
└── NetworkError                   # transport failures
```

Also raised locally: `FileExistsError` from `download_file()` when the
destination exists and `overwrite=False`.
