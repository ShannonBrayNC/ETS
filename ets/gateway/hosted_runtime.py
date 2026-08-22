"""Production composition for the hosted Microsoft ETS Gateway profile."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, status

from ets.api.auth import AppScopeMap, AuthPolicy, ProductionJWKSAuthPolicy
from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_DEFAULT_SCOPE,
    MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
    MICROSOFT_PURVIEW_DEFAULT_SCOPE,
    AzureManagedIdentityCredentialProfile,
    AzureManagedIdentityCredentialProvider,
)
from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_connector import (
    ENTRA_CONNECTOR_ID,
    ENTRA_OBSERVED_EVENT_TYPE,
    ENTRA_SOURCE_SYSTEM,
    MicrosoftEntraDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_entra_delta import EntraDeltaCollection
from ets.connectors.enterprise.microsoft_health import (
    MicrosoftOperationalHealthPolicyV1,
    MicrosoftOperationalPostureV1,
    evaluate_microsoft_operational_posture,
)
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewManagementProfile,
    purview_management_profile,
)
from ets.connectors.enterprise.microsoft_purview_connector import (
    PURVIEW_EVENT_TYPE,
    PURVIEW_SOURCE_SYSTEM,
    MicrosoftPurviewActivityAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    SHAREPOINT_OBSERVED_EVENT_TYPE,
    SHAREPOINT_SOURCE_SYSTEM,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime import ConnectorObservationState, ConnectorRuntimeStateV1
from ets.connectors.runtime_store import (
    ConnectorInstanceNotFoundError,
    ConnectorRuntimeStore,
)
from ets.connectors.sdk import ConnectorAdapter
from ets.core.sqlite_store import SQLiteEventStore
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_runner import GatewayConnectorCollectionRunner
from ets.gateway.core_relay import GatewayCoreRelayWorker
from ets.gateway.core_relay_http import ETSCoreHttpRelayClient
from ets.gateway.entra_core_token import AzureManagedIdentityCoreTokenProvider
from ets.gateway.ingress import GatewayIngressConfig
from ets.gateway.management_host import create_gateway_management_app
from ets.gateway.microsoft_graph_commit import (
    MICROSOFT_GRAPH_RESOURCE_EVENT_TYPE,
    MICROSOFT_GRAPH_SOURCE_SYSTEM,
    MICROSOFT_GRAPH_TRANSFORMATION_PROFILE,
    GatewayMicrosoftGraphResourceCommitter,
    MicrosoftGraphResourceCommitter,
)
from ets.gateway.microsoft_graph_lifecycle import (
    GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_LIFETIME_SECONDS,
    GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_RENEWAL_WINDOW_SECONDS,
    GRAPH_DRIVE_SUBSCRIPTION_MAXIMUM_LIFETIME_SECONDS,
    GRAPH_DRIVE_SUBSCRIPTION_MINIMUM_LIFETIME_SECONDS,
    MicrosoftGraphSubscriptionLifecycleManager,
    sharepoint_drive_subscription_resource,
)
from ets.gateway.microsoft_graph_state import SQLiteMicrosoftGraphSubscriptionStore
from ets.gateway.microsoft_graph_webhook import create_microsoft_graph_webhook_app
from ets.gateway.microsoft_operational_posture_api import (
    GatewayMicrosoftOperationalPostureService,
    MicrosoftOperationalPostureProvider,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue
from ets.runtime.sync_queue_scope import source_scoped_sync_queue_status

_HOSTED_GATEWAY_VERSION = "0.3.0-p0-microsoft-graph-lifecycle-r1"
_DEFAULT_STATE_DIR = "/var/lib/ets"
_DEFAULT_MANIFEST_DIR = "/app/config/connectors/enterprise"
_WORKER_OWNER = "ets-hosted-microsoft-gateway"
_SHAREPOINT_PROFILE_ID = "hosted-microsoft"
_DIRECTORY_PROFILE_ID = "hosted-microsoft-directory"
_PURVIEW_PROFILE_ID = "hosted-microsoft-purview"
_PURVIEW_CONNECTOR_ID = "microsoft.purview.activity"
_ENTRA_USERS_SUFFIX = "entra-users"
_ENTRA_GROUPS_SUFFIX = "entra-groups"
_PURVIEW_SUFFIX = "purview-audit-general"
_ENTRA_USERS_PRINCIPAL = "gateway://microsoft/entra/users"
_ENTRA_GROUPS_PRINCIPAL = "gateway://microsoft/entra/groups"
_PURVIEW_PRINCIPAL = "gateway://microsoft/purview/audit-general"
_GRAPH_NOTIFICATION_PRINCIPAL = "gateway://microsoft/graph/notifications"


@dataclass(frozen=True, slots=True)
class HostedMicrosoftGatewaySettings:
    """Deployment-authoritative settings for one hosted SharePoint Gateway instance."""

    state_dir: Path
    manifest_dir: Path
    managed_identity_client_id: str
    directory_managed_identity_client_id: str
    purview_managed_identity_client_id: str
    core_base_url: str
    core_scope: str
    tenant_id: str
    workspace_id: str
    instance_id: str
    source_id: str
    source_principal: str
    microsoft_tenant_id: str
    microsoft_application_id: str
    sharepoint_drive_id: str
    poll_interval_seconds: int
    auth_jwks_json: str | None
    auth_jwks_url: str | None
    auth_issuer: str
    auth_audience: str
    auth_tenant_id: str
    auth_app_scope_map: AppScopeMap
    graph_notification_url: str | None
    graph_client_state: str | None
    graph_subscription_lifetime_seconds: int
    graph_subscription_renewal_window_seconds: int
    health_policy: MicrosoftOperationalHealthPolicyV1 | None

    @classmethod
    def from_env(cls) -> HostedMicrosoftGatewaySettings:
        state_dir = Path(os.getenv("ETS_GATEWAY_STATE_DIR", _DEFAULT_STATE_DIR))
        manifest_dir = Path(os.getenv("ETS_GATEWAY_MANIFEST_DIR", _DEFAULT_MANIFEST_DIR))
        poll_interval = _bounded_int_env(
            "ETS_GATEWAY_POLL_INTERVAL_SECONDS",
            default=60,
            minimum=30,
            maximum=3600,
        )
        jwks_json = _optional_env("ETS_AUTH_JWKS_JSON")
        jwks_url = _optional_env("ETS_AUTH_JWKS_URL")
        if (jwks_json is None) == (jwks_url is None):
            raise RuntimeError(
                "hosted Gateway requires exactly one of ETS_AUTH_JWKS_JSON or ETS_AUTH_JWKS_URL"
            )

        graph_notification_url = _optional_env("ETS_GATEWAY_GRAPH_NOTIFICATION_URL")
        graph_client_state = _optional_env("ETS_GATEWAY_GRAPH_CLIENT_STATE")
        policy_raw = _optional_env("ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON")
        configured_graph_values = (
            graph_notification_url,
            graph_client_state,
            policy_raw,
        )
        if any(value is not None for value in configured_graph_values) and any(
            value is None for value in configured_graph_values
        ):
            raise RuntimeError(
                "Graph notification URL, clientState, and health policy must be configured together"
            )
        if graph_notification_url is not None:
            graph_notification_url = _validate_graph_notification_url(
                graph_notification_url
            )
        if graph_client_state is not None and len(graph_client_state) > 128:
            raise RuntimeError("ETS_GATEWAY_GRAPH_CLIENT_STATE exceeds 128 characters")
        health_policy = (
            None
            if policy_raw is None
            else MicrosoftOperationalHealthPolicyV1.model_validate_json(policy_raw)
        )
        graph_subscription_lifetime_seconds = _bounded_int_env(
            "ETS_GATEWAY_GRAPH_SUBSCRIPTION_LIFETIME_SECONDS",
            default=GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_LIFETIME_SECONDS,
            minimum=GRAPH_DRIVE_SUBSCRIPTION_MINIMUM_LIFETIME_SECONDS,
            maximum=GRAPH_DRIVE_SUBSCRIPTION_MAXIMUM_LIFETIME_SECONDS,
        )
        graph_subscription_renewal_window_seconds = _bounded_int_env(
            "ETS_GATEWAY_GRAPH_SUBSCRIPTION_RENEWAL_WINDOW_SECONDS",
            default=GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_RENEWAL_WINDOW_SECONDS,
            minimum=60,
            maximum=GRAPH_DRIVE_SUBSCRIPTION_MAXIMUM_LIFETIME_SECONDS - 1,
        )
        if (
            graph_subscription_renewal_window_seconds
            >= graph_subscription_lifetime_seconds
        ):
            raise RuntimeError(
                "Graph subscription renewal window must be shorter than its lifetime"
            )

        managed_identity_client_id = _required_env(
            "ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID", maximum=100
        )
        directory_managed_identity_client_id = _required_env(
            "ETS_GATEWAY_DIRECTORY_MANAGED_IDENTITY_CLIENT_ID", maximum=100
        )
        purview_managed_identity_client_id = _required_env(
            "ETS_GATEWAY_PURVIEW_MANAGED_IDENTITY_CLIENT_ID", maximum=100
        )
        identity_client_ids = {
            managed_identity_client_id.casefold(),
            directory_managed_identity_client_id.casefold(),
            purview_managed_identity_client_id.casefold(),
        }
        if len(identity_client_ids) != 3:
            raise RuntimeError(
                "hosted Microsoft connector profiles require three distinct managed identities"
            )

        microsoft_application_id = _required_env(
            "ETS_GATEWAY_MICROSOFT_APPLICATION_ID", maximum=36
        )
        if microsoft_application_id.casefold() != managed_identity_client_id.casefold():
            raise RuntimeError(
                "SharePoint Microsoft application id must match the SharePoint/Core identity"
            )

        return cls(
            state_dir=state_dir,
            manifest_dir=manifest_dir,
            managed_identity_client_id=managed_identity_client_id,
            directory_managed_identity_client_id=directory_managed_identity_client_id,
            purview_managed_identity_client_id=purview_managed_identity_client_id,
            core_base_url=_required_env("ETS_GATEWAY_CORE_BASE_URL", maximum=500),
            core_scope=_required_env("ETS_GATEWAY_CORE_SCOPE", maximum=500),
            tenant_id=_required_env("ETS_GATEWAY_TENANT_ID", maximum=128),
            workspace_id=_required_env("ETS_GATEWAY_WORKSPACE_ID", maximum=128),
            instance_id=_required_env("ETS_GATEWAY_INSTANCE_ID", maximum=128),
            source_id=_required_env("ETS_GATEWAY_SOURCE_ID", maximum=200),
            source_principal=_required_env("ETS_GATEWAY_SOURCE_PRINCIPAL", maximum=500),
            microsoft_tenant_id=_required_env(
                "ETS_GATEWAY_MICROSOFT_TENANT_ID", maximum=36
            ),
            microsoft_application_id=microsoft_application_id,
            sharepoint_drive_id=_required_env(
                "ETS_GATEWAY_SHAREPOINT_DRIVE_ID", maximum=500
            ),
            poll_interval_seconds=poll_interval,
            auth_jwks_json=jwks_json,
            auth_jwks_url=jwks_url,
            auth_issuer=_required_env("ETS_AUTH_ISSUER", maximum=500),
            auth_audience=_required_env("ETS_AUTH_AUDIENCE", maximum=500),
            auth_tenant_id=_required_env("ETS_AUTH_TENANT_ID", maximum=36),
            auth_app_scope_map=_load_app_scope_map(),
            graph_notification_url=graph_notification_url,
            graph_client_state=graph_client_state,
            graph_subscription_lifetime_seconds=graph_subscription_lifetime_seconds,
            graph_subscription_renewal_window_seconds=(
                graph_subscription_renewal_window_seconds
            ),
            health_policy=health_policy,
        )


@dataclass(frozen=True, slots=True)
class HostedMicrosoftConnectorWorker:
    """One deployment-authoritative connector instance and isolated collection runner."""

    instance: ConnectorInstanceV1
    adapter: ConnectorAdapter
    runner: GatewayConnectorCollectionRunner
    principal: str


class HostedMicrosoftPurviewProfileResolver:
    """Resolve exactly one server-owned Purview Management Activity profile."""

    def __init__(self, profile: MicrosoftPurviewManagementProfile) -> None:
        self._profile = profile

    def resolve(self, profile_id: str) -> MicrosoftPurviewManagementProfile:
        if profile_id != self._profile.profile_id:
            raise ValueError("unknown hosted Purview management profile")
        return self._profile


class HostedMicrosoftOperationalPostureProvider(MicrosoftOperationalPostureProvider):
    """Read one policy-bound posture from the hosted Gateway's authoritative state."""

    def __init__(
        self,
        *,
        adapter: MicrosoftSharePointDeltaAdapter,
        queue: SyncQueue,
        subscription_store: SQLiteMicrosoftGraphSubscriptionStore,
        subscription_resource: str,
        source_id: str,
        microsoft_tenant_id: str,
        policy: MicrosoftOperationalHealthPolicyV1,
    ) -> None:
        self._adapter = adapter
        self._queue = queue
        self._subscription_store = subscription_store
        self._subscription_resource = subscription_resource
        self._source_id = source_id
        self._microsoft_tenant_id = microsoft_tenant_id
        self._policy = policy

    def read(
        self,
        instance: ConnectorInstanceV1,
        runtime: ConnectorRuntimeStateV1,
    ) -> MicrosoftOperationalPostureV1:
        subscription = self._subscription_store.get_for_resource(
            tenant_id=self._microsoft_tenant_id,
            resource=self._subscription_resource,
        )
        if subscription is None:
            raise RuntimeError("configured Microsoft Graph subscription state is unavailable")
        now = datetime.now(UTC)
        queue = source_scoped_sync_queue_status(
            self._queue,
            tenant_id=instance.scope.tenant_id,
            workspace_id=instance.scope.workspace_id,
            source_id=self._source_id,
            upstream_status=self._queue.get_upstream_status(),
            now=now,
        )
        return evaluate_microsoft_operational_posture(
            instance_id=instance.instance_id,
            ets_tenant_id=instance.scope.tenant_id,
            workspace_id=instance.scope.workspace_id,
            source_id=self._source_id,
            microsoft_tenant_id=self._microsoft_tenant_id,
            source_health=self._adapter.health(instance),
            runtime=runtime,
            subscription=subscription,
            queue=queue,
            reconciliation=None,
            policy=self._policy,
            evaluated_at_utc=now,
        )


