"""Reusable connector contract checks for built-in and enterprise adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue

from ets.connectors.models import ConnectorEvidenceCandidateV1, ConnectorInstanceV1
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.sdk import ConnectorAdapter


@dataclass(frozen=True, slots=True)
class ConnectorConformanceReport:
    connector_id: str
    adapter_version: str
    instance_valid: bool
    candidate_valid: bool


class ConnectorConformanceHarness:
    """Minimal reusable G2A conformance harness.

    Source-specific qualification remains the responsibility of each connector tranche. This
    harness checks the shared contract: registry compatibility, adapter configuration, and the
    normalized candidate boundary before Gateway capture/commit processing.
    """

    def __init__(self, registry: ConnectorRegistry) -> None:
        self._registry = registry

    def validate_sample(
        self,
        adapter: ConnectorAdapter,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorConformanceReport:
        registered = self._registry.validate_adapter_instance(instance)
        if registered is not adapter:
            raise ValueError("registered adapter does not match supplied adapter")
        candidate = adapter.normalize(instance, record)
        # Re-validate even if the adapter annotated the return type incorrectly at runtime.
        validated = ConnectorEvidenceCandidateV1.model_validate(candidate.model_dump(mode="python"))
        return ConnectorConformanceReport(
            connector_id=adapter.definition.connector_id,
            adapter_version=adapter.definition.adapter_version,
            instance_valid=True,
            candidate_valid=validated == candidate,
        )
