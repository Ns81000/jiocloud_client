"""
Integration tests for JioCloudClient against live API endpoints.
"""

import unittest
import sys
from pathlib import Path

sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud import JioCloudClient

class TestJioClientIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config_path = sdk_root / "config.json"
        if not config_path.exists():
            raise unittest.SkipTest("config.json not found, skipping live integration tests.")
        cls.client = JioCloudClient.from_config(str(config_path))

    def test_01_user_profile(self):
        profile = self.client.get_user_profile()
        self.assertIsNotNone(profile.user_id)
        self.assertTrue(len(profile.user_id) > 10)
        self.assertTrue(profile.quota.total_allocated_bytes > 0)
        print(f"\n[Test 1] User: {profile.name}, Quota: {profile.quota.total_allocated_gb:.2f} GB")

    def test_02_list_files(self):
        files = self.client.list_files(limit=5)
        self.assertTrue(len(files) > 0)
        first_file = files[0]
        self.assertIsNotNone(first_file.object_key)
        self.assertIsNotNone(first_file.object_name)
        print(f"[Test 2] First file: {first_file.object_name} ({first_file.human_size})")

    def test_03_list_folders(self):
        folders = self.client.list_folders()
        self.assertIsInstance(folders, list)
        print(f"[Test 3] Subfolders count: {len(folders)}")

    def test_04_trash_list(self):
        trash = self.client.list_trash(limit=5)
        self.assertIsInstance(trash, list)
        print(f"[Test 4] Trash items count: {len(trash)}")

    def test_05_create_share_link(self):
        files = self.client.list_files(limit=1)
        if files:
            link = self.client.create_share_link(files[0].object_key)
            self.assertTrue(link.share_url.startswith("https://www.jioaicloud.com/"))
            print(f"[Test 5] Generated Share URL: {link.share_url}")

if __name__ == "__main__":
    unittest.main()
