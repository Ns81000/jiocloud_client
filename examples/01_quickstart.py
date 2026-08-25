#!/usr/bin/env python3
"""
Example 01: Quickstart & Account Overview
Demonstrates connecting to Jio AI Cloud and reading user profile and storage quota.
"""

import sys
from pathlib import Path

# Add SDK root to python path
sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud import JioCloudClient, format_bytes

def main():
    config_file = sdk_root / "config.json"
    print(f"Connecting to Jio Cloud using: {config_file}")
    client = JioCloudClient.from_config(str(config_file))

    profile = client.get_user_profile()
    print("\n--- User Profile ---")
    print(f"Name      : {profile.name}")
    print(f"Email     : {profile.email}")
    print(f"Phone     : {profile.mobile_number}")
    print(f"Root Key  : {profile.root_folder_key}")

    quota = profile.quota
    print("\n--- Storage Quota ---")
    print(f"Total Quota : {quota.total_allocated_gb:.2f} GB")
    print(f"Total Used  : {quota.total_used_gb:.2f} GB ({quota.usage_percentage:.1f}%)")
    print(f"  - Documents: {format_bytes(quota.document_usage_bytes)}")
    print(f"  - Videos   : {format_bytes(quota.video_usage_bytes)}")
    print(f"  - Photos   : {format_bytes(quota.photo_usage_bytes)}")
    print(f"  - Audio    : {format_bytes(quota.audio_usage_bytes)}")

if __name__ == "__main__":
    main()
