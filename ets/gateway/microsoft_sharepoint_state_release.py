"""SharePoint/OneDrive derived claims and commitment-gated state release for G2E-DQ.

The candidate hook classifies successive minimized metadata before commitment without
mutating operational state. The release hook advances that state only after every page
observation has reached local append plus durable synchronization queueing.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from pydantic import JsonValue

from ets.connectors.enterprise.microsoft_sharepoint_state import (
    MicrosoftSharePointStateError,
    SharePointMetadataSnapshotV1,
    SharePointMetadataStateStore,
    snapshot_sharepoint_metadata_record,
)
from ets.connectors.models import ConnectorCollectionResultV1, ConnectorEvidenceCandidateV1
from ets.gateway.connector_runner import GatewayConnectorReleaseError

SHAREPOINT_TRANSITION_CLAIM_SCHEMA = "ets.connector.microsoft.sharepoint.metadata_transition.v1"


class SharePointMetadataTransitionCandidateHook:
    """Add a bounded derived transition claim while preserving observed metadata."""

    def __init__(self, store: SharePointMetadataStateStore, *, source_key: str) -> None:
        if not source_key:
            raise ValueError("SharePoint transition source_key is required")
        self._store: SharePointMetadataStateStore = store
        self._source_key: str = source_key

    def transform(
        self,
        record: Mapping[str, JsonValue],
        candidate: ConnectorEvidenceCandidateV1,
    ) -> ConnectorEvidenceCandidateV1:
        """Classify against committed prior state without advancing that state."""

        snapshot = snapshot_sharepoint_metadata_record(record)
        self._validate_candidate_binding(record, candidate, snapshot)
        transition = self._store.classify(self._source_key, snapshot)

        if "derived_transition" in candidate.metadata:
            raise MicrosoftSharePointStateError(
                "SharePoint adapter candidate already contains a derived transition claim"
            )

        kinds: list[JsonValue] = [kind for kind in transition.kinds]
        claim: dict[str, JsonValue] = {
            "schema_version": SHAREPOINT_TRANSITION_CLAIM_SCHEMA,
            "claim_type": "derived_metadata_transition",
            "basis": "successive_minimized_metadata_observations",
            "kinds": kinds,
            "prior_metadata_sha256": transition.prior_sha256,
            "current_metadata_sha256": transition.current_sha256,
        }
        metadata: dict[str, JsonValue] = dict(candidate.metadata)
        metadata["derived_transition"] = claim
        return candidate.model_copy(update={"metadata": metadata})

    @staticmethod
    def _validate_candidate_binding(
        record: Mapping[str, JsonValue],
        candidate: ConnectorEvidenceCandidateV1,
        snapshot: SharePointMetadataSnapshotV1,
    ) -> None:
        if candidate.source_record_id != record.get("source_record_id"):
            raise MicrosoftSharePointStateError(
                "SharePoint transition candidate source record does not match collection record"
            )
        if candidate.metadata.get("object_id") != snapshot.object_id:
            raise MicrosoftSharePointStateError(
                "SharePoint transition candidate object does not match collection record"
            )
        if candidate.metadata.get("scope") != snapshot.scope:
            raise MicrosoftSharePointStateError(
                "SharePoint transition candidate scope does not match collection record"
            )
        if candidate.metadata.get("deleted") is not snapshot.deleted:
            raise MicrosoftSharePointStateError(
                "SharePoint transition candidate deletion state does not match collection record"
            )
        if candidate.metadata.get("metadata") != snapshot.metadata:
            raise MicrosoftSharePointStateError(
                "SharePoint transition candidate does not preserve observed minimized metadata"
            )


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
