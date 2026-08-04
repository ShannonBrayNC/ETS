from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from ets.api.app import create_app
from ets.api.auth import ProductionJWTAuthPolicy
from ets.api.telemetry import emit_security_event
from ets.core.signing import TreeHeadSigner
from ets.core.tree_head import SignedTreeHead


class FailingSigner(TreeHeadSigner):
    def sign(self, tree_head: SignedTreeHead) -> SignedTreeHead:
        raise RuntimeError("signer unavailable")


def telemetry_payloads(caplog) -> list[dict[str, object]]:
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "ets.telemetry"
    ]


def test_emit_security_event_uses_application_insights_shape(caplog) -> None:
    caplog.set_level(logging.INFO, logger="ets.telemetry")

    emit_security_event(
        "ets.auth.rejected",
        severity="Warning",
        correlation_id="corr_001",
        dimensions={"reason": "missing bearer token"},
    )

    [payload] = telemetry_payloads(caplog)
    assert payload["name"] == "ets.auth.rejected"
    assert payload["severityLevel"] == "Warning"
    assert payload["customDimensions"]["component"] == "ets-api"
    assert payload["customDimensions"]["correlation_id"] == "corr_001"
    assert payload["customDimensions"]["reason"] == "missing bearer token"


def test_auth_failure_emits_application_insights_compatible_event(caplog) -> None:
    caplog.set_level(logging.INFO, logger="ets.telemetry")
    client = TestClient(
        create_app(
            auth_policy=ProductionJWTAuthPolicy("s" * 32),
            auth_mode="production_jwt",
        )
    )

    response = client.get("/api/v1/events", headers={"X-Correlation-ID": "corr_auth"})

    assert response.status_code == 401
    [payload] = telemetry_payloads(caplog)
    assert payload["name"] == "ets.auth.rejected"
    assert payload["severityLevel"] == "Warning"
    assert payload["customDimensions"]["correlation_id"] == "corr_auth"
    assert payload["customDimensions"]["auth_mode"] == "production_jwt"


def test_signing_failure_emits_application_insights_compatible_event(caplog) -> None:
    caplog.set_level(logging.INFO, logger="ets.telemetry")
    client = TestClient(create_app(signer=FailingSigner(), signing_mode="production"))

    try:
        client.get("/api/v1/log/head")
    except RuntimeError:
        pass

    [payload] = telemetry_payloads(caplog)
    assert payload["name"] == "ets.signing.failed"
    assert payload["severityLevel"] == "Error"
    assert payload["customDimensions"]["log_id"] == "ets-local-dev"
    assert payload["customDimensions"]["reason"] == "signer unavailable"
