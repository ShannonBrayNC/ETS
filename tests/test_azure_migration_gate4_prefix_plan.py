from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate4_prefix_plan as prefix_plan
from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate4_prefix_plan import (
    _prefix_state,
    plan_resumable_prefix,
)
from scripts.azure_migration_gate4_restore import _canonical_entities
from scripts.azure_migration_prefix_preflight import _validated_state


def _entities(count: int) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = [
        {
            "PartitionKey": "ets-live-primary",
            "RowKey": "meta",
            "kind": "metadata",
            "next_index": count,
            "schema_version": 1,
            "log_id": "ets-live-primary",
        }
    ]
    for index in range(count):
        event_id = f"event-{index:03d}"
        entities.extend(
            [
                {
                    "PartitionKey": "ets-live-primary",
                    "RowKey": f"entry-{index:020d}",
                    "kind": "entry",
                    "log_index": index,
                    "event_json": f'{{"event_id":"{event_id}"}}',
                    "event_hash": hashlib.sha256(
                        f"event:{index}".encode()
                    ).hexdigest(),
                    "leaf_hash": hashlib.sha256(
                        f"leaf:{index}".encode()
                    ).hexdigest(),
                },
                {
                    "PartitionKey": "ets-live-primary",
                    "RowKey": (
                        "event-"
                        f"{hashlib.sha256(event_id.encode()).hexdigest()}"
                    ),
                    "kind": "event_index",
                    "log_index": index,
                    "event_id": event_id,
                },
            ]
        )
    return _canonical_entities(entities)


def _manifest(source: list[dict[str, object]]) -> dict[str, object]:
    state = _validated_state(source)
    return {
        "evidence": {
            "entity_count": state["entity_count"],
            "next_index": state["next_index"],
        },
        "gateway": {"file_count": 5},
    }


def test_runtime_shape_49_to_37_plans_only_missing_suffix() -> None:
    source = _entities(49)
    destination = _entities(37)

    result = _prefix_state(source, destination)

    assert result["source_next_index"] == 49
    assert result["source_entity_count"] == 99
    assert result["destination_next_index"] == 37
    assert result["destination_entity_count"] == 75
    assert result["missing_event_count"] == 12
    assert result["missing_table_entity_count"] == 24


def test_prefix_state_rejects_divergent_existing_event() -> None:
    source = _entities(2)
    destination = _entities(1)
    for entity in destination:
        if entity.get("kind") == "entry":
            entity["leaf_hash"] = "f" * 64

    with pytest.raises(
        MigrationControlError,
        match="not an exact protected-source prefix",
    ):
        _prefix_state(source, destination)


def test_prefix_state_rejects_destination_ahead_of_snapshot() -> None:
    source = _entities(1)
    destination = _entities(2)

    with pytest.raises(
        MigrationControlError,
        match="high-water mark exceeds",
    ):
        _prefix_state(source, destination)


def test_plan_preserves_prefix_and_performs_no_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _entities(49)
    destination = _entities(37)
    manifest = _manifest(source)
    source_files = [
        {"name": f"file-{index}", "size": 0, "sha256": "a" * 64}
        for index in range(5)
    ]

    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg")
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "share")
    monkeypatch.setattr(
        prefix_plan,
        "_load_protected_workspace",
        Mock(return_value=(manifest, source, source_files)),
    )
    zero_replicas = Mock(return_value=None)
    monkeypatch.setattr(prefix_plan, "_verify_zero_replicas", zero_replicas)
    monkeypatch.setattr(
        prefix_plan,
        "_discover_storage_accounts",
        Mock(return_value=("core", "gateway")),
    )
    identity = Mock(return_value=None)
    monkeypatch.setattr(prefix_plan, "_verify_restore_identity_scopes", identity)
    monkeypatch.setattr(
        prefix_plan,
        "_query_full_entities",
        Mock(return_value=destination),
    )
    gateway = Mock(return_value=5)
    monkeypatch.setattr(prefix_plan, "_verify_gateway_files", gateway)

    result = plan_resumable_prefix(tmp_path, "d" * 64, "sub")

    assert result["destination_prefix_preserved"] is True
    assert result["destination_write_performed"] is False
    assert result["apply_supported"] is False
    assert result["missing_event_count"] == 12
    assert result["missing_table_entity_count"] == 24
    assert result["metadata_update_required"] is True
    assert result["gateway_byte_equivalence_proven"] is False
    zero_replicas.assert_called_once_with("rg")
    identity.assert_called_once()
    gateway.assert_called_once_with("gateway", "share")


def test_planner_exposes_no_apply_parameter() -> None:
    parameters = inspect.signature(plan_resumable_prefix).parameters

    assert "apply" not in parameters
    assert "authorization" not in parameters
