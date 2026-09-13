from __future__ import annotations

from pathlib import Path

import pytest

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate6_final_capture import _canonicalize_gateway_capture
from scripts.azure_migration_prefix_preflight import (
    _GATEWAY_SYNC_WAL_SIDECARS,
    EXPECTED_GATEWAY_FILES,
)


def _file(name: str, size: int) -> dict[str, object]:
    return {"name": name, "size": size, "sha256": "a" * 64}


def test_inert_sidecars_are_removed_only_from_protected_local_copy(tmp_path: Path) -> None:
    gateway = tmp_path / "gateway"
    gateway.mkdir()
    files = [_file(name, 10) for name in sorted(EXPECTED_GATEWAY_FILES)]
    files.extend(
        [
            _file("gateway-sync.db-shm", 32),
            _file("gateway-sync.db-wal", 0),
        ]
    )
    for sidecar in _GATEWAY_SYNC_WAL_SIDECARS:
        (gateway / sidecar).write_bytes(b"" if sidecar.endswith("-wal") else b"x")

    durable, total_bytes = _canonicalize_gateway_capture(tmp_path, files)

    assert {str(item["name"]) for item in durable} == EXPECTED_GATEWAY_FILES
    assert total_bytes == 30
    for sidecar in _GATEWAY_SYNC_WAL_SIDECARS:
        assert not (gateway / sidecar).exists()


def test_nonzero_wal_blocks_final_capture(tmp_path: Path) -> None:
    gateway = tmp_path / "gateway"
    gateway.mkdir()
    files = [_file(name, 10) for name in sorted(EXPECTED_GATEWAY_FILES)]
    files.extend(
        [
            _file("gateway-sync.db-shm", 32),
            _file("gateway-sync.db-wal", 1),
        ]
    )

    with pytest.raises(MigrationControlError, match="WAL sidecar is not inert"):
        _canonicalize_gateway_capture(tmp_path, files)
