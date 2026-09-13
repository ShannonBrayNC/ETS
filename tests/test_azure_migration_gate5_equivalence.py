from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import scripts.azure_migration_gate5_equivalence as gate5
from scripts.azure_migration_control import MigrationControlError


def _set_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg-destination")
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "gateway-share")
    monkeypatch.setattr(gate5, "_verify_zero_replicas", lambda _rg: None)
    monkeypatch.setattr(
        gate5,
        "_discover_storage_accounts",
        lambda _rg: ("coreaccount", "gatewayaccount"),
    )
    monkeypatch.setattr(
        gate5,
        "_verify_restore_identity_scopes",
        lambda *_args: None,
    )


def _manifest() -> dict[str, object]:
    return {
        "manifest_version": 1,
        "source_next_index": 2,
        "metadata_digest": "meta",
        "pair_digests": ["a", "b"],
    }


def _destination() -> dict[str, object]:
    return {
        "next_index": 2,
        "entity_count": 5,
        "metadata_digest": "meta",
        "pair_digests": ["a", "b"],
    }


def test_verify_table_exact_accepts_identical_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_boundary(monkeypatch)
    monkeypatch.setattr(gate5, "_read_manifest", lambda _path: _manifest())
    monkeypatch.setattr(gate5, "_read_evidence_entities", lambda *_args: [])
    monkeypatch.setattr(gate5, "_validated_state", lambda _items: _destination())

    result = gate5.verify_table_exact(tmp_path / "table.json", "subscription")

    assert result == {"next_index": 2, "entity_count": 5}


def test_verify_table_exact_rejects_high_water_divergence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_boundary(monkeypatch)
    monkeypatch.setattr(gate5, "_read_manifest", lambda _path: _manifest())
    state = _destination()
    state["next_index"] = 1
    monkeypatch.setattr(gate5, "_read_evidence_entities", lambda *_args: [])
    monkeypatch.setattr(gate5, "_validated_state", lambda _items: state)

    with pytest.raises(MigrationControlError) as caught:
        gate5.verify_table_exact(tmp_path / "table.json", "subscription")

    assert str(caught.value) == "Gate 5 equivalence stage failed: table_high_water"


def test_verify_table_exact_rejects_digest_divergence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_boundary(monkeypatch)
    monkeypatch.setattr(gate5, "_read_manifest", lambda _path: _manifest())
    state = _destination()
    state["pair_digests"] = ["a", "changed"]
    monkeypatch.setattr(gate5, "_read_evidence_entities", lambda *_args: [])
    monkeypatch.setattr(gate5, "_validated_state", lambda _items: state)

    with pytest.raises(MigrationControlError) as caught:
        gate5.verify_table_exact(tmp_path / "table.json", "subscription")

    assert str(caught.value) == "Gate 5 equivalence stage failed: table_digest"


def test_verify_gate5_requires_gateway_equivalence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        gate5,
        "verify_table_exact",
        lambda *_args: {"next_index": 2, "entity_count": 5},
    )
    monkeypatch.setattr(
        gate5,
        "verify_gateway",
        lambda *_args: {"file_count": 3, "total_bytes": 123},
    )

    result = gate5.verify_gate5(
        tmp_path / "table.json",
        tmp_path / "gateway.json",
        "subscription",
    )

    assert result == {
        "next_index": 2,
        "entity_count": 5,
        "gateway_file_count": 3,
        "gateway_total_bytes": 123,
    }


def test_gateway_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        gate5,
        "verify_table_exact",
        lambda *_args: {"next_index": 2, "entity_count": 5},
    )

    def fail_gateway(*_args: object) -> dict[str, int]:
        raise MigrationControlError("private gateway detail")

    monkeypatch.setattr(gate5, "verify_gateway", fail_gateway)

    with pytest.raises(MigrationControlError) as caught:
        gate5.verify_gate5(
            tmp_path / "table.json",
            tmp_path / "gateway.json",
            "subscription",
        )

    assert str(caught.value) == "Gate 5 equivalence stage failed: gateway_equivalence"
    assert "private gateway detail" not in str(caught.value)


def test_gate5_module_contains_no_write_path() -> None:
    source = inspect.getsource(gate5)

    for forbidden in (
        "storage entity insert",
        "storage entity merge",
        "storage entity replace",
        "storage entity delete",
        "storage file upload",
        "storage file delete",
        "containerapp update",
        "afd route update",
    ):
        assert forbidden not in source


def test_gate5_workflow_is_manual_read_only_and_ephemeral() -> None:
    workflow = Path(
        ".github/workflows/azure-migration-gate5-equivalence.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "actions/upload-artifact" not in workflow
    assert "az storage entity insert" not in workflow
    assert "az storage entity merge" not in workflow
    assert "az storage entity replace" not in workflow
    assert "az storage file upload" not in workflow
    assert "az storage file delete" not in workflow
    assert "az containerapp update" not in workflow
    assert "az afd" not in workflow
    assert "rm -f \"$TABLE_MANIFEST\" \"$GATEWAY_MANIFEST\"" in workflow
