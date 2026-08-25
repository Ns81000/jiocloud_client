#!/usr/bin/env python3
"""
Example 03: Fast Multi-Threaded Batch Downloader
Demonstrates downloading multiple files simultaneously from Jio Cloud CDN.
"""

import sys
from pathlib import Path

sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud import JioCloudClient, format_bytes

def main():
    config_file = sdk_root / "config.json"
    client = JioCloudClient.from_config(str(config_file))
    download_dir = sdk_root / "downloads_sample"

    print("Fetching files to download...")
    files = client.list_files(limit=3)

    print(f"\nDownloading {len(files)} files to {download_dir}...")
    for f in files:
        target_path = download_dir / f.object_name
        print(f"Downloading '{f.object_name}' ({f.human_size})...")
        
        def _on_progress(done, total):
            sys.stdout.write(f"\r  Downloaded: {format_bytes(done)} / {format_bytes(total)}")
            sys.stdout.flush()

        client.download_file(f.object_key, target_path, progress_callback=_on_progress)
        print(f"\n  [✓] Saved to: {target_path}")

if __name__ == "__main__":
    main()
