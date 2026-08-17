from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_DEFAULT_SCOPE,
    AzureManagedIdentityGraphCredentialProvider,
)
from ets.connectors.credentials.models import (
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialReferenceV1,
)
from ets.connectors.credentials.provider import (
    CredentialProviderError,
    CredentialResolutionError,
)

NOW = datetime(2026, 8, 16, 21, 0, tzinfo=UTC)


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
            token="graph-runtime-token",
            expires_on=int((NOW + timedelta(hours=1)).timestamp()),
        )
        self.error = error
        self.requested_scopes: list[tuple[str, ...]] = []
        self.closed = False

    def get_token(self, *scopes: str) -> FakeAccessToken:
        self.requested_scopes.append(scopes)
        if self.error is not None:
            raise self.error
        return self.token

    def close(self) -> None:
        self.closed = True


def reference(value: str = MICROSOFT_GRAPH_CREDENTIAL_REFERENCE) -> CredentialReferenceV1:
    return CredentialReferenceV1.model_validate(
        {
            "schema_version": CREDENTIAL_REFERENCE_SCHEMA_VERSION,
            "ref": value,
        }
    )


def provider(
    credential: FakeCredential,
) -> AzureManagedIdentityGraphCredentialProvider:
    return AzureManagedIdentityGraphCredentialProvider(
        client_id="11111111-2222-3333-4444-555555555555",
        credential=credential,
        clock=lambda: NOW,
    )


def test_describe_exposes_no_token_material() -> None:
    credential = FakeCredential()
    instance = provider(credential)

    metadata = instance.describe(reference())

    assert metadata.provider == "azure-managed-identity"
    assert metadata.status == "available"
    assert metadata.version is None
    assert metadata.expires_at_utc is None
    assert "graph-runtime-token" not in metadata.model_dump_json()
    assert credential.requested_scopes == []


def test_resolve_acquires_only_fixed_graph_scope_and_zeroizes_lease() -> None:
    credential = FakeCredential()
    instance = provider(credential)

    lease = instance.resolve(reference())

    assert credential.requested_scopes == [(MICROSOFT_GRAPH_DEFAULT_SCOPE,)]
    assert lease.reveal() == b"graph-runtime-token"
    assert lease.metadata.expires_at_utc == NOW + timedelta(hours=1)
    assert "graph-runtime-token" not in repr(lease)
    lease.close()
    with pytest.raises(Exception, match="closed"):
        lease.reveal()


def test_resolve_fails_closed_when_managed_identity_cannot_get_token() -> None:
    instance = provider(FakeCredential(error=RuntimeError("identity endpoint unavailable")))

    with pytest.raises(CredentialResolutionError) as exc_info:
        instance.resolve(reference())

    assert exc_info.value.status == "unavailable"
    assert "identity endpoint unavailable" not in str(exc_info.value)


def test_resolve_rejects_expired_token() -> None:
    credential = FakeCredential(
        token=FakeAccessToken(
            token="expired-token",
            expires_on=int((NOW - timedelta(seconds=1)).timestamp()),
        )
    )
    instance = provider(credential)

    with pytest.raises(CredentialResolutionError) as exc_info:
        instance.resolve(reference())

    assert exc_info.value.status == "expired"


def test_provider_rejects_non_graph_reference() -> None:
    instance = provider(FakeCredential())

    with pytest.raises(CredentialProviderError):
        instance.describe(reference("azure-mi://other-resource"))


def test_provider_closes_underlying_credential() -> None:
    credential = FakeCredential()
    instance = provider(credential)

    instance.close()

    assert credential.closed is True