class HostedMicrosoftGatewayRuntime:
    """Own the durable hosted Gateway services and bounded Microsoft polling workers."""

    def __init__(
        self,
        *,
        settings: HostedMicrosoftGatewaySettings,
        workers: tuple[HostedMicrosoftConnectorWorker, ...],
        store: ConnectorRuntimeStore,
        relay: GatewayCoreRelayWorker,
        event_store: SQLiteEventStore,
        microsoft_credentials: AzureManagedIdentityCredentialProvider,
        core_tokens: AzureManagedIdentityCoreTokenProvider,
        graph_subscription_store: SQLiteMicrosoftGraphSubscriptionStore | None,
        graph_subscription_lifecycle: MicrosoftGraphSubscriptionLifecycleManager | None,
        graph_resource_committer: MicrosoftGraphResourceCommitter | None,
    ) -> None:
        if not workers:
            raise ValueError("hosted Microsoft Gateway requires at least one connector worker")
        instance_ids = tuple(worker.instance.instance_id for worker in workers)
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("hosted Microsoft connector instance ids must be unique")
        principals = tuple(worker.principal for worker in workers)
        if len(principals) != len(set(principals)):
            raise ValueError("hosted Microsoft connector principals must be unique")
        self.settings = settings
        self.workers = workers
        self.instances = tuple(worker.instance for worker in workers)
        self.instance = workers[0].instance
        self.store = store
        self.relay = relay
        self.event_store = event_store
        self.microsoft_credentials = microsoft_credentials
        self.core_tokens = core_tokens
        self.graph_subscription_store = graph_subscription_store
        self.graph_subscription_lifecycle = graph_subscription_lifecycle
        self.graph_resource_committer = graph_resource_committer
        self._workers_by_instance_id = {
            worker.instance.instance_id: worker for worker in workers
        }
        self.last_worker_error: str | None = None
        self.last_worker_cycle_at_utc: datetime | None = None
        self._task: asyncio.Task[None] | None = None

    def run_cycle(self) -> None:
        """Run every due composed source once and one bounded Core relay drain."""

        now = datetime.now(UTC)
        claimed = self.store.claim_due(
            owner=_WORKER_OWNER,
            now=now,
            lease_seconds=min(max(self.settings.poll_interval_seconds * 2, 60), 3600),
            limit=len(self.workers),
            instance_ids=tuple(self._workers_by_instance_id),
        )
        failures: list[Exception] = []
        if self.graph_subscription_lifecycle is not None:
            try:
                self.graph_subscription_lifecycle.run_once(now=now)
            except Exception as exc:
                failures.append(exc)
        for instance_id in claimed:
            worker = self._workers_by_instance_id[instance_id]
            try:
                self._run_claimed_collection(worker, now)
            except Exception as exc:
                failures.append(exc)
            finally:
                try:
                    self.store.release_lease(
                        instance_id,
                        owner=_WORKER_OWNER,
                        now=datetime.now(UTC),
                    )
                except Exception as exc:
                    failures.append(exc)
        try:
            self.relay.run_once(limit=50)
        except Exception as exc:
            failures.append(exc)
        self.last_worker_cycle_at_utc = datetime.now(UTC)
        if failures:
            raise RuntimeError(
                f"hosted Microsoft cycle failed in {len(failures)} bounded operation(s)"
            ) from failures[0]
        self.last_worker_error = None

    def _run_claimed_collection(
        self,
        worker: HostedMicrosoftConnectorWorker,
        now: datetime,
    ) -> None:
        instance = worker.instance
        runtime = self.store.get_runtime(instance.instance_id)
        result = worker.runner.run(
            adapter=worker.adapter,
            instance=instance,
            principal=worker.principal,
            checkpoint=runtime.checkpoint,
        )
        if result.code == "ok":
            observation_state: ConnectorObservationState = (
                "collection_gap" if runtime.gap_open else "healthy_observation"
            )
            self.store.set_checkpoint(
                instance.instance_id,
                result.checkpoint_to_persist,
                expected_checkpoint_revision=runtime.checkpoint_revision,
                observation_state=observation_state,
                gap_open=runtime.gap_open,
                last_success_at_utc=now,
                now=now,
            )
            return
        if result.code in {
            "retryable_error",
            "throttled",
            "authentication_failed",
        }:
            if runtime.retry_count >= instance.retry.max_attempts:
                self.store.mark_gap(instance.instance_id, now=now)
                return
            multiplier = 2 ** min(runtime.retry_count, 6)
            delay = min(
                self.settings.poll_interval_seconds * multiplier,
                min(instance.retry.max_age_seconds, 3600),
            )
            self.store.schedule_retry(
                instance.instance_id,
                next_attempt_at_utc=now + timedelta(seconds=delay),
                now=now,
            )
            return
        self.store.mark_gap(instance.instance_id, now=now)

    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("hosted Gateway worker is already started")
        self._task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.microsoft_credentials.close()
        self.core_tokens.close()
        if self.graph_subscription_store is not None:
            self.graph_subscription_store.close()
        self.event_store.close()

    async def _worker_loop(self) -> None:
        while True:
            try:
                await asyncio.to_thread(self.run_cycle)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_worker_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                self.last_worker_cycle_at_utc = datetime.now(UTC)
            await asyncio.sleep(self.settings.poll_interval_seconds)


