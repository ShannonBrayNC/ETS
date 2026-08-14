"""Versioned, product-neutral connector models for ETS Gateway integrations."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

CONNECTOR_DEFINITION_SCHEMA_VERSION = "ets.connector.definition.v1"
CONNECTOR_INSTANCE_SCHEMA_VERSION = "ets.connector.instance.v1"
CONNECTOR_SDK_CONTRACT_VERSION = "ets.connector.sdk.v1"
CAPTURE_ENVELOPE_VERSION = "ets.capture.v1"
GATEWAY_CONNECTOR_HOST_VERSION = "ets.gateway.connector-host.v1"

MAX_CONNECTOR_MAPPING_BYTES = 32 * 1024
CONNECTOR_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
INSTANCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SETTING_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PROHIBITED_SECRET_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "client_secret",
        "credential",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
    }
)

ConnectorDeliveryMode = Literal["push", "poll"]
ConnectorHealthState = Literal["healthy", "degraded", "failed", "unknown"]
ConnectorOperationCode = Literal[
    "ok",
    "unsupported",
    "invalid_config",
    "authentication_failed",
    "authorization_failed",
    "throttled",
    "retryable_error",
    "terminal_error",
    "gap_detected",
    "unknown_observation",
    "incompatible_version",
]


class StrictConnectorModel(BaseModel):
    """Strict immutable base for the connector contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ConnectorCapabilities(StrictConnectorModel):
    """Capabilities declared by a connector definition."""

    delivery_modes: tuple[ConnectorDeliveryMode, ...] = Field(min_length=1, max_length=2)
    authentication_methods: tuple[str, ...] = Field(min_length=1, max_length=16)
    discovery: bool = False
    checkpointing: bool = False
    reconciliation: bool = False
    normalization: bool = True
    health: bool = True

    @field_validator("delivery_modes")
    @classmethod
    def unique_delivery_modes(
        cls, value: tuple[ConnectorDeliveryMode, ...]
    ) -> tuple[ConnectorDeliveryMode, ...]:
        if len(set(value)) != len(value):
            raise ValueError("delivery_modes must not contain duplicates")
        return value

    @field_validator("authentication_methods")
    @classmethod
    def validate_authentication_methods(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(method.strip() for method in value)
        if any(not method or len(method) > 100 for method in normalized):
            raise ValueError("authentication_methods must contain values 1-100 characters long")
        if len(set(normalized)) != len(normalized):
            raise ValueError("authentication_methods must not contain duplicates")
        return normalized


class ConnectorConfigurationSchema(StrictConnectorModel):
    """Schema references declared by a connector definition."""

    instance_schema: Literal["ets.connector.instance.v1"]
    settings_schema_ref: str | None = Field(default=None, min_length=1, max_length=500)


class ConnectorDefinitionV1(StrictConnectorModel):
    """Versioned connector type metadata shipped by ETS or a qualified extension."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.net/schemas/connectors/v1/"
                "connector-definition.schema.json"
            ),
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        },
    )

    schema_version: Literal["ets.connector.definition.v1"]
    connector_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    display_name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    implementation_class: Literal["native", "enterprise_api", "generic", "third_party"]
    source_classes: tuple[str, ...] = Field(min_length=1, max_length=16)
    adapter_version: str = Field(min_length=1, max_length=100)
    sdk_contract_version: Literal["ets.connector.sdk.v1"]
    capture_envelope_versions: tuple[str, ...] = Field(min_length=1, max_length=8)
    gateway_host_versions: tuple[str, ...] = Field(min_length=1, max_length=8)
    capabilities: ConnectorCapabilities
    configuration_schema: ConnectorConfigurationSchema

    @field_validator("source_classes", "capture_envelope_versions", "gateway_host_versions")
    @classmethod
    def unique_bounded_strings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item or len(item) > 200 for item in normalized):
            raise ValueError("connector list entries must be 1-200 characters long")
        if len(set(normalized)) != len(normalized):
            raise ValueError("connector list entries must not contain duplicates")
        return normalized


class ConnectorScope(StrictConnectorModel):
    """Requested ETS scope; runtime authorization remains server-side."""

    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)


class ConnectorSource(StrictConnectorModel):
    """Human-readable source identity and deployment environment."""

    name: str = Field(min_length=1, max_length=200)
    environment: str = Field(min_length=1, max_length=100)


class ConnectorAuthentication(StrictConnectorModel):
    """Authentication metadata containing only an opaque credential reference."""

    method: str = Field(min_length=1, max_length=100)
    credential_ref: str | None = Field(default=None, min_length=1, max_length=500)


class ConnectorCollection(StrictConnectorModel):
    """Generic collection controls shared by push and polling adapters."""

    mode: ConnectorDeliveryMode
    interval_seconds: int | None = Field(default=None, ge=1, le=86_400)
    batch_size: int = Field(default=500, ge=1, le=10_000)

    @model_validator(mode="after")
    def require_poll_interval(self) -> ConnectorCollection:
        if self.mode == "poll" and self.interval_seconds is None:
            raise ValueError("poll connectors require interval_seconds")
        if self.mode == "push" and self.interval_seconds is not None:
            raise ValueError("push connectors must not set interval_seconds")
        return self


class ConnectorCheckpointPolicy(StrictConnectorModel):
    strategy: Literal["none", "source_cursor", "time_window", "source_sequence"] = "none"
    durable: bool = True


class ConnectorPolicyBinding(StrictConnectorModel):
    """References to governed policy/normalization profiles, not inline policy logic."""

    capture_profile: str = Field(min_length=1, max_length=200)
    normalization_profile: str = Field(min_length=1, max_length=200)


class ConnectorRetryPolicy(StrictConnectorModel):
    max_attempts: int = Field(default=8, ge=0, le=100)
    backoff: Literal["fixed", "exponential"] = "exponential"
    max_age_seconds: int = Field(default=86_400, ge=1, le=2_592_000)


class ConnectorGapPolicy(StrictConnectorModel):
    enabled: bool = True


class ConnectorInstanceV1(StrictConnectorModel):
    """Customer connector configuration without reusable credential material."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.net/schemas/connectors/v1/"
                "connector-instance.schema.json"
            ),
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        },
    )

    schema_version: Literal["ets.connector.instance.v1"]
    instance_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    connector_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    connector_version: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    scope: ConnectorScope
    source: ConnectorSource
    authentication: ConnectorAuthentication
    collection: ConnectorCollection
    checkpoint: ConnectorCheckpointPolicy = Field(default_factory=ConnectorCheckpointPolicy)
    policy: ConnectorPolicyBinding
    retry: ConnectorRetryPolicy = Field(default_factory=ConnectorRetryPolicy)
    gap_detection: ConnectorGapPolicy = Field(default_factory=ConnectorGapPolicy)
    settings: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_mapping(value, enforce_setting_keys=True)
        _reject_embedded_secret_keys(value)
        return value


