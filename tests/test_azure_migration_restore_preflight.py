"""Safety tests for the Azure migration restore preflight."""

import os
import unittest
from unittest.mock import patch

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_restore_preflight import preflight


class RestorePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = {
            "MIGRATION_RESOURCE_GROUP": "rg-destination",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "ets-gateway-state-q1-v2",
        }

    @staticmethod
    def _healthy_read(args: list[str]):
        if args[:2] == ["containerapp", "list"]:
            return [
                {"name": "core", "min": 0, "max": 1},
                {"name": "gateway", "min": 0, "max": 1},
            ]
        if args[:3] == ["containerapp", "replica", "list"]:
            return []
        if args[:2] == ["resource", "list"]:
            return [
                {"name": "corestore"},
                {"name": "etsgwstate"},
            ]
        if args[:3] == ["storage", "entity", "query"]:
            return {
                "items": [
                    {
                        "PartitionKey": "log-test",
                        "RowKey": "meta",
                        "kind": "metadata",
                        "next_index": 0,
                        "schema_version": 1,
                        "log_id": "ets-live-primary",
                    }
                ]
            }
        if args[:3] == ["storage", "file", "list"]:
            return [
                {"name": "connector-runtime.db"},
                {"name": "gateway-events.db"},
                {"name": "gateway-sync.db"},
            ]
        raise AssertionError(args)

    def test_preflight_accepts_fenced_initialization_state(self) -> None:
        calls: list[list[str]] = []

        def read(args: list[str]):
            calls.append(args)
            return self._healthy_read(args)

        with patch.dict(os.environ, self.env, clear=True):
            with patch(
                "scripts.azure_migration_restore_preflight.az_json",
                side_effect=read,
            ):
                result = preflight()

        self.assertEqual(result["evidence_entities"], 1)
        self.assertEqual(result["metadata_next_index"], 0)
        self.assertEqual(result["gateway_root_entries"], 3)
        forbidden = {"create", "delete", "update", "set", "start", "stop", "restart"}
        self.assertFalse(any(any(token in forbidden for token in call) for call in calls))

    def test_preflight_rejects_nonzero_replica_fence(self) -> None:
        def read(args: list[str]):
            if args[:2] == ["containerapp", "list"]:
                return [
                    {"name": "core", "min": 1, "max": 1},
                    {"name": "gateway", "min": 0, "max": 1},
                ]
            return self._healthy_read(args)

        with patch.dict(os.environ, self.env, clear=True):
            with patch(
                "scripts.azure_migration_restore_preflight.az_json",
                side_effect=read,
            ):
                with self.assertRaisesRegex(MigrationControlError, "scale fence"):
                    preflight()

    def test_preflight_rejects_changed_evidence_state(self) -> None:
        def read(args: list[str]):
            if args[:3] == ["storage", "entity", "query"]:
                return {
                    "items": [
                        {
                            "RowKey": "meta",
                            "kind": "metadata",
                            "next_index": 1,
                            "schema_version": 1,
                            "log_id": "ets-live-primary",
                        },
                        {"RowKey": "entry-0", "kind": "entry"},
                    ]
                }
            return self._healthy_read(args)

        with patch.dict(os.environ, self.env, clear=True):
            with patch(
                "scripts.azure_migration_restore_preflight.az_json",
                side_effect=read,
            ):
                with self.assertRaisesRegex(MigrationControlError, "initialization-only"):
                    preflight()

    def test_preflight_rejects_changed_gateway_files(self) -> None:
        def read(args: list[str]):
            if args[:3] == ["storage", "file", "list"]:
                return [
                    {"name": "connector-runtime.db"},
                    {"name": "gateway-events.db"},
                    {"name": "gateway-sync.db"},
                    {"name": "unexpected.db"},
                ]
            return self._healthy_read(args)

        with patch.dict(os.environ, self.env, clear=True):
            with patch(
                "scripts.azure_migration_restore_preflight.az_json",
                side_effect=read,
            ):
                with self.assertRaisesRegex(MigrationControlError, "file set changed"):
                    preflight()


if __name__ == "__main__":
    unittest.main()