def create_app_from_env() -> FastAPI:
    """Compose the production-only hosted Microsoft Gateway from environment state."""

    settings = HostedMicrosoftGatewaySettings.from_env()
    runtime, management, auth_policy, posture_service = _compose_runtime(settings)
    app = create_gateway_management_app(
        management,
        auth_policy=auth_policy,
        auth_mode="production_jwks",
        microsoft_posture_service=posture_service,
    )
    if (
        runtime.graph_subscription_store is not None
        and runtime.graph_resource_committer is not None
    ):
        graph_webhook_app = create_microsoft_graph_webhook_app(
            runtime.graph_subscription_store,
            resource_committer=runtime.graph_resource_committer,
        )
        app.include_router(graph_webhook_app.router)

    @app.get("/health", tags=["runtime"])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "ets-gateway",
            "version": _HOSTED_GATEWAY_VERSION,
        }

    @app.get("/ready", tags=["runtime"])
    def ready() -> dict[str, object]:
        for instance in runtime.instances:
            runtime.store.get_instance(instance.instance_id)
        runtime.event_store.list_entries()
        if runtime.last_worker_error is not None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="hosted Gateway worker is degraded",
            )
        return {
            "status": "ready",
            "service": "ets-gateway",
            "instance_id": runtime.instance.instance_id,
            "instance_ids": [instance.instance_id for instance in runtime.instances],
            "last_worker_cycle_at_utc": (
                None
                if runtime.last_worker_cycle_at_utc is None
                else runtime.last_worker_cycle_at_utc.isoformat().replace("+00:00", "Z")
            ),
        }

    @app.get("/version", tags=["runtime"])
    def version() -> dict[str, str]:
        return {
            "service": "ets-gateway",
            "version": _HOSTED_GATEWAY_VERSION,
            "profile": "hosted_microsoft",
        }

    @app.on_event("startup")
    async def _start_runtime() -> None:
        await runtime.start()

    @app.on_event("shutdown")
    async def _stop_runtime() -> None:
        await runtime.stop()

    return app


