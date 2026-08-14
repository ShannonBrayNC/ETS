"""Native Gateway connector definitions bound to existing G1 transport owners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ets.connectors.models import ConnectorDefinitionV1, ConnectorHealthV1, ConnectorInstanceV1
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.sdk import ConnectorCapabilityError, ConnectorConfigurationError

NativeConnectorReadiness = Literal["qualified", "transport_pending"]
NativeAssuranceLabel = Literal["production_preferred", "bounded_local", "compatibility"]


@dataclass(frozen=True, slots=True)
class NativeConnectorBinding:
    """Bind one catalog connector to a qualified G1 runtime without duplicating it."""

    connector_id: str
    runtime_owner: str
    transport_profile: str
    readiness: NativeConnectorReadiness
    assurance_label: NativeAssuranceLabel
    allowed_setting_keys: frozenset[str]


NATIVE_CONNECTOR_BINDINGS: dict[str, NativeConnectorBinding] = {
    "native.webhook": NativeConnectorBinding(
        connector_id="native.webhook",
        runtime_owner="ets.gateway.host_runner/create_gateway_app",
        transport_profile="ets.gateway.https.v1",
        readiness="qualified",
        assurance_label="production_preferred",
        allowed_setting_keys=frozenset(
            {
                "bind_host",
                "bind_port",
                "max_body_bytes",
                "max_concurrency",
                "request_timeout_seconds",
            }
        ),
    ),
    "native.syslog": NativeConnectorBinding(
        connector_id="native.syslog",
        runtime_owner="ets.gateway.syslog_host/GatewaySyslogHost",
        transport_profile="ets.gateway.syslog-tls.v1",
        readiness="qualified",
        assurance_label="production_preferred",
        allowed_setting_keys=frozenset(
            {
                "bind_host",
                "bind_port",
                "max_connections",
                "max_message_bytes",
                "read_idle_timeout_seconds",
            }
        ),
    ),
    "native.file_drop": NativeConnectorBinding(
        connector_id="native.file_drop",
        runtime_owner="ets.gateway.file_drop_host/GatewayFileDropHost",
        transport_profile="ets.gateway.file-drop.v1",
        readiness="qualified",
        assurance_label="bounded_local",
        allowed_setting_keys=frozenset(
            {
                "intake_root",
                "max_concurrent_submissions",
                "max_object_bytes",
                "read_chunk_bytes",
                "graceful_shutdown_seconds",
            }
        ),
    ),
    "native.otlp": NativeConnectorBinding(
        connector_id="native.otlp",
        runtime_owner="GATE-G1F-C/GATE-G1F-D",
        transport_profile="ets.gateway.otlp.v1",
        readiness="transport_pending",
        assurance_label="production_preferred",
        allowed_setting_keys=frozenset(
            {
                "bind_host",
                "http_port",
                "grpc_port",
                "max_request_bytes",
                "max_concurrency",
                "processing_timeout_seconds",
            }
        ),
    ),
}


class NativeConnectorAdapter:
    """Management adapter for push-native G1 transports.

    Parsing, authorization, normalization, ETS commitment, and synchronization remain owned by
    the qualified G1 runtime. This adapter exists only to validate shared connector configuration
    and expose truthful management health while the concrete host binding remains external.
    """

    def __init__(self, definition: ConnectorDefinitionV1, binding: NativeConnectorBinding) -> None:
        if definition.connector_id != binding.connector_id:
            raise ValueError("native connector definition and runtime binding ids must match")
        if definition.implementation_class != "native":
            raise ValueError("native connector adapter requires a native definition")
        self._definition = definition
        self._binding = binding

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    @property
    def binding(self) -> NativeConnectorBinding:
        return self._binding

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        unexpected = sorted(set(instance.settings) - self._binding.allowed_setting_keys)
        if unexpected:
            raise ConnectorConfigurationError(
                "unsupported native connector settings: " + ", ".join(unexpected)
            )
        if instance.collection.mode != "push":
            raise ConnectorConfigurationError("native Gateway connectors require push collection")

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        if self._binding.readiness == "transport_pending":
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="unsupported",
                message="native transport is declared but has not completed G1 qualification",
            )
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="unknown",
            code="unknown_observation",
            message=(
                "native connector configuration is valid; host liveness must be supplied by "
                "the owning Gateway transport runtime"
            ),
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        raise ConnectorCapabilityError("native push connectors do not implement discovery")

    def collect(self, instance: ConnectorInstanceV1, checkpoint: object) -> object:
        self.validate_config(instance)
        raise ConnectorCapabilityError("native push connectors do not implement polling")

    def checkpoint(self, result: object) -> None:
        raise ConnectorCapabilityError("native push connectors do not expose source checkpoints")

    def reconcile(self, instance: ConnectorInstanceV1, checkpoint: object) -> object:
        self.validate_config(instance)
        raise ConnectorCapabilityError("native push connectors do not implement reconciliation")

    def normalize(self, instance: ConnectorInstanceV1, record: object) -> object:
        self.validate_config(instance)
        raise ConnectorCapabilityError("native G1 runtimes own normalization")

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)


def load_native_connector_registry(manifest_directory: Path) -> ConnectorRegistry:
    """Load shipped native definitions and register management-only native adapters."""

    registry = ConnectorRegistry.from_manifest_directory(manifest_directory)
    for definition in registry.list_definitions():
        try:
            binding = NATIVE_CONNECTOR_BINDINGS[definition.connector_id]
        except KeyError as exc:
            raise ConnectorConfigurationError(
                f"native connector definition has no G1 runtime binding: {definition.connector_id}"
            ) from exc
        registry.register_adapter(NativeConnectorAdapter(definition, binding))
    return registry
