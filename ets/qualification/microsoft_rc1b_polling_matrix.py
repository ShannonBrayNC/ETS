"""Deterministic RC1B directory/drive polling matrix for the release image.

The matrix exercises the shipped Entra and SharePoint/OneDrive delta adapters,
HTTP retry policy, and Gateway commit path with synthetic non-customer fixtures
and isolated temporary state. It never mutates the live Microsoft tenant or the
live Gateway database and never returns identifiers, cursors, or credentials.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_connector import (
    ENTRA_CONNECTOR_ID,
    MicrosoftEntraDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_entra_delta import (
    EntraDeltaCollection,
    EntraDeltaRequestProfile,
    MicrosoftEntraDeltaPageV1,
    entra_delta_request_profile,
    parse_entra_delta_page,
)
from ets.connectors.enterprise.microsoft_entra_http import (
    MicrosoftEntraDeltaHttpClient,
    MicrosoftEntraDeltaStateExpiredError,
    MicrosoftEntraDeltaThrottleError,
)
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRecordV1,
    MicrosoftSharePointDeltaRequestProfile,
    sharepoint_drive_delta_request_profile,
)
from ets.connectors.enterprise.microsoft_sharepoint_http import (
    MicrosoftSharePointDeltaHttpClient,
    MicrosoftSharePointDeltaStateExpiredError,
    MicrosoftSharePointDeltaThrottleError,
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
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.connector_runner import GatewayConnectorCollectionRunner
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

NOW = datetime(2026, 8, 24, 18, 0, tzinfo=UTC)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
CREDENTIAL_REF = "fixture://microsoft/rc1b"
CREDENTIAL_MATERIAL = b"bounded-rc1b-fixture-token"
PROFILE_ID = "rc1b-matrix"
DRIVE_ID = "drive-rc1b-matrix"
MANIFESTS = Path("config/connectors/enterprise")


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
        return CredentialLease(CREDENTIAL_MATERIAL, self.describe(reference))


class _EntraClient:
    def __init__(
        self,
        pages: tuple[MicrosoftEntraDeltaPageV1, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.pages = pages
        self.error = error
        self.request_urls: list[str | None] = []

    def fetch(self, request_url: str | None = None) -> MicrosoftEntraDeltaPageV1:
        self.request_urls.append(request_url)
        if self.error is not None:
            raise self.error
        if not self.pages:
            raise RuntimeError("RC1B Entra matrix client has no page")
        index = min(len(self.request_urls) - 1, len(self.pages) - 1)
        return self.pages[index]

    def close(self) -> None:
        return None


class _DriveClient:
    def __init__(
        self,
        pages: tuple[MicrosoftSharePointDeltaPageV1, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.pages = pages
        self.error = error
        self.request_urls: list[str | None] = []

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        self.request_urls.append(request_url)
        if self.error is not None:
            raise self.error
        if not self.pages:
            raise RuntimeError("RC1B drive matrix client has no page")
        index = min(len(self.request_urls) - 1, len(self.pages) - 1)
        return self.pages[index]

    def close(self) -> None:
        return None


class _ThrottleOpener:
    def open(self, request: Request, *, timeout: float) -> object:
        headers = Message()
        headers["Retry-After"] = "90"
        raise HTTPError(request.full_url, 429, "matrix throttle", headers, None)


class _FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("bounded RC1B matrix queue failure")
        return super().enqueue(payload)


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
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


def _entra_instance(collection: EntraDeltaCollection) -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": f"rc1b-matrix-{collection}",
            "connector_id": ENTRA_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="matrix-tenant", workspace_id="matrix-workspace"
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name=f"entra-{collection}-matrix", environment="qualification"
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer", credential_ref=CREDENTIAL_REF
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll", interval_seconds=60, batch_size=100
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor", durable=True
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.entra.delta.v1",
                normalization_profile="normalize.microsoft.entra.delta.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "collection": collection,
            },
        }
    )


def _drive_instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "rc1b-matrix-drive",
            "connector_id": SHAREPOINT_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="matrix-tenant", workspace_id="matrix-workspace"
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="onedrive-metadata-matrix", environment="qualification"
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer", credential_ref=CREDENTIAL_REF
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll", interval_seconds=60, batch_size=100
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor", durable=True
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.sharepoint.metadata.v1",
                normalization_profile="normalize.microsoft.sharepoint.metadata.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "scope": "drive",
                "drive_id": DRIVE_ID,
            },
        }
    )


def _entra_pages(
    collection: EntraDeltaCollection,
) -> tuple[MicrosoftEntraDeltaPageV1, MicrosoftEntraDeltaPageV1]:
    profile = entra_delta_request_profile(_tenant(), collection)
    next_url = profile.initial_url + "?$skiptoken=matrix-next"
    delta_url = profile.initial_url + "?$deltatoken=matrix-final"
    if collection == "users":
        active = {"id": "matrix-user", "accountEnabled": True, "userType": "Member"}
    else:
        active = {
            "id": "matrix-group",
            "mailEnabled": False,
            "securityEnabled": True,
            "groupTypes": [],
        }
    first = parse_entra_delta_page(
        json.dumps({"@odata.nextLink": next_url, "value": [active]}).encode(),
        profile=profile,
        request_url=profile.initial_url,
    )
    removed = {"id": active["id"], "@removed": {"reason": "deleted"}}
    final = parse_entra_delta_page(
        json.dumps({"@odata.deltaLink": delta_url, "value": [removed]}).encode(),
        profile=profile,
        request_url=next_url,
    )
    return first, final


def _drive_pages() -> tuple[MicrosoftSharePointDeltaPageV1, MicrosoftSharePointDeltaPageV1]:
    profile = sharepoint_drive_delta_request_profile(PROFILE_ID, _tenant(), DRIVE_ID)
    next_url = profile.initial_url + "?$skiptoken=matrix-next"
    delta_url = profile.initial_url + "?$deltatoken=matrix-final"
    active = MicrosoftSharePointDeltaRecordV1(
        source_record_id="matrix-drive-active",
        object_id="matrix-item",
        scope="drive",
        deleted=False,
        source_modified_at_utc=NOW,
        metadata={
            "name": "matrix-document.docx",
            "size": 128,
            "parent": {"id": "matrix-folder", "drive_id": DRIVE_ID},
        },
    )
    removed = MicrosoftSharePointDeltaRecordV1(
        source_record_id="matrix-drive-removed",
        object_id="matrix-item",
        scope="drive",
        deleted=True,
        source_modified_at_utc=None,
        metadata={},
    )
    return (
        MicrosoftSharePointDeltaPageV1(
            scope="drive",
            records=(active,),
            checkpoint_url=next_url,
            cycle_complete=False,
        ),
        MicrosoftSharePointDeltaPageV1(
            scope="drive",
            records=(removed,),
            checkpoint_url=delta_url,
            cycle_complete=True,
        ),
    )


def _entra_adapter(client: _EntraClient) -> MicrosoftEntraDeltaAdapter:
    def factory(
        profile: EntraDeltaRequestProfile,
        material: bytes,
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> _EntraClient:
        if material != CREDENTIAL_MATERIAL or profile.graph_root != "https://graph.microsoft.com":
            raise ValueError("RC1B matrix Entra boundary changed")
        if timeout_seconds != 30.0 or maximum_response_bytes != 2 * 1024 * 1024:
            raise ValueError("RC1B matrix Entra bounds changed")
        return client

    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    return MicrosoftEntraDeltaAdapter(
        registry.get_definition(ENTRA_CONNECTOR_ID),
        _CredentialResolver(),
        {PROFILE_ID: _tenant()},
        client_factory=factory,
    )


def _drive_adapter(client: _DriveClient) -> MicrosoftSharePointDeltaAdapter:
    def factory(
        profile: MicrosoftSharePointDeltaRequestProfile,
        material: bytes,
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> _DriveClient:
        if (
            material != CREDENTIAL_MATERIAL
            or profile.tenant_profile_id != PROFILE_ID
            or profile.resource_path != f"/v1.0/drives/{DRIVE_ID}/root/delta"
        ):
            raise ValueError("RC1B matrix drive boundary changed")
        if timeout_seconds != 30.0 or maximum_response_bytes != 1024 * 1024:
            raise ValueError("RC1B matrix drive bounds changed")
        return client

    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    return MicrosoftSharePointDeltaAdapter(
        registry.get_definition(SHAREPOINT_CONNECTOR_ID),
        _CredentialResolver(),
        {PROFILE_ID: _tenant()},
        client_factory=factory,
    )


def _runner(
    state_path: Path,
    registration: SourceRegistration,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayConnectorCollectionRunner, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(state_path)
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([registration]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def _entra_registration() -> SourceRegistration:
    return SourceRegistration(
        principal="spiffe://example.test/rc1b-entra-matrix",
        source_id="rc1b-entra-matrix",
        source_system=ENTRA_CONNECTOR_ID,
        tenant_id="matrix-tenant-authoritative",
        workspace_id="matrix-workspace-authoritative",
        adapter_id=ENTRA_CONNECTOR_ID,
        adapter_version="1.0",
        event_type="microsoft.entra.directory_change.observed",
        classification="internal",
        redaction_profile="microsoft-entra-redaction-v1",
        minimization_profile="microsoft-entra-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="unknown",
    )


def _drive_registration() -> SourceRegistration:
    return SourceRegistration(
        principal="spiffe://example.test/rc1b-drive-matrix",
        source_id="rc1b-drive-matrix",
        source_system=SHAREPOINT_CONNECTOR_ID,
        tenant_id="matrix-tenant-authoritative",
        workspace_id="matrix-workspace-authoritative",
        adapter_id=SHAREPOINT_CONNECTOR_ID,
        adapter_version="1.0",
        event_type="microsoft.sharepoint.metadata.observed",
        classification="internal",
        redaction_profile="sharepoint-metadata-redaction-v1",
        minimization_profile="sharepoint-metadata-only-v1",
        clock_quality="unknown",
    )


def _http_retry_after_verified() -> bool:
    entra_profile = entra_delta_request_profile(_tenant(), "users")
    entra = MicrosoftEntraDeltaHttpClient(entra_profile, CREDENTIAL_MATERIAL)
    entra._opener = _ThrottleOpener()  # type: ignore[assignment]
    try:
        entra.fetch()
    except MicrosoftEntraDeltaThrottleError as exc:
        entra_ok = exc.retry_after_seconds == 90
    else:
        entra_ok = False
    finally:
        entra.close()

    drive_profile = sharepoint_drive_delta_request_profile(PROFILE_ID, _tenant(), DRIVE_ID)
    drive = MicrosoftSharePointDeltaHttpClient(drive_profile, CREDENTIAL_MATERIAL)
    drive._opener = _ThrottleOpener()  # type: ignore[assignment]
    try:
        drive.fetch()
    except MicrosoftSharePointDeltaThrottleError as exc:
        drive_ok = exc.retry_after_seconds == 90
    else:
        drive_ok = False
    finally:
        drive.close()
    return entra_ok and drive_ok


def run_rc1b_directory_drive_fault_matrix() -> dict[str, bool]:
    """Run the bounded matrix and return public-safe pass predicates only."""

    user_pages = _entra_pages("users")
    user_client = _EntraClient(user_pages)
    user_adapter = _entra_adapter(user_client)
    user_instance = _entra_instance("users")
    user_first = user_adapter.collect(user_instance, None)
    user_final = user_adapter.collect(user_instance, user_first.checkpoint)
    user_removed = user_adapter.normalize(user_instance, user_final.records[0])
    user_progression = (
        user_first.code == "ok"
        and user_first.has_more
        and user_first.checkpoint is not None
        and user_final.code == "ok"
        and not user_final.has_more
        and user_final.checkpoint is not None
        and user_first.checkpoint != user_final.checkpoint
        and user_client.request_urls == [None, user_first.checkpoint.cursor]
    )
    user_audit = user_removed.metadata.get("audit")
    user_tombstone = (
        user_removed.event_type == "microsoft.entra.directory_object.removed"
        and isinstance(user_audit, dict)
        and user_audit.get("removed_reason") == "deleted"
    )

    group_pages = _entra_pages("groups")
    group_client = _EntraClient(group_pages)
    group_adapter = _entra_adapter(group_client)
    group_instance = _entra_instance("groups")
    group_first = group_adapter.collect(group_instance, None)
    group_final = group_adapter.collect(group_instance, group_first.checkpoint)
    group_removed = group_adapter.normalize(group_instance, group_final.records[0])
    group_progression = (
        group_first.code == "ok"
        and group_first.has_more
        and group_final.code == "ok"
        and not group_final.has_more
        and group_first.checkpoint is not None
        and group_final.checkpoint is not None
        and group_first.checkpoint != group_final.checkpoint
    )
    group_tombstone = group_removed.event_type == "microsoft.entra.directory_object.removed"

    drive_pages = _drive_pages()
    drive_client = _DriveClient(drive_pages)
    drive_adapter = _drive_adapter(drive_client)
    drive_instance = _drive_instance()
    drive_first = drive_adapter.collect(drive_instance, None)
    drive_final = drive_adapter.collect(drive_instance, drive_first.checkpoint)
    drive_removed = drive_adapter.normalize(drive_instance, drive_final.records[0])
    drive_progression = (
        drive_first.code == "ok"
        and drive_first.has_more
        and drive_first.checkpoint is not None
        and drive_final.code == "ok"
        and not drive_final.has_more
        and drive_final.checkpoint is not None
        and drive_first.checkpoint != drive_final.checkpoint
        and drive_client.request_urls == [None, drive_first.checkpoint.cursor]
    )
    drive_tombstone = (
        drive_removed.event_type == "microsoft.sharepoint.metadata.deleted"
        and drive_removed.metadata["deleted"] is True
    )

    prior_user_checkpoint = user_final.checkpoint
    prior_drive_checkpoint = drive_final.checkpoint
    if prior_user_checkpoint is None or prior_drive_checkpoint is None:
        raise RuntimeError("RC1B matrix terminal checkpoint is unavailable")
    entra_throttled = _entra_adapter(
        _EntraClient(error=MicrosoftEntraDeltaThrottleError(90))
    ).collect(user_instance, prior_user_checkpoint)
    drive_throttled = _drive_adapter(
        _DriveClient(error=MicrosoftSharePointDeltaThrottleError(90))
    ).collect(drive_instance, prior_drive_checkpoint)
    throttle_withheld = (
        entra_throttled.code == "throttled"
        and entra_throttled.checkpoint == prior_user_checkpoint
        and drive_throttled.code == "throttled"
        and drive_throttled.checkpoint == prior_drive_checkpoint
    )

    entra_expired_adapter = _entra_adapter(
        _EntraClient(error=MicrosoftEntraDeltaStateExpiredError("matrix expired"))
    )
    drive_expired_adapter = _drive_adapter(
        _DriveClient(error=MicrosoftSharePointDeltaStateExpiredError("matrix expired"))
    )
    entra_gap = entra_expired_adapter.reconcile(user_instance, prior_user_checkpoint)
    drive_gap = drive_expired_adapter.reconcile(drive_instance, prior_drive_checkpoint)
    expired_cursor_gap = (
        entra_gap.code == "gap_detected"
        and entra_gap.gap_detected
        and not entra_gap.reconciled
        and entra_gap.checkpoint == prior_user_checkpoint
        and drive_gap.code == "gap_detected"
        and drive_gap.gap_detected
        and not drive_gap.reconciled
        and drive_gap.checkpoint == prior_drive_checkpoint
    )

    with tempfile.TemporaryDirectory(prefix="ets-rc1b-matrix-") as directory:
        root = Path(directory)
        entra_runner, entra_log, entra_queue = _runner(
            root / "entra-replay.db", _entra_registration()
        )
        replay_page = _entra_pages("users")[0]
        replay_page = replay_page.model_copy(
            update={"next_link": None, "delta_link": replay_page.checkpoint_url}
        )
        replay_adapter = _entra_adapter(_EntraClient((replay_page,)))
        replay_first = entra_runner.run(
            adapter=replay_adapter,
            instance=user_instance,
            principal=_entra_registration().principal,
            checkpoint=None,
        )
        replay_second = entra_runner.run(
            adapter=replay_adapter,
            instance=user_instance,
            principal=_entra_registration().principal,
            checkpoint=None,
        )
        entra_replay = (
            replay_first.code == "ok"
            and replay_second.code == "ok"
            and len(entra_log.list_entries()) == 1
            and entra_queue.status().queue_depth == 1
        )

        drive_runner, drive_log, drive_queue = _runner(
            root / "drive-replay.db", _drive_registration()
        )
        drive_replay_page = replace(drive_pages[0], cycle_complete=True)
        drive_replay_adapter = _drive_adapter(_DriveClient((drive_replay_page,)))
        drive_replay_first = drive_runner.run(
            adapter=drive_replay_adapter,
            instance=drive_instance,
            principal=_drive_registration().principal,
            checkpoint=None,
        )
        drive_replay_second = drive_runner.run(
            adapter=drive_replay_adapter,
            instance=drive_instance,
            principal=_drive_registration().principal,
            checkpoint=None,
        )
        drive_replay = (
            drive_replay_first.code == "ok"
            and drive_replay_second.code == "ok"
            and len(drive_log.list_entries()) == 1
            and drive_queue.status().queue_depth == 1
        )

        failed_queue = _FailOnceQueue(root / "partial-commit.db")
        partial_runner, partial_log, partial_queue = _runner(
            root / "partial-commit.db",
            _entra_registration(),
            queue=failed_queue,
        )
        partial_adapter = _entra_adapter(_EntraClient((replay_page,)))
        partial_first = partial_runner.run(
            adapter=partial_adapter,
            instance=user_instance,
            principal=_entra_registration().principal,
            checkpoint=None,
        )
        partial_retry = partial_runner.run(
            adapter=partial_adapter,
            instance=user_instance,
            principal=_entra_registration().principal,
            checkpoint=None,
        )
        evidence_loss_withheld = (
            partial_first.code == "retryable_error"
            and partial_first.checkpoint_to_persist is None
            and partial_first.partial_commit == 1
            and partial_retry.code == "ok"
            and partial_retry.checkpoint_to_persist is not None
            and len(partial_log.list_entries()) == 1
            and partial_queue.status().queue_depth == 1
        )

    predicates = {
        "entra_users_checkpoint_progression": user_progression,
        "entra_users_tombstone_verified": user_tombstone,
        "entra_groups_checkpoint_progression": group_progression,
        "entra_groups_tombstone_verified": group_tombstone,
        "onedrive_checkpoint_progression": drive_progression,
        "onedrive_tombstone_verified": drive_tombstone,
        "entra_replay_idempotent": entra_replay,
        "onedrive_replay_idempotent": drive_replay,
        "graph_retry_after_verified": _http_retry_after_verified(),
        "throttle_checkpoint_withheld": throttle_withheld,
        "expired_cursor_gap_verified": expired_cursor_gap,
        "evidence_loss_checkpoint_withheld": evidence_loss_withheld,
        "fault_matrix_public_safe": True,
    }
    failed = sorted(key for key, value in predicates.items() if value is not True)
    if failed:
        raise RuntimeError("RC1B directory/drive fault matrix failed: " + ",".join(failed))
    return predicates
