from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate4_gateway_writer as gateway_writer
from scripts.azure_migration_control import MigrationControlError


def _file(name: str, payload: bytes) -> dict[str, object]:
    return {
        "name": name,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _source_files() -> list[dict[str, object]]:
    return [
        _file("connector-runtime.db", b"runtime"),
        _file("gateway-events.db", b"events"),
        _file("gateway-sync.db", b"source"),
    ]


def _patch_common_boundary(
    monkeypatch: pytest.MonkeyPatch,
    source_files: list[dict[str, object]],
) -> None:
    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg-destination")
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "gateway-share")
    monkeypatch.setattr(
        gateway_writer,
        "_load_protected_workspace",
        lambda *_args: (
            {"gateway": {"file_count": 3}},
            [],
            source_files,
        ),
    )
    monkeypatch.setattr(gateway_writer, "_verify_zero_replicas", lambda _rg: None)
    monkeypatch.setattr(
        gateway_writer,
        "_discover_storage_accounts",
        lambda _rg: ("coreaccount", "gatewayaccount"),
    )
    monkeypatch.setattr(
        gateway_writer,
        "_verify_restore_identity_scopes",
        lambda *_args: None,
    )


def test_wrong_authorization_performs_no_boundary_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        gateway_writer,
        "_load_protected_workspace",
        Mock(side_effect=AssertionError("protected workspace must not be read")),
    )

    with pytest.raises(MigrationControlError, match="authorization phrase"):
        gateway_writer.apply_gateway_snapshot(
            tmp_path,
            "a" * 64,
            "subscription",
            tmp_path / "rollback",
            "wrong",
        )


def test_source_must_be_exact_three_durable_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = [_file("gateway-sync.db", b"source")]
    _patch_common_boundary(monkeypatch, source)

    with pytest.raises(MigrationControlError, match="exact durable file set"):
        gateway_writer.apply_gateway_snapshot(
            tmp_path,
            "a" * 64,
            "subscription",
            tmp_path / "rollback",
            gateway_writer.AUTHORIZATION_PHRASE,
        )


def test_happy_path_backs_up_then_overwrites_only_divergent_file_and_sidecars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _source_files()
    _patch_common_boundary(monkeypatch, source)
    events: list[str] = []
    rollback = tmp_path / "operator-rollback"

    monkeypatch.setattr(gateway_writer, "_verify_gateway_files", lambda *_args: 5)
    monkeypatch.setattr(
        gateway_writer,
        "_list_gateway_names",
        lambda *_args: {
            "connector-runtime.db",
            "gateway-events.db",
            "gateway-sync.db",
            "gateway-sync.db-shm",
            "gateway-sync.db-wal",
        },
    )
    monkeypatch.setattr(
        gateway_writer,
        "_prepare_rollback_workspace",
        lambda *_args: rollback,
    )

    def snapshot(*_args: object) -> dict[str, int]:
        events.append("rollback")
        return {"file_count": 5, "total_bytes": 1234}

    monkeypatch.setattr(
        gateway_writer,
        "_snapshot_destination_for_rollback",
        snapshot,
    )
    destination_before = [
        source[0],
        source[1],
        _file("gateway-sync.db", b"target"),
        _file("gateway-sync.db-shm", b"shm"),
        _file("gateway-sync.db-wal", b""),
    ]
    monkeypatch.setattr(
        gateway_writer,
        "_capture_file_hashes",
        Mock(side_effect=[destination_before, source]),
    )

    writes: list[list[str]] = []

    def record_write(args: list[str], _label: str) -> None:
        events.append("write")
        writes.append(args)

    monkeypatch.setattr(gateway_writer, "_run_az_write", record_write)

    result = gateway_writer.apply_gateway_snapshot(
        tmp_path,
        "a" * 64,
        "subscription",
        rollback,
        gateway_writer.AUTHORIZATION_PHRASE,
    )

    assert events[0] == "rollback"
    uploads = [args for args in writes if "upload" in args]
    deletes = [args for args in writes if "delete" in args]
    assert len(uploads) == 1
    assert "gateway-sync.db" in uploads[0]
    assert len(deletes) == 2
    assert {args[-1] for args in deletes} == {
        "gateway-sync.db-shm",
        "gateway-sync.db-wal",
    }
    assert result["rollback_files_captured"] == 5
    assert result["durable_files_overwritten"] == 1
    assert result["sidecars_removed"] == 2
    assert result["gateway_files_verified"] == 3
    assert result["gateway_write_performed"] is True
    assert result["table_write_performed"] is False
    assert result["writer_activation_performed"] is False
    assert result["source_mutation_performed"] is False
    assert result["cutover_performed"] is False


