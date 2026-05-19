"""Synthetic non-PII dataset generation for ETS experiments."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ets.core.models import EvidenceEvent


def generate_synthetic_events(count: int, tenant_id: str = "tenant_lab") -> list[EvidenceEvent]:
    if count < 0:
        raise ValueError("count must be non-negative")
    start = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    return [
        EvidenceEvent(
            event_id=f"evt_lab_{index:04d}",
            tenant_id=tenant_id,
            workspace_id="workspace_lab",
            evidence_id=f"evidence_lab_{index:04d}",
            event_type="evidence.synthetic",
            subject_ref=None,
            content_hash=f"{index:064x}"[-64:],
            content_hash_alg="sha256",
            metadata={"case": "synthetic", "ordinal": index},
            created_at_utc=start + timedelta(seconds=index),
            redaction_profile="none",
        )
        for index in range(count)
    ]
