"""Application Insights-compatible telemetry helpers for hosted ETS."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

LOGGER = logging.getLogger("ets.telemetry")


def emit_security_event(
    name: str,
    *,
    severity: str,
    correlation_id: str | None = None,
    dimensions: dict[str, Any] | None = None,
) -> None:
    """Emit a structured security event compatible with Application Insights logs."""

    payload: dict[str, Any] = {
        "name": name,
        "time": datetime.now(UTC).isoformat(),
        "severityLevel": severity,
        "customDimensions": {
            "component": "ets-api",
            "correlation_id": correlation_id,
            **(dimensions or {}),
        },
    }
    LOGGER.info(json.dumps(payload, sort_keys=True, separators=(",", ":")))
