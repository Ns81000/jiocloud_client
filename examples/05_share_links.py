#!/usr/bin/env python3
"""
Example 05: Public Share Link Generator
Demonstrates generating universal public sharing links (ulinks) for files or folders.
"""

import sys
from pathlib import Path

sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud import JioCloudClient

def main():
    config_file = sdk_root / "config.json"
    client = JioCloudClient.from_config(str(config_file))

    # Get first available file
    files = client.list_files(limit=1)
    if not files:
        print("No files available to share.")
        return

    target_file = files[0]
    print(f"Target File: {target_file.object_name} (Key: {target_file.object_key})")
    
    print("\nGenerating Public Share Link...")
    share_link = client.create_share_link(target_file.object_key)
    
    print("\n[✓] Share Link Generated Successfully!")
    print(f"  Public URL : {share_link.share_url}")
    print(f"  Share Nonce: {share_link.nonce}")

if __name__ == "__main__":
    main()
