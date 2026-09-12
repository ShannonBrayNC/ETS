from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate4_restore import (
    AUTHORIZATION_PHRASE,
    _canonical_entities,
    _entity_args,
    _load_protected_workspace,
    _prepare_workspace,
    _sha256_file,
    _verify_restore_identity_scopes,
    gate4,
)
from scripts.azure_migration_prefix_preflight import _validated_state


def _sample_entities() -> list[dict[str, object]]:
    event_id = "event-001"
    return [
        {
            "PartitionKey": "ets-live-primary",
            "RowKey": "meta",
            "kind": "metadata",
            "next_index": 1,
            "schema_version": 1,
            "log_id": "ets-live-primary",
            "Timestamp": "2026-09-12T00:00:00Z",
            "Timestamp@odata.type": "Edm.DateTime",
            "etag": "W/\"datetime'ignored'\"",
            "@odata.etag": "W/\"datetime'ignored-too'\"",
        },
        {
            "PartitionKey": "ets-live-primary",
            "RowKey": "entry-00000000000000000000",
            "kind": "entry",
            "log_index": 0,
            "event_json": '{"event_id":"event-001"}',
            "event_hash": "a" * 64,
            "leaf_hash": "b" * 64,
        },
        {
            "PartitionKey": "ets-live-primary",
            "RowKey": (
                "event-"
                f"{hashlib.sha256(event_id.encode()).hexdigest()}"
            ),
            "kind": "event_index",
            "log_index": 0,
            "event_id": event_id,
        },
    ]


def _write_workspace(tmp_path: Path) -> tuple[Path, str]:
    workspace = tmp_path / "protected"
    gateway = workspace / "gateway"
    gateway.mkdir(parents=True)

    entities = _sample_entities()
    table_path = workspace / "ETSEvents.full.json"
    table_path.write_text(
        json.dumps(entities, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    canonical = _canonical_entities(entities)
    state = _validated_state(canonical)

    files = []
    total_bytes = 0
    for name, payload in (
        ("connector-runtime.db", b"connector"),
        ("gateway-events.db", b"events"),
        ("gateway-sync.db", b"sync"),
    ):
        path = gateway / name
        path.write_bytes(payload)
        files.append(
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        total_bytes += len(payload)

    manifest = {
        "manifest_version": 1,
        "gate": 3,
        "claim": "non_final_source_export_integrity_proof",
        "source_fenced": False,
        "final_copy": False,
        "destination_write_performed": False,
        "source_mutation_performed": False,
        "protected_bytes_uploaded": False,
        "evidence": {
            "entity_count": state["entity_count"],
            "next_index": state["next_index"],
            "payload_sha256": _sha256_file(table_path),
            "metadata_digest": state["metadata_digest"],
            "pair_digests": state["pair_digests"],
        },
        "gateway": {
            "file_count": len(files),
            "total_bytes": total_bytes,
            "files": files,
        },
    }
    manifest_path = workspace / "gate3-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return workspace, _sha256_file(manifest_path)


def test_prepare_workspace_rejects_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "repo"
    protected = checkout / "protected"
    protected.mkdir(parents=True)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(checkout))
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore.shutil.which",
        lambda _: "/usr/bin/az",
    )

    with pytest.raises(
        MigrationControlError,
        match="outside the repository checkout",
    ):
        _prepare_workspace(protected)


def test_load_workspace_verifies_manifest_payload_and_gateway(
    tmp_path: Path,
) -> None:
    workspace, digest = _write_workspace(tmp_path)

    manifest, entities, files = _load_protected_workspace(
        workspace,
        digest,
    )

    assert manifest["evidence"]["next_index"] == 1
    assert len(entities) == 3
    assert len(files) == 3
    assert all(
        "Timestamp" not in entity
        and "Timestamp@odata.type" not in entity
        and "etag" not in entity
        and "@odata.etag" not in entity
        for entity in entities
    )


def test_load_workspace_rejects_table_tamper(tmp_path: Path) -> None:
    workspace, digest = _write_workspace(tmp_path)
    (workspace / "ETSEvents.full.json").write_text(
        "[]\n",
        encoding="utf-8",
    )

    with pytest.raises(
        MigrationControlError,
        match="Table payload SHA-256 mismatch",
    ):
        _load_protected_workspace(workspace, digest)


def test_load_workspace_rejects_gateway_tamper(tmp_path: Path) -> None:
    workspace, digest = _write_workspace(tmp_path)
    (workspace / "gateway" / "gateway-sync.db").write_bytes(b"tampered")

    with pytest.raises(
        MigrationControlError,
        match="does not match manifest",
    ):
        _load_protected_workspace(workspace, digest)


def test_load_workspace_rejects_gateway_extra_directory(
    tmp_path: Path,
) -> None:
    workspace, digest = _write_workspace(tmp_path)
    (workspace / "gateway" / "unexpected").mkdir()

    with pytest.raises(
        MigrationControlError,
        match="invalid out-of-manifest entry",
    ):
        _load_protected_workspace(workspace, digest)


def test_canonical_entities_reject_duplicate_keys() -> None:
    entity = {
        "PartitionKey": "p",
        "RowKey": "r",
        "kind": "metadata",
    }
    with pytest.raises(
        MigrationControlError,
        match="duplicate entity keys",
    ):
        _canonical_entities([entity, dict(entity)])


def test_entity_args_preserve_app_odata_and_strip_server_fields() -> None:
    args = _entity_args(
        {
            "PartitionKey": "p",
            "RowKey": "r",
            "count": 9223372036854775807,
            "count@odata.type": "Edm.Int64",
            "enabled": True,
            "Timestamp": "ignored",
            "Timestamp@odata.type": "Edm.DateTime",
            "@odata.etag": "ignored",
        }
    )

    assert "count=9223372036854775807" in args
    assert "count@odata.type=Edm.Int64" in args
    assert "enabled=true" in args
    assert all(not item.startswith("Timestamp=") for item in args)
    assert all(not item.startswith("Timestamp@odata.type=") for item in args)
    assert all(not item.startswith("@odata.etag=") for item in args)


def test_verify_restore_identity_requires_exact_three_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = "sub"
    rg = "rg-ets-prod-eastus"
    core = "etscore"
    gateway = "etsgwstate"
    table = "ETSEvents"
    share = "ets-gateway-state-q1-v2"
    base = f"/subscriptions/{subscription}/resourceGroups/{rg}"
    table_scope = (
        f"{base}/providers/Microsoft.Storage/storageAccounts/{core}"
        f"/tableServices/default/tables/{table}"
    )
    share_scope = (
        f"{base}/providers/Microsoft.Storage/storageAccounts/{gateway}"
        f"/fileServices/default/shares/{share}"
    )
    responses = iter(
        [
            {"user": {"name": "restore-principal"}},
            [
                {"role": "Reader", "scope": base},
                {
                    "role": "Storage Table Data Contributor",
                    "scope": table_scope,
                },
                {
                    "role": "Storage File Data Privileged Contributor",
                    "scope": share_scope,
                },
            ],
        ]
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore.az_json",
        lambda _args: next(responses),
    )

    _verify_restore_identity_scopes(
        subscription,
        rg,
        core,
        gateway,
        table,
        share,
    )


def test_verify_restore_identity_rejects_broad_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            {"user": {"name": "restore-principal"}},
            [
                {
                    "role": "Contributor",
                    "scope": "/subscriptions/sub",
                }
            ],
        ]
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore.az_json",
        lambda _args: next(responses),
    )

    with pytest.raises(
        MigrationControlError,
        match="forbidden broad administrative role",
    ):
        _verify_restore_identity_scopes(
            "sub",
            "rg",
            "core",
            "gateway",
            "ETSEvents",
            "share",
        )


