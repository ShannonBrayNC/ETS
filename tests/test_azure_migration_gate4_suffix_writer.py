from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate4_suffix_writer as suffix_writer
from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate4_restore import _canonical_entities
from scripts.azure_migration_gate4_suffix_writer import (
    AUTHORIZATION_PHRASE,
    _analyze_destination,
    apply_resumable_suffix,
)
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


def _staged_destination(
    source: list[dict[str, object]],
    committed_count: int,
) -> list[dict[str, object]]:
    metadata = dict(next(item for item in source if item.get("kind") == "metadata"))
    metadata["next_index"] = committed_count
    return _canonical_entities(
        [metadata, *[item for item in source if item.get("kind") != "metadata"]]
    )


def test_analyze_runtime_shape_plans_only_missing_suffix() -> None:
    source = _entities(49)
    destination = _entities(37)

    result = _analyze_destination(source, destination)

    assert result["source_next_index"] == 49
    assert result["destination_next_index"] == 37
    assert result["missing_entity_count"] == 24
    assert result["staged_entity_count"] == 0
    assert result["metadata_update_required"] is True


def test_analyze_accepts_exact_interrupted_staged_row() -> None:
    source = _entities(3)
    destination = _entities(1)
    staged = next(
        item
        for item in source
        if item.get("kind") == "entry" and item.get("log_index") == 2
    )
    destination = _canonical_entities([*destination, staged])

    result = _analyze_destination(source, destination)

    assert result["staged_entity_count"] == 1
    assert result["missing_entity_count"] == 3


def test_analyze_rejects_divergent_staged_row() -> None:
    source = _entities(2)
    destination = _entities(1)
    staged = dict(
        next(
            item
            for item in source
            if item.get("kind") == "entry" and item.get("log_index") == 1
        )
    )
    staged["leaf_hash"] = "f" * 64
    destination = _canonical_entities([*destination, staged])

    with pytest.raises(
        MigrationControlError,
        match="differs from the protected source snapshot",
    ):
        _analyze_destination(source, destination)


def test_analyze_rejects_unexpected_destination_row() -> None:
    source = _entities(2)
    destination = _entities(1)
    destination = _canonical_entities(
        [
            *destination,
            {
                "PartitionKey": "ets-live-primary",
                "RowKey": "entry-99999999999999999999",
                "kind": "entry",
                "log_index": 999,
                "event_json": "{}",
                "event_hash": "a" * 64,
                "leaf_hash": "b" * 64,
            },
        ]
    )

    with pytest.raises(
        MigrationControlError,
        match="outside the protected source snapshot",
    ):
        _analyze_destination(source, destination)


def _patch_apply_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    source: list[dict[str, object]],
    destination: list[dict[str, object]],
) -> Mock:
    manifest = _manifest(source)
    destination_next = int(_validated_state(destination)["next_index"])
    staged = _staged_destination(source, destination_next)
    responses = iter([destination, staged, source])

    monkeypatch.setenv("MIGRATION_RESOURCE_GROUP", "rg-ets-prod-eastus")
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "ets-gateway-state-q1-v2")
    monkeypatch.setattr(
        suffix_writer,
        "_load_protected_workspace",
        Mock(return_value=(manifest, source, [])),
    )
    monkeypatch.setattr(suffix_writer, "_verify_zero_replicas", Mock())
    monkeypatch.setattr(
        suffix_writer,
        "_discover_storage_accounts",
        Mock(return_value=("core", "gateway")),
    )
    monkeypatch.setattr(
        suffix_writer,
        "_verify_restore_identity_scopes",
        Mock(),
    )
    monkeypatch.setattr(
        suffix_writer,
        "_verify_gateway_files",
        Mock(return_value=5),
    )
    monkeypatch.setattr(
        suffix_writer,
        "_query_full_entities",
        Mock(side_effect=lambda *_args: next(responses)),
    )
    writer = Mock()
    monkeypatch.setattr(suffix_writer, "_run_az_write", writer)
    return writer


def _if_exists_value(command: list[str]) -> str:
    index = command.index("--if-exists")
    return command[index + 1]


def test_apply_inserts_only_suffix_and_updates_metadata_last(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _entities(3)
    destination = _entities(1)
    writer = _patch_apply_dependencies(monkeypatch, source, destination)

    result = apply_resumable_suffix(
        tmp_path,
        "d" * 64,
        "sub",
        AUTHORIZATION_PHRASE,
    )

    assert writer.call_count == 5
    commands = [call.args[0] for call in writer.call_args_list]
    assert all(_if_exists_value(command) == "fail" for command in commands[:-1])
    assert _if_exists_value(commands[-1]) == "replace"
    assert any(value == "RowKey=meta" for value in commands[-1])
    assert result["suffix_entities_inserted"] == 4
    assert result["metadata_updated"] is True
    assert result["destination_prefix_replaced"] is False
    assert result["gateway_write_performed"] is False


def test_apply_requires_exact_authorization_before_reads(tmp_path: Path) -> None:
    with pytest.raises(
        MigrationControlError,
        match="authorization phrase is missing",
    ):
        apply_resumable_suffix(tmp_path, "d" * 64, "sub", "wrong")


def test_writer_has_no_cli_or_execution_workflow() -> None:
    source = inspect.getsource(suffix_writer)
    assert "def main(" not in source
    assert '__name__ == "__main__"' not in source

    root = Path(__file__).resolve().parents[1]
    workflow = (
        root
        / ".github"
        / "workflows"
        / "azure-migration-gate4-resumable-write.yml"
    )
    assert not workflow.exists()
