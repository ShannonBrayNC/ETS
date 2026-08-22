from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_DEFAULT_SCOPE,
    MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
    MICROSOFT_PURVIEW_DEFAULT_SCOPE,
    AzureManagedIdentityCredentialProfile,
    AzureManagedIdentityCredentialProvider,
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
ROOT = Path(__file__).resolve().parents[1]
IDENTITY_BOUNDARY = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_IDENTITY_BOUNDARY_V1.md"
).read_text(encoding="utf-8")


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
        self.close_count = 0

    def get_token(self, *scopes: str) -> FakeAccessToken:
        self.requested_scopes.append(scopes)
        if self.error is not None:
            raise self.error
        return self.token

    def close(self) -> None:
        self.closed = True
        self.close_count += 1


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


def test_profiled_provider_routes_directory_and_purview_to_separate_identities() -> None:
    directory = FakeCredential()
    purview = FakeCredential(
        token=FakeAccessToken(
            token="purview-runtime-token",
            expires_on=int((NOW + timedelta(hours=1)).timestamp()),
        )
    )
    directory_client_id = "11111111-2222-3333-4444-555555555555"
    purview_client_id = "66666666-7777-8888-9999-000000000000"
    instance = AzureManagedIdentityCredentialProvider(
        (
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
                client_id=directory_client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
                client_id=purview_client_id,
                scope=MICROSOFT_PURVIEW_DEFAULT_SCOPE,
            ),
        ),
        credentials={
            directory_client_id: directory,
            purview_client_id: purview,
        },
        clock=lambda: NOW,
    )

    with instance.resolve(reference(MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE)) as lease:
        assert lease.reveal() == b"graph-runtime-token"
    with instance.resolve(reference(MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE)) as lease:
        assert lease.reveal() == b"purview-runtime-token"

    assert directory.requested_scopes == [(MICROSOFT_GRAPH_DEFAULT_SCOPE,)]
    assert purview.requested_scopes == [(MICROSOFT_PURVIEW_DEFAULT_SCOPE,)]


def test_profiled_provider_rejects_unconfigured_reference_without_token_request() -> None:
    directory = FakeCredential()
    client_id = "11111111-2222-3333-4444-555555555555"
    instance = AzureManagedIdentityCredentialProvider(
        (
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
                client_id=client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
        ),
        credentials={client_id: directory},
        clock=lambda: NOW,
    )

    with pytest.raises(CredentialProviderError, match="unconfigured reference"):
        instance.resolve(reference(MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE))

    assert directory.requested_scopes == []


@pytest.mark.parametrize(
    ("reference_value", "scope"),
    (
        ("local://microsoft-graph/directory", MICROSOFT_GRAPH_DEFAULT_SCOPE),
        (MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE, "http://graph.microsoft.com/.default"),
        (MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE, "https://graph.microsoft.com/User.Read.All"),
        (MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE, "https://user@example.com/.default"),
    ),
)
def test_profile_rejects_non_qualified_reference_or_audience(
    reference_value: str,
    scope: str,
) -> None:
    with pytest.raises(ValueError):
        AzureManagedIdentityCredentialProfile(
            reference=reference_value,
            client_id="11111111-2222-3333-4444-555555555555",
            scope=scope,
        )


def test_profiled_provider_closes_shared_transport_once() -> None:
    shared = FakeCredential()
    client_id = "11111111-2222-3333-4444-555555555555"
    instance = AzureManagedIdentityCredentialProvider(
        (
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
                client_id=client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
                client_id=client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
        ),
        credentials={client_id: shared},
        clock=lambda: NOW,
    )

    instance.close()
    instance.close()

    assert shared.closed is True
    assert shared.close_count == 1


def test_profiled_provider_does_not_initialize_transport_after_close() -> None:
    created_client_ids: list[str] = []
    client_id = "11111111-2222-3333-4444-555555555555"

    def credential_factory(value: str) -> FakeCredential:
        created_client_ids.append(value)
        return FakeCredential()

    instance = AzureManagedIdentityCredentialProvider(
        (
            AzureManagedIdentityCredentialProfile(
                reference=MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
                client_id=client_id,
                scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
            ),
        ),
        credential_factory=credential_factory,
        clock=lambda: NOW,
    )
    instance.close()

    with pytest.raises(CredentialProviderError, match="provider is closed"):
        instance.resolve(reference(MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE))

    assert created_client_ids == []


def test_p0_identity_boundary_is_separated_and_does_not_expand_onedrive() -> None:
    for required in (
        MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
        MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
        "\x60User.Read.All\x60",
        "\x60Group.Read.All\x60",
        "\x60ActivityFeed.Read\x60",
        "must not receive \x60Directory.Read.All\x60",
        "does not grant \x60Files.Read.All\x60",
        "does not start the soak clock",
        "public hostname",
    ):
        assert required in IDENTITY_BOUNDARY
