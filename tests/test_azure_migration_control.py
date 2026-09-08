"""Safety tests for the bounded Azure migration OIDC control."""

import os
import unittest
from unittest.mock import patch

from scripts.azure_migration_control import MigrationControlError, inventory, verify_context

TENANT = "11111111-1111-1111-1111-111111111111"
SUBSCRIPTION = "22222222-2222-2222-2222-222222222222"
ACCOUNT = {"id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled"}


class MigrationControlTests(unittest.TestCase):
    def test_context_mismatch_fails_closed(self) -> None:
        wrong = {**ACCOUNT, "tenantId": SUBSCRIPTION}
        with patch("scripts.azure_migration_control.az_json", return_value=wrong):
            with self.assertRaisesRegex(MigrationControlError, "mismatch"):
                verify_context(TENANT, SUBSCRIPTION)

    def test_inventory_uses_read_only_azure_commands(self) -> None:
        env = {
            "MIGRATION_RESOURCE_GROUP": "rg-test",
            "MIGRATION_CORE_STORAGE_ACCOUNT": "corestore",
            "MIGRATION_GATEWAY_STORAGE_ACCOUNT": "gatewaystore",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "state",
        }
        calls: list[list[str]] = []

        def read(args: list[str]):
            calls.append(args)
            if args[:2] == ["resource", "list"]:
                return [{"type": "Microsoft.Storage/storageAccounts"}]
            if args[:3] == ["storage", "entity", "query"]:
                return {
                    "items": [
                        {"kind": "metadata", "next_index": 1},
                        {"kind": "entry", "log_index": 0},
                        {"kind": "event_index", "log_index": 0},
                    ]
                }
            if args[:3] == ["storage", "file", "list"]:
                return [{"name": "gateway.db"}]
            raise AssertionError(args)

        with patch.dict(os.environ, env, clear=False):
            with patch("scripts.azure_migration_control.az_json", side_effect=read):
                result = inventory()

        self.assertEqual(result["resource_count"], 1)
        self.assertEqual(result["evidence_entities"], 3)
        self.assertEqual(result["gateway_root_entries"], 1)
        forbidden = {"create", "delete", "update", "set", "start", "stop", "restart"}
        self.assertFalse(any(any(token in forbidden for token in call) for call in calls))

    def test_data_plane_failure_is_sanitized_and_incomplete(self) -> None:
        env = {
            "MIGRATION_RESOURCE_GROUP": "rg-test",
            "MIGRATION_CORE_STORAGE_ACCOUNT": "corestore",
            "MIGRATION_GATEWAY_STORAGE_ACCOUNT": "gatewaystore",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "state",
        }

        def read(args: list[str]):
            if args[:2] == ["resource", "list"]:
                return []
            raise MigrationControlError("SENSITIVE PROVIDER DETAIL")

        with patch.dict(os.environ, env, clear=False):
            with patch("scripts.azure_migration_control.az_json", side_effect=read):
                result = inventory()

        self.assertEqual(result["evidence_status"], "blocked")
        self.assertEqual(result["gateway_status"], "blocked")
        self.assertNotIn("SENSITIVE", str(result))


if __name__ == "__main__":
    unittest.main()
