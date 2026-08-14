from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_connector import (
    ENTRA_CONNECTOR_ID,
    MicrosoftEntraDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_entra_delta import MicrosoftEntraDeltaPageV1
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCheckpointV1,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.gateway.connector_management import (
    ConnectorManagementAuthorizationError,
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.microsoft_entra_resync import (
    MicrosoftEntraFullResyncError,
    authorize_microsoft_entra_full_resync,
)

NOW = datetime(2026, 8, 14, 16, 0, tzinfo=UTC)
PROFILE_ID = "entra-prod"
CREDENTIAL_REF = "fixture://microsoft/entra-directory"


class FixtureCredentialResolver:
    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            updated_at_utc=NOW,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return CredentialLease(b"fixture-entra-token", self.describe(reference))


class FixtureClient:
    def fetch(self, request_url: str | None = None) -> MicrosoftEntraDeltaPageV1:
        raise AssertionError("resync management tests must not call the source")

    def close(self) -> None:
        return None


def _tenant_profile() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "application_id": "22222222-2222-2222-2222-222222222222",
            "cloud": "global",
            "credential_ref": {
                "schema_version": "ets.connector.credential_ref.v1",
                "ref": CREDENTIAL_REF,
            },
            "consent_state": "granted",
        }
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "entra-directory-prod",
            "connector_id": ENTRA_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="tenant-a",
                workspace_id="workspace-a",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="entra-directory",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref=CREDENTIAL_REF,
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=100,
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor",
                durable=True,
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.entra.delta.v1",
                normalization_profile="normalize.microsoft.entra.delta.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "collection": "users",
            },
        }
    )


def _service(tmp_path: Path) -> ConnectorManagementService:
    registry = ConnectorRegistry.from_manifest_directory(Path("config/connectors/enterprise"))

    def factory(_profile, _material: bytes, _timeout: float, _maximum: int) -> FixtureClient:
        return FixtureClient()

    registry.register_adapter(
        MicrosoftEntraDeltaAdapter(
            registry.get_definition(ENTRA_CONNECTOR_ID),
            FixtureCredentialResolver(),
            {PROFILE_ID: _tenant_profile()},
            client_factory=factory,
        )
    )
    return ConnectorManagementService(
        registry=registry,
        store=ConnectorRuntimeStore(tmp_path / "connector-runtime.db"),
        now=lambda: NOW,
    )


def _manage_principal() -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="operator-1",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        can_manage=True,
    )


def _read_only_principal() -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="auditor-1",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        can_manage=False,
    )


def _seed_expired_gap(
    service: ConnectorManagementService,
    principal: ConnectorManagementPrincipal,
) -> None:
    service.create_instance(principal, _instance())
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor="https://graph.microsoft.com/v1.0/users/delta?$deltatoken=expired",
    )
    service.update_checkpoint(
        principal,
        _instance().instance_id,
        checkpoint,
        expected_checkpoint_revision=0,
        observation_state="healthy_observation",
        gap_open=False,
        last_success_at_utc=NOW,
    )
    service.mark_gap(principal, _instance().instance_id)


def test_manage_authorized_full_resync_clears_cursor_but_keeps_gap_open(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    principal = _manage_principal()
    _seed_expired_gap(service, principal)
    before = service.get_runtime(principal, _instance().instance_id)

    after = authorize_microsoft_entra_full_resync(
        service,
        principal,
        _instance().instance_id,
        expected_checkpoint_revision=before.checkpoint_revision,
    )

    assert before.checkpoint is not None
    assert before.gap_open is True
    assert before.observation_state == "collection_gap"
    assert after.checkpoint is None
    assert after.checkpoint_revision == before.checkpoint_revision + 1
    assert after.gap_open is True
    assert after.observation_state == "collection_gap"
    assert after.last_success_at_utc == before.last_success_at_utc


def test_read_only_principal_cannot_authorize_full_resync(tmp_path: Path) -> None:
    service = _service(tmp_path)
    manager = _manage_principal()
    _seed_expired_gap(service, manager)
    runtime = service.get_runtime(manager, _instance().instance_id)

    with pytest.raises(ConnectorManagementAuthorizationError):
        authorize_microsoft_entra_full_resync(
            service,
            _read_only_principal(),
            _instance().instance_id,
            expected_checkpoint_revision=runtime.checkpoint_revision,
        )


def test_full_resync_requires_an_open_collection_gap(tmp_path: Path) -> None:
    service = _service(tmp_path)
    principal = _manage_principal()
    service.create_instance(principal, _instance())
    runtime = service.update_checkpoint(
        principal,
        _instance().instance_id,
        ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            cursor="https://graph.microsoft.com/v1.0/users/delta?$deltatoken=healthy",
        ),
        expected_checkpoint_revision=0,
        observation_state="healthy_observation",
        gap_open=False,
        last_success_at_utc=NOW,
    )

    with pytest.raises(MicrosoftEntraFullResyncError, match="open collection gap"):
        authorize_microsoft_entra_full_resync(
            service,
            principal,
            _instance().instance_id,
            expected_checkpoint_revision=runtime.checkpoint_revision,
        )


def test_full_resync_requires_existing_source_cursor(tmp_path: Path) -> None:
    service = _service(tmp_path)
    principal = _manage_principal()
    service.create_instance(principal, _instance())
    service.mark_gap(principal, _instance().instance_id)
    runtime = service.get_runtime(principal, _instance().instance_id)

    with pytest.raises(MicrosoftEntraFullResyncError, match="existing source cursor"):
        authorize_microsoft_entra_full_resync(
            service,
            principal,
            _instance().instance_id,
            expected_checkpoint_revision=runtime.checkpoint_revision,
        )
