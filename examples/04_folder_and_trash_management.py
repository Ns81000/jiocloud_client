#!/usr/bin/env python3
"""
Example 04: Folder Creation & Trash Management
Demonstrates creating cloud folders, renaming, favoriting, listing trash,
moving items to trash, and restoring.

UNOFFICIAL PROJECT — personal backup / data-portability use only.
Not affiliated with Reliance Jio Infocomm Ltd. See docs/DISCLAIMER.md.
"""

import sys
import time
from pathlib import Path

sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud import JioCloudClient


def main():
    config_file = sdk_root / "config.json"
    client = JioCloudClient.from_config(str(config_file))

    # 1. List top-level folders
    print("1. Listing top-level folders...")
    folders = client.list_folders()
    for f in folders:
        print(f"  - Folder: {f.object_name} (Key: {f.object_key})")

    # 2. Create a demo folder (full lifecycle, cleaned up afterwards)
    demo_name = "_example_demo"
    print(f"\n2. Creating folder '{demo_name}'...")
    folder = client.create_folder(demo_name)
    print(f"   Created: {folder.object_name} | Key: {folder.object_key}")
    time.sleep(2)

    try:
        # 3. Rename it
        new_name = "_example_demo_renamed"
        client.rename_object(folder.object_key, new_name, is_folder=True)
        time.sleep(2)
        print(f"3. Renamed to '{new_name}'")

        # 4. Favorite + unfavorite
        client.set_favorite(folder.object_key, True)
        client.set_favorite(folder.object_key, False)
        print("4. Favorited then unfavorited")

        # 5. Move to trash
        res = client.delete_to_trash(folder.object_key)
        if res.get("unprocessed"):
            raise RuntimeError("trash rejected — see docs/KNOWN_ISSUES.md")
        print("5. Moved to trash; waiting for trash listing to update…")
        deadline = time.time() + 90
        while time.time() < deadline:
            time.sleep(6)
            if any(i.object_key == folder.object_key
                   for i in client.list_trash(limit=300)):
                print("   ✓ visible in trash")
                break

        # 6. Restore from trash
        client.restore_from_trash(folder.object_key)
        time.sleep(4)
        still_there = any(i.object_key == folder.object_key
                          for i in client.list_trash(limit=300))
        print(f"6. Restored from trash (still listed: {still_there})")
    finally:
        # 7. Cleanup — leave the account as we found it
        print("7. Cleaning up (final trash)…")
        client.delete_to_trash(folder.object_key)


if __name__ == "__main__":
    main()
