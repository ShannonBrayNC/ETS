"""Product-neutral connector adapter protocol."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorCollectionResultV1,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorReconciliationResultV1,
)


class ConnectorConfigurationError(ValueError):
    """Raised when an adapter rejects connector-specific settings."""


class ConnectorCapabilityError(NotImplementedError):
    """Raised when an adapter method is not declared by its capabilities."""


@runtime_checkable
class ConnectorAdapter(Protocol):
    """Stable G2A adapter contract.

    Implementations never receive signer material or ETS Core internals through this contract.
    Gateway runtime supplies server-authorized scope and capture-policy orchestration outside the
    adapter. `normalize` returns a pre-commit candidate that deliberately has no tenant/workspace,
    Merkle, proof, signature, or signer fields.
    """

    @property
    def definition(self) -> ConnectorDefinitionV1:
        """Return immutable adapter metadata and capability declarations."""
        ...

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        """Validate connector-specific settings after shared schema validation."""
        ...

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        """Test source connectivity without advancing a checkpoint."""
        ...

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        """Return bounded source-resource identifiers when discovery is supported."""
        ...

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        """Collect a bounded source batch without committing ETS evidence."""
        ...

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        """Return the source checkpoint represented by a successful collection result."""
        ...

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        """Report source continuity, known gaps, or unknown observation state."""
        ...

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        """Normalize one already-governed source record into an ETS evidence candidate."""
        ...

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        """Return connector operational health, not ETS evidence verification state."""
        ...
