#!/usr/bin/env python3
"""
Jio AI Cloud - Command Line Interface (CLI)
Interact with your Jio Cloud storage directly from your terminal.

UNOFFICIAL TOOL — for personal backup / data portability of YOUR OWN account.
Not affiliated with Reliance Jio Infocomm Ltd. See DISCLAIMER.md.
"""

import argparse
import sys
import os
import json
import csv
from pathlib import Path

# Add package directory to python path
sys.path.insert(0, str(Path(__file__).parent))

from jiocloud import (
    JioCloudClient,
    format_bytes,
    AGENT_TOOLS_SCHEMA,
    JioAgentBridge,
    handle_tool_call
)
from jiocloud.exceptions import JioCloudError


def get_client(config_path="config.json") -> JioCloudClient:
    cfg = Path(config_path)
    if not cfg.exists():
        # Look in same directory as cli.py
        cfg = Path(__file__).parent / config_path

    if cfg.exists():
        return JioCloudClient.from_config(str(cfg))
    else:
        try:
            return JioCloudClient.from_env()
        except Exception:
            print(f"Error: Config file '{config_path}' not found and environment variables not set.")
            print("Please create 'config.json' from 'config.example.json' or set JIOCLOUD_* environment variables.")
            sys.exit(1)


def cmd_info(args):
    client = get_client(args.config)
    profile = client.get_user_profile()
    q = profile.quota

    print("\n" + "=" * 60)
    print("           JIO AI CLOUD - ACCOUNT OVERVIEW")
    print("=" * 60)
    print(f"User Name        : {profile.name}")
    print(f"Email ID         : {profile.email} ({'✓ Verified' if profile.is_email_verified else 'Unverified'})")
    print(f"Mobile Number    : {profile.mobile_number} ({'✓ Verified' if profile.is_mobile_verified else 'Unverified'})")
    print(f"User ID          : {profile.user_id}")
    print(f"Root Folder Key  : {profile.root_folder_key}")
    print(f"Account Status   : {'Active' if profile.status == 'A' else profile.status}")
    if args.devices:
        for d in client.list_devices():
            print(f"  Device: {d.get('deviceName')} ({d.get('platformType')}, key={str(d.get('deviceKey'))[:8]}…)")
    print("-" * 60)

    used_gb = q.total_used_gb
    total_gb = q.total_allocated_gb
    pct = q.usage_percentage

    bar_len = 30
    filled = int((pct / 100.0) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)

    print(f"Storage Quota    : {used_gb:.2f} GB / {total_gb:.2f} GB ({pct:.1f}%)")
    print(f"Capacity Usage   : [{bar}]")
    print("\nStorage Breakdown by Category:")
    print(f"  Documents   : {format_bytes(q.document_usage_bytes):>10}")
    print(f"  Videos      : {format_bytes(q.video_usage_bytes):>10}")
    print(f"  Photos      : {format_bytes(q.photo_usage_bytes):>10}")
    print(f"  Audio       : {format_bytes(q.audio_usage_bytes):>10}")
    print("=" * 60 + "\n")


def _emit(items, fmt, header):
    if fmt == "json":
        out = [i.raw_data if hasattr(i, 'raw_data') else i for i in items]
        print(json.dumps(out, indent=2))
        return
    if fmt == "csv":
        w = csv.writer(sys.stdout)
        if items and hasattr(items[0], "object_name"):
            w.writerow(["Name", "Extension", "Size", "Created", "Modified", "ObjectKey", "ParentKey"])
            for f in items:
                w.writerow([f.object_name, f.extension, f.size_bytes, f.created_datetime,
                            f.modified_datetime, f.object_key, f.parent_object_key])
        return
    print(header)
    for i in items:
        if hasattr(i, "object_name"):
            name = i.object_name[:52] + "…" if len(i.object_name) > 55 else i.object_name
            fav = "★" if getattr(i, "is_favorite", False) else " "
            kind = "DIR " if i.is_folder else "FILE"
            dt = str(i.modified_datetime)[:19] if i.modified_datetime else "-"
            print(f"{kind} {fav}| {name:<55} | {i.human_size:>9} | {dt} | {i.object_key[:12]}…")
        else:
            print(i)


def cmd_list(args):
    client = get_client(args.config)
    objs, envelope = client.list_directory(
        folder_key=args.folder,
        limit=args.limit,
        object_type={"all": "a", "files": "f", "folders": "w"}[args.type],
        sort=args.sort,
        endpoint=args.endpoint
    )
    hdr = "\n" + "=" * 110 + f"\n Directory listing ({len(objs)} items)\n" + "=" * 110
    _emit(objs, args.format, hdr)
    if args.format == "table":
        print("=" * 110)
        print(f"Total listed: {len(objs)} items | Quota used: {format_bytes(envelope.get('usedSpace', 0))}\n")


