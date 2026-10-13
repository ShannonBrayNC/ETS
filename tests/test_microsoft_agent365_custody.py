from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
)
from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft_agent365 import (
    build_source_envelope,
    parse_agent365_inventory_response,
)
from ets.connectors.enterprise.microsoft_agent365_custody import (
    MicrosoftAgent365CredentialSession,
    MicrosoftAgent365CustodyConflict,
    MicrosoftAgent365CustodyStore,
)
from ets.connectors.enterprise.microsoft_agent365_http import (
    MicrosoftAgent365HttpResponse,
    MicrosoftAgent365InventoryAcquisition,
    MicrosoftAgent365InventorySnapshot,
)

TENANT_ID = "11111111-2222-3333-4444-555555555555"
NOW = datetime(2026, 9, 16, 20, 0, tzinfo=UTC)


def _inventory_acquisition(
    body: bytes,
    *,
    sequence: int,
    previous_hash: str | None,
) -> MicrosoftAgent365InventoryAcquisition:
    page = parse_agent365_inventory_response(body)
    response = MicrosoftAgent365HttpResponse(
        request_url="https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages",
        body=body,
        content_type="application/json",
    )
    envelope = build_source_envelope(
        body,
        source_type="agent365.package_inventory",
        tenant_id=TENANT_ID,
        acquisition_time=NOW + timedelta(seconds=sequence),
        api_version="v1.0",
        api_maturity="stable",
        request_path="/v1.0/copilot/admin/catalog/packages",
        collector_identity="ets-agent365-test",
        collector_version="1.0",
        acquisition_sequence=sequence,
        previous_envelope_hash=previous_hash,
    )
    return MicrosoftAgent365InventoryAcquisition(
        response=response,
        envelope=envelope,
        page=page,
    )


def test_custody_store_survives_reopen_and_chains_checkpoints(tmp_path: Path) -> None:
    path = tmp_path / "agent365.db"
    first = _inventory_acquisition(
        b'{"value":[{"id":"pkg-1","displayName":"One"}]}',
        sequence=0,
        previous_hash=None,
    )
    store = MicrosoftAgent365CustodyStore(path)
    checkpoint_one = store.commit_snapshot(
        MicrosoftAgent365InventorySnapshot(
            inventory_pages=(first,),
            package_details=(),
        ),
        completed_at_utc=NOW,
    )

    reopened = MicrosoftAgent365CustodyStore(path)
    assert reopened.get_latest_checkpoint(TENANT_ID) == checkpoint_one
    assert reopened.list_envelopes(TENANT_ID) == (first.envelope,)
    assert set(reopened.get_latest_inventory_state(TENANT_ID)) == {"pkg-1"}

    second = _inventory_acquisition(
        b'{"value":[{"id":"pkg-1","displayName":"One v2"},{"id":"pkg-2"}]}',
        sequence=1,
        previous_hash=first.envelope.envelope_hash,
    )
    checkpoint_two = reopened.commit_snapshot(
        MicrosoftAgent365InventorySnapshot(
            inventory_pages=(second,),
            package_details=(),
        ),
        completed_at_utc=NOW + timedelta(minutes=1),
    )

    assert checkpoint_two.previous_checkpoint_hash == checkpoint_one.checkpoint_hash
    assert checkpoint_two.last_acquisition_sequence == 1
    assert checkpoint_two.package_count == 2
    assert len(reopened.list_envelopes(TENANT_ID)) == 2


def test_custody_store_rejects_sequence_regression_or_fork(tmp_path: Path) -> None:
    store = MicrosoftAgent365CustodyStore(tmp_path / "agent365.db")
    first = _inventory_acquisition(
        b'{"value":[{"id":"pkg-1"}]}',
        sequence=0,
        previous_hash=None,
    )
    store.commit_snapshot(
        MicrosoftAgent365InventorySnapshot((first,), ()),
        completed_at_utc=NOW,
    )

    conflicting = _inventory_acquisition(
        b'{"value":[{"id":"pkg-2"}]}',
        sequence=0,
        previous_hash=None,
    )
    with pytest.raises(MicrosoftAgent365CustodyConflict, match="sequence"):
        store.commit_snapshot(
            MicrosoftAgent365InventorySnapshot((conflicting,), ()),
            completed_at_utc=NOW + timedelta(minutes=1),
        )


class _Provider:
    scheme = "azure-mi"

    def __init__(self) -> None:
        self.resolved = 0

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return _metadata(reference)

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        self.resolved += 1
        return CredentialLease(b"short-lived-token", _metadata(reference))


def _metadata(reference: CredentialReferenceV1) -> CredentialMetadataV1:
    return CredentialMetadataV1(
        schema_version="ets.connector.credential_metadata.v1",
        reference=reference,
        provider="fixture",
        status="available",
        version="1",
        expires_at_utc=NOW + timedelta(minutes=10),
        updated_at_utc=NOW,
    )


def _graph_reference() -> CredentialReferenceV1:
    return CredentialReferenceV1(
        schema_version="ets.connector.credential_ref.v1",
        ref=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    )


def test_credential_session_uses_existing_graph_broker_and_closes_material() -> None:
    provider = _Provider()
    session = MicrosoftAgent365CredentialSession(provider, _graph_reference())
    collector = session.collector(
        tenant_id=TENANT_ID,
        collector_identity="gateway-agent365",
        collector_version="1.0",
    )
    assert collector is not None
    assert provider.resolved == 1
    assert "short-lived-token" not in repr(session.client)

    session.close()
    with pytest.raises(RuntimeError, match="closed"):
        session.client.fetch_inventory()


def test_credential_session_rejects_non_graph_route() -> None:
    provider = _Provider()
    wrong = CredentialReferenceV1(
        schema_version="ets.connector.credential_ref.v1",
        ref="azure-mi://office-365-management/purview",
    )
    with pytest.raises(ValueError, match="Microsoft Graph credential route"):
        MicrosoftAgent365CredentialSession(provider, wrong)
    assert provider.resolved == 0
