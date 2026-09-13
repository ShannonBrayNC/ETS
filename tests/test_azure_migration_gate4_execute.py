from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate4_execute as execute
from scripts.azure_migration_control import MigrationControlError


def _table_result() -> dict[str, object]:
    return {
        "source_next_index": 49,
        "destination_start_next_index": 37,
        "suffix_entities_inserted": 24,
        "staged_entities_reused": 0,
        "metadata_updated": True,
        "destination_write_performed": True,
    }


def _gateway_result() -> dict[str, object]:
    return {
        "rollback_files_captured": 5,
        "rollback_bytes_captured": 331776,
        "durable_files_overwritten": 1,
        "sidecars_removed": 2,
        "gateway_files_verified": 3,
        "gateway_write_performed": True,
    }


def test_execution_requires_exact_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    table = Mock(side_effect=AssertionError("Table writer must not run"))
    gateway = Mock(side_effect=AssertionError("Gateway writer must not run"))
    monkeypatch.setattr(execute, "apply_resumable_suffix", table)
    monkeypatch.setattr(execute, "apply_gateway_snapshot", gateway)

    with pytest.raises(MigrationControlError, match="authorization phrase"):
        execute.execute_gate4_restore(
            Path("/protected/source"),
            "manifest",
            "subscription",
            Path("/protected/rollback"),
            "wrong",
        )

    table.assert_not_called()
    gateway.assert_not_called()


def test_execution_runs_table_before_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def table_writer(**kwargs: object) -> dict[str, object]:
        calls.append("table")
        assert kwargs["authorization"] == execute.SUFFIX_AUTHORIZATION_PHRASE
        return _table_result()

    def gateway_writer(**kwargs: object) -> dict[str, object]:
        calls.append("gateway")
        assert kwargs["authorization"] == execute.GATEWAY_AUTHORIZATION_PHRASE
        assert kwargs["rollback_workspace"] == Path("/protected/rollback")
        return _gateway_result()

    monkeypatch.setattr(execute, "apply_resumable_suffix", table_writer)
    monkeypatch.setattr(execute, "apply_gateway_snapshot", gateway_writer)

    result = execute.execute_gate4_restore(
        Path("/protected/source"),
        "manifest",
        "subscription",
        Path("/protected/rollback"),
        execute.AUTHORIZATION_PHRASE,
    )

    assert calls == ["table", "gateway"]
    assert result["table_suffix_entities_inserted"] == 24
    assert result["gateway_durable_files_overwritten"] == 1
    assert result["destination_prefix_replaced"] is False
    assert result["writer_activation_performed"] is False
    assert result["source_mutation_performed"] is False
    assert result["rbac_change_performed"] is False
    assert result["cutover_performed"] is False


def test_table_failure_blocks_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    table = Mock(side_effect=MigrationControlError("table blocked"))
    gateway = Mock(side_effect=AssertionError("Gateway writer must not run"))
    monkeypatch.setattr(execute, "apply_resumable_suffix", table)
    monkeypatch.setattr(execute, "apply_gateway_snapshot", gateway)

    with pytest.raises(MigrationControlError, match="table blocked"):
        execute.execute_gate4_restore(
            Path("/protected/source"),
            "manifest",
            "subscription",
            Path("/protected/rollback"),
            execute.AUTHORIZATION_PHRASE,
        )

    gateway.assert_not_called()


def test_gateway_failure_propagates_after_resumable_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = Mock(return_value=_table_result())
    gateway = Mock(side_effect=MigrationControlError("gateway blocked"))
    monkeypatch.setattr(execute, "apply_resumable_suffix", table)
    monkeypatch.setattr(execute, "apply_gateway_snapshot", gateway)

    with pytest.raises(MigrationControlError, match="gateway blocked"):
        execute.execute_gate4_restore(
            Path("/protected/source"),
            "manifest",
            "subscription",
            Path("/protected/rollback"),
            execute.AUTHORIZATION_PHRASE,
        )

    table.assert_called_once()
    gateway.assert_called_once()