def _compose_runtime(
    settings: HostedMicrosoftGatewaySettings,
) -> tuple[
    HostedMicrosoftGatewayRuntime,
    ConnectorManagementService,
    AuthPolicy,
    GatewayMicrosoftOperationalPostureService | None,
]:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    if not settings.manifest_dir.is_dir():
        raise RuntimeError("Gateway connector manifest directory is unavailable")

    microsoft_credentials = AzureManagedIdentityCredentialProvider(
        (
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
                client_id=settings.managed_identity_client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
                client_id=settings.directory_managed_identity_client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
                client_id=settings.purview_managed_identity_client_id,
                scope=MICROSOFT_PURVIEW_DEFAULT_SCOPE,
            ),
        )
    )
    broker = CredentialBroker()
    broker.register(microsoft_credentials)
    sharepoint_tenant_profile = MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=settings.microsoft_tenant_id,
        application_id=settings.microsoft_application_id,
        cloud="global",
        credential_ref=_credential_reference(MICROSOFT_GRAPH_CREDENTIAL_REFERENCE),
        consent_state="granted",
    )
    directory_tenant_profile = MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=settings.microsoft_tenant_id,
        application_id=settings.directory_managed_identity_client_id,
        cloud="global",
        credential_ref=_credential_reference(MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE),
        consent_state="granted",
    )
    purview_tenant_profile = MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=settings.microsoft_tenant_id,
        application_id=settings.purview_managed_identity_client_id,
        cloud="global",
        credential_ref=_credential_reference(MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE),
        consent_state="granted",
    )
    purview_profile = purview_management_profile(
        _PURVIEW_PROFILE_ID,
        purview_tenant_profile,
        plan="enterprise",
        publisher_identifier=settings.microsoft_tenant_id,
    )

    registry = ConnectorRegistry.from_manifest_directory(settings.manifest_dir)
    sharepoint_definition = registry.get_definition(SHAREPOINT_CONNECTOR_ID)
    entra_definition = registry.get_definition(ENTRA_CONNECTOR_ID)
    purview_definition = registry.get_definition(_PURVIEW_CONNECTOR_ID)
    sharepoint_adapter = MicrosoftSharePointDeltaAdapter(
        sharepoint_definition,
        broker,
        {_SHAREPOINT_PROFILE_ID: sharepoint_tenant_profile},
    )
    entra_adapter = MicrosoftEntraDeltaAdapter(
        entra_definition,
        broker,
        {_DIRECTORY_PROFILE_ID: directory_tenant_profile},
    )
    purview_adapter = MicrosoftPurviewActivityAdapter(
        purview_definition,
        HostedMicrosoftPurviewProfileResolver(purview_profile),
        broker,
    )
    registry.register_adapter(sharepoint_adapter)
    registry.register_adapter(entra_adapter)
    registry.register_adapter(purview_adapter)

    sharepoint_instance = _connector_instance(
        settings,
        sharepoint_definition.adapter_version,
    )
    entra_users_instance = _entra_connector_instance(
        settings,
        entra_definition.adapter_version,
        "users",
    )
    entra_groups_instance = _entra_connector_instance(
        settings,
        entra_definition.adapter_version,
        "groups",
    )
    purview_instance = _purview_connector_instance(
        settings,
        purview_definition.adapter_version,
    )
    instances = (
        sharepoint_instance,
        entra_users_instance,
        entra_groups_instance,
        purview_instance,
    )
    for instance in instances:
        registry.validate_adapter_instance(instance)

    runtime_store = ConnectorRuntimeStore(settings.state_dir / "connector-runtime.db")
    management = ConnectorManagementService(
        registry=registry,
        store=runtime_store,
        credential_broker=broker,
    )
    bootstrap = ConnectorManagementPrincipal(
        actor_id="ets-gateway-bootstrap",
        tenant_id=settings.tenant_id,
        workspace_id=settings.workspace_id,
        can_manage=True,
        can_read=True,
    )
    for instance in instances:
        try:
            existing = runtime_store.get_instance(instance.instance_id)
        except ConnectorInstanceNotFoundError:
            management.create_instance(bootstrap, instance)
        else:
            if existing.instance != instance:
                raise RuntimeError(
                    "persisted connector instance differs from deployment-authoritative "
                    "configuration"
                )

    source_registry = StaticSourceRegistry(
        (
            SourceRegistration(
                principal=settings.source_principal,
                source_id=settings.source_id,
                source_system=SHAREPOINT_SOURCE_SYSTEM,
                tenant_id=settings.tenant_id,
                workspace_id=settings.workspace_id,
                adapter_id=SHAREPOINT_CONNECTOR_ID,
                adapter_version=sharepoint_definition.adapter_version,
                event_type=SHAREPOINT_OBSERVED_EVENT_TYPE,
                classification="enterprise_metadata",
                redaction_profile="microsoft_sharepoint_metadata_v1",
                minimization_profile="microsoft_sharepoint_metadata_v1",
                clock_quality="unknown",
            ),
            SourceRegistration(
                principal=_GRAPH_NOTIFICATION_PRINCIPAL,
                source_id=settings.source_id,
                source_system=MICROSOFT_GRAPH_SOURCE_SYSTEM,
                tenant_id=settings.tenant_id,
                workspace_id=settings.workspace_id,
                adapter_id="microsoft.graph",
                adapter_version="1.0.0-g2e-b",
                event_type=MICROSOFT_GRAPH_RESOURCE_EVENT_TYPE,
                classification="enterprise_metadata",
                redaction_profile=MICROSOFT_GRAPH_TRANSFORMATION_PROFILE,
                minimization_profile=MICROSOFT_GRAPH_TRANSFORMATION_PROFILE,
                clock_quality="unknown",
            ),
            SourceRegistration(
                principal=_ENTRA_USERS_PRINCIPAL,
                source_id=_derived_identifier(
                    settings.source_id,
                    _ENTRA_USERS_SUFFIX,
                    maximum=500,
                ),
                source_system=ENTRA_SOURCE_SYSTEM,
                tenant_id=settings.tenant_id,
                workspace_id=settings.workspace_id,
                adapter_id=ENTRA_CONNECTOR_ID,
                adapter_version=entra_definition.adapter_version,
                event_type=ENTRA_OBSERVED_EVENT_TYPE,
                classification="enterprise_directory_metadata",
                redaction_profile="microsoft_entra_directory_metadata_v1",
                minimization_profile="microsoft_entra_directory_metadata_v1",
                clock_quality="unknown",
            ),
            SourceRegistration(
                principal=_ENTRA_GROUPS_PRINCIPAL,
                source_id=_derived_identifier(
                    settings.source_id,
                    _ENTRA_GROUPS_SUFFIX,
                    maximum=500,
                ),
                source_system=ENTRA_SOURCE_SYSTEM,
                tenant_id=settings.tenant_id,
                workspace_id=settings.workspace_id,
                adapter_id=ENTRA_CONNECTOR_ID,
                adapter_version=entra_definition.adapter_version,
                event_type=ENTRA_OBSERVED_EVENT_TYPE,
                classification="enterprise_directory_metadata",
                redaction_profile="microsoft_entra_directory_metadata_v1",
                minimization_profile="microsoft_entra_directory_metadata_v1",
                clock_quality="unknown",
            ),
            SourceRegistration(
                principal=_PURVIEW_PRINCIPAL,
                source_id=_derived_identifier(
                    settings.source_id,
                    _PURVIEW_SUFFIX,
                    maximum=500,
                ),
                source_system=PURVIEW_SOURCE_SYSTEM,
                tenant_id=settings.tenant_id,
                workspace_id=settings.workspace_id,
                adapter_id=_PURVIEW_CONNECTOR_ID,
                adapter_version=purview_definition.adapter_version,
                event_type=PURVIEW_EVENT_TYPE,
                classification="enterprise_audit_metadata",
                redaction_profile="microsoft_purview_common_schema_v1",
                minimization_profile="microsoft_purview_common_schema_v1",
                clock_quality="unknown",
            ),
        )
    )
    event_store = SQLiteEventStore(settings.state_dir / "gateway-events.db")
    sync_queue = SyncQueue(settings.state_dir / "gateway-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=source_registry,
        event_log=event_store,
        sync_queue=sync_queue,
        config=GatewayIngressConfig(collector_id="ets-gateway-hosted-microsoft"),
    )
    workers = (
        HostedMicrosoftConnectorWorker(
            instance=sharepoint_instance,
            adapter=sharepoint_adapter,
            runner=GatewayConnectorCollectionRunner(ingress),
            principal=settings.source_principal,
        ),
        HostedMicrosoftConnectorWorker(
            instance=entra_users_instance,
            adapter=entra_adapter,
            runner=GatewayConnectorCollectionRunner(ingress),
            principal=_ENTRA_USERS_PRINCIPAL,
        ),
        HostedMicrosoftConnectorWorker(
            instance=entra_groups_instance,
            adapter=entra_adapter,
            runner=GatewayConnectorCollectionRunner(ingress),
            principal=_ENTRA_GROUPS_PRINCIPAL,
        ),
        HostedMicrosoftConnectorWorker(
            instance=purview_instance,
            adapter=purview_adapter,
            runner=GatewayConnectorCollectionRunner(ingress),
            principal=_PURVIEW_PRINCIPAL,
        ),
    )
    core_tokens = AzureManagedIdentityCoreTokenProvider(
        client_id=settings.managed_identity_client_id,
        core_scope=settings.core_scope,
        tenant_id=settings.tenant_id,
        workspace_id=settings.workspace_id,
    )
    relay = GatewayCoreRelayWorker(
        event_log=event_store,
        sync_queue=sync_queue,
        client=ETSCoreHttpRelayClient(settings.core_base_url),
        token_provider=core_tokens,
    )

    graph_store: SQLiteMicrosoftGraphSubscriptionStore | None = None
    graph_lifecycle: MicrosoftGraphSubscriptionLifecycleManager | None = None
    graph_committer: MicrosoftGraphResourceCommitter | None = None
    posture_service: GatewayMicrosoftOperationalPostureService | None = None
    if settings.graph_notification_url is not None:
        if settings.graph_client_state is None or settings.health_policy is None:
            raise RuntimeError("hosted Graph lifecycle configuration is incomplete")
        graph_resource = sharepoint_drive_subscription_resource(
            settings.sharepoint_drive_id
        )
        graph_store = SQLiteMicrosoftGraphSubscriptionStore(
            settings.state_dir / "microsoft-graph-subscriptions.db"
        )
        graph_lifecycle = MicrosoftGraphSubscriptionLifecycleManager(
            tenant_profile=sharepoint_tenant_profile,
            credential_resolver=broker,
            store=graph_store,
            resource=graph_resource,
            notification_url=settings.graph_notification_url,
            client_state=settings.graph_client_state,
            lifetime_seconds=settings.graph_subscription_lifetime_seconds,
            renewal_window_seconds=(
                settings.graph_subscription_renewal_window_seconds
            ),
        )
        graph_committer = GatewayMicrosoftGraphResourceCommitter(
            ingress,
            principal=_GRAPH_NOTIFICATION_PRINCIPAL,
        )
        posture_provider = HostedMicrosoftOperationalPostureProvider(
            adapter=sharepoint_adapter,
            queue=sync_queue,
            subscription_store=graph_store,
            subscription_resource=graph_resource,
            source_id=settings.source_id,
            microsoft_tenant_id=settings.microsoft_tenant_id,
            policy=settings.health_policy,
        )
        posture_service = GatewayMicrosoftOperationalPostureService(
            management=management,
            providers={SHAREPOINT_CONNECTOR_ID: posture_provider},
        )

    runtime = HostedMicrosoftGatewayRuntime(
        settings=settings,
        workers=workers,
        store=runtime_store,
        relay=relay,
        event_store=event_store,
        microsoft_credentials=microsoft_credentials,
        core_tokens=core_tokens,
        graph_subscription_store=graph_store,
        graph_subscription_lifecycle=graph_lifecycle,
        graph_resource_committer=graph_committer,
    )
    return runtime, management, _auth_policy(settings), posture_service


