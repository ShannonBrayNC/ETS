"""Safety boundaries for the offline migration discovery utility."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.azure_migration_discover import collect

TENANT = "11111111-1111-1111-1111-111111111111"
SUBSCRIPTION = "22222222-2222-2222-2222-222222222222"
ACCOUNT = {"id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled"}


class DiscoverySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_wrong_tenant_stops_before_resource_reads_or_output(self):
        output = self.root / "discovery"
        wrong = {**ACCOUNT, "tenantId": SUBSCRIPTION}
        with patch("scripts.azure_migration_discover.az_json", return_value=wrong) as azure:
            with self.assertRaisesRegex(RuntimeError, "mismatch"):
                collect(TENANT, SUBSCRIPTION, output)
        self.assertEqual(azure.call_count, 1)
        self.assertFalse(output.exists())

    def test_existing_capture_cannot_be_overwritten(self):
        with patch("scripts.azure_migration_discover.az_json", return_value=ACCOUNT) as azure:
            with self.assertRaises(FileExistsError):
                collect(TENANT, SUBSCRIPTION, self.root)
        self.assertEqual(azure.call_count, 1)

    def test_capture_in_git_working_tree_is_rejected(self):
        (self.root / ".git").mkdir()
        with patch("scripts.azure_migration_discover.az_json") as azure:
            with self.assertRaisesRegex(ValueError, "outside a Git"):
                collect(TENANT, SUBSCRIPTION, self.root / "capture")
        azure.assert_not_called()

    def test_forbidden_read_is_incomplete_and_does_not_leak_error(self):
        def read(args):
            if args[:2] == ["account", "show"]:
                return ACCOUNT
            raise RuntimeError("SENSITIVE PROVIDER DETAIL")

        output = self.root / "discovery"
        with patch("scripts.azure_migration_discover.az_json", side_effect=read):
            self.assertFalse(collect(TENANT, SUBSCRIPTION, output))
        content = (output / "manifest.json").read_text()
        self.assertNotIn("SENSITIVE", content)
        manifest = json.loads(content)
        self.assertFalse(manifest["discovery_reads_complete"])
        self.assertEqual(manifest["credit_entitlement"], "UNVERIFIED")
        self.assertTrue(all(row["status"] == "blocked" for row in manifest["reads"].values()))
