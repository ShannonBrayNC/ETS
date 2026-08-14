"""Bounded Gateway push integration for Kubernetes audit webhook batches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ets.connectors.enterprise.kubernetes import (
    KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS,
    KUBERNETES_DEFAULT_MAXIMUM_EVENT_BYTES,
    KubernetesAuditAdapter,
    parse_kubernetes_audit_event_list,
)
from ets.connectors.models import ConnectorInstanceV1
from ets.gateway.connector_capture import GatewayConnectorCandidateRequest
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.ingress import GatewayIngressReceipt, GatewayPartialCommitError


@dataclass(frozen=True, slots=True)
class GatewayKubernetesAuditBatchResult:
    """Successful batch result without implying source-delivery completeness."""

    decoded_events: int
    committed_local: int
    sync_queued: int
    duplicates: int
    receipts: tuple[GatewayIngressReceipt, ...]


class GatewayKubernetesAuditBatchError(RuntimeError):
    """Fail-closed batch error preserving only already-produced ETS receipts."""

    def __init__(
        self,
        *,
        failed_index: int,
        receipts: tuple[GatewayIngressReceipt, ...],
    ) -> None:
        super().__init__(
            f"Kubernetes audit batch processing failed at event index {failed_index}"
        )
        self.failed_index = failed_index
        self.receipts = receipts


class GatewayKubernetesAuditIngressService:
    """Decode, minimize and commit authenticated Kubernetes audit batches in order."""

    def __init__(
        self,
        *,
        adapter: KubernetesAuditAdapter,
        ingress: GatewayConnectorIngressService,
    ) -> None:
        self._adapter = adapter
        self._ingress = ingress

    def ingest(
        self,
        *,
        principal: str,
        instance: ConnectorInstanceV1,
        body: bytes,
        correlation_id: str | None = None,
        received_at_utc: datetime | None = None,
    ) -> GatewayKubernetesAuditBatchResult:
        """Commit one authenticated webhook batch without processing past a failed event."""

        self._adapter.validate_config(instance)
        maximum_batch_events = _integer_setting(
            instance,
            "maximum_batch_events",
            KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS,
        )
        maximum_event_bytes = _integer_setting(
            instance,
            "maximum_event_bytes",
            KUBERNETES_DEFAULT_MAXIMUM_EVENT_BYTES,
        )
        batch = parse_kubernetes_audit_event_list(
            body,
            maximum_body_bytes=self._ingress.max_body_bytes,
            maximum_batch_events=maximum_batch_events,
            maximum_event_bytes=maximum_event_bytes,
        )
        receipt_time = received_at_utc or datetime.now(UTC)
        if receipt_time.tzinfo is None or receipt_time.utcoffset() is None:
            raise ValueError("received_at_utc must be timezone-aware")
        receipt_time = receipt_time.astimezone(UTC)

        receipts: list[GatewayIngressReceipt] = []
        for index, record in enumerate(batch.records):
            try:
                candidate = self._adapter.normalize(instance, record)
                receipt = self._ingress.ingest_candidate(
                    principal,
                    GatewayConnectorCandidateRequest(
                        candidate=candidate,
                        correlation_id=correlation_id,
                        received_at_utc=receipt_time,
                    ),
                )
            except GatewayPartialCommitError as exc:
                receipts.append(exc.receipt)
                raise GatewayKubernetesAuditBatchError(
                    failed_index=index,
                    receipts=tuple(receipts),
                ) from exc
            except Exception as exc:
                raise GatewayKubernetesAuditBatchError(
                    failed_index=index,
                    receipts=tuple(receipts),
                ) from exc
            receipts.append(receipt)

        return GatewayKubernetesAuditBatchResult(
            decoded_events=len(batch.records),
            committed_local=sum(receipt.committed_local for receipt in receipts),
            sync_queued=sum(receipt.sync_queued for receipt in receipts),
            duplicates=sum(receipt.duplicate for receipt in receipts),
            receipts=tuple(receipts),
        )


def _integer_setting(
    instance: ConnectorInstanceV1,
    key: str,
    default: int,
) -> int:
    value = instance.settings.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"validated Kubernetes setting {key} is not an integer")
    return value
