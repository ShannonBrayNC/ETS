from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.microsoft_agent365_custody import (
    MicrosoftAgent365SnapshotCheckpointV1,
)
from ets.connectors.enterprise.microsoft_agent365_reconciliation import (
    MicrosoftAgent365PackageChangeV1,
    MicrosoftAgent365ReconciliationConflict,
    MicrosoftAgent365ReconciliationHistoryStore,
    project_agent365_reconciliation,
    reconcile_agent365_inventory,
)

TENANT_ID = "11111111-2222-3333-4444-555555555555"
BASE_TIME = datetime(2026, 9, 17, 2, 0, tzinfo=UTC)


def _state_hash(state: dict[str, str]) -> str:
    encoded = json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _checkpoint(
    *,
    checkpoint_hash: str,
    snapshot_id: str,
    state: dict[str, str],
    previous_checkpoint_hash: str | None,
    sequence: int,
    completed_at_utc: datetime,
) -> MicrosoftAgent365SnapshotCheckpointV1:
    return MicrosoftAgent365SnapshotCheckpointV1(
        tenant_id=TENANT_ID,
        snapshot_id=snapshot_id,
        completed_at_utc=completed_at_utc,
        envelope_count=1,
        package_count=len(state),
        first_acquisition_sequence=sequence,
        last_acquisition_sequence=sequence,
        last_envelope_hash="e" * 64,
        inventory_state_sha256=_state_hash(state),
        previous_checkpoint_hash=previous_checkpoint_hash,
        checkpoint_hash=checkpoint_hash,
    )


def _adjacent_checkpoints() -> tuple[
    MicrosoftAgent365SnapshotCheckpointV1,
    MicrosoftAgent365SnapshotCheckpointV1,
    dict[str, str],
    dict[str, str],
]:
    previous_state = {
        "agent-a": "a" * 64,
        "agent-b": "b" * 64,
        "agent-c": "c" * 64,
    }
    current_state = {
        "agent-a": "a" * 64,
        "agent-b": "d" * 64,
        "agent-d": "f" * 64,
    }
    previous = _checkpoint(
        checkpoint_hash="1" * 64,
        snapshot_id="a" * 64,
        state=previous_state,
        previous_checkpoint_hash=None,
        sequence=0,
        completed_at_utc=BASE_TIME,
    )
    current = _checkpoint(
        checkpoint_hash="2" * 64,
        snapshot_id="b" * 64,
        state=current_state,
        previous_checkpoint_hash=previous.checkpoint_hash,
        sequence=1,
        completed_at_utc=BASE_TIME + timedelta(minutes=5),
    )
    return previous, current, previous_state, current_state


def test_reconciliation_classifies_adjacent_snapshot_differences() -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()

    record = reconcile_agent365_inventory(
        previous_checkpoint=previous,
        current_checkpoint=current,
        previous_state=previous_state,
        current_state=current_state,
    )

    assert [(change.package_id, change.change_kind) for change in record.changes] == [
        ("agent-a", "UNCHANGED"),
        ("agent-b", "CHANGED"),
        ("agent-c", "REMOVED"),
        ("agent-d", "ADDED"),
    ]
    assert record.added_count == 1
    assert record.changed_count == 1
    assert record.removed_count == 1
    assert record.unchanged_count == 1
    assert record.previous_checkpoint_hash == previous.checkpoint_hash
    assert record.current_checkpoint_hash == current.checkpoint_hash


def test_reconciliation_is_deterministic_across_mapping_order() -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()

    first = reconcile_agent365_inventory(
        previous_checkpoint=previous,
        current_checkpoint=current,
        previous_state=previous_state,
        current_state=current_state,
    )
    second = reconcile_agent365_inventory(
        previous_checkpoint=previous,
        current_checkpoint=current,
        previous_state=dict(reversed(tuple(previous_state.items()))),
        current_state=dict(reversed(tuple(current_state.items()))),
    )

    assert first.reconciliation_hash == second.reconciliation_hash
    assert first.changes == second.changes


def test_reconciliation_can_omit_unchanged_projection_noise() -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()
    record = reconcile_agent365_inventory(
        previous_checkpoint=previous,
        current_checkpoint=current,
        previous_state=previous_state,
        current_state=current_state,
    )

    projected = project_agent365_reconciliation(record)

    assert [item.package_id for item in projected] == ["agent-b", "agent-c", "agent-d"]
    assert all(item.object_class == "A365_AGENT_CONFIGURATION" for item in projected)
    assert all(
        item.observation_semantics == "microsoft_attributable_reconciliation"
        for item in projected
    )
    assert all(item.reconciliation_hash == record.reconciliation_hash for item in projected)


def test_reconciliation_rejects_nonadjacent_checkpoints() -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()
    detached = current.model_copy(update={"previous_checkpoint_hash": "9" * 64})

    with pytest.raises(MicrosoftAgent365ReconciliationConflict):
        reconcile_agent365_inventory(
            previous_checkpoint=previous,
            current_checkpoint=detached,
            previous_state=previous_state,
            current_state=current_state,
        )


def test_reconciliation_rejects_state_not_committed_by_checkpoint() -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()
    tampered = dict(current_state)
    tampered["agent-b"] = "0" * 64

    with pytest.raises(MicrosoftAgent365ReconciliationConflict):
        reconcile_agent365_inventory(
            previous_checkpoint=previous,
            current_checkpoint=current,
            previous_state=previous_state,
            current_state=tampered,
        )


def test_package_change_shape_is_fail_closed() -> None:
    with pytest.raises(ValidationError):
        MicrosoftAgent365PackageChangeV1(
            package_id="agent-a",
            change_kind="ADDED",
            previous_configuration_sha256="a" * 64,
            current_configuration_sha256="b" * 64,
        )


def test_history_store_chains_reconciliations_across_adjacent_checkpoints(
    tmp_path: Path,
) -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()
    next_state = {
        "agent-a": "a" * 64,
        "agent-b": "d" * 64,
        "agent-e": "9" * 64,
    }
    next_checkpoint = _checkpoint(
        checkpoint_hash="3" * 64,
        snapshot_id="c" * 64,
        state=next_state,
        previous_checkpoint_hash=current.checkpoint_hash,
        sequence=2,
        completed_at_utc=BASE_TIME + timedelta(minutes=10),
    )
    store = MicrosoftAgent365ReconciliationHistoryStore(tmp_path / "reconciliation.sqlite")

    first = store.reconcile_and_commit(
        previous_checkpoint=previous,
        current_checkpoint=current,
        previous_state=previous_state,
        current_state=current_state,
    )
    second = store.reconcile_and_commit(
        previous_checkpoint=current,
        current_checkpoint=next_checkpoint,
        previous_state=current_state,
        current_state=next_state,
    )

    history = store.list_history(TENANT_ID)
    assert history == (first, second)
    assert second.previous_reconciliation_hash == first.reconciliation_hash
    assert second.previous_checkpoint_hash == first.current_checkpoint_hash


def test_history_store_is_idempotent_for_same_reconciliation(tmp_path: Path) -> None:
    previous, current, previous_state, current_state = _adjacent_checkpoints()
    store = MicrosoftAgent365ReconciliationHistoryStore(tmp_path / "reconciliation.sqlite")
    record = reconcile_agent365_inventory(
        previous_checkpoint=previous,
        current_checkpoint=current,
        previous_state=previous_state,
        current_state=current_state,
    )

    store.commit(record)
    store.commit(record)

    assert store.list_history(TENANT_ID) == (record,)
