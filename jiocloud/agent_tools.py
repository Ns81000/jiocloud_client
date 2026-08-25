"""
Jio AI Cloud SDK - AI Agent Integration Layer

Provides:
  1. AGENT_TOOLS_SCHEMA  — an OpenAI/Anthropic-compatible JSON tool schema
     describing every agent-callable operation (drop into any function-calling
     LLM's tools array).
  2. JioAgentBridge      — dispatches {"tool": name, "arguments": {...}} calls,
     returning structured JSON envelopes that are safe for agents to parse.
  3. handle_tool_call()  — single-entry convenience dispatcher.
  4. An MCP-style stdio loop (`python -m jiocloud.agent_tools serve`) so any
     Model Context Protocol host can drive the client as a tool server.

All output is strict JSON: {"ok": true, "result": ...} or
{"ok": false, "error": {"type", "message"}}. Credentials never appear in
output. Destructive operations require explicit confirm=true.
"""

import sys
import json
from typing import Any, Dict, List, Optional, Union

try:
    from .client import JioCloudClient
    from .auth import JioCloudAuth
    from .exceptions import JioCloudError, RateLimitError, ServerError, NetworkError
except ImportError:  # direct script execution fallback
    from client import JioCloudClient  # type: ignore
    from auth import JioCloudAuth  # type: ignore
    from exceptions import JioCloudError, RateLimitError, ServerError, NetworkError  # type: ignore


AGENT_TOOLS_SCHEMA = [
    {
        "name": "account_info",
        "description": "Get account profile, storage quota and usage breakdown for the connected Jio AI Cloud account.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_files",
        "description": "List files in a cloud folder. Omit folder_key to use the account root. Returns name, key, size, dates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_key": {"type": "string", "description": "Parent folder objectKey; omit for root"},
                "limit": {"type": "integer", "default": 50},
                "sort": {"type": "string", "default": "-fileCreatedDate"}
            }
        }
    },
    {
        "name": "search_files",
        "description": "Search ALL files in the account by name/source-path substring and optional extension filter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "extension": {"type": "string", "description": "e.g. pdf, docx (no dot needed)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "download_file",
        "description": "Download one file by objectKey to a local path. Requires confirm=true because it writes to local disk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_key": {"type": "string"},
                "destination": {"type": "string"},
                "confirm": {"type": "boolean"}
            },
            "required": ["object_key", "destination", "confirm"]
        }
    },
    {
        "name": "download_all",
        "description": "Bulk-download every file (optionally filtered by extension) into a local directory with parallel workers. Requires confirm=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination_dir": {"type": "string"},
                "extension": {"type": "string"},
                "max_workers": {"type": "integer", "default": 4},
                "confirm": {"type": "boolean"}
            },
            "required": ["destination_dir", "confirm"]
        }
    },
    {
        "name": "create_folder",
        "description": "Create a new folder in the cloud (mutating).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "parent_folder_key": {"type": "string"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "move_to_trash",
        "description": "Move one or more objects to trash (destructive but reversible). Requires confirm=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_keys": {"type": "array", "items": {"type": "string"}},
                "confirm": {"type": "boolean"}
            },
            "required": ["object_keys", "confirm"]
        }
    },
    {
        "name": "restore_from_trash",
        "description": "Restore previously trashed objects back to their original location. Requires confirm=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_keys": {"type": "array", "items": {"type": "string"}},
                "confirm": {"type": "boolean"}
            },
            "required": ["object_keys", "confirm"]
        }
    },
    {
        "name": "list_trash",
        "description": "List items currently in the account trash."
        ,
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 100}}
        }
    },
    {
        "name": "share_link",
        "description": "Create a public share link for one or more objects (makes data publicly accessible to anyone with the URL). Requires confirm=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_keys": {"type": "array", "items": {"type": "string"}},
                "confirm": {"type": "boolean"}
            },
            "required": ["object_keys", "confirm"]
        }
    },
    {
        "name": "rename_object",
        "description": "Rename a file or folder (mutating).",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_key": {"type": "string"},
                "new_name": {"type": "string"},
                "is_folder": {"type": "boolean", "default": False}
            },
            "required": ["object_key", "new_name"]
        }
    },
    {
        "name": "set_favorite",
        "description": "Favorite or unfavorite one or more objects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_keys": {"type": "array", "items": {"type": "string"}},
                "favorite": {"type": "boolean", "default": True}
            },
            "required": ["object_keys"]
        }
    },
    {
        "name": "version_history",
        "description": "List version history entries for a file.",
        "input_schema": {
            "type": "object",
            "properties": {"object_key": {"type": "string"}},
            "required": ["object_key"]
        }
    },
    {
        "name": "recent_activity",
        "description": "Recent files feed (photos/docs) as shown on the web home screen.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "list_boards",
        "description": "List shared boards / photo albums.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_contacts",
        "description": "Fetch cloud-synced contacts (for share suggestions).",
        "input_schema": {"type": "object", "properties": {}}
    }
]


