"""Connector definition registry, compatibility checks, and manifest discovery."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from ets.connectors.models import (
    CAPTURE_ENVELOPE_VERSION,
    CONNECTOR_SDK_CONTRACT_VERSION,
    GATEWAY_CONNECTOR_HOST_VERSION,
    ConnectorDefinitionV1,
    ConnectorInstanceV1,
)
from ets.connectors.sdk import ConnectorAdapter


class ConnectorRegistryError(ValueError):
    """Base error for registry and manifest failures."""


class ConnectorNotFoundError(ConnectorRegistryError):
    """Raised when an instance references an unknown connector id."""


class ConnectorCompatibilityError(ConnectorRegistryError):
    """Raised when connector, SDK, or capture contract versions are incompatible."""


class ConnectorRegistry:
    """Deterministic registry for versioned connector definitions and adapters."""

    def __init__(
        self,
        definitions: Iterable[ConnectorDefinitionV1] = (),
        *,
        sdk_contract_version: str = CONNECTOR_SDK_CONTRACT_VERSION,
        capture_envelope_version: str = CAPTURE_ENVELOPE_VERSION,
        gateway_host_version: str = GATEWAY_CONNECTOR_HOST_VERSION,
    ) -> None:
        self._definitions: dict[str, ConnectorDefinitionV1] = {}
        self._adapters: dict[str, ConnectorAdapter] = {}
        self._sdk_contract_version = sdk_contract_version
        self._capture_envelope_version = capture_envelope_version
        self._gateway_host_version = gateway_host_version
        for definition in definitions:
            self.register_definition(definition)

    @property
    def sdk_contract_version(self) -> str:
        return self._sdk_contract_version

    @property
    def capture_envelope_version(self) -> str:
        return self._capture_envelope_version

    @property
    def gateway_host_version(self) -> str:
        return self._gateway_host_version

    def register_definition(self, definition: ConnectorDefinitionV1) -> None:
        existing = self._definitions.get(definition.connector_id)
        if existing is not None:
            raise ConnectorRegistryError(
                f"duplicate connector definition: {definition.connector_id}"
            )
        self._definitions[definition.connector_id] = definition

    def register_adapter(self, adapter: ConnectorAdapter) -> None:
        if not isinstance(adapter, ConnectorAdapter):
            raise ConnectorRegistryError("adapter does not implement the connector SDK contract")
        definition = adapter.definition
        existing = self._definitions.get(definition.connector_id)
        if existing is None:
            self.register_definition(definition)
        elif existing != definition:
            raise ConnectorRegistryError(
                f"adapter definition conflicts with registered connector: {definition.connector_id}"
            )
        if definition.connector_id in self._adapters:
            raise ConnectorRegistryError(f"duplicate connector adapter: {definition.connector_id}")
        self._adapters[definition.connector_id] = adapter

    def get_definition(self, connector_id: str) -> ConnectorDefinitionV1:
        try:
            return self._definitions[connector_id]
        except KeyError as exc:
            raise ConnectorNotFoundError(f"unknown connector: {connector_id}") from exc

    def get_adapter(self, connector_id: str) -> ConnectorAdapter:
        self.get_definition(connector_id)
        try:
            return self._adapters[connector_id]
        except KeyError as exc:
            raise ConnectorNotFoundError(
                f"connector has no registered runtime adapter: {connector_id}"
            ) from exc

    def list_definitions(self) -> tuple[ConnectorDefinitionV1, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def validate_instance(self, instance: ConnectorInstanceV1) -> ConnectorDefinitionV1:
        definition = self.get_definition(instance.connector_id)
        problems: list[str] = []
        if definition.adapter_version != instance.connector_version:
            problems.append(
                f"adapter version {instance.connector_version!r} != {definition.adapter_version!r}"
            )
        if definition.sdk_contract_version != self._sdk_contract_version:
            problems.append(
                "connector SDK contract "
                f"{definition.sdk_contract_version!r} != runtime {self._sdk_contract_version!r}"
            )
        if self._gateway_host_version not in definition.gateway_host_versions:
            problems.append(
                "connector does not support Gateway connector host "
                f"{self._gateway_host_version!r}"
            )
        if self._capture_envelope_version not in definition.capture_envelope_versions:
            problems.append(
                "connector does not support capture envelope "
                f"{self._capture_envelope_version!r}"
            )
        if instance.collection.mode not in definition.capabilities.delivery_modes:
            problems.append(
                f"delivery mode {instance.collection.mode!r} is not declared by connector"
            )
        if instance.authentication.method not in definition.capabilities.authentication_methods:
            problems.append(
                "authentication method "
                f"{instance.authentication.method!r} is not declared by connector"
            )
        if problems:
            raise ConnectorCompatibilityError("; ".join(problems))
        return definition

    def validate_adapter_instance(self, instance: ConnectorInstanceV1) -> ConnectorAdapter:
        self.validate_instance(instance)
        adapter = self.get_adapter(instance.connector_id)
        adapter.validate_config(instance)
        return adapter

    @classmethod
    def from_manifest_directory(
        cls,
        path: Path,
        *,
        sdk_contract_version: str = CONNECTOR_SDK_CONTRACT_VERSION,
        capture_envelope_version: str = CAPTURE_ENVELOPE_VERSION,
        gateway_host_version: str = GATEWAY_CONNECTOR_HOST_VERSION,
    ) -> ConnectorRegistry:
        if not path.is_dir():
            raise ConnectorRegistryError(f"connector manifest directory does not exist: {path}")
        registry = cls(
            sdk_contract_version=sdk_contract_version,
            capture_envelope_version=capture_envelope_version,
            gateway_host_version=gateway_host_version,
        )
        for manifest_path in sorted(path.glob("*.json")):
            try:
                definition = ConnectorDefinitionV1.model_validate_json(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError) as exc:
                raise ConnectorRegistryError(
                    f"invalid connector definition manifest: {manifest_path.name}"
                ) from exc
            registry.register_definition(definition)
        return registry
