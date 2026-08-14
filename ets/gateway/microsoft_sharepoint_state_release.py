"""Post-commit SharePoint/OneDrive operational state release for G2E-DQ.

The hook in this module is intentionally downstream of Gateway evidence commitment.
It advances only connector operational prior-state used for later metadata-diff
classification. It does not alter canonical ETS evidence or source checkpoints.
"""

from __future__ import annotations

import sqlite3

from ets.connectors.enterprise.microsoft_sharepoint_state import (
    MicrosoftSharePointStateError,
    SharePointMetadataSnapshotV1,
    SharePointMetadataStateStore,
    snapshot_sharepoint_metadata_record,
)
from ets.connectors.models import ConnectorCollectionResultV1
from ets.gateway.connector_runner import GatewayConnectorReleaseError


class SharePointMetadataStateReleaseHook:
    """Release minimized SharePoint state only after Gateway queued-state success."""

    def __init__(self, store: SharePointMetadataStateStore, *, source_key: str) -> None:
        if not source_key:
            raise ValueError("SharePoint release source_key is required")
        self._store: SharePointMetadataStateStore = store
        self._source_key: str = source_key

    def release(self, collection: ConnectorCollectionResultV1) -> None:
        """Atomically persist page state after all observations reached queued state.

        A completed delta cycle marks the source baseline complete. Intermediate
        pages advance observed object state but do not permit unseen objects to be
        classified as newly created until the baseline cycle has completed.
        """

        try:
            snapshots: tuple[SharePointMetadataSnapshotV1, ...] = tuple(
                snapshot_sharepoint_metadata_record(record) for record in collection.records
            )
            self._store.apply(
                self._source_key,
                snapshots,
                mark_baseline_complete=not collection.has_more,
            )
        except (MicrosoftSharePointStateError, sqlite3.Error, OSError) as exc:
            raise GatewayConnectorReleaseError(
                "SharePoint operational state release failed"
            ) from exc
