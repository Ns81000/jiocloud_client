# API Reference — Unofficial Jio AI Cloud SDK

> **UNSTABLE TARGET — Last verified: 2026-08-25 (26/26 checks passed).**
> Jio AI Cloud has no public API. Endpoints change without notice and can
> break at any time. Features may stop working at any moment — check
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for current status.

All endpoints below were **verified against live production servers**
(2026-08-25). Base URLs and the exact request/response shapes are documented;
error codes reference [ERROR_CODES.md](ERROR_CODES.md).

**Required headers on EVERY request (including bodiless GETs)** — see
[AUTHENTICATION.md](AUTHENTICATION.md):

```
Authorization: Basic <session-token>
X-User-Id: <32-char hex>
X-Device-Key: <uuid>
X-Device-Type: W
X-Api-Key: c153b48e-d8a1-48a0-a40d-293f1dc5be0e      (public web-app constant)
X-App-Secret: ODc0MDE2M2EtNGY0MC00YmU2LTgwZDUtYjNlZjIxZGRkZjlj
X-Client-Details: clientType:WEB; appVersion:86.0.1
Accept / Content-Type: application/json; charset=UTF-8   ← Content-Type REQUIRED even on GET
User-Agent, Accept-Language
```

---

## 1. Account & Session — `https://api.jioaicloud.com`

| Method | Path | Purpose |
|---|---|---|
| GET | `/security/users` | Profile, quota, root folder key, devices |
| GET | `/security/users/promotions` | Active/expired storage promotions |
| GET | `/app/settings?os=web` | Backup policy & client settings |
| POST | `/security/getokenforcookie` | Exchange web JWT for download nonce |

### GET /security/users → 200
```jsonc
{
  "userId": "…", "authProviderId": 4, "emailId": "…",
  "firstName": "…", "status": "A",
  "rootFolderKey": "0123456789ABCDEF0123456789ABCDEF",   // per-account
  "isMobileNumVerified": true, "isEmailIdVerified": true,
  "mobileNumber": "+916****8825",
  "quota": { "allocatedSpace": 107374182400, "usedSpace": …,
             "photoUsage": …, "videoUsage": …, "audioUsage": …,
             "documentUsage": …, "totalAllocatedQuota": …,
             "totalUsedQuota": …, "paidPlanQuota": 0,
             "defaultStorageSpace": …, "totalPromotionalQuota": 0 },
  "devices": [ { "deviceName": "Web Device", "deviceKey": "uuid",
                 "deviceType": "W", "platformType": "Chrome", … } ]
}
```

SDK: `get_user_profile()`, `get_storage_quota()`, `list_devices()`,
`get_app_settings()`, `get_promotions()`, `get_cookie_nonce(jwt)`

---

## 2. Metadata & Files — `https://jaws-api.jioaicloud.com`

### Directory listing

| Method | Path | Notes |
|---|---|---|
| GET | `/nms/metadata/defaultview/myfiles/v1` | Default view |
| GET | `/nms/metadata` | Legacy view (supports `page` param) |

Query params (both):
- `limit` — page size (verified up to 2000)
- `folderKey` — parent folder key (**required**)
- `type` — **only `f` (files) or `w` (folders)**; anything else → `400 NMSOM0129`
- `sort` — e.g. `+fileCreatedDate`, `-lastModifiedDate`, `+objectName`
- `page` — offset page index (legacy endpoint)

Response envelope:
```jsonc
{ "allocatedSpace": …, "usedSpace": …, "isUploadAllowed": true,
  "objects": [ { /* object schema — see DATA_MODELS.md */ } ] }
```

SDK: `list_directory()`, `list_files()`, `list_folders()`,
`stream_all_files()` (recursive walker; issues w+f queries per directory due
to ISSUE-003), `search_files()` (client-side over full walk)

### Batch metadata operations — `PUT /nms/metadata/1.0`

```jsonc
// request
{ "objects": [ { "operation": "<OP>", "correlationId": "<userId>",
                 "object": { /* FULL object echo — see below */ } } ] }
// response 200
{ "objects": [ /* processed ops with updated object */ ],
  "unprocessed": [ { "operation": "...", "object": {
      "objectKey": "...", "errorMessage": "...", "errorCode": "..." } } ],
  "usedSpace": …, "isUploadAllowed": true }
```

Verified operations: `SETFAV`, `UNSETFAV`, `RENAME`, `MOVE`, `TRASH`.

**Constraint (server-verified):** the object must be a *full echo* of the
item's current server state. Missing fields cause silent rejection into
`unprocessed[]`:

| Missing field | Error surfaced in unprocessed |
|---|---|
| `objectName` | `TEJVF0001` constraint validation on objectName |
| `sourceName` | `NMSOM0021` Source name is null or empty |

For `TRASH`, the payload's `"status"` must be pre-set to `"T"` (see
KNOWN_ISSUES.md (docs/KNOWN_ISSUES.md, ISSUE-001). The SDK resolves current state via
`_resolve_objects()` before mutating.

SDK: `rename_object()`, `move_object()`, `set_favorite()`, `delete_to_trash()`

### Trash & restore

| Method | Path | Body | Status |
|---|---|---|---|
| PUT | `/nms/metadata/restore` | `{"objectKeys": ["<key>", …]}` |  verified |
| GET | `/nms/trash?limit=&sort=` | — |  verified |
| ~~PUT~~ | ~~`/nms/metadata/delete`~~ | legacy delete — now silently rejects all keys |  deprecated server-side |

