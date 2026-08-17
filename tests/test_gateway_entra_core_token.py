from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from ets.gateway.core_relay import CoreRelayTerminalError
from ets.gateway.entra_core_token import AzureManagedIdentityCoreTokenProvider


@dataclass(frozen=True, slots=True)
class FakeAccessToken:
    token: str
    expires_on: int


class FakeCredential:
    def __init__(
        self,
        token: FakeAccessToken | None = None,
        error: Exception | None = None,
    ) -> None:
        self.token = token or FakeAccessToken(
            token="ets-core-runtime-token",
            expires_on=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        )
        self.error = error
        self.scopes: list[tuple[str, ...]] = []
        self.closed = False

    def get_token(self, *scopes: str) -> FakeAccessToken:
        self.scopes.append(scopes)
        if self.error is not None:
            raise self.error
        return self.token

    def close(self) -> None:
        self.closed = True


def provider(
    credential: FakeCredential,
) -> AzureManagedIdentityCoreTokenProvider:
    return AzureManagedIdentityCoreTokenProvider(
        client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        core_scope="api://11111111-2222-3333-4444-555555555555/.default",
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
        credential=credential,
    )


def test_acquire_uses_only_fixed_core_scope_and_zeroizes_lease() -> None:
    credential = FakeCredential()
    instance = provider(credential)

    lease = instance.acquire(tenant_id="tenant-demo", workspace_id="workspace-demo")

    assert credential.scopes == [
        ("api://11111111-2222-3333-4444-555555555555/.default",)
    ]
    assert lease.reveal() == b"ets-core-runtime-token"
    assert "ets-core-runtime-token" not in repr(lease)
    lease.close()
    with pytest.raises(Exception, match="closed"):
        lease.reveal()


def test_acquire_rejects_any_scope_mapping_mismatch_before_token_request() -> None:
    credential = FakeCredential()
    instance = provider(credential)

    with pytest.raises(CoreRelayTerminalError, match="outside its configured ETS scope"):
        instance.acquire(tenant_id="other-tenant", workspace_id="workspace-demo")
    with pytest.raises(CoreRelayTerminalError, match="outside its configured ETS scope"):
        instance.acquire(tenant_id="tenant-demo", workspace_id="other-workspace")

    assert credential.scopes == []


def test_acquire_fails_closed_on_identity_error_without_exposing_source_error() -> None:
    credential = FakeCredential(error=RuntimeError("managed identity endpoint detail"))
    instance = provider(credential)

    with pytest.raises(CoreRelayTerminalError) as exc_info:
        instance.acquire(tenant_id="tenant-demo", workspace_id="workspace-demo")

    assert "managed identity endpoint detail" not in str(exc_info.value)


def test_acquire_rejects_expired_token() -> None:
    credential = FakeCredential(
        token=FakeAccessToken(
            token="expired-core-token",
            expires_on=int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
        )
    )
    instance = provider(credential)

    with pytest.raises(CoreRelayTerminalError, match="expired"):
        instance.acquire(tenant_id="tenant-demo", workspace_id="workspace-demo")


def test_scope_must_be_a_fixed_resource_default_scope() -> None:
    credential = FakeCredential()
    with pytest.raises(ValueError, match="default scope"):
        AzureManagedIdentityCoreTokenProvider(
            client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            core_scope="api://11111111-2222-3333-4444-555555555555/events.write",
            tenant_id="tenant-demo",
            workspace_id="workspace-demo",
            credential=credential,
        )
    with pytest.raises(ValueError, match="api:// or https://"):
        AzureManagedIdentityCoreTokenProvider(
            client_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            core_scope="urn:ets:core/.default",
            tenant_id="tenant-demo",
            workspace_id="workspace-demo",
            credential=credential,
        )


def test_close_releases_underlying_credential() -> None:
    credential = FakeCredential()
    instance = provider(credential)

    instance.close()

    assert credential.closed is True
