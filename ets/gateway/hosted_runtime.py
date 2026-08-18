"""Production composition for the hosted Microsoft ETS Gateway profile."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from ets.api.auth import AppScopeMap, AuthPolicy, ProductionJWKSAuthPolicy
from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    AzureManagedIdentityGraphCredentialProvider,
)
from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import MicrosoftGraphSubscriptionStateV1
from ets.connectors.enterprise.microsoft_health import (
    MicrosoftOperationalHealthPolicyV1,
    MicrosoftOperationalPostureV1,
    evaluate_microsoft_operational_posture,
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
from ets.gateway.microsoft_graph_state import SQLiteMicrosoftGraphSubscriptionStore
from ets.gateway.microsoft_operational_posture_api import (
    GatewayMicrosoftOperationalPostureService,
    MicrosoftOperationalPostureProvider,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue
from ets.runtime.sync_queue_scope import source_scoped_sync_queue_status

_HOSTED_GATEWAY_VERSION = "0.1.0-p0-gateway-r1"
_DEFAULT_STATE_DIR = "/var/lib/ets"
_DEFAULT_MANIFEST_DIR = "/app/config/connectors/enterprise"
_WORKER_OWNER = "ets-hosted-microsoft-gateway"


@dataclass(frozen=True, slots=True)
class HostedMicrosoftGatewaySettings:
    """Deployment-authoritative settings for one hosted SharePoint Gateway instance."""

    state_dir: Path
    manifest_dir: Path
    managed_identity_client_id: str
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
    graph_subscription: MicrosoftGraphSubscriptionStateV1 | None
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

        graph_raw = _optional_env("ETS_GATEWAY_GRAPH_SUBSCRIPTION_JSON")
        policy_raw = _optional_env("ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON")
        if (graph_raw is None) != (policy_raw is None):
            raise RuntimeError(
                "Graph subscription and Microsoft health policy must be configured together"
            )
        graph_subscription = (
            None
            if graph_raw is None
            else MicrosoftGraphSubscriptionStateV1.model_validate_json(graph_raw)
        )
        health_policy = (
            None
            if policy_raw is None
            else MicrosoftOperationalHealthPolicyV1.model_validate_json(policy_raw)
        )

        return cls(
            state_dir=state_dir,
            manifest_dir=manifest_dir,
            managed_identity_client_id=_required_env(
                "ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID", maximum=100
            ),
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
            microsoft_application_id=_required_env(
                "ETS_GATEWAY_MICROSOFT_APPLICATION_ID", maximum=36
            ),
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
            graph_subscription=graph_subscription,
            health_policy=health_policy,
        )


class HostedMicrosoftOperationalPostureProvider(MicrosoftOperationalPostureProvider):
    """Read one policy-bound posture from the hosted Gateway's authoritative state."""

    def __init__(
        self,
        *,
        adapter: MicrosoftSharePointDeltaAdapter,
        queue: SyncQueue,
        subscription_store: SQLiteMicrosoftGraphSubscriptionStore,
        subscription_id: str,
        source_id: str,
        microsoft_tenant_id: str,
        policy: MicrosoftOperationalHealthPolicyV1,
    ) -> None:
        self._adapter = adapter
        self._queue = queue
        self._subscription_store = subscription_store
        self._subscription_id = subscription_id
        self._source_id = source_id
        self._microsoft_tenant_id = microsoft_tenant_id
        self._policy = policy

    def read(
        self,
        instance: ConnectorInstanceV1,
        runtime: ConnectorRuntimeStateV1,
    ) -> MicrosoftOperationalPostureV1:
        subscription = self._subscription_store.get(self._subscription_id)
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
    """Own the durable hosted Gateway services and one bounded polling worker."""

    def __init__(
        self,
        *,
        settings: HostedMicrosoftGatewaySettings,
        instance: ConnectorInstanceV1,
        store: ConnectorRuntimeStore,
        runner: GatewayConnectorCollectionRunner,
        adapter: MicrosoftSharePointDeltaAdapter,
        relay: GatewayCoreRelayWorker,
        event_store: SQLiteEventStore,
        graph_credentials: AzureManagedIdentityGraphCredentialProvider,
        core_tokens: AzureManagedIdentityCoreTokenProvider,
        graph_subscription_store: SQLiteMicrosoftGraphSubscriptionStore | None,
    ) -> None:
        self.settings = settings
        self.instance = instance
        self.store = store
        self.runner = runner
        self.adapter = adapter
        self.relay = relay
        self.event_store = event_store
        self.graph_credentials = graph_credentials
        self.core_tokens = core_tokens
        self.graph_subscription_store = graph_subscription_store
        self.last_worker_error: str | None = None
        self.last_worker_cycle_at_utc: datetime | None = None
        self._task: asyncio.Task[None] | None = None

    def run_cycle(self) -> None:
        """Run one due source collection and one bounded Core relay drain."""

        now = datetime.now(UTC)
        claimed = self.store.claim_due(
            owner=_WORKER_OWNER,
            now=now,
            lease_seconds=min(max(self.settings.poll_interval_seconds * 2, 60), 3600),
            limit=1,
        )
        if self.instance.instance_id in claimed:
            try:
                self._run_claimed_collection(now)
            finally:
                self.store.release_lease(
                    self.instance.instance_id,
                    owner=_WORKER_OWNER,
                    now=datetime.now(UTC),
                )
        self.relay.run_once(limit=50)
        self.last_worker_cycle_at_utc = datetime.now(UTC)
        self.last_worker_error = None

    def _run_claimed_collection(self, now: datetime) -> None:
        runtime = self.store.get_runtime(self.instance.instance_id)
        result = self.runner.run(
            adapter=self.adapter,
            instance=self.instance,
            principal=self.settings.source_principal,
            checkpoint=runtime.checkpoint,
        )
        if result.code == "ok":
            observation_state: ConnectorObservationState = (
                "collection_gap" if runtime.gap_open else "healthy_observation"
            )
            self.store.set_checkpoint(
                self.instance.instance_id,
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
            if runtime.retry_count >= self.instance.retry.max_attempts:
                self.store.mark_gap(self.instance.instance_id, now=now)
                return
            multiplier = 2 ** min(runtime.retry_count, 6)
            delay = min(
                self.settings.poll_interval_seconds * multiplier,
                min(self.instance.retry.max_age_seconds, 3600),
            )
            self.store.schedule_retry(
                self.instance.instance_id,
                next_attempt_at_utc=now + timedelta(seconds=delay),
                now=now,
            )
            return
        self.store.mark_gap(self.instance.instance_id, now=now)

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
        self.graph_credentials.close()
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

    @app.get("/health", tags=["runtime"])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "ets-gateway",
            "version": _HOSTED_GATEWAY_VERSION,
        }

    @app.get("/ready", tags=["runtime"])
    def ready() -> dict[str, object]:
        runtime.store.get_instance(runtime.instance.instance_id)
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

    graph_credentials = AzureManagedIdentityGraphCredentialProvider(
        client_id=settings.managed_identity_client_id
    )
    broker = CredentialBroker()
    broker.register(graph_credentials)
    credential_ref = CredentialReferenceV1(
        schema_version="ets.connector.credential_ref.v1",
        ref=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    )
    tenant_profile = MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=settings.microsoft_tenant_id,
        application_id=settings.microsoft_application_id,
        cloud="global",
        credential_ref=credential_ref,
        consent_state="granted",
    )

    registry = ConnectorRegistry.from_manifest_directory(settings.manifest_dir)
    definition = registry.get_definition(SHAREPOINT_CONNECTOR_ID)
    adapter = MicrosoftSharePointDeltaAdapter(
        definition,
        broker,
        {"hosted-microsoft": tenant_profile},
    )
    registry.register_adapter(adapter)

    instance = _connector_instance(settings, definition.adapter_version)
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
    try:
        existing = runtime_store.get_instance(instance.instance_id)
    except ConnectorInstanceNotFoundError:
        management.create_instance(bootstrap, instance)
    else:
        if existing.instance != instance:
            raise RuntimeError(
                "persisted connector instance differs from deployment-authoritative configuration"
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
                adapter_version=definition.adapter_version,
                event_type=SHAREPOINT_OBSERVED_EVENT_TYPE,
                classification="enterprise_metadata",
                redaction_profile="microsoft_sharepoint_metadata_v1",
                minimization_profile="microsoft_sharepoint_metadata_v1",
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
    runner = GatewayConnectorCollectionRunner(ingress)
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
    posture_service: GatewayMicrosoftOperationalPostureService | None = None
    if settings.graph_subscription is not None and settings.health_policy is not None:
        graph_store = SQLiteMicrosoftGraphSubscriptionStore(
            settings.state_dir / "microsoft-graph-subscriptions.db"
        )
        graph_store.register(settings.graph_subscription)
        posture_provider = HostedMicrosoftOperationalPostureProvider(
            adapter=adapter,
            queue=sync_queue,
            subscription_store=graph_store,
            subscription_id=settings.graph_subscription.subscription_id,
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
        instance=instance,
        store=runtime_store,
        runner=runner,
        adapter=adapter,
        relay=relay,
        event_store=event_store,
        graph_credentials=graph_credentials,
        core_tokens=core_tokens,
        graph_subscription_store=graph_store,
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
            "tenant_profile_id": "hosted-microsoft",
            "scope": "drive",
            "drive_id": settings.sharepoint_drive_id,
        },
    )


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
