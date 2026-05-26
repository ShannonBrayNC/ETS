import base64
from datetime import UTC, datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

from ets import __version__
from ets.api.app import create_app
from ets.core.models import EvidenceEvent
from ets.core.signing import Ed25519TreeHeadSigner


def make_event(event_id: str = "evt_001") -> dict:
    event = EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id="evidence_001",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="c" * 64,
        content_hash_alg="sha256",
        metadata={"case": "alpha"},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    )
    return event.model_dump(mode="json")


def make_client() -> TestClient:
    return TestClient(create_app())


def append_event(client: TestClient, event_id: str = "evt_001") -> dict:
    response = client.post("/api/v1/events", json=make_event(event_id))
    assert response.status_code == 201
    return response.json()


def make_artifact_registration(
    artifact_id: str = "artifact_001",
    content: bytes = b"synthetic artifact",
    metadata: dict | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_base64": base64.b64encode(content).decode("ascii"),
        "tenant_id": "tenant_a",
        "workspace_id": "workspace_a",
        "content_type": "application/json",
        "metadata": metadata or {"case": "sprint-2"},
        "source_system": "pytest",
    }


def test_health_and_ready_routes():
    client = make_client()

    assert client.get("/health").json() == {"status": "ok", "version": __version__}
    assert client.get("/version").json() == {
        "name": "Evidence Transparency System",
        "version": __version__,
        "api_version": "v1",
    }
    assert client.get("/ready").json() == {
        "status": "ready",
        "storage": "in_memory",
        "version": __version__,
        "auth": "local_header",
        "signing": "local_unsigned",
    }


def test_log_head_route_returns_unsigned_local_head():
    client = make_client()

    response = client.get("/api/v1/log/head")

    assert response.status_code == 200
    body = response.json()
    assert body["tree_size"] == 0
    assert body["log_id"] == "ets-local-dev"
    assert body["signature"] is None


def test_tree_head_signature_routes_verify_valid_invalid_and_expired_keys():
    private_key_hex = "07" * 32
    public_key_hex = (
        Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
        .hex()
    )
    client = TestClient(
        create_app(
            signer=Ed25519TreeHeadSigner(private_key_hex, "fixture-key"),
            signing_mode="ed25519",
        )
    )
    tree_head = client.get("/tree-head/latest").json()

    valid_response = client.post(
        "/verify/signature",
        json={"tree_head": tree_head, "public_key_hex": public_key_hex},
    )
    wrong_signer_response = client.post(
        "/verify/signature",
        json={"tree_head": tree_head, "public_key_hex": "0" * 64},
    )
    expired_response = client.post(
        "/verify/signature",
        json={
            "tree_head": tree_head,
            "public_key_hex": public_key_hex,
            "valid_at_utc": "2026-05-26T12:00:00Z",
            "key_not_after_utc": "2026-05-25T12:00:00Z",
        },
    )

    assert tree_head["signature_alg"] == "ed25519"
    assert client.get("/tree-head/latest").status_code == 200
    assert client.get("/tree-head/latest").json()["signature"] is not None
    assert client.get("/tree-head/current").status_code == 404
    assert valid_response.json()["valid"] is True
    assert wrong_signer_response.json()["valid"] is False
    assert expired_response.json()["reason"] == "key is expired"


def test_event_ingestion_updates_tree_and_returns_proof_url():
    client = make_client()

    body = append_event(client)

    assert body["event_id"] == "evt_001"
    assert body["log_index"] == 0
    assert len(body["event_hash"]) == 64
    assert body["tree_head"]["tree_size"] == 1
    assert body["inclusion_proof_url"] == "/api/v1/proofs/inclusion/evt_001"


def test_anchor_routes_export_history_and_verify_roots():
    client = make_client()
    append_event(client, "evt_001")

    latest_response = client.get("/anchors/latest?target=azure_immutable_storage")
    history_response = client.get("/anchors/history")
    verify_response = client.post("/verify/anchor", json=latest_response.json())

    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["target"] == "azure_immutable_storage"
    assert latest["tree_size"] == 1
    assert latest["merkle_root"] == latest["signed_tree_head"]["root_hash"]
    assert len(latest["latest_block_hash"]) == 64
    assert history_response.status_code == 200
    assert history_response.json()[0]["anchor_id"] == latest["anchor_id"]
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert verify_response.json()["reason"] == "ok"


def test_anchor_verify_rejects_mismatch_without_server_state():
    client = make_client()
    append_event(client, "evt_001")
    anchor = client.get("/anchors/latest").json()
    anchor["latest_block_hash"] = "0" * 64

    response = client.post("/verify/anchor", json=anchor)

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["reason"] == "anchor hash does not match contents"


