#!/usr/bin/env python3
"""
Example 02: List & Search Files
Demonstrates fetching files, streaming through pages, and searching by keyword/extension.
"""

import sys
from pathlib import Path

sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud import JioCloudClient

def main():
    config_file = sdk_root / "config.json"
    client = JioCloudClient.from_config(str(config_file))

    print("Fetching the 10 most recent files...")
    recent_files = client.list_files(limit=10)
    for i, f in enumerate(recent_files, 1):
        print(f"  {i:02d}. {f.object_name} ({f.human_size}) - Ext: {f.extension}")

    print("\nSearching for files containing 'pdf' or 'report'...")
    results = client.search_files("report", filter_extension=".pdf")
    print(f"Found {len(results)} matching PDF files:")
    for f in results[:5]:
        print(f"  - {f.object_name} ({f.human_size}) | Key: {f.object_key}")

if __name__ == "__main__":
    main()