SDK: `delete_to_trash()` (uses TRASH op), `restore_from_trash()`, `list_trash()`
Note: trash listing lags a few seconds after mutation (ISSUE-007).

### Versions

```
GET /nms/metadata/version/<objectKey>  → 200
{ "totalVersions": 1,
  "objVersions": [ { "version": 1, "displayVersion": "V1",
                     "createdDate": …, "isCurrentVersion": true, … } ] }
```

 Envelope key is `objVersions` (not `versions`). Unknown key → `404`.
SDK: `get_version_history()`

### Feeds & discovery (all GET, jaws-api)

| Path | Query | Response envelope |
|---|---|---|
| `/nms/metadata/recent/objects` | — | `{objectsImgs:[…], objectsDocs:[…]}` |
| `/nms/spotlights/metadata` | `page`, `limit` | `{spotLights:[…]}` |
| `/nms/collshare/byme` | `page`, `limit`, `sort=-smd` | `{objects:[…]}` |
| `/nms/headless/linkedapp/metadata` | `appcode=dgl`, `page`, `limit` | `{objects:[…]}` |
| `/nms/manual/tag/recents` | — | `[ … ]` (bare array) |
| `/nms/manual/tags/<objectKey>` | — | `[ … ]` (bare array) |
| `/cspp/intg/doc/supported` | — | `{supportedExtensions:{view:[],edit:[],favIconUrls:{}}}` |

SDK: `get_recent_objects()`, `get_spotlights()`, `get_shared_by_me()`,
`get_linked_app_objects()`, `get_manual_tags()`, `get_recent_tags()`,
`get_supported_office_extensions()`

### Folders & sharing

| Method | Path | Body | Status |
|---|---|---|---|
| POST | `/nms/folders` | `{"objectName","parentObjectKey","sourceName":"DRIVE"}` → **201** |  |
| POST | `/share/ulinks` | `{"objects":[{"objectKey"}…],"shareName":"25Aug2026_HHMMSS","shareType":"L"}` → **201** `{"shareURL":"https://www.jioaicloud.com/l/?u=<token>"}` |  |

SDK: `create_folder()`, `create_share_link(keys[])` (multi-object supported)

---

## 3. Downloads — `https://jaws-dl.jioaicloud.com`

| Path | Purpose |
|---|---|
| `GET /download/files/<objectKey>` | Original binary stream (Content-Length set) |
| `GET /download/avimages/<objectKey>` | Transcoded image/video thumbnail (404 if none exists) |

SDK: `download_file()` (chunked, atomic `.part→final` rename, retry on
5xx/network), `download_thumbnail()`, `download_all()` (thread-pool bulk)

---

## 4. Boards / Albums — `https://boards.jioaicloud.com`

| Method | Path | Notes |
|---|---|---|
| GET | `/boards/sync/initial?page=0&limit=2000&albumType=p` | List boards (`albumType=p` personal) |
| POST | `/boards` | Create → **201** with board object |
| GET | `/boards/<boardKey>?page=0&limit=5000&sort=-lastModifiedDate` | Board details + files |
| GET | `/invites/boards/<boardKey>/members` | Roster (`boardMembers[]`, owner `memberType:"O"`) |
| PUT | `/invites/boards/<boardKey>/unjoin` | Leave board (body `[]`) — board disappears from your list if you created it |

SDK: `list_boards()`, `create_board()`, `get_board()`, `get_board_members()`, `leave_board()`

---

## 5. Contacts — `https://jaws-contacts.jioaicloud.com`

| Path | Required extras | Envelope |
|---|---|---|
| `GET /amiko/cab/contacts?sort=displayname&onlyActive=true&nextPageDate=1970-01-01 00:00:00.000000` | headers `X-Offset: 0`, `X-CHUNK-SIZE: 30` | `{contacts:[…]}` |
| `GET /amiko/cab/emails` | headers `X-Offset: 0`, `X-CHUNK-SIZE: 30` | `{contactEmail:[…]}` |

Missing `X-Offset` or malformed `nextPageDate` → `400 TEJRF0400`.
SDK: `get_contacts(fetch_all=True)` auto-pages via X-Offset, `get_contact_emails()`

---

## 6. Messaging — `https://jaws-msg.jioaicloud.com`

`GET /promo/banner/list` → `{"cards":[…]}` — SDK: `get_promo_banners()`

---

## 7. Agent Tools (JSON mode / MCP)

16 tools registered in `jiocloud.AGENT_TOOLS_SCHEMA` (OpenAI/Anthropic
function-calling format):

`account_info`, `list_files`, `search_files`, `download_file*`,
`download_all*`, `create_folder`, `move_to_trash*`, `restore_from_trash*`,
`list_trash`, `share_link*`, `rename_object`, `set_favorite`,
`version_history`, `recent_activity`, `list_boards`, `get_contacts`

\* = requires `arguments.confirm = true`; otherwise the bridge returns
`confirmation_required` without executing.

Entry points:
- `jiocloud.handle_tool_call(payload_dict_or_json)` — one-shot dispatcher
- `JioAgentBridge(client).execute(tool, args)` — programmatic
- `python cli.py agent schema|call|serve` — CLI (serve = stdio loop;
  commands `schema`, `ping`, `quit` also supported)

Guarantees: strict JSON envelopes, no credential leakage in output,
typed error names, never raises to caller.
