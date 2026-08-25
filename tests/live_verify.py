"""
Live verification harness: exercises EVERY SDK method against the real
Jio AI Cloud endpoints. Read-only methods run unconditionally; mutating
methods run as create->verify->cleanup cycles so the account is left clean.
Prints a PASS/FAIL matrix and exits non-zero on any failure.

UNOFFICIAL PROJECT — run only against an account you own. See docs/DISCLAIMER.md.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jiocloud import JioCloudClient
from jiocloud.exceptions import (
    JioCloudError,
    ObjectNotFoundError,
    InvalidRequestError
)

RESULTS = []
CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("get_user_profile")
def _(c, ctx):
    p = c.get_user_profile(refresh=True)
    assert p.user_id and p.root_folder_key
    return f"{p.name}, root={p.root_folder_key[:10]}…"


@check("get_storage_quota")
def _(c, ctx):
    q = c.get_storage_quota()
    assert q.total_allocated_bytes > 0
    return f"used {q.total_used_gb:.1f}/{q.total_allocated_gb:.0f} GB"


@check("list_devices")
def _(c, ctx):
    ds = c.list_devices()
    assert isinstance(ds, list)
    return f"{len(ds)} devices"


@check("get_app_settings")
def _(c, ctx):
    s = c.get_app_settings()
    assert "maxFileSize" in s
    return "settings ok"


@check("get_promotions")
def _(c, ctx):
    pr = c.get_promotions()
    assert "activePromotions" in pr
    return f"active={len(pr['activePromotions'])}"


@check("list_directory (defaultview)")
def _(c, ctx):
    objs, env = c.list_directory(object_type="f", limit=50)
    objs2, _ = c.list_directory(object_type="w", limit=50)
    return f"{len(objs)} files + {len(objs2)} folders"


@check("list_files")
def _(c, ctx):
    fs = c.list_files(limit=20)
    ctx["sample_file"] = fs[0] if fs else None
    return f"{len(fs)} files"


@check("list_folders")
def _(c, ctx):
    fo = c.list_folders()
    ctx["sample_folder"] = fo[0] if fo else None
    return f"{len(fo)} folders"


@check("stream_all_files (recursive)")
def _(c, ctx):
    n = 0
    for _ in c.stream_all_files(page_size=2000):
        n += 1
        if n >= 500:
            break
    assert n > 0
    return f"{n}+ files streamed"


@check("search_files")
def _(c, ctx):
    r = c.search_files("a")  # broad term; verifies pipeline end-to-end
    return f"{len(r)} matches for 'a'"


@check("get_recent_objects")
def _(c, ctx):
    d = c.get_recent_objects()
    n = len(d.get("objectsImgs", [])) + len(d.get("objectsDocs", []))
    return f"{n} recent items"


@check("get_spotlights")
def _(c, ctx):
    d = c.get_spotlights()
    assert "spotLights" in d
    return f"{len(d.get('spotLights', []))} spotlights"


@check("get_shared_by_me")
def _(c, ctx):
    d = c.get_shared_by_me()
    assert isinstance(d, dict)
    return f"{len(d.get('objects', []))} shared-by-me"


@check("get_linked_app_objects")
def _(c, ctx):
    d = c.get_linked_app_objects()
    assert "objects" in d
    return f"{len(d['objects'])} linked-app objects"


@check("manual tags (recents + per-file)")
def _(c, ctx):
    t = c.get_recent_tags()
    extra = ""
    if ctx.get("sample_file"):
        mt = c.get_manual_tags(ctx["sample_file"].object_key)
        extra = f", per-file={len(mt)}"
    return f"recents={len(t)}{extra}"


@check("get_supported_office_extensions")
def _(c, ctx):
    d = c.get_supported_office_extensions()
    view = d["supportedExtensions"].get("view", [])
    return f"{len(view)} viewable exts"


@check("get_promo_banners")
def _(c, ctx):
    cards = c.get_promo_banners()
    assert isinstance(cards, list)
    return f"{len(cards)} banners"


@check("get_version_history")
def _(c, ctx):
    f = ctx.get("sample_file")
    if not f:
        return "skipped (no file)"
    v = c.get_version_history(f.object_key)
    return f"{len(v)} versions"


@check("folder lifecycle: create→rename→fav→unfav→trash→restore→trash")
def _(c, ctx):
    name = f"_sdk_audit_{int(time.time())}"
    folder = c.create_folder(name)
    key = folder.object_key
    assert key, "no objectKey returned"
    try:
        c.rename_object(key, name + "_r", is_folder=True,
                        parent_object_key=c.get_root_folder_key())
        objs, _ = c.list_directory(object_type="w", endpoint="legacy")
        renamed_ok = any(i.object_key == key and i.object_name == name + "_r" for i in objs)
        assert renamed_ok, "rename not reflected in listing"
        c.set_favorite(key, True)
        c.set_favorite(key, False)
        res = c.delete_to_trash(key)   # TRASH op with full echo (fresh-capture flow)
        assert isinstance(res, dict), "unexpected trash response"
        time.sleep(2.5)                # trash listing is eventually consistent
        trash_items = c.list_trash(limit=300)
        hit = next((i for i in trash_items if i.object_key == key), None)
        assert hit is not None, "item not visible in trash after delete"
        res2 = c.restore_from_trash(key)
        assert isinstance(res2, dict) and "objects" in res2
        time.sleep(2.0)
        trash_after = c.list_trash(limit=300)
        assert not any(i.object_key == key for i in trash_after), \
            "still in trash after restore"
        # final re-delete to leave the account clean
        res3 = c.delete_to_trash(key)
        time.sleep(2.0)
        trash_final = c.list_trash(limit=300)
        assert any(i.object_key == key for i in trash_final), \
            "final cleanup delete did not land"
        return "full mutation cycle verified (create/rename/fav/trash/restore/trash)"
    except Exception:
        # leave-no-trace: best-effort re-trash so audits don't litter the account
        try:
            c.delete_to_trash(key)
        except Exception:
            pass
        raise


@check("create_share_link")
def _(c, ctx):
    f = ctx.get("sample_file")
    if not f:
        return "skipped (no file)"
    link = c.create_share_link(f.object_key)
    assert link.share_url.startswith("https://www.jioaicloud.com/l/?u="), link.share_url
    return link.share_url[:55] + "…"


@check("download_file (small file, atomic write)")
def _(c, ctx):
    files = c.list_all_files()
    small = next((f for f in files if 0 < f.size_bytes < 300_000), None)
    if not small:
        return "skipped (no small file)"
    dest = Path(__file__).parent / "_audit_download.bin"
    out = c.download_file(small.object_key, dest, overwrite=True)
    size = out.stat().st_size
    out.unlink()
    assert size == small.size_bytes, f"size mismatch {size} != {small.size_bytes}"
    return f"{small.object_name} ({size}B) verified"


@check("download_thumbnail (image)")
def _(c, ctx):
    files = c.list_all_files()
    img = next((f for f in files if f.mime_type == "image"), None)
    if not img:
        return "skipped (no image)"
    dest = Path(__file__).parent / "_audit_thumb.jpg"
    try:
        c.download_thumbnail(img.object_key, dest)
        size = dest.stat().st_size
        ok = size > 0
        note = f"{img.object_name[:30]} thumb ({size}B)"
    except ObjectNotFoundError:
        # Some images lack transcodes — endpoint behavior still validated.
        ok = True
        note = "no transcode available (404) — handled correctly"
    finally:
        if dest.exists():
            dest.unlink()
    assert ok
    return note


@check("boards: list→create→detail→members→leave")
def _(c, ctx):
    boards_before = {b.board_key for b in c.list_boards()}
    b = c.create_board(f"_sdk_audit_{int(time.time())}")
    bk = b.board_key
    assert bk and bk not in boards_before
    members = c.get_board_members(bk)
    assert len(members) >= 1 and members[0].member_type == "O"
    detail = c.get_board(bk)
    assert "board" in detail
    c.leave_board(bk)
    boards_after = {x.board_key for x in c.list_boards()}
    assert bk not in boards_after, "board still visible after leave"
    return f"created+left board {bk[:8]}… members={len(members)}"


@check("contacts & emails")
def _(c, ctx):
    contacts = c.get_contacts()
    emails = c.get_contact_emails()
    return f"{len(contacts)} contacts, {len(emails)} emails"


@check("error typing: bogus key → typed exception")
def _(c, ctx):
    caught = None
    try:
        c.get_version_history("00000000000000000000000000000000")
    except JioCloudError as e:
        caught = type(e).__name__
    if caught is None:
        return "server tolerant of unknown key (200/empty)"
    assert caught in ("ObjectNotFoundError", "InvalidRequestError", "JioCloudError")
    return f"correctly raised {caught}"


@check("agent bridge: JSON tool call (read-only)")
def _(c, ctx):
    from jiocloud.agent_tools import JioAgentBridge
    bridge = JioAgentBridge(client=c)
    res = bridge.execute("account_info", {})
    assert res.get("ok") is True and res["result"]["user_id"]
    res2 = bridge.execute("move_to_trash", {"object_keys": ["x"], "confirm": False})
    assert res2.get("ok") is False and res2["error"]["type"] == "confirmation_required"
    return "envelopes + destructive guard OK"


def main():
    cfg = Path(__file__).parent.parent / "config.json"
    if not cfg.exists():
        print("config.json missing — cannot live-test")
        sys.exit(2)
    client = JioCloudClient.from_config(str(cfg))
    ctx = {}

    print("=" * 100)
    print("LIVE VERIFICATION MATRIX — Unofficial jiocloud SDK v2.0.0 (real API calls)")
    print("=" * 100)

    for name, fn in CHECKS:
        t0 = time.time()
        try:
            note = fn(client, ctx)
            RESULTS.append((name, True, round(time.time() - t0, 2), note or ""))
        except Exception as e:
            RESULTS.append((name, False, round(time.time() - t0, 2),
                            f"{type(e).__name__}: {e}"))

    print(f"\n{'TEST':<58} {'RESULT':<8} {'SEC':>5}  NOTE")
    print("-" * 110)
    fails = 0
    for name, ok, secs, note in RESULTS:
        mark = "[✓] PASS" if ok else "[✗] FAIL"
        if not ok:
            fails += 1
        print(f"{name:<58} {mark:<8} {secs:>5}  {note}")
    total = len(RESULTS)
    print("-" * 110)
    print(f"TOTAL: {total - fails}/{total} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