class JioAgentBridge:
    """
    Dispatches structured agent tool calls against a live JioCloudClient.
    Every return value is a JSON-serializable dict.
    """

    DESTRUCTIVE = {
        "download_file", "download_all",           # local disk writes
        "move_to_trash", "restore_from_trash",     # mutating
        "share_link"                               # public exposure
    }

    def __init__(self, client: Optional[JioCloudClient] = None, config_path: str = "config.json"):
        self.client = client or (
            JioCloudClient.from_config(config_path)
            if _find_config(config_path) else None
        )

    def _client(self) -> JioCloudClient:
        if self.client is None:
            raise JioCloudError(
                "No credentials available. Provide config.json or pass a JioCloudClient."
            )
        return self.client

    def execute(self, tool: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = dict(arguments or {})
        try:
            if tool in self.DESTRUCTIVE and not args.get("confirm"):
                return {
                    "ok": False,
                    "error": {
                        "type": "confirmation_required",
                        "message": f"'{tool}' is a destructive/exposing operation. Re-issue with confirm=true."
                    }
                }

            c = self._client()

            if tool == "account_info":
                p = c.get_user_profile()
                q = p.quota
                return {"ok": True, "result": {
                    "user_id": p.user_id, "name": p.name, "email": p.email,
                    "root_folder_key": p.root_folder_key,
                    "quota_bytes": q.total_allocated_bytes, "used_bytes": q.total_used_bytes,
                    "usage_percent": round(q.usage_percentage, 2),
                    "documents_bytes": q.document_usage_bytes,
                    "photos_bytes": q.photo_usage_bytes,
                    "videos_bytes": q.video_usage_bytes,
                    "audio_bytes": q.audio_usage_bytes
                }}

            if tool == "list_files":
                files = c.list_files(
                    folder_key=args.get("folder_key"),
                    limit=int(args.get("limit", 50)),
                    sort=args.get("sort", "-fileCreatedDate")
                )
                return {"ok": True, "result": [_file_brief(f) for f in files]}

            if tool == "search_files":
                results = c.search_files(args["query"], filter_extension=args.get("extension"))
                return {"ok": True, "count": len(results),
                        "result": [_file_brief(f) for f in results[:200]]}

            if tool == "download_file":
                path = c.download_file(args["object_key"], args["destination"], overwrite=True)
                return {"ok": True, "result": {"saved_to": str(path)}}

            if tool == "download_all":
                stats = c.download_all(
                    destination_dir=args["destination_dir"],
                    filter_extension=args.get("extension"),
                    max_workers=int(args.get("max_workers", 4))
                )
                return {"ok": True, "result": stats}

            if tool == "create_folder":
                folder = c.create_folder(args["name"], parent_folder_key=args.get("parent_folder_key"))
                return {"ok": True, "result": {"object_key": folder.object_key,
                                               "name": folder.object_name}}

            if tool == "move_to_trash":
                res = c.delete_to_trash(args["object_keys"])
                return {"ok": True, "result_count": len(res.get("objects", []))}

            if tool == "restore_from_trash":
                res = c.restore_from_trash(args["object_keys"])
                return {"ok": True, "result_count": len(res.get("objects", []))}

            if tool == "list_trash":
                items = c.list_trash(limit=int(args.get("limit", 100)))
                return {"ok": True, "result": [_file_brief(f) for f in items]}

            if tool == "share_link":
                link = c.create_share_link(args["object_keys"])
                return {"ok": True, "result": {"share_url": link.share_url}}

            if tool == "rename_object":
                res = c.rename_object(
                    args["object_key"], args["new_name"],
                    is_folder=bool(args.get("is_folder", False))
                )
                return {"ok": True, "result": res if isinstance(res, dict) else {}}

            if tool == "set_favorite":
                c.set_favorite(args["object_keys"], favorite=bool(args.get("favorite", True)))
                return {"ok": True, "result_count": len(args["object_keys"])}

            if tool == "version_history":
                versions = c.get_version_history(args["object_key"])
                return {"ok": True, "result": [{
                    "version": v.version_number, "display": v.display_version,
                    "current": v.is_current, "created": str(v.created_datetime)
                } for v in versions]}

            if tool == "recent_activity":
                data = c.get_recent_objects()
                imgs = data.get("objectsImgs", [])
                docs = data.get("objectsDocs", [])
                briefs = [_file_brief_raw(o) for o in (imgs + docs)]
                return {"ok": True, "result": briefs[:50]}

            if tool == "list_boards":
                boards = c.list_boards()
                return {"ok": True, "result": [{
                    "board_key": b.board_key, "name": b.board_name,
                    "files": b.files_count, "images": b.image_count
                } for b in boards]}

            if tool == "get_contacts":
                return {"ok": True, "result": c.get_contacts()}

            return {"ok": False, "error": {"type": "unknown_tool",
                    "message": f"No handler registered for tool '{tool}'"}}

        except JioCloudError as e:
            return {"ok": False, "error": {"type": type(e).__name__, "message": str(e)}}
        except FileNotFoundError as e:
            return {"ok": False, "error": {"type": "LocalPathError", "message": str(e)}}
        except Exception as e:  # last-resort envelope; never leak tracebacks to agents
            return {"ok": False, "error": {"type": "InternalError", "message": str(e)}}


def _file_brief(f) -> Dict[str, Any]:
    return {
        "object_key": f.object_key,
        "name": f.object_name,
        "size_bytes": f.size_bytes,
        "human_size": f.human_size,
        "extension": f.extension,
        "modified": str(f.modified_datetime) if f.modified_datetime else None,
        "is_folder": f.is_folder,
        "parent_object_key": f.parent_object_key
    }


def _file_brief_raw(o: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "object_key": o.get("objectKey"),
        "name": o.get("objectName"),
        "size_bytes": o.get("sizeInBytes"),
        "mime": f"{o.get('mimeType','')}/{o.get('mimeSubType','')}",
        "url": o.get("url"),
        "parent_object_key": o.get("parentObjectKey")
    }


def _find_config(path: str) -> bool:
    import os
    if os.path.exists(path):
        return True
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.exists(os.path.join(os.path.dirname(here), path))


def handle_tool_call(payload: Union[str, Dict[str, Any]], bridge: Optional[JioAgentBridge] = None) -> Dict[str, Any]:
    """
    One-shot entry point. Accepts either a JSON string like
      '{"tool":"search_files","arguments":{"query":"invoice","extension":"pdf"}}'
    or an already-parsed dict. Returns the response envelope dict.
    """
    bridge = bridge or JioAgentBridge()
    try:
        call = json.loads(payload) if isinstance(payload, str) else payload
        tool = call.get("tool") or call.get("name")
        args = call.get("arguments") or call.get("parameters") or {}
        if not tool:
            return {"ok": False, "error": {"type": "bad_request",
                    "message": "Payload must include 'tool' (or 'name')"}}
        return bridge.execute(tool, args)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": {"type": "bad_json", "message": str(e)}}


def serve_stdio() -> int:
    """
    Minimal MCP-style JSON-RPC-ish stdio server loop:
    each line on stdin = {"tool": ..., "arguments": {...}} -> one JSON line out.
    Special commands: 'schema' (dump tool schema), 'ping', 'quit'.
    """
    bridge = JioAgentBridge()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line == "quit":
            break
        if line == "ping":
            print(json.dumps({"ok": True, "result": "pong"}), flush=True)
            continue
        if line == "schema":
            print(json.dumps({"ok": True, "tools": AGENT_TOOLS_SCHEMA}), flush=True)
            continue
        print(json.dumps(handle_tool_call(line, bridge)), flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        sys.exit(serve_stdio())
    else:
        print(json.dumps(AGENT_TOOLS_SCHEMA, indent=2))
