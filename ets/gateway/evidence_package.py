"""Product-layer evidence export with connector provenance and continuity declarations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.connectors.enterprise.microsoft_reconciliation import MicrosoftReconciliationGapV1
from ets.core.bundle import EvidenceProofBundle
from ets.core.proofs import VerificationResult
from ets.verifier import verify_bundle

GATEWAY_EVIDENCE_PACKAGE_SCHEMA_VERSION: Literal["ets.gateway.evidence_package.v1"] = (
    "ets.gateway.evidence_package.v1"
)
CONNECTOR_SOURCE_PROVENANCE_SCHEMA_VERSION: Literal[
    "ets.connector.source_provenance.v1"
] = "ets.connector.source_provenance.v1"
CONNECTOR_GAP_DECLARATION_SCHEMA_VERSION: Literal[
    "ets.connector.gap_declaration.v1"
] = "ets.connector.gap_declaration.v1"


class GatewayEvidencePackageError(ValueError):
    """Raised when product-layer evidence declarations cannot be bound safely."""


class StrictEvidencePackageModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ConnectorSourceProvenanceV1(StrictEvidencePackageModel):
    """Connector provenance that is cross-checked against the committed ETS event."""

    schema_version: Literal["ets.connector.source_provenance.v1"] = (
        CONNECTOR_SOURCE_PROVENANCE_SCHEMA_VERSION
    )
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    connector_id: str = Field(min_length=1, max_length=200)
    connector_instance_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    )
    source_id: str = Field(min_length=1, max_length=500)
    source_system: str = Field(min_length=1, max_length=200)
    source_record_id: str = Field(min_length=1, max_length=500)
    transformation_profile: str = Field(min_length=1, max_length=200)
    raw_source_payload_retained: Literal[False] = False


class ConnectorGapDeclarationV1(StrictEvidencePackageModel):
    """Minimized source-continuity declaration carried beside, not inside, proof validity."""

    schema_version: Literal["ets.connector.gap_declaration.v1"] = (
        CONNECTOR_GAP_DECLARATION_SCHEMA_VERSION
    )
    gap_id: str = Field(min_length=1, max_length=200)
    instance_id: str = Field(min_length=1, max_length=128)
    source_system: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=50)
    detected_at_utc: datetime
    updated_at_utc: datetime
    reconciliation_started_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    outcome: str | None = Field(default=None, min_length=1, max_length=50)
    recovered_records: int = Field(default=0, ge=0)
    acknowledged_at_utc: datetime | None = None
    source_completeness_claimed: Literal[False] = False
    affects_cryptographic_verification: Literal[False] = False

    @field_validator(
        "detected_at_utc",
        "updated_at_utc",
        "reconciliation_started_at_utc",
        "resolved_at_utc",
        "acknowledged_at_utc",
    )
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("connector gap declaration timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_temporal_order(self) -> ConnectorGapDeclarationV1:
        if self.updated_at_utc < self.detected_at_utc:
            raise ValueError("connector gap declaration update precedes detection")
        started = self.reconciliation_started_at_utc
        resolved = self.resolved_at_utc
        acknowledged = self.acknowledged_at_utc
        if started is not None and started < self.detected_at_utc:
            raise ValueError("connector gap reconciliation precedes detection")
        if resolved is not None and (started is None or resolved < started):
            raise ValueError("connector gap resolution precedes reconciliation")
        if acknowledged is not None and (resolved is None or acknowledged < resolved):
            raise ValueError("connector gap acknowledgement precedes resolution")
        lifecycle_times = tuple(
            value for value in (started, resolved, acknowledged) if value is not None
        )
        if any(self.updated_at_utc < value for value in lifecycle_times):
            raise ValueError("connector gap update precedes lifecycle state")
        return self


class GatewayEvidencePackageV1(StrictEvidencePackageModel):
    """Portable proof bundle plus non-normative connector operational declarations."""

    schema_version: Literal["ets.gateway.evidence_package.v1"] = (
        GATEWAY_EVIDENCE_PACKAGE_SCHEMA_VERSION
    )
    proof_bundle: EvidenceProofBundle
    source_provenance: ConnectorSourceProvenanceV1
    gap_declarations: tuple[ConnectorGapDeclarationV1, ...] = Field(
        default_factory=tuple,
        max_length=100,
    )
    exported_at_utc: datetime
    verification_claimed_by_operational_declarations: Literal[False] = False
    source_truth_claimed: Literal[False] = False
    source_completeness_claimed: Literal[False] = False

    @field_validator("exported_at_utc")
    @classmethod
    def normalize_export_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence package export timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def bind_operational_declarations_to_committed_event(self) -> GatewayEvidencePackageV1:
        _validate_source_provenance(self.proof_bundle, self.source_provenance)
        if self.exported_at_utc < self.proof_bundle.tree_head.created_at_utc:
            raise ValueError("evidence package export precedes proof tree head")

        instance_id = self.source_provenance.connector_instance_id
        seen_gap_ids: set[str] = set()
        for gap in self.gap_declarations:
            if gap.gap_id in seen_gap_ids:
                raise ValueError("evidence package contains duplicate connector gap_id")
            seen_gap_ids.add(gap.gap_id)
            if gap.source_system != self.source_provenance.source_system:
                raise ValueError(
                    "connector gap declaration source_system does not match package provenance"
                )
            if instance_id is None:
                raise ValueError(
                    "connector gap declaration requires event-bound connector instance provenance"
                )
            if gap.instance_id != instance_id:
                raise ValueError(
                    "connector gap declaration instance_id does not match package provenance"
                )
            if gap.detected_at_utc > self.exported_at_utc:
                raise ValueError("connector gap declaration was detected after package export")
            if gap.updated_at_utc > self.exported_at_utc:
                raise ValueError("connector gap declaration was updated after package export")
        return self


def microsoft_gap_declaration(
    gap: MicrosoftReconciliationGapV1,
) -> ConnectorGapDeclarationV1:
    """Project qualified Microsoft gap state into a minimized evidence-package declaration."""

    return ConnectorGapDeclarationV1(
        gap_id=gap.gap_id,
        instance_id=gap.instance_id,
        source_system=gap.source_system,
        reason=gap.reason,
        status=gap.status,
        detected_at_utc=gap.detected_at_utc,
        updated_at_utc=gap.updated_at_utc,
        reconciliation_started_at_utc=gap.reconciliation_started_at_utc,
        resolved_at_utc=gap.resolved_at_utc,
        outcome=gap.outcome,
        recovered_records=gap.recovered_records,
        acknowledged_at_utc=gap.acknowledged_at_utc,
    )


def verify_gateway_evidence_package(
    package: GatewayEvidencePackageV1,
) -> VerificationResult:
    """Verify only the embedded ETS proof bundle.

    Connector provenance and gap declarations are operational context. They are validated for
    bounded structure and source binding when the package is parsed, but they never alter the
    cryptographic verification algorithm or its result.
    """

    return verify_bundle(package.proof_bundle)


def _validate_source_provenance(
    bundle: EvidenceProofBundle,
    provenance: ConnectorSourceProvenanceV1,
) -> None:
    event = bundle.event
    if event.tenant_id != provenance.tenant_id or event.workspace_id != provenance.workspace_id:
        raise GatewayEvidencePackageError(
            "connector source provenance tenant/workspace does not match committed event"
        )
    if event.source_system != provenance.source_system:
        raise GatewayEvidencePackageError(
            "connector source provenance source_system does not match committed event"
        )

    metadata = event.metadata
    if metadata.get("adapter_id") != provenance.connector_id:
        raise GatewayEvidencePackageError(
            "connector source provenance connector_id does not match committed event"
        )
    source = metadata.get("source")
    if not isinstance(source, dict) or source.get("identifier") != provenance.source_id:
        raise GatewayEvidencePackageError(
            "connector source provenance source_id does not match committed event"
        )
    capture_metadata = metadata.get("capture_metadata")
    if not isinstance(capture_metadata, dict):
        raise GatewayEvidencePackageError(
            "committed event is missing connector capture provenance metadata"
        )
    if capture_metadata.get("connector_source_system") != provenance.source_system:
        raise GatewayEvidencePackageError(
            "connector source provenance source_system conflicts with capture metadata"
        )
    committed_instance_id = capture_metadata.get("connector_instance_id")
    if committed_instance_id != provenance.connector_instance_id:
        raise GatewayEvidencePackageError(
            "connector source provenance instance_id does not match committed event"
        )
    if capture_metadata.get("connector_source_record_id") != provenance.source_record_id:
        raise GatewayEvidencePackageError(
            "connector source provenance source_record_id does not match committed event"
        )
    if (
        capture_metadata.get("connector_transformation_profile")
        != provenance.transformation_profile
    ):
        raise GatewayEvidencePackageError(
            "connector source provenance transformation profile does not match committed event"
        )
    if capture_metadata.get("raw_source_payload_retained") is not False:
        raise GatewayEvidencePackageError(
            "connector evidence package requires committed no-raw-payload retention posture"
        )
