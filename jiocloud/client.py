"""
Jio AI Cloud SDK - Master API Client (v2)

Comprehensive, zero-dependency Python client for Jio AI Cloud storage services.
Every endpoint implemented here was verified against live traffic captures
(2026-08) and exercised against production servers.

UNOFFICIAL PROJECT — not affiliated with, endorsed by, or connected to
Reliance Jio Infocomm Ltd. Intended strictly for personal backup and data
portability of YOUR OWN account. See docs/DISCLAIMER.md / docs/LEGAL.md.
"""

import json
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator, Callable, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .auth import JioCloudAuth
from .exceptions import (
    JioCloudError,
    AuthenticationError,
    ForbiddenError,
    ObjectNotFoundError,
    InvalidRequestError,
    RateLimitError,
    ConflictError,
    PayloadTooLargeError,
    ServerError,
    NetworkError
)
from .models import (
    JioUserProfile,
    JioStorageQuota,
    JioFile,
    JioFolder,
    JioShareLink,
    JioBoard,
    JioBoardMember,
    JioFileVersion,
    format_bytes
)


class JioCloudClient:
    """
    Main client interface for interacting with Jio AI Cloud services.
    Thread-safe for concurrent downloads (each request builds its own headers).
    """

    BASE_JAWS_API = "https://jaws-api.jioaicloud.com"
    BASE_USER_API = "https://api.jioaicloud.com"
    BASE_DOWNLOAD_CDN = "https://jaws-dl.jioaicloud.com"
    BASE_BOARDS_API = "https://boards.jioaicloud.com"
    BASE_CONTACTS_API = "https://jaws-contacts.jioaicloud.com"
    BASE_MSG_API = "https://jaws-msg.jioaicloud.com"

    def __init__(self, auth: JioCloudAuth, max_retries: int = 3, retry_backoff: float = 1.5):
        self.auth = auth
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._user_profile: Optional[JioUserProfile] = None
        self._root_folder_key: Optional[str] = None

    @classmethod
    def from_config(cls, config_path: str = "config.json", **kwargs) -> "JioCloudClient":
        """Initialize client directly from JSON configuration file."""
        auth = JioCloudAuth.from_file(config_path)
        return cls(auth, **kwargs)

    @classmethod
    def from_env(cls, **kwargs) -> "JioCloudClient":
        """Initialize client from environment variables."""
        auth = JioCloudAuth.from_env()
        return cls(auth, **kwargs)

    # -------------------------------------------------------------------------
    # Internal Request Dispatcher with Retry & Error Recovery
    # -------------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: int = 30,
        retries: Optional[int] = None,
        raw: bool = False,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        Execute authenticated HTTP request with JSON parsing, error mapping,
        and automatic exponential backoff on 429 / 5xx / transient network faults.
        Set raw=True to receive the raw bytes of the response body.

        NOTE (verified against production): Jio endpoints REQUIRE a
        Content-Type header even on bodiless GETs (error NMSOM0003 /
        BRSOM0036 otherwise), so it is always sent.
        """
        if params:
            query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query_string}"

        data_bytes = None
        if json_body is not None:
            data_bytes = json.dumps(json_body).encode("utf-8")
        content_type = "application/json; charset=UTF-8"  # required on ALL verbs

        attempts_left = self.max_retries if retries is None else retries
        last_exc: Optional[JioCloudError] = None

        for attempt in range(attempts_left + 1):
            headers = self.auth.get_headers(content_type=content_type)
            if extra_headers:
                headers.update(extra_headers)
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = resp.read()
                    if raw:
                        return body
                    if not body:
                        return {}
                    try:
                        return json.loads(body.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        return {"_raw": body}

            except urllib.error.HTTPError as e:
                raw_err = ""
                try:
                    raw_err = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                err_code = None
                err_msg = getattr(e, "reason", "HTTP Error")
                try:
                    err_json = json.loads(raw_err)
                    err_msg = err_json.get("error") or err_json.get("message") or err_msg
                    err_code = err_json.get("code")
                except Exception:
                    pass

                exc_map = {
                    400: InvalidRequestError,
                    401: AuthenticationError,
                    403: ForbiddenError,
                    404: ObjectNotFoundError,
                    409: ConflictError,
                    413: PayloadTooLargeError,
                    429: RateLimitError,
                }
                cls = exc_map.get(e.code) or (ServerError if e.code >= 500 else JioCloudError)
                exc = cls(
                    f"HTTP {e.code}: {err_msg}",
                    status_code=e.code,
                    error_code=err_code,
                    raw_response=raw_err[:2000]
                )

                # Retry only on transient conditions
                if isinstance(exc, (RateLimitError, ServerError)) and attempt < attempts_left:
                    delay = self.retry_backoff * (2 ** attempt)
                    time.sleep(delay)
                    last_exc = exc
                    continue
                raise exc

            except (urllib.error.URLError, OSError, TimeoutError) as e:
                reason = getattr(e, "reason", e)
                exc = NetworkError(f"Network error connecting to Jio Cloud: {reason}")
                if attempt < attempts_left:
                    time.sleep(self.retry_backoff * (2 ** attempt))
                    last_exc = exc
                    continue
                raise exc

        raise last_exc or JioCloudError("Request failed after retries")

    # -------------------------------------------------------------------------
    # Account & Profile APIs
    # -------------------------------------------------------------------------

    def get_user_profile(self, refresh: bool = False) -> JioUserProfile:
        """Fetch current authenticated user profile, quota, root folder key, devices."""
        if self._user_profile and not refresh:
            return self._user_profile

        url = f"{self.BASE_USER_API}/security/users"
        data = self._request("GET", url)
        self._user_profile = JioUserProfile.from_dict(data)
        self._root_folder_key = self._user_profile.root_folder_key
        return self._user_profile

    def get_storage_quota(self) -> JioStorageQuota:
        """Retrieve storage allocation and category usage breakdown."""
        profile = self.get_user_profile()
        return profile.quota

    def get_root_folder_key(self) -> str:
        """Get the root container key for the account (fetched live from profile)."""
        if not self._root_folder_key:
            self.get_user_profile()
        if not self._root_folder_key:
            raise JioCloudError("Root folder key unavailable from user profile.")
        return self._root_folder_key

    def get_app_settings(self) -> Dict[str, Any]:
        """Fetch cloud backup policies and device client settings."""
        url = f"{self.BASE_USER_API}/app/settings"
        return self._request("GET", url, params={"os": "web"})

    def get_promotions(self) -> Dict[str, Any]:
        """Fetch active/expired storage promotions for the account."""
        url = f"{self.BASE_USER_API}/security/users/promotions"
        return self._request("GET", url)

    def get_cookie_nonce(self, jwt: str) -> str:
        """
        Exchange a web-session JWT for a short-lived download nonce
        (POST /security/getokenforcookie). Returns the nonce UUID.
        Used by the official web app for browser-based downloads.
        """
        url = f"{self.BASE_USER_API}/security/getokenforcookie"
        data = self._request("POST", url, json_body={"jwt": jwt})
        return data.get("nonce", "")

    def list_devices(self) -> List[Dict[str, Any]]:
        """List devices registered to this account (from the user profile)."""
        return self.get_user_profile().devices

    # -------------------------------------------------------------------------
    # File & Folder Query APIs
    # -------------------------------------------------------------------------

    def list_directory(
        self,
        folder_key: Optional[str] = None,
        limit: int = 200,
        object_type: str = "f",   # 'f' files, 'w' folders (server rejects other values)
        sort: str = "+fileCreatedDate",
        endpoint: str = "defaultview"
    ) -> Tuple[List[JioFile], Dict[str, Any]]:
        """
        Fetch one page of directory entries. Returns (objects, envelope).
        Envelope carries quota info: allocatedSpace / usedSpace / isUploadAllowed.

        Verified endpoints:
          - defaultview: GET /nms/metadata/defaultview/myfiles/v1
          - legacy:      GET /nms/metadata
        NOTE: `type` accepts only 'f' (files) or 'w' (folders); anything else
        returns 400 NMSOM0129 ("Kindly provide valid value for folder(W) or
        file(F) Search"). To walk everything, list folders + files separately.
        """
        target = folder_key or self.get_root_folder_key()
        path = ("/nms/metadata/defaultview/myfiles/v1"
                if endpoint == "defaultview" else "/nms/metadata")
        url = f"{self.BASE_JAWS_API}{path}"
        params = {"limit": limit, "folderKey": target, "type": object_type, "sort": sort}
        data = self._request("GET", url, params=params)
        objects = [JioFile.from_dict(o) for o in data.get("objects", [])]
        return objects, data

    def list_folders(self, parent_folder_key: Optional[str] = None) -> List["JioFolder"]:
        """List subfolders inside a target directory or root."""
        objs, _ = self.list_directory(parent_folder_key, object_type="w", sort="+fileCreatedDate")
        return objs

    def list_files(
        self,
        folder_key: Optional[str] = None,
        limit: int = 200,
        sort: str = "-fileCreatedDate"
    ) -> List[JioFile]:
        """Fetch single page of files inside a directory (up to limit items)."""
        objs, _ = self.list_directory(folder_key, limit=limit, object_type="f", sort=sort)
        return objs

    def stream_all_files(
        self,
        folder_key: Optional[str] = None,
        sort: str = "-fileCreatedDate",
        page_size: int = 2000,
        page_delay: float = 0.15,
        recursive: bool = True
    ) -> Generator[JioFile, None, None]:
        """
        Streaming generator that paginates through every file in the account
        (or one subtree). Pagination is offset-based via the page parameter;
        deduplicates by objectKey as a safety net. Memory-light by design.
        """
        root = folder_key or self.get_root_folder_key()
        seen_keys = set()
        queue = [root]
        visited_folders = set()

        while queue:
            current = queue.pop(0)
            if current in visited_folders:
                continue
            visited_folders.add(current)
            # Folders first (to build the traversal queue), then files of this dir
            for type_code, is_dir_query in (("w", True), ("f", False)):
                page = 0
                while True:
                    url = f"{self.BASE_JAWS_API}/nms/metadata"
                    params = {
                        "page": page,
                        "limit": page_size,
                        "folderKey": current,
                        "type": type_code,
                        "sort": sort
                    }
                    data = self._request("GET", url, params=params)
                    objs = data.get("objects", [])
                    for o in objs:
                        k = o.get("objectKey")
                        if k and k not in seen_keys:
                            seen_keys.add(k)
                            item = JioFile.from_dict(o)
                            if item.is_file:
                                if not is_dir_query:
                                    yield item
                            elif recursive and item.is_folder:
                                if is_dir_query:
                                    queue.append(k)
                            elif not recursive and not is_dir_query:
                                yield item
                    if len(objs) < page_size:
                        break
                    page += 1
                    if page_delay > 0:
                        time.sleep(page_delay)

    def list_all_files(
        self,
        folder_key: Optional[str] = None,
        sort: str = "-fileCreatedDate",
        recursive: bool = True
    ) -> List[JioFile]:
        """Fetch every file in the account and return as a complete list."""
        return list(self.stream_all_files(folder_key=folder_key, sort=sort, recursive=recursive))

    def search_files(
        self,
        query: str,
        filter_extension: Optional[str] = None,
        cached_files: Optional[List[JioFile]] = None,
        case_sensitive: bool = False
    ) -> List[JioFile]:
        """Search files by filename, extension, or original backup source path."""
        files = cached_files if cached_files is not None else self.list_all_files()
        q = query if case_sensitive else query.lower().strip()
        ext = filter_extension.lower().strip() if filter_extension else None
        if ext and not ext.startswith("."):
            ext = "." + ext

        results = []
        for f in files:
            name = f.object_name if case_sensitive else f.object_name.lower()
            src = f.source_folder if case_sensitive else f.source_folder.lower()
            matches_query = (q in name) or (q in src)
            matches_ext = (f.extension == ext) if ext else True
            if matches_query and matches_ext:
                results.append(f)
        return results

    def get_recent_objects(self) -> Dict[str, Any]:
        """
        Recent files feed shown on the web home (photos + docs).
        Raw envelope: objectsImgs[], objectsDocs[], etc.
        """
        url = f"{self.BASE_JAWS_API}/nms/metadata/recent/objects"
        return self._request("GET", url)

    def get_spotlights(self, page: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Spotlighted memory/photo cards. Envelope: spotLights[]."""
        url = f"{self.BASE_JAWS_API}/nms/spotlights/metadata"
        return self._request("GET", url, params={"page": page, "limit": limit})

    def get_shared_by_me(self, page: int = 0, limit: int = 200, sort: str = "-smd") -> Dict[str, Any]:
        """Objects shared by me with others (collaborative shares)."""
        url = f"{self.BASE_JAWS_API}/nms/collshare/byme"
        return self._request("GET", url, params={"page": page, "limit": limit, "sort": sort})

    def get_linked_app_objects(self, appcode: str = "dgl", page: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Objects ingested via linked partner apps (appcode=dgl => DigiLocker)."""
        url = f"{self.BASE_JAWS_API}/nms/headless/linkedapp/metadata"
        return self._request("GET", url, params={"appcode": appcode, "page": page, "limit": limit})

    def get_manual_tags(self, object_key: str) -> List[Any]:
        """User-applied manual tags for an object."""
        url = f"{self.BASE_JAWS_API}/nms/manual/tags/{object_key}"
        data = self._request("GET", url)
        return data if isinstance(data, list) else data.get("tags", [])

    def get_recent_tags(self) -> List[Any]:
        """Recently used manual tags account-wide."""
        url = f"{self.BASE_JAWS_API}/nms/manual/tag/recents"
        data = self._request("GET", url)
        return data if isinstance(data, list) else data.get("tags", [])

    def get_supported_office_extensions(self) -> Dict[str, Any]:
        """Office-for-web view/edit capability matrix from the CSPP service."""
        url = f"{self.BASE_JAWS_API}/cspp/intg/doc/supported"
        return self._request("GET", url)

    def get_promo_banners(self) -> List[Dict[str, Any]]:
        """Marketing banners pushed to the web UI (jaws-msg service)."""
        url = f"{self.BASE_MSG_API}/promo/banner/list"
        data = self._request("GET", url)
        return data.get("cards", [])

    def get_version_history(self, object_key: str) -> List[JioFileVersion]:
        """
        Retrieve version history for a specific file.
        API shape (verified): {"totalVersions": N, "objVersions": [...]}
        """
        url = f"{self.BASE_JAWS_API}/nms/metadata/version/{object_key}"
        data = self._request("GET", url)
        return [JioFileVersion.from_dict(v) for v in data.get("objVersions", [])]

    # -------------------------------------------------------------------------
    # Direct File Download APIs
    # -------------------------------------------------------------------------

    def download_file(
        self,
        object_key: str,
        destination_path: Union[str, Path],
        chunk_size: int = 131072,  # 128 KB chunks
        progress_callback: Optional[Callable[[int, int], None]] = None,
        overwrite: bool = False
    ) -> Path:
        """
        Stream download a file directly from Jio CDN servers to local disk.

        :param object_key: Unique GUID of the file
        :param destination_path: Target local file path or directory
        :param chunk_size: Read buffer size in bytes
        :param progress_callback: Optional callback func(downloaded_bytes, total_bytes)
        :param overwrite: Replace existing local file instead of erroring
        """
        dest = Path(destination_path)
        if dest.is_dir():
            # Try to resolve a nice name later; caller usually passes full path.
            dest = dest / f"{object_key}.bin"

        if dest.exists() and not overwrite:
            raise FileExistsError(f"Destination exists (pass overwrite=True): {dest}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.BASE_DOWNLOAD_CDN}/download/files/{object_key}"

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            headers = self.auth.get_headers(content_type=None)
            req = urllib.request.Request(url, headers=headers, method="GET")
            try:
                tmp = dest.with_suffix(dest.suffix + ".part")
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total_size = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    with open(tmp, "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_size)
                tmp.replace(dest)   # atomic finalize
                return dest
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
                last_exc = e
                if isinstance(e, urllib.error.HTTPError) and e.code < 500 and e.code != 429:
                    raise NetworkError(f"Download failed HTTP {e.code} for {object_key}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2 ** attempt))
                    continue
        raise NetworkError(f"Download failed after retries for {object_key}: {last_exc}")

    def download_thumbnail(self, object_key: str, destination_path: Union[str, Path]) -> Path:
        """Download dynamic preview/transcoded thumbnail for images/videos."""
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.BASE_DOWNLOAD_CDN}/download/avimages/{object_key}"
        headers = self.auth.get_headers(content_type=None)
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest, "wb") as f:
                    f.write(resp.read())
        except urllib.error.HTTPError as e:
            raise ObjectNotFoundError(f"Thumbnail unavailable (HTTP {e.code}) for {object_key}")
        return dest

    def download_all(
        self,
        destination_dir: Union[str, Path],
        filter_extension: Optional[str] = None,
        max_workers: int = 4,
        mirror_folders: bool = False,
        skip_existing: bool = True,
        on_file_complete: Optional[Callable[[JioFile, bool, Optional[str]], None]] = None
    ) -> Dict[str, Any]:
        """
        Bulk multi-threaded downloader with optional cloud folder-structure
        mirroring, resume-friendly skip_existing, and per-file callbacks.
        """
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        files = self.list_all_files()

        if filter_extension:
            ext = filter_extension if filter_extension.startswith(".") else f".{filter_extension}"
            files = [f for f in files if f.extension.lower() == ext.lower()]

        stats = {"total": len(files), "success": 0, "failed": 0, "skipped": 0, "bytes": 0}
        stats_lock_dest = dest_dir  # name collisions resolved per-file below

        def _target_for(f: JioFile) -> Path:
            base_dir = dest_dir
            if mirror_folders:
                rel_parent = f.parent_object_key
                sub = dest_dir / "_folders" / rel_parent[:12]
                sub.mkdir(parents=True, exist_ok=True)
                base_dir = sub
            target = base_dir / f.object_name
            if target.exists():
                if skip_existing:
                    return target  # caller checks before download
                stem, suffix = target.stem, target.suffix
                target = base_dir / f"{stem}_{f.object_key[:8]}{suffix}"
            return target

        def _download_task(f: JioFile):
            target_path = _target_for(f)
            if skip_existing and target_path.exists():
                return (f, True, "skipped", target_path.stat().st_size)
            try:
                self.download_file(f.object_key, target_path, overwrite=True)
                return (f, True, None, f.size_bytes)
            except Exception as e:
                return (f, False, str(e), 0)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(_download_task, f): f for f in files}
            for future in as_completed(future_to_file):
                f, success, err, size = future.result()
                if success and err == "skipped":
                    stats["skipped"] += 1
                elif success:
                    stats["success"] += 1
                    stats["bytes"] += size
                else:
                    stats["failed"] += 1
                if on_file_complete:
                    on_file_complete(f, success, err)

        return stats

    # -------------------------------------------------------------------------
    # Management & Mutation APIs (Write / Delete / Restore / Share)
    # -------------------------------------------------------------------------

    def _metadata_op(self, operation: str, object_patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal helper for batch operations against PUT /nms/metadata/1.0.
        Raises InvalidRequestError when the server reports the op in
        `unprocessed[]` (per-object errorCode like NMSOM0021).
        """
        url = f"{self.BASE_JAWS_API}/nms/metadata/1.0"
        payload = {
            "objects": [{
                "operation": operation,
                "correlationId": self.auth.user_id,
                "object": object_patch
            }]
        }
        result = self._request("PUT", url, json_body=payload)
        if isinstance(result, dict):
            failed = result.get("unprocessed") or []
            if failed:
                first = failed[0]
                obj = first.get("object") or {}
                raise InvalidRequestError(
                    f"{operation} rejected: {obj.get('errorMessage', first.get('errorMessage', 'unknown'))}",
                    status_code=400,
                    error_code=obj.get("errorCode", first.get("errorCode")),
                    raw_response=json.dumps(failed)[:1000]
                )
        return result

    def create_folder(self, folder_name: str, parent_folder_key: Optional[str] = None) -> JioFolder:
        """Create a new folder in cloud storage (sourceName=DRIVE verified)."""
        parent_key = parent_folder_key or self.get_root_folder_key()
        url = f"{self.BASE_JAWS_API}/nms/folders"
        payload = {
            "objectName": folder_name,
            "parentObjectKey": parent_key,
            "sourceName": "DRIVE"
        }
        data = self._request("POST", url, json_body=payload)
        return JioFolder.from_dict(data)

    def rename_object(
        self,
        object_key: str,
        new_name: str,
        is_folder: bool = False,
        parent_object_key: Optional[str] = None,
        source_name: str = "DRIVE",
        current_object: Optional[JioFile] = None
    ) -> Dict[str, Any]:
        """
        Rename a file or folder (operation=RENAME).

        Server-verified: the batch patch must be the FULL object echo
        (missing sourceName → NMSOM0021, missing objectName → TEJVF0001).
        When `current_object` is not supplied, this method resolves live
        server state automatically.
        """
        if current_object is not None:
            obj = dict(current_object.raw_data)
            obj["objectName"] = new_name
        else:
            resolved = self._resolve_objects([object_key])
            if object_key not in resolved:
                raise ObjectNotFoundError(
                    f"Cannot rename: object key not found in any folder: {object_key}")
            obj = resolved[object_key]
            obj["objectName"] = new_name
        return self._metadata_op("RENAME", obj)

    def move_object(
        self,
        object_key: str,
        new_parent_folder_key: str,
        source_name: str = "DRIVE",
        current_object: Optional[JioFile] = None
    ) -> Dict[str, Any]:
        """
        Move a file/folder into another folder (operation=MOVE).
        Full object echo required by server — resolved automatically unless
        `current_object` is passed.
        """
        if current_object is not None:
            obj = dict(current_object.raw_data)
        else:
            resolved = self._resolve_objects([object_key])
            if object_key not in resolved:
                raise ObjectNotFoundError(
                    f"Cannot move: object key not found in any folder: {object_key}")
            obj = resolved[object_key]
        obj["parentObjectKey"] = new_parent_folder_key
        return self._metadata_op("MOVE", obj)

    def _resolve_objects(self, keys: List[str], roots: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Resolve object keys to their FULL current server-side raw objects.
        Needed because metadata/1.0 batch ops require a complete object echo
        (missing sourceName -> NMSOM0021, missing objectName -> TEJVF0001).

        Uses the defaultview endpoint (reliable pagination for large folders);
        walks the tree breadth-first until all keys are found or the tree is
        exhausted.
        """
        remaining = set(keys)
        resolved: Dict[str, Dict[str, Any]] = {}
        root = self.get_root_folder_key()
        queue = list(roots) if roots else [root]
        visited = set()
        while queue and remaining:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for type_code in ("w", "f"):
                # paginate defensively: keep fetching while pages return full
                page = 0
                while True:
                    objs, _ = self.list_directory(current, limit=1000,
                                                  object_type=type_code,
                                                  sort="+objectName",
                                                  endpoint="defaultview")
                    for f in objs:
                        if f.object_key in remaining:
                            resolved[f.object_key] = dict(f.raw_data)
                            remaining.discard(f.object_key)
                        if f.is_folder and f.object_key not in visited:
                            queue.append(f.object_key)
                    if len(objs) < 1000 or page > 50:
                        break
                    page += 1
                    time.sleep(0.2)
        return resolved

    def set_favorite(self, object_keys: Union[str, List[str]], favorite: bool = True) -> List[Dict[str, Any]]:
        """
        Favorite/unfavorite one or more objects (operations SETFAV/UNSETFAV).

        Server-verified: the batch patch must include the full object
        (objectName etc.), otherwise it lands in unprocessed[] with
        TEJVF0001 "constraint validation on objectName for value null".
        This method resolves each key from a live listing first.

        Returns per-object result entries from the batch responses.
        """
        keys = [object_keys] if isinstance(object_keys, str) else object_keys
        op = "SETFAV" if favorite else "UNSETFAV"
        resolved = self._resolve_objects(keys)
        missing = [k for k in keys if k not in resolved]
        if missing:
            raise ObjectNotFoundError(
                f"Cannot {op}: object(s) not found in any folder: {sorted(missing)}")
        results = []
        for k in keys:
            obj = resolved[k]
            obj["isFavorite"] = favorite
            results.append(self._metadata_op(op, obj))
        return results

    def delete_to_trash(self, object_keys: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Move one or more files/folders to Trash.

        Server-verified flow (fresh capture 2026-08-24T21:16): the web client
        issues batch op "TRASH" against PUT /nms/metadata/1.0 with the FULL
        object echo AND `"status": "T"` pre-set in the request payload.
        (The legacy PUT /nms/metadata/delete endpoint now silently rejects
        every key into unprocessed[] — see docs/KNOWN_ISSUES.md.)

        Raises InvalidRequestError if any op lands in unprocessed[].
        """
        keys = [object_keys] if isinstance(object_keys, str) else object_keys
        resolved = self._resolve_objects(keys)
        missing = [k for k in keys if k not in resolved]
        if missing:
            raise ObjectNotFoundError(
                f"Cannot trash: object(s) not found in any folder: {sorted(missing)}")
        last_result: Dict[str, Any] = {}
        for k in keys:
            obj = resolved[k]
            obj["status"] = "T"   # server requires the trashed state in-payload
            last_result = self._metadata_op("TRASH", obj)
        return last_result

    def restore_from_trash(self, object_keys: Union[str, List[str]]) -> Dict[str, Any]:
        """Restore one or more files/folders from Trash (PUT /nms/metadata/restore)."""
        keys = [object_keys] if isinstance(object_keys, str) else object_keys
        url = f"{self.BASE_JAWS_API}/nms/metadata/restore"
        payload = {"objectKeys": keys}
        return self._request("PUT", url, json_body=payload)

    def list_trash(self, limit: int = 100, sort: str = "-fileCreatedDate") -> List[JioFile]:
        """List all items currently in Trash (GET /nms/trash)."""
        url = f"{self.BASE_JAWS_API}/nms/trash"
        params = {"limit": limit, "sort": sort}
        data = self._request("GET", url, params=params)
        return [JioFile.from_dict(o) for o in data.get("objects", [])]

    def create_share_link(
        self,
        object_keys: Union[str, List[str]],
        share_name: Optional[str] = None,
        share_type: str = "L"
    ) -> JioShareLink:
        """
        Generate a universal public sharing link for one or more objects.
        Verified payload: {"objects":[{"objectKey":...}], "shareName":"25Aug2026_HHMMSS", "shareType":"L"}
        Response: {"shareURL": "https://www.jioaicloud.com/l/?u=<token>"}
        """
        keys = [object_keys] if isinstance(object_keys, str) else object_keys
        stamp = datetime.datetime.now().strftime("%d%b%Y_%H%M%S")
        name = share_name or stamp
        url = f"{self.BASE_JAWS_API}/share/ulinks"
        payload = {
            "objects": [{"objectKey": k} for k in keys],
            "shareName": name,
            "shareType": share_type
        }
        data = self._request("POST", url, json_body=payload)
        return JioShareLink.from_dict(keys, data, share_name=name)

    # -------------------------------------------------------------------------
    # Shared Boards (Albums) APIs
    # -------------------------------------------------------------------------

    def list_boards(self, album_type: str = "p") -> List[JioBoard]:
        """List shared boards / photo albums (albumType p=personal)."""
        url = f"{self.BASE_BOARDS_API}/boards/sync/initial"
        params = {"page": 0, "limit": 2000, "albumType": album_type}
        data = self._request("GET", url, params=params)
        return [JioBoard.from_dict(b) for b in data.get("boards", [])]

    def create_board(self, board_name: str, board_description: str = "") -> JioBoard:
        """Create a new collaborative shared album/board (returns 201 + board)."""
        url = f"{self.BASE_BOARDS_API}/boards"
        payload = {
            "boardName": board_name,
            "boardDescription": board_description,
            "parentObjectKey": None
        }
        data = self._request("POST", url, json_body=payload)
        return JioBoard.from_dict(data)

    def get_board(self, board_key: str, page: int = 0, limit: int = 5000,
                  sort: str = "-lastModifiedDate") -> Dict[str, Any]:
        """Board details + contained files. Envelope: {"board": {...}}."""
        url = f"{self.BASE_BOARDS_API}/boards/{board_key}"
        return self._request("GET", url, params={"page": page, "limit": limit, "sort": sort})

    def get_board_members(self, board_key: str) -> List[JioBoardMember]:
        """Member roster of a board. Envelope: boardMembers[]."""
        url = f"{self.BASE_BOARDS_API}/invites/boards/{board_key}/members"
        data = self._request("GET", url)
        return [JioBoardMember.from_dict(m) for m in data.get("boardMembers", [])]

    def leave_board(self, board_key: str) -> Dict[str, Any]:
        """Unjoin (leave) a shared board. PUT /invites/boards/{key}/unjoin."""
        url = f"{self.BASE_BOARDS_API}/invites/boards/{board_key}/unjoin"
        return self._request("PUT", url, json_body=[])

    # -------------------------------------------------------------------------
    # Contacts APIs
    # -------------------------------------------------------------------------

    def get_contacts(self, only_active: bool = True, offset: int = 0,
                     chunk_size: int = 30, fetch_all: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch cloud-synced address book contacts (amiko/cab service).

        Server-verified contract (errors TEJRF0400 otherwise):
          - requires `X-Offset` request header
          - requires `nextPageDate` query param, format
            'yyyy-MM-dd HH:mm:ss.SSSSSS' (epoch-zero fetches everything)
          - pages via X-Offset / X-CHUNK-SIZE when fetch_all=True
        """
        url = f"{self.BASE_CONTACTS_API}/amiko/cab/contacts"
        all_contacts: List[Dict[str, Any]] = []
        while True:
            data = self._request(
                "GET", url,
                params={
                    "sort": "displayname",
                    "onlyActive": str(bool(only_active)).lower(),
                    "nextPageDate": "1970-01-01 00:00:00.000000"
                },
                extra_headers={"X-Offset": str(offset), "X-CHUNK-SIZE": str(chunk_size)}
            )
            batch = data.get("contacts", [])
            all_contacts.extend(batch)
            if not fetch_all or len(batch) < chunk_size:
                break
            offset += chunk_size
        return all_contacts

    def get_contact_emails(self) -> List[Any]:
        """Fetch contact email registry used for sharing suggestions."""
        url = f"{self.BASE_CONTACTS_API}/amiko/cab/emails"
        data = self._request(
            "GET", url,
            extra_headers={"X-Offset": "0", "X-CHUNK-SIZE": "30"}
        )
        return data.get("contactEmail", [])