def cmd_tree(args):
    """Recursive walk of a folder subtree."""
    client = get_client(args.config)
    root = args.folder or client.get_root_folder_key()
    depth = args.depth

    def walk(key, prefix, level):
        if depth is not None and level > depth:
            return
        folders, _ = client.list_directory(key, limit=2000, object_type="w", endpoint="legacy")
        files, _ = client.list_directory(key, limit=2000, object_type="f", endpoint="legacy")
        entries = [(f, True) for f in folders] + [(f, False) for f in files]
        for i, (item, is_dir) in enumerate(entries):
            last = (i == len(entries) - 1)
            branch = "└── " if last else "├── "
            print(f"{prefix}{branch}{item.object_name}" + ("/" if is_dir else ""))
            if is_dir:
                walk(item.object_key, prefix + ("    " if last else "│   "), level + 1)

    print("[root]")
    walk(root, "", 1)


def cmd_search(args):
    client = get_client(args.config)
    results = client.search_files(args.query, filter_extension=args.ext)
    hdr = f"\nSearch '{args.query}' → {len(results)} matches\n" + "-" * 100
    _emit(results[:args.max], args.format, hdr)
    if args.format == "table":
        print("-" * 100 + f"\nShowing min({len(results)},{args.max}) of {len(results)}\n")


def cmd_download(args):
    client = get_client(args.config)
    dest = Path(args.dest or "./")

    def _progress(done, total):
        if total > 0:
            pct = (done / total) * 100
            sys.stdout.write(f"\r  Progress: {format_bytes(done)} / {format_bytes(total)} ({pct:.1f}%)")
        else:
            sys.stdout.write(f"\r  Progress: {format_bytes(done)}")
        sys.stdout.flush()

    out_path = client.download_file(args.key, dest, progress_callback=_progress, overwrite=True)
    print(f"\n[✓] Downloaded to: {out_path}")


def cmd_sync(args):
    client = get_client(args.config)
    dest = Path(args.dest or "./jiocloud_backup")
    print(f"Syncing to '{dest}' (workers={args.workers}, ext={args.ext or 'ALL'}, skip-existing={'yes' if args.skip_existing else 'no'})…")

    def _on_file(f, success, err):
        status = "✓" if success and err != "skipped" else ("↷" if success else "✗")
        detail = f"- {err}" if err and err != "skipped" else ("- already present" if err == "skipped" else "")
        print(f"  [{status}] {f.object_name} ({f.human_size}) {detail}")

    stats = client.download_all(
        dest, filter_extension=args.ext, max_workers=args.workers,
        skip_existing=not args.no_skip, on_file_complete=_on_file
    )
    print("\n" + "=" * 60)
    print("SYNC SUMMARY:")
    for k, v in stats.items():
        label = "bytes" if k == "bytes" else k
        val = format_bytes(v) if k == "bytes" else v
        print(f"  {label:<20}: {val}")
    print("=" * 60 + "\n")


def cmd_mkdir(args):
    client = get_client(args.config)
    folder = client.create_folder(args.name, parent_folder_key=args.parent)
    print(f"[✓] Created folder: {folder.object_name} | Key: {folder.object_key}")


def cmd_rename(args):
    client = get_client(args.config)
    res = client.rename_object(args.key, args.new_name, is_folder=args.dir)
    print(f"[✓] Rename requested for {args.key} -> '{args.new_name}'")


def cmd_move(args):
    client = get_client(args.config)
    res = client.move_object(args.key, args.dest_folder)
    print(f"[✓] Move requested: {args.key} -> folder {args.dest_folder}")


def cmd_fav(args):
    client = get_client(args.config)
    client.set_favorite(args.keys, favorite=not args.remove)
    verb = "removed from" if args.remove else "added to"
    print(f"[✓] {len(args.keys)} object(s) {verb} favorites.")


def cmd_trash(args):
    client = get_client(args.config)
    res = client.delete_to_trash(args.keys)
    n = len(res.get("objects", [])) if isinstance(res, dict) else "?"
    print(f"[✓] Moved to trash ({n} confirmed).")


def cmd_restore(args):
    client = get_client(args.config)
    res = client.restore_from_trash(args.keys)
    n = len(res.get("objects", [])) if isinstance(res, dict) else "?"
    print(f"[✓] Restored ({n} confirmed).")


