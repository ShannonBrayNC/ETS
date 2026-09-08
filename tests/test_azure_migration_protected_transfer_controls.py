"""Static safety tests for protected cross-tenant migration controls."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_BOOTSTRAP = ROOT / "scripts" / "azure_migration_source_transfer_oidc_bootstrap.sh"
TRANSFER_PREFLIGHT = (
    ROOT / ".github" / "workflows" / "azure-migration-protected-transfer-preflight.yml"
)


class ProtectedTransferControlTests(unittest.TestCase):
    def test_source_transfer_identity_is_read_only(self) -> None:
        text = SOURCE_BOOTSTRAP.read_text(encoding="utf-8")

        self.assertIn("Storage Table Data Reader", text)
        self.assertIn("Storage File Data Privileged Reader", text)
        self.assertIn('ensure_role "$principal_id" "Reader" "$live_rg_id"', text)
        self.assertNotIn("Storage Table Data Contributor", text)
        self.assertNotIn("Storage File Data Privileged Contributor", text)
        self.assertNotIn('ensure_role "$principal_id" "Contributor"', text)
        self.assertIn(
            "repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-restore",
            text,
        )

    def test_transfer_preflight_contains_no_data_transfer_action(self) -> None:
        text = TRANSFER_PREFLIGHT.read_text(encoding="utf-8")

        self.assertIn("environment: ets-azure-migration-destination-restore", text)
        self.assertIn("azure_migration_control", text)
        self.assertIn("azure_migration_restore_preflight", text)
        forbidden = (
            "actions/upload-artifact",
            "actions/download-artifact",
            "storage entity insert",
            "storage entity merge",
            "storage entity replace",
            "storage file upload",
            "storage copy",
            "containerapp update",
            "containerapp revision activate",
        )
        for token in forbidden:
            self.assertNotIn(token, text.lower())


if __name__ == "__main__":
    unittest.main()
