from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

import scripts.azure_migration_gateway_equivalence as gateway_eq
from scripts.azure_migration_control import MigrationControlError


def _file(name: str, payload: bytes) -> dict[str, object]:
    return {
        "name": name,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _manifest(files: list[dict[str, object]]) -> dict[str, object]:
    return {
        "manifest_version": 1,
        "claim": "ephemeral_source_gateway_byte_manifest",
        "file_count": len(files),
        "total_bytes": sum(int(item["size"]) for item in files),
        "files": files,
    }


def _write_manifest(path: Path, files: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(_manifest(files)), encoding="utf-8")


def _set_destination_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg-destination")
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "gateway-share")
    monkeypatch.setattr(gateway_eq, "_verify_zero_replicas", lambda _rg: None)
    monkeypatch.setattr(
        gateway_eq,
        "_discover_storage_accounts",
        lambda _rg: ("coreaccount", "gatewayaccount"),
    )
    monkeypatch.setattr(
        gateway_eq,
        "_verify_restore_identity_scopes",
        lambda *_args: None,
    )


def test_read_manifest_rejects_duplicate_names(tmp_path: Path) -> None:
    payload = b"abc"
    item = _file("gateway-sync.db", payload)
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, [item, item])

    with pytest.raises(MigrationControlError, match="duplicate names"):
        gateway_eq._read_manifest(manifest_path)


def test_verify_destination_accepts_exact_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    files = [
        _file("connector-runtime.db", b"one"),
        _file("gateway-events.db", b"two"),
        _file("gateway-sync.db", b"three"),
    ]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, files)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(gateway_eq, "_capture_file_hashes", lambda *_args: files)

    result = gateway_eq.verify_destination(manifest_path, "subscription")

    assert result == {
        "file_count": 3,
        "total_bytes": sum(int(item["size"]) for item in files),
    }


def test_verify_destination_rejects_size_divergence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = [_file("gateway-sync.db", b"source")]
    destination = [_file("gateway-sync.db", b"changed")]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(
        gateway_eq,
        "_capture_file_hashes",
        lambda *_args: destination,
    )

    with pytest.raises(MigrationControlError, match="size differs"):
        gateway_eq.verify_destination(manifest_path, "subscription")


def test_verify_destination_rejects_hash_divergence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = [_file("gateway-sync.db", b"source")]
    destination = [_file("gateway-sync.db", b"target")]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(
        gateway_eq,
        "_capture_file_hashes",
        lambda *_args: destination,
    )

    with pytest.raises(MigrationControlError, match="SHA-256 differs"):
        gateway_eq.verify_destination(manifest_path, "subscription")


def test_verify_destination_rejects_file_set_divergence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = [_file("gateway-sync.db", b"source")]
    destination = [_file("unexpected.db", b"source")]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(
        gateway_eq,
        "_capture_file_hashes",
        lambda *_args: destination,
    )

    with pytest.raises(MigrationControlError, match="file set differs"):
        gateway_eq.verify_destination(manifest_path, "subscription")


def test_capture_source_manifest_records_only_hash_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    files = [_file("gateway-sync.db", b"source")]
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg-source")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "gateway-share")
    monkeypatch.setattr(
        gateway_eq,
        "_discover_storage_accounts",
        lambda _rg: ("coreaccount", "gatewayaccount"),
    )
    monkeypatch.setattr(gateway_eq, "_capture_file_hashes", lambda *_args: files)

    result = gateway_eq.capture_source_manifest(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["file_count"] == 1
    assert payload["files"] == files
    assert "payload" not in payload
    assert "content" not in payload


def test_module_contains_no_gateway_write_path() -> None:
    source = inspect.getsource(gateway_eq)

    assert "storage file upload" not in source
    assert "storage file delete" not in source
    assert "_run_az_write" not in source
    assert "destination_write_performed" not in source


def test_workflow_is_manual_and_read_only() -> None:
    workflow = Path(
        ".github/workflows/azure-migration-gateway-equivalence.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "az storage file upload" not in workflow
    assert "az storage file delete" not in workflow
    assert "az storage entity insert" not in workflow
    assert "az containerapp update" not in workflow
    assert "actions/upload-artifact" not in workflow
    assert "${{ runner.temp }}" not in workflow
    assert "$RUNNER_TEMP/ets-gateway-equivalence.json" in workflow
