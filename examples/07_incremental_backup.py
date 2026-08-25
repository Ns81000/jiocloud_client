#!/usr/bin/env python3
"""
Example 07 — Incremental Backup & Restore Utility
Practical batch workflow:
  1. Builds a local manifest (JSON) of every cloud file: key, name, size, hash.
  2. Downloads only files that are new or changed vs. the previous manifest.
  3. Optionally prunes local copies of files deleted from the cloud.

UNOFFICIAL PROJECT — personal backup / data-portability use only.
Not affiliated with Reliance Jio Infocomm Ltd. See DISCLAIMER.md.

Usage:
    python examples/07_incremental_backup.py ./backup_dir [--prune] [--dry-run]
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jiocloud import JioCloudClient, format_bytes


def load_manifest(backup_dir: Path) -> dict:
    mf = backup_dir / ".jiocloud_manifest.json"
    if mf.exists():
        return json.loads(mf.read_text(encoding="utf-8"))
    return {}


def save_manifest(backup_dir: Path, manifest: dict):
    mf = backup_dir / ".jiocloud_manifest.json"
    tmp = mf.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    tmp.replace(mf)


def safe_local_path(base: Path, cloud_name: str, object_key: str) -> Path:
    target = base / cloud_name
    if target.exists():
        stem, suffix = target.stem, target.suffix
        target = base / f"{stem}_{object_key[:8]}{suffix}"
    return target


def main():
    ap = argparse.ArgumentParser(description="Incremental Jio Cloud backup utility")
    ap.add_argument("backup_dir")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--ext", help="Only back up this extension (e.g. pdf)")
    ap.add_argument("--prune", action="store_true", help="Delete local copies missing from cloud")
    ap.add_argument("--dry-run", action="store_true", help="Show plan without downloading")
    args = ap.parse_args()

    client = JioCloudClient.from_config(args.config)
    base = Path(args.backup_dir)
    base.mkdir(parents=True, exist_ok=True)

    print("Cataloguing cloud account…")
    cloud_files = client.list_all_files()
    if args.ext:
        e = args.ext if args.ext.startswith(".") else "." + args.ext
        cloud_files = [f for f in cloud_files if f.extension.lower() == e.lower()]
    print(f"  {len(cloud_files)} file(s) in scope")

    old_manifest = load_manifest(base)
    new_manifest = {}

    to_download = []
    for f in cloud_files:
        entry = {
            "name": f.object_name,
            "size": f.size_bytes,
            "hash": f.hash_md5,
            "modified": f.modified_timestamp_ms,
        }
        new_manifest[f.object_key] = entry
        prev = old_manifest.get(f.object_key)
        if prev is None or prev.get("hash") != f.hash_md5 or prev.get("size") != f.size_bytes:
            to_download.append(f)

    total_bytes = sum(f.size_bytes for f in to_download)
    mode = "[DRY-RUN] would download" if args.dry_run else "downloading"
    print(f"{mode} {len(to_download)} new/changed file(s), {format_bytes(total_bytes)}")

    if not args.dry_run:
        ok = fail = skipped = 0
        got = 0
        for i, f in enumerate(to_download, 1):
            dest = safe_local_path(base, f.object_name, f.object_key)
            try:
                if not args.dry_run and dest.exists() and dest.stat().st_size == f.size_bytes:
                    skipped += 1          # identical size already present; keep copy
                else:
                    client.download_file(f.object_key, dest, overwrite=True)
                    got += f.size_bytes
                ok += 1
                print(f"  [{i}/{len(to_download)}] ✓ {f.object_name}")
            except Exception as e:
                fail += 1
                print(f"  [{i}/{len(to_download)}] ✗ {f.object_name}: {e}")
        print(f"\nDone: {ok} ok ({skipped} kept identical), {fail} failed, {format_bytes(got)} transferred")
        if fail == 0:
            save_manifest(base, new_manifest)
            print("Manifest updated:", base / ".jiocloud_manifest.json")

    if args.prune:
        cloud_keys = set(new_manifest.keys())
        pruned = 0
        for local in old_manifest.keys():
            if local not in cloud_keys:
                # find its file by stored name pattern
                matches = list(base.glob(f"*{old_manifest[local]['name']}*"))
                for m in matches:
                    if m.name != ".jiocloud_manifest.json":
                        if not args.dry_run:
                            m.unlink()
                        pruned += 1
                        print(f"  prune: {m.name}")
        print(f"Pruned {pruned} orphaned local file(s)" + (" [DRY-RUN]" if args.dry_run else ""))


if __name__ == "__main__":
    main()
