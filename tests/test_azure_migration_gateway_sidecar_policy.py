from __future__ import annotations

import hashlib
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


def _write_manifest(path: Path, files: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "claim": "ephemeral_source_gateway_byte_manifest",
                "file_count": len(files),
                "total_bytes": sum(int(item["size"]) for item in files),
                "files": files,
            }
        ),
        encoding="utf-8",
    )


def _source_files() -> list[dict[str, object]]:
    return [
        _file("connector-runtime.db", b"connector"),
        _file("gateway-events.db", b"events"),
        _file("gateway-sync.db", b"sync"),
    ]


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


def test_verify_destination_accepts_approved_inert_sqlite_sidecars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _source_files()
    destination = [
        *source,
        _file("gateway-sync.db-shm", b"shared-memory-index"),
        _file("gateway-sync.db-wal", b""),
    ]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(
        gateway_eq,
        "_capture_file_hashes",
        lambda *_args: sorted(destination, key=lambda item: str(item["name"])),
    )

    result = gateway_eq.verify_destination(manifest_path, "subscription")

    assert result == {
        "file_count": 3,
        "total_bytes": sum(int(item["size"]) for item in source),
    }


def test_verify_destination_rejects_nonzero_wal_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _source_files()
    destination = [
        *source,
        _file("gateway-sync.db-shm", b"shared-memory-index"),
        _file("gateway-sync.db-wal", b"uncheckpointed"),
    ]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(
        gateway_eq,
        "_capture_file_hashes",
        lambda *_args: sorted(destination, key=lambda item: str(item["name"])),
    )

    with pytest.raises(MigrationControlError, match="stage failed: wal_state"):
        gateway_eq.verify_destination(manifest_path, "subscription")


def test_verify_destination_rejects_partial_sqlite_sidecar_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _source_files()
    destination = [
        *source,
        _file("gateway-sync.db-shm", b"shared-memory-index"),
    ]
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source)
    _set_destination_boundary(monkeypatch)
    monkeypatch.setattr(
        gateway_eq,
        "_capture_file_hashes",
        lambda *_args: sorted(destination, key=lambda item: str(item["name"])),
    )

    with pytest.raises(MigrationControlError, match="stage failed: file_set"):
        gateway_eq.verify_destination(manifest_path, "subscription")