def _connector_instance(
    settings: HostedMicrosoftGatewaySettings,
    adapter_version: str,
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=settings.instance_id,
        connector_id=SHAREPOINT_CONNECTOR_ID,
        connector_version=adapter_version,
        enabled=True,
        scope=ConnectorScope(
            tenant_id=settings.tenant_id,
            workspace_id=settings.workspace_id,
        ),
        source=ConnectorSource(
            name="EchoMedia SharePoint",
            environment="production",
        ),
        authentication=ConnectorAuthentication(
            method="bearer",
            credential_ref=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        ),
        collection=ConnectorCollection(
            mode="poll",
            interval_seconds=settings.poll_interval_seconds,
            batch_size=500,
        ),
        checkpoint=ConnectorCheckpointPolicy(
            strategy="source_cursor",
            durable=True,
        ),
        policy=ConnectorPolicyBinding(
            capture_profile="ets.capture.microsoft.sharepoint.metadata.v1",
            normalization_profile=(
                "ets.connector.microsoft.sharepoint-onedrive-metadata.v1"
            ),
        ),
        retry=ConnectorRetryPolicy(
            max_attempts=8,
            backoff="exponential",
            max_age_seconds=86_400,
        ),
        gap_detection=ConnectorGapPolicy(enabled=True),
        settings={
            "tenant_profile_id": _SHAREPOINT_PROFILE_ID,
            "scope": "drive",
            "drive_id": settings.sharepoint_drive_id,
        },
    )


