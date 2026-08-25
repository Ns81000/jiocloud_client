# Data Models & Schemas

> **UNSTABLE TARGET — Last verified: 2026-08-25 (26/26 checks passed).**
> Jio AI Cloud has no public API. Endpoints change without notice and can
> break at any time. Features may stop working at any moment — check
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for current status.

Typed dataclasses live in `jiocloud/models.py`. Every field maps to a
verified production response shape (2026-08 captures).

---

## JioUserProfile — from `GET /security/users`

| Field | Type | Source key |
|---|---|---|
| `user_id` | str | `userId` |
| `name` | str | `firstName` + `lastName` |
| `email` | str | `emailId` |
| `mobile_number` | str | `mobileNumber` (masked server-side) |
| `root_folder_key` | str | `rootFolderKey` |
| `status` | str | `status` (`"A"` = active) |
| `is_mobile_verified` / `is_email_verified` | bool | `isMobileNumVerified` / `isEmailIdVerified` |
| `quota` | JioStorageQuota | `quota{…}` |
| `auth_provider_id` | int? | `authProviderId` |
| `devices` | list[dict] | `devices[]` |
| `raw_data` | dict | full payload |

## JioStorageQuota

| Field | Source key |
|---|---|
| `total_allocated_bytes` | `totalAllocatedQuota` / `allocatedSpace` |
| `total_used_bytes` | `totalUsedQuota` / `usedSpace` |
| `document_usage_bytes` | `documentUsage` |
| `photo_usage_bytes` | `photoUsage` |
| `video_usage_bytes` | `videoUsage` |
| `audio_usage_bytes` | `audioUsage` |
| `paid_plan_quota_bytes` | `paidPlanQuota` |
| `default_storage_space_bytes` | `defaultStorageSpace` |
| `total_promotional_quota_bytes` | `totalPromotionalQuota` |

Properties: `total_allocated_gb`, `total_used_gb`, `usage_percentage`.

## JioFile (= JioFolder alias) — object schema used across listings, trash, boards

| Field | Type | Source key |
|---|---|---|
| `object_key` | str | `objectKey` (32-hex GUID) |
| `parent_object_key` | str | `parentObjectKey` |
| `object_name` | str | `objectName` |
| `object_type` | str | `objectType` — `"FE"` file entry / `"FR"` folder reference |
| `size_bytes` | int | `sizeInBytes` |
| `mime_type` / `mime_subtype` | str | `mimeType` / `mimeSubType` |
| `source_folder` | str | `sourceFolder` (original upload path for phone backups) |
| `hash_md5` | str | `hash` |
| `created_timestamp_ms` / `modified_timestamp_ms` | int? | `fileCreatedDate` / `lastModifiedDate` |
| `status` | str | `status` (`A`=active, `T`=trashed) |
| `is_hidden/locked/readonly/favorite` | bool | `isHidden/isLocked/isReadonly/isFavorite` |
| `download_url_direct` | str | `url` (fallback constructed) |
| `image_transcode_url` | str | `imageTranscodeUrl` |
| `version`, `source_name` | int, str | `version`, `sourceName` (`DRIVE`,`UPA`,`repocopy`,…) |

Properties: `is_folder`, `is_file`, `extension` (`.pdf` style), `human_size`,
`created_datetime`, `modified_datetime`.

Server-side computed display fields seen in payloads but not modeled
(kept in `raw_data`): `displayName`, `iconName`, `tileName`, `gridDate`,
`cMonthNo/cYear`, `latestVersion`, `recipientsObjRights`, etc.

## JioShareLink — from `POST /share/ulinks`

`share_url` (`shareURL`, format `https://www.jioaicloud.com/l/?u=<token>`),
`nonce` (the `u=` token), `share_name`, `object_key` (comma-joined keys).

## JioBoard

`board_key/board_name/board_type/status/description/owner_user_id`,
counts (`files_count`, `image_count`, `video_count`, `audio_count`,
`comments_count`, `users_count`, `size_in_bytes`),
`created_timestamp_ms`, `last_modified_timestamp_ms`.

## JioBoardMember — from board members roster

`user_id`, `first_name`, `member_type` (`"O"` owner), `member_status`
(`"A"` active), `member_since_ms` (`memCreatedDate`).

## JioFileVersion — from `/nms/metadata/version/<key>`

 envelope: `{"totalVersions": N, "objVersions": [...]}`.
Fields: `version_number` (`version`), `display_version`, timestamps,
`is_current` (`isCurrentVersion`), `created_by_name`
(`versionCreatedBy.firstName`), `last_updated_by`.

## Agent envelope (JSON mode)

```jsonc
// request
{"tool": "<name>", "arguments": {...}}
// success
{"ok": true, "result": ..., "count": 0}        // count optional
// failure
{"ok": false, "error": {"type": "InvalidRequestError", "message": "..."}}
// guard
{"ok": false, "error": {"type": "confirmation_required", "message": "..."}}
```
