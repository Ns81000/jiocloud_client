"""
Jio AI Cloud SDK - Data Models
Typed dataclasses representing entities returned by the Jio Cloud API.
Schemas verified against live traffic captures (2026-08).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    if not num_bytes:
        return "0 B"
    b = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"


def parse_timestamp(ms: Optional[int]) -> Optional[datetime]:
    """Parse epoch milliseconds to datetime object."""
    if not ms:
        return None
    try:
        # Guard against absurd legacy timestamps (e.g. 1071503137000 is valid, 0 is not)
        return datetime.fromtimestamp(ms / 1000.0)
    except Exception:
        return None


@dataclass
class JioStorageQuota:
    total_allocated_bytes: int
    total_used_bytes: int
    document_usage_bytes: int
    photo_usage_bytes: int
    video_usage_bytes: int
    audio_usage_bytes: int
    paid_plan_quota_bytes: int = 0
    default_storage_space_bytes: int = 0
    total_promotional_quota_bytes: int = 0

    @property
    def total_allocated_gb(self) -> float:
        return self.total_allocated_bytes / (1024 ** 3)

    @property
    def total_used_gb(self) -> float:
        return self.total_used_bytes / (1024 ** 3)

    @property
    def usage_percentage(self) -> float:
        if self.total_allocated_bytes == 0:
            return 0.0
        return (self.total_used_bytes / self.total_allocated_bytes) * 100.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JioStorageQuota":
        return cls(
            total_allocated_bytes=data.get("totalAllocatedQuota", data.get("allocatedSpace", 0)),
            total_used_bytes=data.get("totalUsedQuota", data.get("usedSpace", 0)),
            document_usage_bytes=data.get("documentUsage", 0),
            photo_usage_bytes=data.get("photoUsage", 0),
            video_usage_bytes=data.get("videoUsage", 0),
            audio_usage_bytes=data.get("audioUsage", 0),
            paid_plan_quota_bytes=data.get("paidPlanQuota", 0),
            default_storage_space_bytes=data.get("defaultStorageSpace", 0),
            total_promotional_quota_bytes=data.get("totalPromotionalQuota", 0)
        )


@dataclass
class JioUserProfile:
    user_id: str
    name: str
    email: str
    mobile_number: str
    root_folder_key: str
    status: str
    is_mobile_verified: bool
    is_email_verified: bool
    quota: JioStorageQuota
    auth_provider_id: Optional[int] = None
    devices: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JioUserProfile":
        return cls(
            user_id=data.get("userId", ""),
            name=f"{data.get('firstName', '')} {data.get('lastName', '')}".strip() or data.get("firstName", ""),
            email=data.get("emailId", ""),
            mobile_number=data.get("mobileNumber", ""),
            root_folder_key=data.get("rootFolderKey", ""),
            status=data.get("status", ""),
            is_mobile_verified=data.get("isMobileNumVerified", False),
            is_email_verified=data.get("isEmailIdVerified", False),
            quota=JioStorageQuota.from_dict(data.get("quota", {})),
            auth_provider_id=data.get("authProviderId"),
            devices=data.get("devices", []) or [],
            raw_data=data
        )


@dataclass
class JioFile:
    object_key: str
    parent_object_key: str
    object_name: str
    object_type: str  # "FE" (File Entry) or "FR" (Folder Reference)
    size_bytes: int
    mime_type: str
    mime_subtype: str
    source_folder: str
    hash_md5: str
    created_timestamp_ms: Optional[int]
    modified_timestamp_ms: Optional[int]
    status: str
    is_hidden: bool = False
    is_locked: bool = False
    is_readonly: bool = False
    is_favorite: bool = False
    download_url_direct: str = ""
    image_transcode_url: str = ""
    version: int = 1
    source_name: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_folder(self) -> bool:
        return self.object_type == "FR"

    @property
    def is_file(self) -> bool:
        return self.object_type == "FE"

    @property
    def extension(self) -> str:
        if self.is_folder:
            return ""
        if "." in self.object_name:
            return "." + self.object_name.rsplit(".", 1)[-1].lower()
        return ""

    @property
    def human_size(self) -> str:
        if self.is_folder:
            return "-"
        return format_bytes(self.size_bytes)

    @property
    def created_datetime(self) -> Optional[datetime]:
        return parse_timestamp(self.created_timestamp_ms)

    @property
    def modified_datetime(self) -> Optional[datetime]:
        return parse_timestamp(self.modified_timestamp_ms)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JioFile":
        key = data.get("objectKey", "")
        return cls(
            object_key=key,
            parent_object_key=data.get("parentObjectKey", ""),
            object_name=data.get("objectName", ""),
            object_type=data.get("objectType", "FE"),
            size_bytes=data.get("sizeInBytes") or data.get("size", 0),
            mime_type=data.get("mimeType", ""),
            mime_subtype=data.get("mimeSubType", ""),
            source_folder=data.get("sourceFolder", ""),
            hash_md5=data.get("hash", ""),
            created_timestamp_ms=data.get("fileCreatedDate") or data.get("createdDate"),
            modified_timestamp_ms=data.get("lastModifiedDate") or data.get("lastUpdatedDate"),
            status=data.get("status", "A"),
            is_hidden=data.get("isHidden", False),
            is_locked=data.get("isLocked", False),
            is_readonly=data.get("isReadonly", False),
            is_favorite=data.get("isFavorite", data.get("isFav") == "Y"),
            download_url_direct=data.get("url", f"https://jaws-dl.jioaicloud.com/download/files/{key}"),
            image_transcode_url=data.get("imageTranscodeUrl", f"https://jaws-dl.jioaicloud.com/download/avimages/{key}"),
            version=data.get("version", 1),
            source_name=data.get("sourceName", ""),
            raw_data=data
        )


# Backwards-friendly alias: API returns identical object shape for folders & files
JioFolder = JioFile


@dataclass
class JioShareLink:
    object_key: str
    share_url: str
    nonce: Optional[str] = None
    share_name: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, object_keys: List[str], data: Dict[str, Any], share_name: str = "") -> "JioShareLink":
        url = data.get("shareURL") or data.get("shareUrl", "")
        nonce = ""
        if "u=" in url:
            nonce = url.split("u=")[-1]
        return cls(
            object_key=",".join(object_keys),
            share_url=url,
            nonce=nonce,
            share_name=share_name,
            raw_data=data
        )


@dataclass
class JioBoard:
    board_key: str
    board_name: str
    board_type: str
    status: str
    files_count: int
    users_count: int
    created_timestamp_ms: Optional[int]
    description: str = ""
    owner_user_id: str = ""
    last_modified_timestamp_ms: Optional[int] = None
    image_count: int = 0
    video_count: int = 0
    audio_count: int = 0
    comments_count: int = 0
    size_in_bytes: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JioBoard":
        return cls(
            board_key=data.get("boardKey", ""),
            board_name=data.get("boardName", ""),
            board_type=data.get("boardType", "P"),
            status=data.get("status", "A"),
            files_count=data.get("filesCount", 0),
            users_count=data.get("usersCount", 1),
            created_timestamp_ms=data.get("createdDate"),
            description=data.get("boardDescription", ""),
            owner_user_id=data.get("ownerUserId", data.get("createdBy", "")),
            last_modified_timestamp_ms=data.get("lastModifiedDate") or data.get("lastUpdatedDate"),
            image_count=data.get("imageCount", 0),
            video_count=data.get("videoCount", 0),
            audio_count=data.get("audioCount", 0),
            comments_count=data.get("commentsCount", 0),
            size_in_bytes=data.get("sizeInBytes", 0),
            raw_data=data
        )


@dataclass
class JioBoardMember:
    user_id: str
    first_name: str
    member_type: str          # "O" = Owner
    member_status: str        # "A" = Active
    member_since_ms: Optional[int] = None
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JioBoardMember":
        return cls(
            user_id=data.get("userId", ""),
            first_name=data.get("firstName", ""),
            member_type=data.get("memberType", ""),
            member_status=data.get("memberStatus", ""),
            member_since_ms=data.get("memCreatedDate"),
            raw_data=data
        )


@dataclass
class JioFileVersion:
    version_number: int
    display_version: str
    created_timestamp_ms: Optional[int]
    updated_timestamp_ms: Optional[int]
    is_current: bool
    created_by_name: str = ""
    last_updated_by: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JioFileVersion":
        vcb = data.get("versionCreatedBy") or {}
        return cls(
            version_number=data.get("version", 0),
            display_version=data.get("displayVersion", ""),
            created_timestamp_ms=data.get("createdDate"),
            updated_timestamp_ms=data.get("lastUpdatedDate"),
            is_current=bool(data.get("isCurrentVersion")),
            created_by_name=vcb.get("firstName", ""),
            last_updated_by=data.get("lastUpdatedBy", ""),
            raw_data=data
        )


@dataclass
class JioContactEmail:
    email: str
    display_name: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Any) -> "JioContactEmail":
        if isinstance(data, str):
            return cls(email=data)
        return cls(
            email=data.get("emailId", data.get("email", "")),
            display_name=data.get("displayName", ""),
            raw_data=data if isinstance(data, dict) else {}
        )