def _entra_connector_instance(
    settings: HostedMicrosoftGatewaySettings,
    adapter_version: str,
    collection: EntraDeltaCollection,
) -> ConnectorInstanceV1:
    suffix = _ENTRA_USERS_SUFFIX if collection == "users" else _ENTRA_GROUPS_SUFFIX
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=_derived_identifier(settings.instance_id, suffix, maximum=128),
        connector_id=ENTRA_CONNECTOR_ID,
        connector_version=adapter_version,
        enabled=True,
        scope=ConnectorScope(
            tenant_id=settings.tenant_id,
            workspace_id=settings.workspace_id,
        ),
        source=ConnectorSource(
            name=f"EchoMedia Entra {collection.title()}",
            environment="production",
        ),
        authentication=ConnectorAuthentication(
            method="bearer",
            credential_ref=MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
        ),
        collection=ConnectorCollection(
            mode="poll",
            interval_seconds=settings.poll_interval_seconds,
            batch_size=1000,
        ),
        checkpoint=ConnectorCheckpointPolicy(
            strategy="source_cursor",
            durable=True,
        ),
        policy=ConnectorPolicyBinding(
            capture_profile="ets.capture.microsoft.entra.directory-metadata.v1",
            normalization_profile="ets.connector.microsoft.entra-directory-delta.v1",
        ),
        retry=ConnectorRetryPolicy(
            max_attempts=8,
            backoff="exponential",
            max_age_seconds=86_400,
        ),
        gap_detection=ConnectorGapPolicy(enabled=True),
        settings={
            "tenant_profile_id": _DIRECTORY_PROFILE_ID,
            "collection": collection,
        },
    )


