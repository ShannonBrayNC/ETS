"""Safety tests for the read-only Azure migration Gate 3 export control."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate3_export import (
    _prepare_workspace,
    _safe_root_name,
    _write_private_json,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "azure_migration_gate3_export.py"
WORKFLOW = (
    ROOT / ".github" / "workflows" / "azure-migration-gate3-source-export.yml"
)


class Gate3ExportControlTests(unittest.TestCase):
    def test_gateway_root_names_reject_path_escape(self) -> None:
        for value in ("", ".", "..", "../secret", "dir/file", "dir\\file"):
            with self.subTest(value=value):
                with self.assertRaises(MigrationControlError):
                    _safe_root_name(value)
        self.assertEqual(_safe_root_name("gateway-sync.db"), "gateway-sync.db")

    def test_protected_workspace_must_be_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp) / "checkout"
            checkout.mkdir()
            with patch.dict(os.environ, {"GITHUB_WORKSPACE": str(checkout)}):
                with self.assertRaises(MigrationControlError):
                    _prepare_workspace(checkout / "protected")

    def test_private_json_is_not_world_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "protected.json"
            _write_private_json(path, {"ok": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_export_script_is_source_read_only_and_nonfinal(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8").lower()
        self.assertIn('"source_fenced": false', text)
        self.assertIn('"final_copy": false', text)
        self.assertIn('"destination_write_performed": false', text)
        self.assertIn('"source_mutation_performed": false', text)
        self.assertIn('"protected_bytes_uploaded": false', text)
        self.assertIn('"storage",\n            "entity",\n            "query"', text)
        self.assertIn('"storage",\n            "file",\n            "download"', text)
        self.assertIn('"--auth-mode",\n            "login"', text)
        self.assertIn('"--backup-intent"', text)

        forbidden = (
            '"entity", "insert"',
            '"entity", "merge"',
            '"entity", "replace"',
            '"entity", "delete"',
            '"file", "upload"',
            '"file", "delete"',
            '"file", "copy"',
            "containerapp update",
            "role assignment create",
        )
        for token in forbidden:
            self.assertNotIn(token, text)

    def test_workflow_is_manual_source_only_and_ephemeral(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("\n  push:", text)
        self.assertIn("environment: ets-azure-migration-destination-restore", text)
        self.assertIn("SOURCE_AZURE_CLIENT_ID", text)
        self.assertIn("azure_migration_gate3_export", text)
        self.assertIn("$RUNNER_TEMP/ets-gate3-source", text)
        self.assertNotIn("${{ runner.temp }}", text)
        self.assertIn('rm -rf -- "$GATE3_WORKSPACE"', text)
        self.assertIn("source fenced: `false`", text)
        self.assertIn("final copy: `false`", text)
        self.assertNotIn("client-id: ${{ vars.AZURE_CLIENT_ID }}", text)
        self.assertNotIn("rg-ets-prod-eastus", text)

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
            self.assertNotIn(token, lower)


if __name__ == "__main__":
    unittest.main()