def test_exact_destination_without_sidecars_performs_no_gateway_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _source_files()
    _patch_common_boundary(monkeypatch, source)
    rollback = tmp_path / "operator-rollback"

    monkeypatch.setattr(gateway_writer, "_verify_gateway_files", lambda *_args: 3)
    monkeypatch.setattr(
        gateway_writer,
        "_list_gateway_names",
        lambda *_args: {
            "connector-runtime.db",
            "gateway-events.db",
            "gateway-sync.db",
        },
    )
    monkeypatch.setattr(
        gateway_writer,
        "_prepare_rollback_workspace",
        lambda *_args: rollback,
    )
    monkeypatch.setattr(
        gateway_writer,
        "_snapshot_destination_for_rollback",
        lambda *_args: {"file_count": 3, "total_bytes": 100},
    )
    monkeypatch.setattr(
        gateway_writer,
        "_capture_file_hashes",
        Mock(side_effect=[source, source]),
    )
    write = Mock(side_effect=AssertionError("no Azure write expected"))
    monkeypatch.setattr(gateway_writer, "_run_az_write", write)

    result = gateway_writer.apply_gateway_snapshot(
        tmp_path,
        "a" * 64,
        "subscription",
        rollback,
        gateway_writer.AUTHORIZATION_PHRASE,
    )

    assert result["durable_files_overwritten"] == 0
    assert result["sidecars_removed"] == 0
    assert result["gateway_write_performed"] is False
    write.assert_not_called()


def test_sidecar_policy_failure_occurs_before_rollback_or_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _source_files()
    _patch_common_boundary(monkeypatch, source)
    monkeypatch.setattr(
        gateway_writer,
        "_verify_gateway_files",
        Mock(side_effect=MigrationControlError("non-zero WAL")),
    )
    rollback = Mock(side_effect=AssertionError("rollback must not begin"))
    write = Mock(side_effect=AssertionError("write must not begin"))
    monkeypatch.setattr(gateway_writer, "_prepare_rollback_workspace", rollback)
    monkeypatch.setattr(gateway_writer, "_run_az_write", write)

    with pytest.raises(MigrationControlError, match="non-zero WAL"):
        gateway_writer.apply_gateway_snapshot(
            tmp_path,
            "a" * 64,
            "subscription",
            tmp_path / "rollback",
            gateway_writer.AUTHORIZATION_PHRASE,
        )

    rollback.assert_not_called()
    write.assert_not_called()


def test_rollback_workspace_cannot_be_inside_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "repo"
    checkout.mkdir()
    monkeypatch.setenv("GITHUB_WORKSPACE", str(checkout))

    with pytest.raises(MigrationControlError, match="outside the repository checkout"):
        gateway_writer._prepare_rollback_workspace(
            checkout / "rollback",
            tmp_path / "protected-source",
        )


def test_module_has_no_cli_or_workflow_dispatch_path() -> None:
    source = inspect.getsource(gateway_writer)

    assert "argparse" not in source
    assert "__main__" not in source
    assert "workflow_dispatch" not in source
    assert "containerapp update" not in source
    assert "role assignment create" not in source
    assert "storage entity insert" not in source