def cmd_trash_list(args):
    client = get_client(args.config)
    items = client.list_trash(limit=args.limit)
    hdr = f"\nTrash ({len(items)} items)\n" + "-" * 100
    _emit(items, args.format, hdr)
    if args.format == "table":
        print("-" * 100)


def cmd_share(args):
    client = get_client(args.config)
    link = client.create_share_link(args.keys, share_name=args.name)
    print(f"[✓] Share link ({len(args.keys)} object(s)):")
    print(f"    URL: {link.share_url}")


def cmd_versions(args):
    client = get_client(args.config)
    versions = client.get_version_history(args.key)
    print(f"\nVersion history ({len(versions)}) for {args.key}:")
    for v in versions:
        cur = " (current)" if v.is_current else ""
        print(f"  {v.display_version or v.version_number}{cur} | created {v.created_datetime} by {v.created_by_name or '?'}")


def cmd_recent(args):
    client = get_client(args.config)
    data = client.get_recent_objects()
    imgs = data.get("objectsImgs", [])
    docs = data.get("objectsDocs", [])
    print(f"\nRecent activity — images: {len(imgs)}, docs: {len(docs)}")
    for o in (imgs + docs)[:args.limit]:
        size = format_bytes(o.get("sizeInBytes", 0))
        print(f"  - {o.get('objectName')} ({size}) key={o.get('objectKey')}")


def cmd_boards(args):
    client = get_client(args.config)
    if args.action == "list":
        boards = client.list_boards()
        print(f"\nBoards ({len(boards)}):")
        for b in boards:
            print(f"  - {b.board_name} [{b.board_key}] files={b.files_count} images={b.image_count} videos={b.video_count}")
    elif args.action == "create":
        b = client.create_board(args.name, args.description or "")
        print(f"[✓] Board created: {b.board_name} [{b.board_key}]")
    elif args.action == "members":
        members = client.get_board_members(args.board)
        print(f"Board {args.board} members ({len(members)}):")
        for m in members:
            role = "OWNER" if m.member_type == "O" else m.member_type
            print(f"  - {m.first_name} ({role})")


def cmd_contacts(args):
    client = get_client(args.config)
    contacts = client.get_contacts()
    emails = client.get_contact_emails()
    print(f"\nContacts: {len(contacts)} | Shared-contact emails: {len(emails)}")
    for c in contacts[:args.limit]:
        print(f"  - {c.get('displayName', c.get('name', '?'))}")


def cmd_promotions(args):
    client = get_client(args.config)
    promo = client.get_promotions()
    active = promo.get("activePromotions", [])
    print(f"\nActive promotions: {len(active)} | Expired: {len(promo.get('expiredPromotions', []))}")
    for p in active:
        print(f"  - {json.dumps(p)[:120]}")


