#!/usr/bin/env python3
"""
Example 08 — Account Inventory Export (CSV + JSON) & Storage Analytics
Batch workflow that produces a full, offline-searchable inventory of the
account: every file with keys, sizes, types and dates — plus per-extension
analytics. Output feeds directly into spreadsheets / data pipelines.

UNOFFICIAL PROJECT — personal backup / data-portability use only.
Not affiliated with Reliance Jio Infocomm Ltd. See DISCLAIMER.md.

Usage:
    python examples/08_inventory_export.py [--out inventory] [--config config.json]
"""

import sys
import csv
import json
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from jiocloud import JioCloudClient, format_bytes


def main():
    ap = argparse.ArgumentParser(description="Full account inventory export")
    ap.add_argument("--out", default="jiocloud_inventory", help="Output file basename")
    ap.add_argument("--config", default="config.json")
    args = ap.parse_args()

    client = JioCloudClient.from_config(args.config)

    profile = client.get_user_profile()
    quota = profile.quota
    print(f"Account : {profile.name} <{profile.email}>")
    print(f"Quota   : {quota.total_used_gb:.2f}/{quota.total_allocated_gb:.2f} GB "
          f"({quota.usage_percentage:.1f}%)\n")

    print("Streaming full file catalogue…")
    files = client.list_all_files()
    print(f"  {len(files)} files found\n")

    # --- CSV export -----------------------------------------------------------
    csv_path = Path(args.out + ".csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["object_key", "name", "extension", "size_bytes", "human_size",
                    "mime", "created", "modified", "favorite", "download_url"])
        for f in files:
            w.writerow([f.object_key, f.object_name, f.extension, f.size_bytes,
                        f.human_size, f"{f.mime_type}/{f.mime_subtype}",
                        f.created_datetime, f.modified_datetime, f.is_favorite,
                        f.download_url_direct])
    print(f"CSV written   : {csv_path}")

    # --- JSON export ----------------------------------------------------------
    json_path = Path(args.out + ".json")
    json_path.write_text(
        json.dumps({
            "exported_at": str(__import__("datetime").datetime.now()),
            "account": {"user_id": profile.user_id, "email": profile.email},
            "quota": {
                "allocated_bytes": quota.total_allocated_bytes,
                "used_bytes": quota.total_used_bytes,
                "documents": quota.document_usage_bytes,
                "photos": quota.photo_usage_bytes,
                "videos": quota.video_usage_bytes,
                "audio": quota.audio_usage_bytes
            },
            "file_count": len(files),
            "files": [f.raw_data for f in files]
        }, indent=1),
        encoding="utf-8"
    )
    print(f"JSON written  : {json_path}")

    # --- Analytics ------------------------------------------------------------
    by_ext = Counter()
    bytes_by_ext = Counter()
    for f in files:
        e = f.extension or "(none)"
        by_ext[e] += 1
        bytes_by_ext[e] += f.size_bytes

    print("\nTop formats by count:")
    for e, n in by_ext.most_common(10):
        print(f"  {e:<10} {n:>6} files  ({format_bytes(bytes_by_ext[e])})")

    largest = sorted(files, key=lambda f: f.size_bytes, reverse=True)[:10]
    print("\n10 largest files:")
    for f in largest:
        print(f"  {format_bytes(f.size_bytes):>9}  {f.object_name[:60]}")


if __name__ == "__main__":
    main()
