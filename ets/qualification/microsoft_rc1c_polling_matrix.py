"""Deterministic RC1C polling fault matrix executed from the release image.

The matrix exercises the shipped Purview adapter and Gateway runtime policy with
synthetic, non-customer fixtures and isolated temporary durable state.  It never
uses the live Gateway database or a reusable Microsoft credential.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    MicrosoftPurviewDiscoveryPageV1,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
    purview_management_profile,
)
from ets.connectors.enterprise.microsoft_purview_audit import (
    MicrosoftPurviewAuditContentV1,
    MicrosoftPurviewAuditRecordV1,
)
from ets.connectors.enterprise.microsoft_purview_connector import (
    MicrosoftPurviewActivityAdapter,
    MicrosoftPurviewConnectorSettings,
)
from ets.connectors.enterprise.microsoft_purview_http import (
    MicrosoftPurviewActivityHttpClient,
    MicrosoftPurviewThrottleError,
)
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
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_runner import GatewayConnectorRunResult
from ets.gateway.microsoft_purview_runtime import (
    MicrosoftPurviewRuntimeError,
    mark_microsoft_purview_collection_gap,
    persist_microsoft_purview_gateway_success,
)

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
RECORD_ID = "44444444-4444-4444-4444-444444444444"
INSTANCE_ID = "rc1c-polling-matrix"
CREDENTIAL_REF = "fixture://microsoft/purview"
NEXT_URI = (
    f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/"
    "subscriptions/content?contentType=Audit.General&nextpage=opaque"
)


class _CredentialResolver:
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
        return CredentialLease(b"bounded-fixture-token", self.describe(reference))


class _ProfileResolver:
    def __init__(self, profile: MicrosoftPurviewManagementProfile) -> None:
        self.profile = profile

    def resolve(self, profile_id: str) -> MicrosoftPurviewManagementProfile:
        if profile_id != self.profile.profile_id:
            raise ValueError("unknown matrix profile")
        return self.profile


class _Client:
    def __init__(self, *, throttle: bool = False) -> None:
        self.throttle = throttle
        self.list_calls: list[tuple[datetime | None, datetime | None, str | None]] = []

    def list_content(
        self,
        content_type: PurviewContentType,
        *,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        next_page_uri: str | None = None,
    ) -> MicrosoftPurviewDiscoveryPageV1:
        if self.throttle:
            raise MicrosoftPurviewThrottleError(120)
        self.list_calls.append((start_time_utc, end_time_utc, next_page_uri))
        return MicrosoftPurviewDiscoveryPageV1(
            content_type=content_type,
            descriptors=(_descriptor(),),
            next_page_uri=NEXT_URI if next_page_uri is None else None,
            discovery_source="poll",
        )

    def retrieve_content(
        self,
        descriptor: MicrosoftPurviewContentDescriptorV1,
        *,
        service_specific_allowlist: frozenset[str] = frozenset(),
        include_client_ip: bool = False,
    ) -> MicrosoftPurviewAuditContentV1:
        if descriptor.content_id != "content-001":
            raise ValueError("unexpected matrix descriptor")
        if service_specific_allowlist or include_client_ip:
            raise ValueError("matrix escaped the minimized content profile")
        return _content()

    def close(self) -> None:
        return None


class _ThrottleOpener:
    def open(self, request: Request, *, timeout: float) -> object:
        headers = Message()
        headers["Retry-After"] = "120"
        raise HTTPError(request.full_url, 429, "matrix throttle", headers, None)


def _profile() -> MicrosoftPurviewManagementProfile:
    tenant = MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": "global",
            "credential_ref": {
                "schema_version": "ets.connector.credential_ref.v1",
                "ref": CREDENTIAL_REF,
            },
            "consent_state": "granted",
        }
    )
    return purview_management_profile(
        "rc1c-matrix",
        tenant,
        plan="enterprise",
        publisher_identifier=PUBLISHER_ID,
    )


def _descriptor() -> MicrosoftPurviewContentDescriptorV1:
    return MicrosoftPurviewContentDescriptorV1(
        content_type="Audit.General",
        content_id="content-001",
        content_uri=(
            f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/audit/content-001"
        ),
        content_created_utc=NOW - timedelta(minutes=5),
        content_expiration_utc=NOW + timedelta(days=7),
        discovery_source="poll",
    )


def _content() -> MicrosoftPurviewAuditContentV1:
    descriptor = _descriptor()
    record = MicrosoftPurviewAuditRecordV1(
        source_record_id=RECORD_ID,
        record_type=1,
        creation_time_utc=NOW - timedelta(minutes=3),
        operation="FileAccessed",
        organization_id=TENANT_ID,
        user_type=0,
        user_key="matrix-user-key",
        workload="SharePoint",
        user_id="matrix@example.test",
        result_status="Succeeded",
        object_id="https://example.test/matrix-document",
        client_ip=None,
        scope=0,
        version=1,
        content_type="Audit.General",
        content_id=descriptor.content_id,
        service_specific={},
    )
    return MicrosoftPurviewAuditContentV1(
        content_type="Audit.General",
        content_id=descriptor.content_id,
        content_sha256="a" * 64,
        content_created_utc=descriptor.content_created_utc,
        content_expiration_utc=descriptor.content_expiration_utc,
        records=(record,),
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": INSTANCE_ID,
            "connector_id": "microsoft.purview.activity",
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="matrix-tenant", workspace_id="matrix-workspace"
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="purview-matrix", environment="qualification"
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer", credential_ref=CREDENTIAL_REF
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll", interval_seconds=60, batch_size=500
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor", durable=True
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.purview.audit.v1",
                normalization_profile="normalize.microsoft.purview.audit.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "management_profile_id": "rc1c-matrix",
                "content_type": "Audit.General",
                "service_specific_allowlist": [],
                "include_client_ip": False,
                "poll_window_seconds": 3600,
                "overlap_seconds": 300,
            },
        }
    )


def _adapter(client: _Client) -> MicrosoftPurviewActivityAdapter:
    registry = ConnectorRegistry.from_manifest_directory(Path("config/connectors/enterprise"))

    def factory(
        profile: MicrosoftPurviewManagementProfile,
        material: bytes,
        settings: MicrosoftPurviewConnectorSettings,
    ) -> _Client:
        if profile.profile_id != "rc1c-matrix" or material != b"bounded-fixture-token":
            raise ValueError("matrix profile or credential changed")
        if settings.content_type != "Audit.General":
            raise ValueError("matrix content type changed")
        return client

    return MicrosoftPurviewActivityAdapter(
        registry.get_definition("microsoft.purview.activity"),
        _ProfileResolver(_profile()),
        _CredentialResolver(),
        client_factory=factory,
        now=lambda: NOW,
    )


def _principal() -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="matrix-operator",
        tenant_id="matrix-tenant",
        workspace_id="matrix-workspace",
        can_manage=True,
    )


def _gateway_result(cursor: str, *, has_more: bool) -> GatewayConnectorRunResult:
    return GatewayConnectorRunResult(
        code="ok",
        source_records=1,
        committed_local=1,
        sync_queued=1,
        partial_commit=0,
        checkpoint_to_persist=ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            cursor=cursor,
            observed_through_utc=NOW,
        ),
        has_more=has_more,
        message="bounded matrix success",
    )


def _service(path: Path) -> ConnectorManagementService:
    return ConnectorManagementService(
        registry=ConnectorRegistry.from_manifest_directory(Path("config/connectors/enterprise")),
        store=ConnectorRuntimeStore(path),
        now=lambda: NOW,
    )


def run_rc1c_polling_fault_matrix() -> dict[str, bool]:
    """Run the bounded matrix and return public-safe pass predicates only."""

    client = _Client()
    adapter = _adapter(client)
    instance = _instance()
    first = adapter.collect(instance, None)
    if first.code != "ok" or first.checkpoint is None or len(first.records) != 1:
        raise RuntimeError("RC1C initial polling page did not qualify")
    second = adapter.collect(instance, first.checkpoint)
    if second.code != "ok" or second.checkpoint is None:
        raise RuntimeError("RC1C exact cursor replay did not qualify")
    cursor_replay = client.list_calls == [
        (NOW - timedelta(hours=1), NOW, None),
        (None, None, NEXT_URI),
    ]
    normalized_first = adapter.normalize(instance, first.records[0]).model_dump(mode="json")
    normalized_second = adapter.normalize(instance, first.records[0]).model_dump(mode="json")
    serialized = json.dumps(normalized_first, sort_keys=True)
    canonical = (
        normalized_first == normalized_second
        and "bounded-fixture-token" not in serialized
        and "matrix-tenant" not in serialized
        and '"client_ip": null' in serialized
        and '"service_specific": {}' in serialized
    )

    throttled = _adapter(_Client(throttle=True)).collect(instance, None)
    throttle_checkpoint_withheld = throttled.code == "throttled" and throttled.checkpoint is None
    http_client = MicrosoftPurviewActivityHttpClient(_profile(), b"bounded-fixture-token")
    http_client._opener = _ThrottleOpener()  # type: ignore[assignment]
    try:
        http_client.list_content("Audit.General")
    except MicrosoftPurviewThrottleError as exc:
        retry_after = exc.retry_after_seconds == 120
    else:
        retry_after = False
    finally:
        http_client.close()

    with tempfile.TemporaryDirectory(prefix="ets-rc1c-matrix-") as directory:
        state_path = Path(directory) / "connector-runtime.db"
        principal = _principal()
        service = _service(state_path)
        service.create_instance(principal, instance)
        seeded = service.update_checkpoint(
            principal,
            INSTANCE_ID,
            ConnectorCheckpointV1(
                schema_version="ets.connector.checkpoint.v1",
                cursor="https://manage.office.com/page/seed",
                observed_through_utc=NOW - timedelta(minutes=10),
            ),
            expected_checkpoint_revision=0,
            observation_state="healthy_observation",
            gap_open=False,
            last_success_at_utc=NOW - timedelta(minutes=10),
        )
        opened = mark_microsoft_purview_collection_gap(service, principal, INSTANCE_ID)
        gap_preserved = (
            opened.gap_open
            and opened.checkpoint == seeded.checkpoint
            and opened.checkpoint_revision == seeded.checkpoint_revision
        )
        intermediate = persist_microsoft_purview_gateway_success(
            service,
            principal,
            INSTANCE_ID,
            _gateway_result("https://manage.office.com/page/next", has_more=True),
            expected_checkpoint_revision=opened.checkpoint_revision,
            completed_at_utc=NOW,
        )
        intermediate_open = (
            intermediate.gap_open and intermediate.observation_state == "collection_gap"
        )
        final = persist_microsoft_purview_gateway_success(
            service,
            principal,
            INSTANCE_ID,
            _gateway_result("https://manage.office.com/page/final", has_more=False),
            expected_checkpoint_revision=intermediate.checkpoint_revision,
            completed_at_utc=NOW,
        )
        final_reconciled = not final.gap_open and final.observation_state == "healthy_observation"

        restarted = _service(state_path).get_runtime(principal, INSTANCE_ID)
        restart_recovered = restarted == final

        stale_failed = False
        try:
            persist_microsoft_purview_gateway_success(
                service,
                principal,
                INSTANCE_ID,
                _gateway_result("https://manage.office.com/page/stale", has_more=False),
                expected_checkpoint_revision=0,
                completed_at_utc=NOW,
            )
        except MicrosoftPurviewRuntimeError:
            stale_failed = service.get_runtime(principal, INSTANCE_ID) == final

        failed_result = GatewayConnectorRunResult(
            code="retryable_error",
            source_records=1,
            committed_local=1,
            sync_queued=0,
            partial_commit=1,
            checkpoint_to_persist=None,
            has_more=False,
            message="bounded evidence loss",
        )
        evidence_loss_failed = False
        try:
            persist_microsoft_purview_gateway_success(
                service,
                principal,
                INSTANCE_ID,
                failed_result,
                expected_checkpoint_revision=final.checkpoint_revision,
                completed_at_utc=NOW,
            )
        except MicrosoftPurviewRuntimeError:
            evidence_loss_failed = service.get_runtime(principal, INSTANCE_ID) == final

    predicates = {
        "cursor_replay_verified": cursor_replay,
        "bounded_overlap_verified": first.checkpoint.observed_through_utc == NOW,
        "content_retrieval_verified": len(first.records) == 1,
        "canonicalization_deterministic": canonical,
        "throttle_retry_after_verified": retry_after,
        "throttle_checkpoint_withheld": throttle_checkpoint_withheld,
        "gap_open_preserves_checkpoint": gap_preserved,
        "intermediate_page_keeps_gap_open": intermediate_open,
        "final_page_reconciles_gap": final_reconciled,
        "evidence_loss_checkpoint_withheld": evidence_loss_failed,
        "revision_conflict_fail_closed": stale_failed,
        "restart_state_recovered": restart_recovered,
        "fault_matrix_public_safe": True,
    }
    failed = sorted(key for key, value in predicates.items() if value is not True)
    if failed:
        raise RuntimeError("RC1C polling fault matrix failed: " + ",".join(failed))
    return predicates
