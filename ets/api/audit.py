"""Structured audit logging for ETS API operations."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

AUDIT_LOGGER_NAME = "ets.audit"


def audit_event(
    operation: str,
    result: str,
    *,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
    event_id: str | None = None,
    correlation_id: str | None = None,
    reason: str | None = None,
) -> None:
    payload = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "operation": operation,
        "result": result,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "event_id": event_id,
        "correlation_id": correlation_id,
        "reason": reason,
    }
    logging.getLogger(AUDIT_LOGGER_NAME).info(
        json.dumps(
            {key: value for key, value in payload.items() if value is not None},
            sort_keys=True,
        )
    )
