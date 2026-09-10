"""Safety tests for bounded destination managed-identity name discovery."""

import os
import unittest
from unittest.mock import patch

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_identity_names import read_identity_names


class MigrationIdentityNameTests(unittest.TestCase):
    def test_reads_only_names_and_sorts_them(self) -> None:
        calls: list[list[str]] = []

        def read(args: list[str]):
            calls.append(args)
            return ["ets-z-gw-id", "ets-a-spo-id"]

        with patch.dict(os.environ, {"MIGRATION_RESOURCE_GROUP": "rg-test"}, clear=True):
            with patch("scripts.azure_migration_identity_names.az_json", side_effect=read):
                names = read_identity_names()

        self.assertEqual(names, ["ets-a-spo-id", "ets-z-gw-id"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ["identity", "list"])
        self.assertIn("[].name", calls[0])
        forbidden = {"create", "delete", "update", "set", "assign", "start", "stop"}
        self.assertFalse(any(token in forbidden for token in calls[0]))

    def test_rejects_non_name_payload(self) -> None:
        with patch.dict(os.environ, {"MIGRATION_RESOURCE_GROUP": "rg-test"}, clear=True):
            with patch(
                "scripts.azure_migration_identity_names.az_json",
                return_value=[{"name": "ets-spo-id", "clientId": "sensitive"}],
            ):
                with self.assertRaisesRegex(MigrationControlError, "invalid shape"):
                    read_identity_names()

    def test_rejects_output_unsafe_name(self) -> None:
        with patch.dict(os.environ, {"MIGRATION_RESOURCE_GROUP": "rg-test"}, clear=True):
            with patch(
                "scripts.azure_migration_identity_names.az_json",
                return_value=["ets-ok-id", "bad\nname"],
            ):
                with self.assertRaisesRegex(MigrationControlError, "safe for public output"):
                    read_identity_names()

    def test_rejects_empty_inventory(self) -> None:
        with patch.dict(os.environ, {"MIGRATION_RESOURCE_GROUP": "rg-test"}, clear=True):
            with patch("scripts.azure_migration_identity_names.az_json", return_value=[]):
                with self.assertRaisesRegex(MigrationControlError, "empty or invalid"):
                    read_identity_names()


if __name__ == "__main__":
    unittest.main()
