import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.core import SignedTreeHead, canonical_sha256, canonicalize
from ets.sdk import (
    APPLICATION_SDK_COMPATIBILITY_V1,
    EventCommitReceiptV1,
    classify_api_error,
)

REPO_ROOT = Path(__file__).parents[2]


def _load_vector(path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def test_application_sdk_compatibility_contract_is_explicit_and_frozen():
    compatibility = APPLICATION_SDK_COMPATIBILITY_V1

    assert compatibility.sdk_contract == "ets.application.sdk.v1"
    assert compatibility.api_versions == ("v1",)
    assert compatibility.evidence_event_versions == ("ets.event.v1",)
    assert compatibility.capture_versions == ("ets.capture.v1",)
    assert compatibility.proof_bundle_versions == ("ets.proof_bundle.v1",)
    assert compatibility.verifier_contracts == ("ets.verifier.v1",)
    assert compatibility.connector_contracts == ("ets.connector.sdk.v1",)


def test_event_commit_receipt_is_local_commitment_only():
    receipt = EventCommitReceiptV1(
        event_id="evt_sdk_001",
        log_index=0,
        event_hash="a" * 64,
        tree_head=SignedTreeHead(
            tree_size=1,
            root_hash="b" * 64,
            created_at_utc=datetime(2026, 9, 25, 12, 0, tzinfo=UTC),
            log_id="ets-local-dev",
        ),
        inclusion_proof_url="/api/v1/proofs/inclusion/evt_sdk_001",
    )

    assert receipt.commitment_state == "committed_local"
    with pytest.raises(ValidationError):
        EventCommitReceiptV1.model_validate(
            {**receipt.model_dump(), "commitment_state": "verified"}
        )


def test_sdk_error_taxonomy_normalizes_api_codes_and_http_fallbacks():
    assert classify_api_error("ETS_EVENT_DUPLICATE", 409) == "conflict"
    assert classify_api_error("ETS_AUTH_REQUIRED", 401) == "authentication_failed"
    assert classify_api_error(None, 403) == "authorization_failed"
    assert classify_api_error(None, 503) == "server_error"
    assert classify_api_error(None, None) == "unknown_error"


def test_canonicalization_golden_vector():
    vector = _load_vector("conformance/sdk/v1/canonicalization/basic.json")

    assert canonicalize(vector["input"]).decode("utf-8") == vector["canonical_utf8"]
    assert canonical_sha256(vector["input"]) == vector["sha256"]


def test_event_hashing_golden_vector():
    vector = _load_vector("conformance/sdk/v1/event-hashing/basic.json")

    assert canonicalize(vector["hashable_payload"]).decode("utf-8") == vector["canonical_utf8"]
    assert canonical_sha256(vector["hashable_payload"]) == vector["sha256"]