class ConnectorCheckpointV1(StrictConnectorModel):
    """Opaque source checkpoint state; it is not ETS Merkle state."""

    schema_version: Literal["ets.connector.checkpoint.v1"]
    cursor: str | None = Field(default=None, min_length=1, max_length=4000)
    sequence: int | str | None = None
    observed_through_utc: datetime | None = None

    @field_validator("observed_through_utc")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checkpoint timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("sequence")
    @classmethod
    def bound_sequence(cls, value: int | str | None) -> int | str | None:
        if isinstance(value, str) and not 1 <= len(value) <= 500:
            raise ValueError("checkpoint sequence strings must be 1-500 characters")
        return value


class ConnectorEvidenceCandidateV1(StrictConnectorModel):
    """Normalized pre-commit candidate with no authoritative scope or proof fields."""

    schema_version: Literal["ets.connector.candidate.v1"]
    source_record_id: str = Field(min_length=1, max_length=500)
    source_system: str = Field(min_length=1, max_length=200)
    observed_at_utc: datetime | None = None
    event_type: str = Field(min_length=1, max_length=128)
    media_type: str | None = Field(default=None, min_length=1, max_length=200)
    transformation_profile: str = Field(min_length=1, max_length=200)
    lossless: bool
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("candidate timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_mapping(value)
        return value


class ConnectorHealthV1(StrictConnectorModel):
    """Connector operational state, explicitly distinct from evidence verification."""

    schema_version: Literal["ets.connector.health.v1"]
    state: ConnectorHealthState
    code: ConnectorOperationCode
    message: str = Field(min_length=1, max_length=1000)
    retry_after_seconds: int | None = Field(default=None, ge=1, le=86_400)


class ConnectorCollectionResultV1(StrictConnectorModel):
    """Bounded adapter collection result before Gateway commitment."""

    schema_version: Literal["ets.connector.collection_result.v1"]
    code: ConnectorOperationCode
    records: tuple[dict[str, JsonValue], ...] = Field(default_factory=tuple, max_length=10_000)
    checkpoint: ConnectorCheckpointV1 | None = None
    has_more: bool = False
    message: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("records")
    @classmethod
    def validate_records(
        cls, value: tuple[dict[str, JsonValue], ...]
    ) -> tuple[dict[str, JsonValue], ...]:
        for record in value:
            _validate_mapping(record)
        return value


class ConnectorReconciliationResultV1(StrictConnectorModel):
    """Explicit reconciliation/gap result for source-observation continuity."""

    schema_version: Literal["ets.connector.reconciliation_result.v1"]
    code: ConnectorOperationCode
    reconciled: bool
    gap_detected: bool
    checkpoint: ConnectorCheckpointV1 | None = None
    message: str | None = Field(default=None, min_length=1, max_length=1000)


def _validate_mapping(
    value: dict[str, JsonValue], *, enforce_setting_keys: bool = False
) -> None:
    if enforce_setting_keys:
        invalid = [key for key in value if SETTING_KEY_PATTERN.fullmatch(key) is None]
        if invalid:
            raise ValueError("connector setting keys must match the connector key pattern")
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("connector mappings must contain JSON-native values") from exc
    if len(encoded) > MAX_CONNECTOR_MAPPING_BYTES:
        raise ValueError("connector mappings must not exceed 32 KiB")


def _reject_embedded_secret_keys(value: dict[str, JsonValue]) -> None:
    stack: list[JsonValue] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, child in current.items():
                if key.casefold() in PROHIBITED_SECRET_KEYS:
                    raise ValueError(
                        "connector settings must reference credentials; "
                        f"embedded key {key!r} is prohibited"
                    )
                stack.append(child)
        elif isinstance(current, list):
            stack.extend(current)
