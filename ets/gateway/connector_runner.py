"""Governed collection runner joining enterprise adapters to shared Gateway commitment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue

from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorInstanceV1,
    ConnectorOperationCode,
)
from ets.connectors.sdk import ConnectorAdapter
from ets.gateway.connector_capture import GatewayConnectorCandidateRequest
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressError,
    GatewayPartialCommitError,
)


@dataclass(frozen=True, slots=True)
class GatewayConnectorRunResult:
    """One bounded collection/commit pass; only successful runs expose a checkpoint to persist."""

    code: ConnectorOperationCode
    source_records: int
    committed_local: int
    sync_queued: int
    partial_commit: int
    checkpoint_to_persist: ConnectorCheckpointV1 | None
    has_more: bool
    message: str


class GatewayConnectorCollectionRunner:
    """Collect, normalize, and commit a connector page before releasing its checkpoint."""

    def __init__(self, ingress: GatewayConnectorIngressService) -> None:
        self._ingress = ingress

    def run(
        self,
        *,
        adapter: ConnectorAdapter,
        instance: ConnectorInstanceV1,
        principal: str,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> GatewayConnectorRunResult:
        collection = adapter.collect(instance, checkpoint)
        if collection.code != "ok":
            return GatewayConnectorRunResult(
                code=collection.code,
                source_records=len(collection.records),
                committed_local=0,
                sync_queued=0,
                partial_commit=0,
                checkpoint_to_persist=None,
                has_more=collection.has_more,
                message=collection.message or "connector collection did not qualify",
            )

        committed_local = 0
        sync_queued = 0
        for record in collection.records:
            result = self._commit_record(
                adapter=adapter,
                instance=instance,
                principal=principal,
                record=record,
            )
            if result is not None:
                return GatewayConnectorRunResult(
                    code=result.code,
                    source_records=len(collection.records),
                    committed_local=committed_local + result.committed_local,
                    sync_queued=sync_queued + result.sync_queued,
                    partial_commit=result.partial_commit,
                    checkpoint_to_persist=None,
                    has_more=collection.has_more,
                    message=result.message,
                )
            committed_local += 1
            sync_queued += 1

        return GatewayConnectorRunResult(
            code="ok",
            source_records=len(collection.records),
            committed_local=committed_local,
            sync_queued=sync_queued,
            partial_commit=0,
            checkpoint_to_persist=collection.checkpoint,
            has_more=collection.has_more,
            message="connector page committed locally and queued for synchronization",
        )

    def _commit_record(
        self,
        *,
        adapter: ConnectorAdapter,
        instance: ConnectorInstanceV1,
        principal: str,
        record: Mapping[str, JsonValue],
    ) -> GatewayConnectorRunResult | None:
        try:
            candidate = adapter.normalize(instance, record)
            receipt = self._ingress.ingest_candidate(
                principal,
                GatewayConnectorCandidateRequest(candidate=candidate),
            )
        except GatewayPartialCommitError:
            return GatewayConnectorRunResult(
                code="retryable_error",
                source_records=1,
                committed_local=1,
                sync_queued=0,
                partial_commit=1,
                checkpoint_to_persist=None,
                has_more=False,
                message="connector observation committed locally but sync enqueue requires retry",
            )
        except GatewayBackpressureError:
            return GatewayConnectorRunResult(
                code="retryable_error",
                source_records=1,
                committed_local=0,
                sync_queued=0,
                partial_commit=0,
                checkpoint_to_persist=None,
                has_more=False,
                message="Gateway synchronization capacity is unavailable",
            )
        except GatewayConflictError:
            return GatewayConnectorRunResult(
                code="terminal_error",
                source_records=1,
                committed_local=0,
                sync_queued=0,
                partial_commit=0,
                checkpoint_to_persist=None,
                has_more=False,
                message="connector source identity conflicts with existing immutable evidence",
            )
        except (GatewayIngressError, ValueError):
            return GatewayConnectorRunResult(
                code="terminal_error",
                source_records=1,
                committed_local=0,
                sync_queued=0,
                partial_commit=0,
                checkpoint_to_persist=None,
                has_more=False,
                message="connector observation failed normalization or Gateway capture validation",
            )

        if not receipt.committed_local or not receipt.sync_queued:
            return GatewayConnectorRunResult(
                code="retryable_error",
                source_records=1,
                committed_local=int(receipt.committed_local),
                sync_queued=int(receipt.sync_queued),
                partial_commit=0,
                checkpoint_to_persist=None,
                has_more=False,
                message="connector observation did not reach qualified queued state",
            )
        return None
