"""Safety tests for the bounded Azure migration OIDC control."""

import os
import unittest
from unittest.mock import patch

from scripts.azure_migration_control import (
    MigrationControlError,
    inventory,
    verify_context,
)

TENANT = "11111111-1111-1111-1111-111111111111"
SUBSCRIPTION = "22222222-2222-2222-2222-222222222222"
ACCOUNT = {"id": SUBSCRIPTION, "tenantId": TENANT, "state": "Enabled"}


class MigrationControlTests(unittest.TestCase):
    def test_context_mismatch_fails_closed(self) -> None:
        wrong = {**ACCOUNT, "tenantId": SUBSCRIPTION}
        with patch("scripts.azure_migration_control.az_json", return_value=wrong):
            with self.assertRaisesRegex(MigrationControlError, "mismatch"):
                verify_context(TENANT, SUBSCRIPTION)

    def test_inventory_discovers_storage_and_uses_read_only_commands(self) -> None:
        env = {
            "MIGRATION_RESOURCE_GROUP": "rg-test",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "state",
        }
        calls: list[list[str]] = []

        def read(args: list[str]):
            calls.append(args)
            if args[:2] == ["resource", "list"]:
                return [
                    {"name": "corestore", "type": "Microsoft.Storage/storageAccounts"},
                    {"name": "etsgwstate", "type": "Microsoft.Storage/storageAccounts"},
                    {"name": "lanternbackup", "type": "Microsoft.Storage/storageAccounts"},
                ]
            if args[:2] == ["account", "show"]:
                return {"user": {"name": "client-id"}}
            if args[:3] == ["role", "assignment", "list"]:
                return [
                    {
                        "role": "Reader",
                        "scope": "/subscriptions/s/resourceGroups/rg-test",
                    },
                    {
                        "role": "Storage Table Data Reader",
                        "scope": (
                            "/subscriptions/s/resourceGroups/rg-test/providers/"
                            "Microsoft.Storage/storageAccounts/corestore"
                        ),
                    },
                ]
            if args[:3] == ["storage", "entity", "query"]:
                self.assertIn("corestore", args)
                return {
                    "items": [
                        {"kind": "metadata", "next_index": 1},
                        {"kind": "entry", "log_index": 0},
                        {"kind": "event_index", "log_index": 0},
                    ]
                }
            if args[:3] == ["storage", "file", "list"]:
                self.assertIn("etsgwstate", args)
                return [{"name": "gateway.db"}]
            raise AssertionError(args)

        with patch.dict(os.environ, env, clear=True):
            with patch("scripts.azure_migration_control.az_json", side_effect=read):
                result = inventory()

        self.assertEqual(result["resource_count"], 3)
        self.assertEqual(result["evidence_entities"], 3)
        self.assertEqual(result["gateway_root_entries"], 1)
        self.assertEqual(result["rbac_status"], "ok")
        self.assertEqual(result["rbac_roles"]["Reader"], {"resource_group": 1})
        forbidden = {"create", "delete", "update", "set", "start", "stop", "restart"}
        self.assertFalse(any(any(token in forbidden for token in call) for call in calls))

    def test_data_plane_failure_is_sanitized_and_incomplete(self) -> None:
        env = {
            "MIGRATION_RESOURCE_GROUP": "rg-test",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "state",
        }

        def read(args: list[str]):
            if args[:2] == ["resource", "list"]:
                return [
                    {"name": "corestore", "type": "Microsoft.Storage/storageAccounts"},
                    {"name": "etsgwstate", "type": "Microsoft.Storage/storageAccounts"},
                ]
            raise MigrationControlError("SENSITIVE PROVIDER DETAIL")

        with patch.dict(os.environ, env, clear=True):
            with patch("scripts.azure_migration_control.az_json", side_effect=read):
                result = inventory()

        self.assertEqual(result["rbac_status"], "blocked")
        self.assertEqual(result["evidence_status"], "blocked")
        self.assertEqual(result["gateway_status"], "blocked")
        self.assertNotIn("SENSITIVE", str(result))


if __name__ == "__main__":
    unittest.main()