def _patch_plan_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entities = _canonical_entities(_sample_entities())
    state = _validated_state(entities)
    manifest = {
        "evidence": {
            "entity_count": state["entity_count"],
            "next_index": state["next_index"],
            "metadata_digest": state["metadata_digest"],
            "pair_digests": state["pair_digests"],
        },
        "gateway": {"file_count": 3},
    }
    files = [
        {
            "name": "connector-runtime.db",
            "size": 1,
            "sha256": "a" * 64,
        },
        {
            "name": "gateway-events.db",
            "size": 1,
            "sha256": "b" * 64,
        },
        {
            "name": "gateway-sync.db",
            "size": 1,
            "sha256": "c" * 64,
        },
    ]
    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg")
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "share")
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._load_protected_workspace",
        lambda *_args: (manifest, entities, files),
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore.destination_preflight",
        Mock(return_value={}),
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._discover_storage_accounts",
        Mock(return_value=("core", "gateway")),
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore."
        "_verify_restore_identity_scopes",
        Mock(return_value=None),
    )


def test_plan_mode_performs_no_destination_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plan_dependencies(monkeypatch)
    table_write = Mock(
        side_effect=AssertionError("table write must not run")
    )
    gateway_write = Mock(
        side_effect=AssertionError("gateway write must not run")
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._restore_table",
        table_write,
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._restore_gateway",
        gateway_write,
    )

    result = gate4(tmp_path, "d" * 64, "sub", False, "")

    assert result["mode"] == "plan-only"
    assert result["destination_write_performed"] is False
    table_write.assert_not_called()
    gateway_write.assert_not_called()


def test_apply_mode_requires_exact_authorization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plan_dependencies(monkeypatch)
    table_write = Mock()
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._restore_table",
        table_write,
    )

    with pytest.raises(
        MigrationControlError,
        match="authorization phrase is missing",
    ):
        gate4(tmp_path, "d" * 64, "sub", True, "wrong")

    table_write.assert_not_called()


def test_apply_mode_runs_restore_and_post_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plan_dependencies(monkeypatch)
    table_write = Mock()
    gateway_write = Mock()
    table_verify = Mock()
    gateway_verify = Mock()
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._restore_table",
        table_write,
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._restore_gateway",
        gateway_write,
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._verify_restored_table",
        table_verify,
    )
    monkeypatch.setattr(
        "scripts.azure_migration_gate4_restore._verify_gateway",
        gateway_verify,
    )

    result = gate4(
        tmp_path,
        "d" * 64,
        "sub",
        True,
        AUTHORIZATION_PHRASE,
    )

    assert result["mode"] == "apply"
    assert result["destination_write_performed"] is True
    table_write.assert_called_once()
    gateway_write.assert_called_once()
    table_verify.assert_called_once()
    gateway_verify.assert_called_once()


def test_gate4_write_workflow_is_intentionally_absent() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (
        root
        / ".github"
        / "workflows"
        / "azure-migration-gate4-restore.yml"
    )
    assert not workflow.exists()
