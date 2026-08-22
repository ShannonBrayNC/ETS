"""Hosted Microsoft Graph subscription lifecycle orchestration.

The lifecycle manager owns source operational state only. It never promotes a
subscription operation to ETS evidence and never persists client state or access-token
material.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol
from urllib.parse import quote

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import (
    GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS,
    GRAPH_MAXIMUM_RESOURCE_CHARACTERS,
    MicrosoftGraphSubscriptionStateV1,
)
from ets.connectors.enterprise.microsoft_graph_subscriptions import (
    MicrosoftGraphSubscriptionHttpClient,
    MicrosoftGraphSubscriptionThrottleError,
)

GRAPH_DRIVE_SUBSCRIPTION_MINIMUM_LIFETIME_SECONDS = 3_600
GRAPH_DRIVE_SUBSCRIPTION_MAXIMUM_LIFETIME_SECONDS = 42_300 * 60
GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_LIFETIME_SECONDS = 28 * 24 * 60 * 60
GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_RENEWAL_WINDOW_SECONDS = 24 * 60 * 60

MicrosoftGraphLifecycleAction = Literal[
    "noop",
    "deferred",
    "created",
    "recreated",
    "reauthorized",
    "renewed",
    "reauthorized_and_renewed",
]


class MicrosoftGraphSubscriptionLifecycleError(RuntimeError):
    """Raised when hosted lifecycle state cannot safely converge."""


class MicrosoftGraphCredentialResolver(Protocol):
    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class MicrosoftGraphSubscriptionLifecycleStore(Protocol):
    def get_for_resource(
        self,
        *,
        tenant_id: str,
        resource: str,
    ) -> MicrosoftGraphSubscriptionStateV1 | None: ...

    def register(self, state: MicrosoftGraphSubscriptionStateV1) -> None: ...

    def replace_for_resource(self, state: MicrosoftGraphSubscriptionStateV1) -> None: ...


class MicrosoftGraphSubscriptionClient(Protocol):
    def create(
        self,
        *,
        resource: str,
        change_type: str,
        expiration_date_time: datetime,
        client_state: str,
    ) -> MicrosoftGraphSubscriptionStateV1: ...

    def renew(
        self,
        subscription: MicrosoftGraphSubscriptionStateV1,
        *,
        expiration_date_time: datetime,
    ) -> MicrosoftGraphSubscriptionStateV1: ...

    def reauthorize(
        self,
        subscription: MicrosoftGraphSubscriptionStateV1,
    ) -> MicrosoftGraphSubscriptionStateV1: ...

    def close(self) -> None: ...


MicrosoftGraphSubscriptionClientFactory = Callable[
    [MicrosoftTenantProfileV1, bytes, str, str],
    MicrosoftGraphSubscriptionClient,
]


@dataclass(frozen=True, slots=True)
class MicrosoftGraphSubscriptionLifecycleResult:
    action: MicrosoftGraphLifecycleAction
    state: MicrosoftGraphSubscriptionStateV1 | None


class MicrosoftGraphSubscriptionLifecycleManager:
    """Converge one approved Graph resource without retaining reusable credentials."""

    def __init__(
        self,
        *,
        tenant_profile: MicrosoftTenantProfileV1,
        credential_resolver: MicrosoftGraphCredentialResolver,
        store: MicrosoftGraphSubscriptionLifecycleStore,
        resource: str,
        notification_url: str,
        client_state: str,
        lifetime_seconds: int = GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_LIFETIME_SECONDS,
        renewal_window_seconds: int = (
            GRAPH_DRIVE_SUBSCRIPTION_DEFAULT_RENEWAL_WINDOW_SECONDS
        ),
        client_factory: MicrosoftGraphSubscriptionClientFactory | None = None,
    ) -> None:
        if tenant_profile.consent_state != "granted":
            raise ValueError("Graph subscription lifecycle requires granted administrator consent")
        if not 1 <= len(resource) <= GRAPH_MAXIMUM_RESOURCE_CHARACTERS:
            raise ValueError("Graph subscription resource length is invalid")
        if any(character in resource for character in ("\x00", "\r", "\n")):
            raise ValueError("Graph subscription resource contains control data")
        if not 1 <= len(client_state) <= min(
            GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS,
            128,
        ):
            raise ValueError("Graph subscription clientState length is invalid")
        if not (
            GRAPH_DRIVE_SUBSCRIPTION_MINIMUM_LIFETIME_SECONDS
            <= lifetime_seconds
            <= GRAPH_DRIVE_SUBSCRIPTION_MAXIMUM_LIFETIME_SECONDS
        ):
            raise ValueError("Graph drive subscription lifetime is outside the qualified bound")
        if not 60 <= renewal_window_seconds < lifetime_seconds:
            raise ValueError("Graph subscription renewal window is outside the qualified bound")

        self._tenant_profile = tenant_profile
        self._credential_resolver = credential_resolver
        self._credential_reference = tenant_profile.credential_ref
        self._store = store
        self._resource = resource
        self._notification_url = notification_url
        self._client_state = client_state
        self._lifetime = timedelta(seconds=lifetime_seconds)
        self._renewal_window = timedelta(seconds=renewal_window_seconds)
        self._client_factory = client_factory or _default_client_factory
        self._retry_not_before_utc: datetime | None = None

    @property
    def resource(self) -> str:
        return self._resource

    def run_once(
        self,
        *,
        now: datetime | None = None,
    ) -> MicrosoftGraphSubscriptionLifecycleResult:
        current_time = _utc(now or datetime.now(UTC))
        if (
            self._retry_not_before_utc is not None
            and current_time < self._retry_not_before_utc
        ):
            return MicrosoftGraphSubscriptionLifecycleResult(
                action="deferred",
                state=self._current(),
            )

        try:
            result = self._converge(current_time)
        except MicrosoftGraphSubscriptionThrottleError as exc:
            self._retry_not_before_utc = current_time + timedelta(
                seconds=exc.retry_after_seconds
            )
            raise
        self._retry_not_before_utc = None
        return result

    def _converge(
        self,
        now: datetime,
    ) -> MicrosoftGraphSubscriptionLifecycleResult:
        current = self._current()
        if current is None:
            created = self._create(now, gap_state="none")
            self._store.replace_for_resource(created)
            return MicrosoftGraphSubscriptionLifecycleResult("created", created)

        if current.status == "removed" or current.expiration_date_time <= now:
            created = self._create(now, gap_state="possible")
            self._store.replace_for_resource(created)
            return MicrosoftGraphSubscriptionLifecycleResult("recreated", created)
        if current.status == "disabled":
            raise MicrosoftGraphSubscriptionLifecycleError(
                "disabled Microsoft Graph subscription requires governed operator review"
            )

        action: MicrosoftGraphLifecycleAction = "noop"
        if current.status == "reauthorization_required":
            with self._client() as client:
                current = client.reauthorize(current)
            self._store.register(current)
            action = "reauthorized"

        if current.expiration_date_time <= now + self._renewal_window:
            with self._client() as client:
                current = client.renew(
                    current,
                    expiration_date_time=now + self._lifetime,
                )
            self._store.register(current)
            action = (
                "reauthorized_and_renewed"
                if action == "reauthorized"
                else "renewed"
            )
        return MicrosoftGraphSubscriptionLifecycleResult(action, current)

    def _create(
        self,
        now: datetime,
        *,
        gap_state: Literal["none", "possible"],
    ) -> MicrosoftGraphSubscriptionStateV1:
        with self._client() as client:
            created = client.create(
                resource=self._resource,
                change_type="updated",
                expiration_date_time=now + self._lifetime,
                client_state=self._client_state,
            )
        if gap_state == "possible":
            created = created.model_copy(update={"gap_state": "possible"})
        return created

    def _current(self) -> MicrosoftGraphSubscriptionStateV1 | None:
        return self._store.get_for_resource(
            tenant_id=self._tenant_profile.tenant_id,
            resource=self._resource,
        )

    @contextmanager
    def _client(self) -> Iterator[MicrosoftGraphSubscriptionClient]:
        with self._credential_resolver.resolve(self._credential_reference) as lease:
            client = self._client_factory(
                self._tenant_profile,
                lease.reveal(),
                self._notification_url,
                self._notification_url,
            )
            try:
                yield client
            finally:
                client.close()


def sharepoint_drive_subscription_resource(drive_id: str) -> str:
    """Return the only hosted P0 Graph resource shape for a SharePoint drive."""

    normalized = drive_id.strip()
    if not 1 <= len(normalized) <= 500:
        raise ValueError("SharePoint drive identifier is outside the qualified bound")
    if any(character in normalized for character in ("\x00", "\r", "\n", "/")):
        raise ValueError("SharePoint drive identifier contains unsupported data")
    return f"drives/{quote(normalized, safe='')}/root"


def _default_client_factory(
    tenant_profile: MicrosoftTenantProfileV1,
    credential_material: bytes,
    notification_url: str,
    lifecycle_notification_url: str,
) -> MicrosoftGraphSubscriptionClient:
    return MicrosoftGraphSubscriptionHttpClient(
        tenant_profile,
        credential_material,
        notification_url=notification_url,
        lifecycle_notification_url=lifecycle_notification_url,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Graph subscription lifecycle clock must be timezone-aware")
    return value.astimezone(UTC)