def cmd_agent(args):
    """
    JSON tool-calling mode for AI agents.
      stdin pipeline : echo '{"tool":"account_info"}' | python cli.py agent call -
      one-shot       : python cli.py agent call '{"tool":"list_files","arguments":{"limit":5}}'
      schema         : python cli.py agent schema
      MCP-style loop : python cli.py agent serve
    """
    bridge = JioAgentBridge(client=get_client(args.config))

    if args.agent_cmd == "schema":
        print(json.dumps(AGENT_TOOLS_SCHEMA, indent=2))
        return

    if args.agent_cmd == "serve":
        import jiocloud.agent_tools as at
        at.JioAgentBridge_instance = bridge  # inject configured client
        original_init = at.JioAgentBridge.__init__

        def _patched(self, client=None, config_path="config.json"):
            self.client = bridge.client
        at.JioAgentBridge.__init__ = _patched
        sys.exit(at.serve_stdio())

    payload = args.payload
    if payload == "-":
        payload = sys.stdin.read()
    result = handle_tool_call(payload, bridge)
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Unofficial Jio AI Cloud CLI Tool (personal backup & data portability)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--config", "-c", default="config.json", help="Path to config.json file")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # info
    p = subparsers.add_parser("info", help="View account details and storage quota")
    p.add_argument("--devices", action="store_true", help="Also list registered devices")
    p.set_defaults(func=cmd_info)

    # list
    p = subparsers.add_parser("list", help="List files and folders")
    p.add_argument("--folder", "-f", default=None, help="Folder key (defaults to root)")
    p.add_argument("--limit", "-l", type=int, default=50, help="Max items per page")
    p.add_argument("--type", choices=["files", "folders"], default="files",
                   help="Server accepts only 'f' (files) or 'w' (folders)")
    p.add_argument("--sort", default="-lastModifiedDate", help="e.g. +objectName, -fileCreatedDate")
    p.add_argument("--endpoint", choices=["defaultview", "legacy"], default="defaultview")
    p.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p.set_defaults(func=cmd_list)

    # tree
    p = subparsers.add_parser("tree", help="Recursive tree view of a folder subtree")
    p.add_argument("--folder", "-f", default=None, help="Folder key (defaults to root)")
    p.add_argument("--depth", type=int, default=None, help="Max recursion depth")
    p.set_defaults(func=cmd_tree)

    # search
    p = subparsers.add_parser("search", help="Search files across the whole account")
    p.add_argument("query", help="Search keyword")
    p.add_argument("--ext", help="Filter by extension (pdf, docx…)")
    p.add_argument("--max", type=int, default=50, help="Table rows to show")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_search)

    # download
    p = subparsers.add_parser("download", help="Download single file by object key")
    p.add_argument("key", help="Object Key GUID of the file")
    p.add_argument("--dest", "-d", default="./", help="Destination file path or directory")
    p.set_defaults(func=cmd_download)

    # sync
    p = subparsers.add_parser("sync", help="Bulk parallel sync/download all files")
    p.add_argument("--dest", "-d", default="./jiocloud_backup")
    p.add_argument("--ext", help="Filter download by extension")
    p.add_argument("--workers", "-w", type=int, default=4)
    p.add_argument("--no-skip", action="store_true", help="Re-download even if local copy exists")
    p.set_defaults(func=cmd_sync)

    # mkdir
    p = subparsers.add_parser("mkdir", help="Create a new folder")
    p.add_argument("name")
    p.add_argument("--parent", help="Parent folder key (defaults to root)")
    p.set_defaults(func=cmd_mkdir)

    # rename
    p = subparsers.add_parser("rename", help="Rename a file/folder")
    p.add_argument("key")
    p.add_argument("new_name")
    p.add_argument("--dir", action="store_true", help="Target is a folder")
    p.set_defaults(func=cmd_rename)

    # move
    p = subparsers.add_parser("move", help="Move an object into another folder")
    p.add_argument("key")
    p.add_argument("dest_folder", help="Destination folder key")
    p.set_defaults(func=cmd_move)

    # favorite
    p = subparsers.add_parser("favorite", help="Add/remove favorites")
    p.add_argument("keys", nargs="+")
    p.add_argument("--remove", action="store_true", help="Remove instead of add")
    p.set_defaults(func=cmd_fav)

    # trash / restore
    p = subparsers.add_parser("trash", help="Move item(s) to trash")
    p.add_argument("keys", nargs="+")
    p.set_defaults(func=cmd_trash)

    p = subparsers.add_parser("restore", help="Restore item(s) from trash")
    p.add_argument("keys", nargs="+")
    p.set_defaults(func=cmd_restore)

    p = subparsers.add_parser("trash-list", help="List trashed items")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p.set_defaults(func=cmd_trash_list)

    # share
    p = subparsers.add_parser("share", help="Generate public share link(s)")
    p.add_argument("keys", nargs="+", help="Object key(s)")
    p.add_argument("--name", help="Share name (defaults to timestamp)")
    p.set_defaults(func=cmd_share)

    # versions
    p = subparsers.add_parser("versions", help="File version history")
    p.add_argument("key")
    p.set_defaults(func=cmd_versions)

    # recent
    p = subparsers.add_parser("recent", help="Recent files feed")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_recent)

    # boards
    p = subparsers.add_parser("boards", help="Shared boards/albums: list|create|members")
    p.add_argument("action", choices=["list", "create", "members"])
    p.add_argument("--name", help="Board name (create)")
    p.add_argument("--description", help="Board description (create)")
    p.add_argument("--board", help="Board key (members)")
    p.set_defaults(func=cmd_boards)

    # contacts
    p = subparsers.add_parser("contacts", help="Cloud address book summary")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_contacts)

    # promotions
    p = subparsers.add_parser("promotions", help="Storage promotions status")
    p.set_defaults(func=cmd_promotions)

    # agent
    p = subparsers.add_parser("agent", help="AI-agent JSON tool interface: schema|call|serve")
    p.add_argument("agent_cmd", choices=["schema", "call", "serve"])
    p.add_argument("payload", nargs="?", default=None, help="JSON tool-call ('-' = stdin)")
    p.set_defaults(func=cmd_agent)

    args = parser.parse_args()
    if hasattr(args, "func"):
        try:
            args.func(args)
        except JioCloudError as e:
            print(f"\n[!] Jio Cloud Error: {e}", file=sys.stderr)
            sys.exit(1)
        except FileExistsError as e:
            print(f"\n[!] {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n[!] Unexpected Error: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