def test_duplicate_event_returns_deterministic_conflict():
    client = make_client()
    append_event(client)

    response = client.post("/api/v1/events", json=make_event())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ETS_EVENT_DUPLICATE"


def test_event_can_be_retrieved_by_id_and_index():
    client = make_client()
    append_event(client)

    by_id = client.get("/api/v1/events/evt_001")
    by_index = client.get("/api/v1/events/by-index/0")

    assert by_id.status_code == 200
    assert by_index.status_code == 200
    assert by_id.json() == by_index.json()
    assert by_id.json()["event"]["event_id"] == "evt_001"


def test_events_can_be_listed_in_log_index_order():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")
    append_event(client, "evt_003")

    response = client.get("/api/v1/events")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert [item["log_index"] for item in body["items"]] == [0, 1, 2]
    assert [item["event"]["event_id"] for item in body["items"]] == [
        "evt_001",
        "evt_002",
        "evt_003",
    ]


def test_empty_event_list_returns_zero_items():
    client = make_client()

    response = client.get("/api/v1/events")

    assert response.status_code == 200
    assert response.json() == {"items": [], "limit": 50, "offset": 0, "total": 0}


def test_event_list_supports_bounded_pagination():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")
    append_event(client, "evt_003")

    response = client.get("/api/v1/events?limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert body["total"] == 3
    assert [item["event"]["event_id"] for item in body["items"]] == ["evt_002"]


def test_event_list_supports_tenant_and_workspace_filters():
    client = make_client()
    client.post("/api/v1/events", json=make_event("evt_001"))
    other = make_event("evt_002")
    other["tenant_id"] = "tenant_b"
    other["workspace_id"] = "workspace_b"
    client.post("/api/v1/events", json=other)

    response = client.get("/api/v1/events?tenant_id=tenant_b&workspace_id=workspace_b")

    assert response.status_code == 200
    assert [item["event"]["event_id"] for item in response.json()["items"]] == ["evt_002"]


def test_event_list_rejects_invalid_pagination_with_error_envelope():
    client = make_client()

    response = client.get("/api/v1/events?limit=501", headers={"X-Correlation-ID": "corr_001"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "ETS_VALIDATION_ERROR"
    assert error["correlation_id"] == "corr_001"


def test_missing_event_returns_404():
    client = make_client()

    response = client.get("/api/v1/events/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ETS_EVENT_NOT_FOUND"


def test_inclusion_proof_route_and_verify_route_accept_valid_proof():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")

    proof_response = client.get("/api/v1/proofs/inclusion/evt_002")
    assert proof_response.status_code == 200

    verify_response = client.post("/api/v1/verify/inclusion", json=proof_response.json())

    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert verify_response.json()["reason"] == "ok"


def test_sprint3_proof_aliases_round_trip():
    client = make_client()
    append_event(client, "evt_001")

    proof_response = client.get("/proofs/event/evt_001")
    verify_response = client.post("/verify/proof", json=proof_response.json())

    assert proof_response.status_code == 200
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True


def test_verify_route_rejects_tampered_proof_without_hidden_state():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")
    proof = client.get("/api/v1/proofs/inclusion/evt_002").json()
    proof["root_hash"] = "0" * 64

    response = client.post("/api/v1/verify/inclusion", json=proof)

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_consistency_proof_route_and_verify_route_accept_valid_proof():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")
    append_event(client, "evt_003")

    proof_response = client.get("/api/v1/proofs/consistency?previous_tree_size=1")
    assert proof_response.status_code == 200

    verify_response = client.post("/api/v1/verify/consistency", json=proof_response.json())

    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert verify_response.json()["reason"] == "ok"


def test_consistency_verify_rejects_tampered_latest_root():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")
    proof = client.get("/api/v1/proofs/consistency?previous_tree_size=1").json()
    proof["latest_root_hash"] = "0" * 64

    response = client.post("/api/v1/verify/consistency", json=proof)

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_federation_assessment_route_reports_quorum_and_conflicts():
    client = make_client()
    append_event(client, "evt_001")
    tree_head = client.get("/api/v1/log/head").json()
    conflicting_head = {**tree_head, "root_hash": "b" * 64}

    response = client.post(
        "/api/v1/federation/assess",
        json={
            "threshold": 2,
            "observations": [
                {"verifier_id": "verifier-a", "tree_head": tree_head},
                {"verifier_id": "verifier-b", "tree_head": tree_head},
                {"verifier_id": "verifier-c", "tree_head": conflicting_head},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["quorum_met"] is True
    assert body["quorum_root_hash"] == tree_head["root_hash"]
    assert body["conflicts"][0]["tree_size"] == tree_head["tree_size"]


def test_proof_bundle_route_returns_offline_verification_artifacts():
    client = make_client()
    append_event(client, "evt_001")

    response = client.get("/api/v1/bundles/evt_001")

    assert response.status_code == 200
    body = response.json()
    assert body["event"]["event_id"] == "evt_001"
    assert body["verification_result"]["valid"] is True
    assert body["tree_head"]["root_hash"] == body["inclusion_proof"]["root_hash"]


def test_metrics_route_reports_activity_counts():
    client = make_client()
    append_event(client, "evt_001")
    proof = client.get("/api/v1/proofs/inclusion/evt_001").json()
    client.post("/api/v1/verify/inclusion", json=proof)

    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.json()["append_count"] == 1
    assert response.json()["proof_count"] == 1
    assert response.json()["verification_success_count"] == 1


def test_rc5_protocol_lab_endpoints_round_trip():
    client = make_client()
    event = make_event("evt_001")
    append_response = client.post("/evidence", json=event)
    expected_hash = append_response.json()["event_hash"]

    read_response = client.get("/evidence/evt_001")
    read_by_sequence_response = client.get("/evidence/sequence/0")
    root_response = client.get("/log/root")
    size_response = client.get("/log/size")
    proof_response = client.get("/proof/inclusion/evt_001")
    verify_event_response = client.post(
        "/verify/evidence",
        json={"event": event, "expected_event_hash": expected_hash},
    )
    verify_proof_response = client.post("/verify/inclusion", json=proof_response.json())
    verify_compat_proof_response = client.post(
        "/verify/proof/inclusion",
        json=proof_response.json(),
    )

    assert append_response.status_code == 201
    assert read_response.status_code == 200
    assert read_by_sequence_response.status_code == 200
    assert len(root_response.json()["root_hash"]) == 64
    assert size_response.json() == {"tree_size": 1}
    assert verify_event_response.json()["valid"] is True
    assert verify_proof_response.json()["valid"] is True
    assert verify_compat_proof_response.json()["valid"] is True


def test_artifact_registration_hashes_bytes_and_returns_receipt():
    client = make_client()

    response = client.post("/evidence/register", json=make_artifact_registration())

    assert response.status_code == 201
    body = response.json()
    assert body["artifact_id"] == "artifact_001"
    assert len(body["artifact_hash"]) == 64
    assert body["event_id"] == "artifact_registered:artifact_001"
    assert body["block_number"] == 0
    assert body["proof_url"] == "/evidence/artifact_001/proof"


def test_registered_artifact_can_be_read_and_proven_without_raw_bytes():
    client = make_client()
    receipt = client.post("/evidence/register", json=make_artifact_registration()).json()

    read_response = client.get("/evidence/artifact_001")
    proof_response = client.get("/evidence/artifact_001/proof")

    assert read_response.status_code == 200
    artifact = read_response.json()
    assert artifact["artifact_hash"] == receipt["artifact_hash"]
    assert artifact["reference_uri"] == "ets://artifact/artifact_001"
    assert artifact["byte_size"] == len(b"synthetic artifact")
    assert "artifact_base64" not in artifact
    assert proof_response.status_code == 200
    assert proof_response.json()["event"]["event_id"] == "artifact_registered:artifact_001"


def test_artifact_verification_accepts_original_and_rejects_tampered_bytes():
    client = make_client()
    client.post("/evidence/register", json=make_artifact_registration())

    valid_response = client.post(
        "/evidence/verify",
        json={
            "artifact_id": "artifact_001",
            "artifact_base64": base64.b64encode(b"synthetic artifact").decode("ascii"),
        },
    )
    tampered_response = client.post(
        "/evidence/verify",
        json={
            "artifact_id": "artifact_001",
            "artifact_base64": base64.b64encode(b"synthetic artifact.").decode("ascii"),
        },
    )

    assert valid_response.status_code == 200
    assert valid_response.json()["valid"] is True
    assert tampered_response.status_code == 200
    assert tampered_response.json()["valid"] is False
    assert tampered_response.json()["reason"] == "artifact hash does not match registered hash"


def test_duplicate_artifact_id_returns_conflict():
    client = make_client()
    payload = make_artifact_registration()
    client.post("/evidence/register", json=payload)

    response = client.post("/evidence/register", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ETS_EVENT_DUPLICATE"


def test_artifact_hash_does_not_depend_on_metadata():
    client = make_client()
    first = client.post(
        "/evidence/register",
        json=make_artifact_registration("artifact_001", metadata={"case": "alpha"}),
    ).json()
    second = client.post(
        "/evidence/register",
        json=make_artifact_registration("artifact_002", metadata={"case": "beta"}),
    ).json()

    assert first["artifact_hash"] == second["artifact_hash"]


def test_lantern_verify_route_returns_machine_readable_codes():
    client = make_client()
    evidence_hash = "c" * 64
    payload = {
        "source_event_id": "evt-1",
        "evidence_hash": evidence_hash,
        "action_type": "customer-message",
        "proof_bundle": {
            "proofId": "proof-1",
            "sourceEventId": "evt-1",
            "artifactHash": evidence_hash,
            "consentEventId": "consent-1",
            "approvalState": "required",
            "merkleInclusionProof": {"leaf": evidence_hash},
        },
        "consent_event": {
            "eventType": "consent.granted",
            "consentId": "consent-1",
            "workspaceId": "default",
            "subjectId": "human-owner",
            "grantedTo": "christina",
            "scope": "customer-message:ticket-12345",
            "sourceEventId": "evt-1",
            "evidenceHash": evidence_hash,
            "createdAt": "2026-05-25T00:00:00Z",
        },
    }

    response = client.post("/api/v1/lantern/verify", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["reasonCode"] == "ok"
    assert body["proofId"] == "proof-1"
    assert body["consentId"] == "consent-1"


def test_lantern_verify_route_rejects_tampered_payload():
    client = make_client()
    evidence_hash = "c" * 64

    response = client.post(
        "/api/v1/lantern/verify",
        json={
            "source_event_id": "evt-1",
            "evidence_hash": evidence_hash,
            "action_type": "customer-message",
            "proof_bundle": {
                "proofId": "proof-1",
                "sourceEventId": "evt-1",
                "artifactHash": "d" * 64,
                "consentEventId": "consent-1",
                "approvalState": "required",
                "merkleInclusionProof": {"leaf": "d" * 64},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["reasonCode"] == "hash-mismatch"


def test_lantern_support_analysis_route_returns_structured_bundle():
    client = make_client()

    response = client.post(
        "/api/v1/lantern/support/analyze",
        json={
            "lanternEventId": "lantern-support-001",
            "eventType": "lantern.support.analysis.requested",
            "sourceSystem": "opshelm",
            "workspaceId": "workspace-alpha",
            "ticketRef": "DEMO-1001",
            "artifactHashes": [
                {"artifactId": "ticket-body", "sha256": "a" * 64, "kind": "ticket"},
                {"artifactId": "har-redacted", "sha256": "b" * 64, "kind": "har"},
            ],
            "requestedOutputs": [
                "customer_summary",
                "internal_summary",
                "technical_findings",
                "recommended_actions",
                "kb_candidates",
            ],
            "approvalState": "required",
            "consentId": "consent-support-001",
            "correlationId": "corr-support-001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "hold-for-approval"
    assert body["reasonCode"] == "approval-required"
    assert body["outputs"]["customerSummary"]["approvalRequired"] is True
    assert body["outputs"]["internalSummary"]["approvalRequired"] is False
    assert body["outputs"]["kbCandidates"][0]["reuseScope"] == "internal-knowledge-base"
    assert body["memoryObservations"][0]["type"] == "recurring_support_pattern"


def test_lantern_recommendation_routes_export_and_update_items():
    client = make_client()

    export_response = client.get("/api/v1/lantern/recommendations")

    assert export_response.status_code == 200
    export = export_response.json()
    assert export["ownerRepo"] == "ShannonBrayNC/ETS"
    assert export["recommendations"][0]["duplicateKey"]
    assert export["sprintCandidates"]

    recommendation_id = export["recommendations"][0]["recommendationId"]
    update_response = client.post(
        f"/api/v1/lantern/recommendations/{recommendation_id}",
        json={
            "status": "in-review",
            "note": "Selected for Christina sprint review.",
            "author": "christina",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()["recommendations"][0]
    assert updated["status"] == "in-review"
    assert updated["reviewNotes"][0]["note"] == "Selected for Christina sprint review."


def test_certificate_report_endpoint_generates_markdown():
    client = make_client()
    append_event(client, "evt_001")
    bundle = client.get("/api/v1/bundles/evt_001").json()

    response = client.post(
        "/reports/certificate",
        json={"bundle": bundle, "format": "markdown"},
    )

    assert response.status_code == 200
    assert response.json()["format"] == "markdown"
    assert "ETS Verification Certificate" in response.json()["content"]


def test_malformed_proof_returns_validation_error():
    client = make_client()

    response = client.post("/api/v1/verify/inclusion", json={"tree_size": "bad"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ETS_VALIDATION_ERROR"


def test_openapi_schema_is_generated_with_required_routes():
    client = make_client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/events" in paths
    assert "/api/v1/verify/inclusion" in paths
    assert paths["/tree-head"]["get"].get("deprecated") is True
