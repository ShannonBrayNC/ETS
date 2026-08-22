from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DURABLE = ROOT / "ets" / "fleet" / "portal_admin_durable.py"
DOC = ROOT / "docs" / "fleet" / "ETS_FLEET_C3A_DURABLE_ADMIN.md"


def test_c3a_durable_admin_has_no_azure_or_product_plane_coupling() -> None:
    source = DURABLE.read_text(encoding="utf-8").lower()
    forbidden = (
        "azure.",
        "iothub",
        "dpsclient",
        "sharedaccesssignature",
        "connectionstring",
        "private_key",
        "authorization:",
        "bearer ",
    )
    for token in forbidden:
        assert token not in source


def test_c3a_reserves_before_lifecycle_apply_and_blocks_pending_replay() -> None:
    source = DURABLE.read_text(encoding="utf-8")
    reserve_position = source.index("retained = self._journal.reserve")
    apply_position = source.index("updated = self._apply")
    assert reserve_position < apply_position
    assert "FleetAdminMutationPending" in source
    assert "pending reconciliation" in source


def test_sqlite_reference_uses_durable_transaction_pragmas() -> None:
    source = DURABLE.read_text(encoding="utf-8")
    assert 'PRAGMA journal_mode=WAL' in source
    assert 'PRAGMA synchronous=FULL' in source
    assert 'PRAGMA foreign_keys=ON' in source
    assert 'BEGIN IMMEDIATE' in source
    assert "status IN ('pending', 'committed')" in source


def test_raw_idempotency_value_is_not_a_journal_field() -> None:
    source = DURABLE.read_text(encoding="utf-8")
    assert "idempotency_key_sha256" in source
    assert "raw_idempotency" not in source
    assert "idempotency_key TEXT" not in source


def test_c3a_documentation_preserves_production_boundary() -> None:
    text = DOC.read_text(encoding="utf-8").lower()
    assert "single-node reference" in text
    assert "not the c3 multi-replica production store" in text
    assert "pending" in text
    assert "reconciliation" in text
    assert "c3b" in text