def _purview_connector_instance(
    settings: HostedMicrosoftGatewaySettings,
    adapter_version: str,
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=_derived_identifier(
            settings.instance_id,
            _PURVIEW_SUFFIX,
            maximum=128,
        ),
        connector_id=_PURVIEW_CONNECTOR_ID,
        connector_version=adapter_version,
        enabled=True,
        scope=ConnectorScope(
            tenant_id=settings.tenant_id,
            workspace_id=settings.workspace_id,
        ),
        source=ConnectorSource(
            name="EchoMedia Purview Audit General",
            environment="production",
        ),
        authentication=ConnectorAuthentication(
            method="bearer",
            credential_ref=MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
        ),
        collection=ConnectorCollection(
            mode="poll",
            interval_seconds=settings.poll_interval_seconds,
            batch_size=500,
        ),
        checkpoint=ConnectorCheckpointPolicy(
            strategy="source_cursor",
            durable=True,
        ),
        policy=ConnectorPolicyBinding(
            capture_profile="ets.capture.microsoft.purview.audit-metadata.v1",
            normalization_profile="ets.connector.microsoft-purview.common-schema.v1",
        ),
        retry=ConnectorRetryPolicy(
            max_attempts=8,
            backoff="exponential",
            max_age_seconds=86_400,
        ),
        gap_detection=ConnectorGapPolicy(enabled=True),
        settings={
            "management_profile_id": _PURVIEW_PROFILE_ID,
            "content_type": "Audit.General",
            "service_specific_allowlist": [],
            "include_client_ip": False,
            "poll_window_seconds": 3600,
            "overlap_seconds": 300,
        },
    )


