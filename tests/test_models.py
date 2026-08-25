"""
Unit tests for Jio Cloud SDK models and parsers.
"""

import unittest
import sys
from pathlib import Path

sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))

from jiocloud.models import (
    JioUserProfile,
    JioStorageQuota,
    JioFile,
    JioFolder,
    JioShareLink,
    format_bytes
)

class TestJioModels(unittest.TestCase):

    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1048576), "1.00 MB")
        self.assertEqual(format_bytes(1073741824), "1.00 GB")

    def test_quota_model(self):
        data = {
            "totalAllocatedQuota": 107374182400,
            "totalUsedQuota": 41748935616,
            "documentUsage": 41215505637,
            "videoUsage": 437175192,
            "photoUsage": 82024811,
            "audioUsage": 14229976
        }
        quota = JioStorageQuota.from_dict(data)
        self.assertAlmostEqual(quota.total_allocated_gb, 100.00, places=2)
        self.assertAlmostEqual(quota.total_used_gb, 38.88, places=2)
        self.assertAlmostEqual(quota.usage_percentage, 38.88, places=1)

    def test_file_model(self):
        data = {
            "objectKey": "24074a0d843347ac880c3c113847ba6a",
            "parentObjectKey": "20E0E5275DFE2C23E063441618ACCF27",
            "objectType": "FE",
            "objectName": "Test_Document.pdf",
            "mimeType": "application",
            "mimeSubType": "pdf",
            "sizeInBytes": 1048576,
            "sourceFolder": "/storage/emulated/0/Download",
            "hash": "fac4d46c2beaaa1764c865def4513ad5",
            "fileCreatedDate": 1787335460068,
            "lastModifiedDate": 1787340352185,
            "status": "A"
        }
        f = JioFile.from_dict(data)
        self.assertTrue(f.is_file)
        self.assertFalse(f.is_folder)
        self.assertEqual(f.extension, ".pdf")
        self.assertEqual(f.human_size, "1.00 MB")
        self.assertEqual(f.object_name, "Test_Document.pdf")
        self.assertIn("24074a0d843347ac880c3c113847ba6a", f.download_url_direct)

    def test_folder_model(self):
        data = {
            "objectKey": "5985F022E2320359E063E31718AC27A5",
            "parentObjectKey": "20E0E5275DFE2C23E063441618ACCF27",
            "objectType": "FR",
            "objectName": "Work",
            "status": "A",
            "createdDate": 1787599206739
        }
        folder = JioFolder.from_dict(data)
        self.assertEqual(folder.object_name, "Work")
        self.assertTrue(folder.is_folder)
        self.assertEqual(folder.object_key, "5985F022E2320359E063E31718AC27A5")

    def test_share_link_model(self):
        # Verified production shape: shareURL with u=<nonce> token
        link = JioShareLink.from_dict(
            ["my_key"],
            {"shareURL": "https://www.jioaicloud.com/l/?u=abcdef-123456"})
        self.assertEqual(link.nonce, "abcdef-123456")
        self.assertEqual(link.share_url,
                         "https://www.jioaicloud.com/l/?u=abcdef-123456")

if __name__ == "__main__":
    unittest.main()
