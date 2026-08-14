"""File/drop extension of the shared Gateway ingestion lifecycle."""

from __future__ import annotations

from dataclasses import replace

from ets.gateway.file_capture import GatewayFileCaptureRequest, build_file_capture
from ets.gateway.ingress import (
    GatewayIngressError,
    GatewayIngressReceipt,
    GatewayIngressService,
    _stable_event_identity,
)


class GatewayFileIngressService(GatewayIngressService):
    """Add qualified file observations without creating a second commit implementation."""

    def ingest_file(
        self,
        principal: str,
        request: GatewayFileCaptureRequest,
    ) -> GatewayIngressReceipt:
        """Ingest one qualified file observation under server-authorized source scope."""

        registration = self._registry.resolve(principal)
        resolved_request = (
            request
            if request.received_at_utc is not None
            else replace(request, received_at_utc=self._now())
        )
        mapped = build_file_capture(
            registration,
            resolved_request,
            collector_id=self._config.collector_id,
        )
        idempotency_key = mapped.envelope.source.idempotency_key
        if idempotency_key is None:
            raise GatewayIngressError("file capture requires an idempotency identity")
        stable_id = _stable_event_identity(registration, idempotency_key)
        event_id = f"gateway:{stable_id}"
        evidence_id = f"gateway-evidence:{stable_id}"
        return self._commit_capture(
            registration,
            mapped.envelope,
            event_id=event_id,
            evidence_id=evidence_id,
            content_hash=mapped.envelope.content_digest.value,
        )