def _credential_reference(value: str) -> CredentialReferenceV1:
    return CredentialReferenceV1(
        schema_version="ets.connector.credential_ref.v1",
        ref=value,
    )


def _derived_identifier(base: str, suffix: str, *, maximum: int) -> str:
    value = f"{base}.{suffix}"
    if len(value) > maximum:
        raise RuntimeError(
            f"derived hosted Microsoft identifier exceeds {maximum} characters"
        )
    return value


def _auth_policy(settings: HostedMicrosoftGatewaySettings) -> AuthPolicy:
    if settings.auth_jwks_json is not None:
        return ProductionJWKSAuthPolicy.from_json(
            settings.auth_jwks_json,
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
            tenant_id=settings.auth_tenant_id,
            app_scope_map=settings.auth_app_scope_map,
        )
    assert settings.auth_jwks_url is not None
    return ProductionJWKSAuthPolicy.from_url(
        settings.auth_jwks_url,
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        tenant_id=settings.auth_tenant_id,
        app_scope_map=settings.auth_app_scope_map,
    )


def _load_app_scope_map() -> AppScopeMap:
    raw = _required_env("ETS_AUTH_APP_SCOPE_MAP_JSON", maximum=16_384)
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ETS_AUTH_APP_SCOPE_MAP_JSON must be valid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("ETS_AUTH_APP_SCOPE_MAP_JSON must be a JSON object")

    result: AppScopeMap = {}
    for client_id, value in decoded.items():
        if not isinstance(client_id, str) or not client_id.strip():
            raise RuntimeError("app scope map keys must be non-empty client IDs")
        if not isinstance(value, dict):
            raise RuntimeError("app scope map values must be JSON objects")
        tenant_id = value.get("tenant_id")
        workspace_id = value.get("workspace_id")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise RuntimeError("app scope map tenant_id must be a non-empty string")
        if not isinstance(workspace_id, str) or not workspace_id:
            raise RuntimeError("app scope map workspace_id must be a non-empty string")
        result[client_id] = (tenant_id, workspace_id)
    return result


def _required_env(name: str, *, maximum: int) -> str:
    value = _optional_env(name)
    if value is None:
        raise RuntimeError(f"{name} is required for hosted Gateway configuration")
    if len(value) > maximum:
        raise RuntimeError(f"{name} exceeds hosted Gateway configured bound")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_graph_notification_url(value: str) -> str:
    if len(value) > 2_000:
        raise RuntimeError("ETS_GATEWAY_GRAPH_NOTIFICATION_URL exceeds configured bound")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != "/gateway/v1/microsoft/graph"
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(
            "Graph notification URL must be an exact HTTPS hosted webhook URL"
        )
    return value


def _bounded_int_env(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value
