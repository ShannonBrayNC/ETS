from __future__ import annotations

from pathlib import Path

import pytest

from ets.connectors.enterprise.microsoft_sharepoint_state import (
    MicrosoftSharePointStateError,
    SharePointMetadataSnapshotV1,
    SharePointMetadataStateStore,
    classify_sharepoint_metadata_transition,
    snapshot_sharepoint_metadata_record,
)

SOURCE_KEY = "tenant-authoritative/workspace-authoritative/sharepoint-source"


def _record(
    *,
    object_id: str = "item-001",
    name: str = "report.docx",
    parent_id: str = "folder-a",
    parent_path: str = "/drive/root:/Reports",
    deleted: bool = False,
    size: int = 1234,
    modified: str = "2026-08-14T20:30:00Z",
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "name": name,
        "size": size,
        "modified_at_utc": modified,
        "parent": {
            "id": parent_id,
            "drive_id": "drive-001",
            "path": parent_path,
        },
    }
    if deleted:
        metadata["deleted"] = True
    return {
        "source_record_id": f"drive:{object_id}:fixture",
        "object_id": object_id,
        "scope": "drive",
        "deleted": deleted,
        "source_modified_at_utc": modified,
        "metadata": metadata,
    }


def _snapshot(**kwargs: object) -> SharePointMetadataSnapshotV1:
    return snapshot_sharepoint_metadata_record(_record(**kwargs))


def test_first_live_observation_is_baseline_not_created() -> None:
    current = _snapshot()

    transition = classify_sharepoint_metadata_transition(
        None,
        current,
        baseline_complete=False,
    )

    assert transition.kinds == ("baseline_observation",)
    assert transition.prior_sha256 is None


def test_unseen_tombstone_is_observed_deleted_not_witnessed_delete() -> None:
    current = _snapshot(deleted=True)

    transition = classify_sharepoint_metadata_transition(
        None,
        current,
        baseline_complete=False,
    )

    assert transition.kinds == ("observed_deleted",)


def test_unseen_live_object_after_completed_baseline_is_created() -> None:
    transition = classify_sharepoint_metadata_transition(
        None,
        _snapshot(object_id="item-new"),
        baseline_complete=True,
    )

    assert transition.kinds == ("created",)


def test_rename_move_and_update_are_derived_from_successive_state() -> None:
    prior = _snapshot()

    rename = classify_sharepoint_metadata_transition(
        prior,
        _snapshot(name="renamed.docx"),
        baseline_complete=True,
    )
    move = classify_sharepoint_metadata_transition(
        prior,
        _snapshot(parent_id="folder-b", parent_path="/drive/root:/Archive"),
        baseline_complete=True,
    )
    rename_and_move = classify_sharepoint_metadata_transition(
        prior,
        _snapshot(
            name="renamed.docx",
            parent_id="folder-b",
            parent_path="/drive/root:/Archive",
        ),
        baseline_complete=True,
    )
    update = classify_sharepoint_metadata_transition(
        prior,
        _snapshot(size=4321),
        baseline_complete=True,
    )

    assert "renamed" in rename.kinds
    assert "moved" in move.kinds
    assert rename_and_move.kinds[:2] == ("renamed", "moved")
    assert update.kinds == ("updated",)


def test_delete_restore_and_unchanged_require_prior_qualified_state() -> None:
    live = _snapshot()
    deleted = _snapshot(deleted=True)

    delete_transition = classify_sharepoint_metadata_transition(
        live,
        deleted,
        baseline_complete=True,
    )
    restore_transition = classify_sharepoint_metadata_transition(
        deleted,
        live,
        baseline_complete=True,
    )
    unchanged = classify_sharepoint_metadata_transition(
        live,
        live,
        baseline_complete=True,
    )
    repeated_tombstone = classify_sharepoint_metadata_transition(
        deleted,
        deleted,
        baseline_complete=True,
    )

    assert delete_transition.kinds == ("deleted",)
    assert restore_transition.kinds == ("restored",)
    assert unchanged.kinds == ("unchanged",)
    assert repeated_tombstone.kinds == ("unchanged",)


def test_source_timestamp_or_etag_only_change_is_an_update_not_rename_or_move() -> None:
    prior = _snapshot(modified="2026-08-14T20:30:00Z")
    current = _snapshot(modified="2026-08-14T20:31:00Z")

    transition = classify_sharepoint_metadata_transition(
        prior,
        current,
        baseline_complete=True,
    )

    assert transition.kinds == ("updated",)


def test_classify_does_not_mutate_state_and_apply_is_explicit(tmp_path: Path) -> None:
    store = SharePointMetadataStateStore(tmp_path / "sharepoint-state.db")
    current = _snapshot()

    transition = store.classify(SOURCE_KEY, current)

    assert transition.kinds == ("baseline_observation",)
    assert store.get(SOURCE_KEY, "drive", "item-001") is None
    assert store.baseline_complete(SOURCE_KEY) is False

    store.apply(SOURCE_KEY, [current], mark_baseline_complete=False)
    assert store.get(SOURCE_KEY, "drive", "item-001") == current
    assert store.baseline_complete(SOURCE_KEY) is False

    store.apply(SOURCE_KEY, [], mark_baseline_complete=True)
    assert store.baseline_complete(SOURCE_KEY) is True


def test_baseline_completion_is_monotonic(tmp_path: Path) -> None:
    store = SharePointMetadataStateStore(tmp_path / "sharepoint-state.db")

    store.apply(SOURCE_KEY, [_snapshot()], mark_baseline_complete=True)
    store.apply(SOURCE_KEY, [], mark_baseline_complete=False)

    assert store.baseline_complete(SOURCE_KEY) is True


def test_apply_rejects_conflicting_duplicate_proposals(tmp_path: Path) -> None:
    store = SharePointMetadataStateStore(tmp_path / "sharepoint-state.db")

    with pytest.raises(MicrosoftSharePointStateError, match="conflicting snapshots"):
        store.apply(
            SOURCE_KEY,
            [_snapshot(name="a.docx"), _snapshot(name="b.docx")],
        )

    assert store.get(SOURCE_KEY, "drive", "item-001") is None


def test_state_item_capacity_is_bounded_without_partial_advance(tmp_path: Path) -> None:
    store = SharePointMetadataStateStore(
        tmp_path / "sharepoint-state.db",
        max_items=1,
    )
    first = _snapshot(object_id="item-001")
    second = _snapshot(object_id="item-002")
    store.apply(SOURCE_KEY, [first])

    with pytest.raises(MicrosoftSharePointStateError, match="capacity"):
        store.apply(SOURCE_KEY, [second])

    assert store.get(SOURCE_KEY, "drive", "item-001") == first
    assert store.get(SOURCE_KEY, "drive", "item-002") is None


def test_snapshot_rejects_non_json_or_oversized_operational_metadata() -> None:
    bad = _record()
    bad["metadata"] = {"name": "x" * (16 * 1024)}

    with pytest.raises(MicrosoftSharePointStateError, match="byte bound"):
        snapshot_sharepoint_metadata_record(bad)
