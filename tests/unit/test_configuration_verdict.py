from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_inclusion_proof,
)
from ets.core.merkle import merkle_root
from ets.core.proofs import verify_inclusion_proof
from ets.core.signing import Ed25519TreeHeadSigner
from ets.verifier.cli import main
from ets.verifier.configuration import (
    ConfigurationVerdictV1,
    verify_configuration_verdict_package,
)
from ets.verifier.service import (
    TreeHeadTrustStore,
    TrustedTreeHeadKey,
    VerifierPolicy,
)

_TIME = datetime(2026, 11, 20, 20, 0, tzinfo=UTC)
_LOG_ID = "ets-configuration-verdict-test"
_KEY_ID = "configuration-verdict-test-key"
_PRIVATE_KEY_HEX = "27" * 32
_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(_PRIVATE_KEY_HEX))
_PUBLIC_KEY_HEX = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
).hex()
_SIGNER = Ed25519TreeHeadSigner(_PRIVATE_KEY_HEX, _KEY_ID)


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _package(
    *,
    verdict: str = "repaired",
    authorization: str = "authorized",
    repair: str = "verified",
    uncertainties: tuple[str, ...] = (),
    event_target: str = "tenant-a/host-7/registry-policy",
) -> tuple[bytes, EvidenceProofBundle, dict[str, bytes], TreeHeadTrustStore]:
    artifacts = {
        "baseline-1": b'{"desired":"enabled"}',
        "before-1": b'{"observed":"disabled"}',
        "approval-1": b'{"approved":true}',
        "tool-result-1": b'{"exit_code":0}',
        "read-back-1": b'{"observed":"enabled"}',
    }
    roles = ("baseline", "before_state", "approval", "tool_result", "read_back")
    artifact_bindings = [
        {
            "role": role,
            "artifact_id": artifact_id,
            "media_type": "application/json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw),
        }
        for role, (artifact_id, raw) in zip(roles, artifacts.items(), strict=True)
    ]
    payload = {
        "schema_version": "ets.configuration_verdict.v1",
        "verdict_id": "verdict-001",
        "case_id": "case-001",
        "target_id": "tenant-a/host-7/registry-policy",
        "baseline_id": "baseline-approved-0042",
        "verdict": verdict,
        "authorization": authorization,
        "repair": repair,
        "uncertainties": list(uncertainties),
        "artifacts": artifact_bindings,
    }
    verdict_bytes = _json_bytes(payload)
    event = EvidenceEvent(
        event_id="evt-configuration-verdict-001",
        tenant_id="tenant-a",
        workspace_id="configuration-assurance",
        evidence_id="verdict-001",
        event_type="configuration.verdict",
        subject_ref=f"configuration-target:{event_target}",
        content_hash=hashlib.sha256(verdict_bytes).hexdigest(),
        content_hash_alg="sha256",
        metadata={"baseline_id": "baseline-approved-0042"},
        created_at_utc=_TIME,
        source_system="configuration-assurance-fixture",
        actor_id="verifier-fixture",
        correlation_id="case-001",
    )
    log = InMemoryAppendOnlyLog()
    entry = log.append(event)
    entries = log.list_entries()
    proof = generate_inclusion_proof(entries, 0, generated_at_utc=_TIME)
    head = _SIGNER.sign(
        SignedTreeHead(
            tree_size=1,
            root_hash=merkle_root([entry.leaf_hash]),
            created_at_utc=_TIME,
            log_id=_LOG_ID,
        )
    )
    bundle = EvidenceProofBundle(
        event=event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=head,
        inclusion_proof=proof,
        verification_result=verify_inclusion_proof(proof),
    )
    trust_store = TreeHeadTrustStore(
        keys=[
            TrustedTreeHeadKey(
                key_id=_KEY_ID,
                signature_alg="ed25519",
                public_key_hex=_PUBLIC_KEY_HEX,
                not_before_utc=_TIME - timedelta(days=1),
                not_after_utc=_TIME + timedelta(days=1),
            )
        ]
    )
    return verdict_bytes, bundle, artifacts, trust_store


def _verify(
    verdict_bytes: bytes,
    bundle: EvidenceProofBundle,
    artifacts: dict[str, bytes],
    trust_store: TreeHeadTrustStore,
):
    return verify_configuration_verdict_package(
        verdict_bytes=verdict_bytes,
        proof_bundle=bundle,
        artifact_payloads=artifacts,
        trust_store=trust_store,
        policy=VerifierPolicy(expected_log_id=_LOG_ID),
    )


def test_configuration_verdict_verifies_exported_bytes_and_signed_checkpoint() -> None:
    result = _verify(*_package())

    assert result.valid is True
    assert result.integrity == "valid"
    assert result.trust == "trusted"
    assert result.authorization == "authorized"
    assert result.repair == "verified"
    assert result.uncertainty == "none_declared"
    assert result.proof.signature_verified is True
    assert all(check.passed for check in result.checks)


def test_configuration_verdict_rejects_tampered_exported_artifact_bytes() -> None:
    verdict_bytes, bundle, artifacts, trust_store = _package()
    artifacts["read-back-1"] = b'{"observed":"disabled"}'

    result = _verify(verdict_bytes, bundle, artifacts, trust_store)

    assert result.valid is False
    assert result.integrity == "invalid"
    assert result.trust == "trusted"
    assert result.uncertainty == "verification_failure"
    assert any(
        check.code == "artifact_digest:read_back" and not check.passed
        for check in result.checks
    )


def test_configuration_verdict_rehashes_exact_exported_verdict_bytes() -> None:
    verdict_bytes, bundle, artifacts, trust_store = _package()

    result = _verify(verdict_bytes + b"\n", bundle, artifacts, trust_store)

    assert result.valid is False
    assert result.integrity == "invalid"
    assert any(
        check.code == "verdict_payload_hash" and not check.passed for check in result.checks
    )


def test_configuration_verdict_rejects_cross_target_event_binding() -> None:
    result = _verify(*_package(event_target="tenant-a/host-8/registry-policy"))

    assert result.valid is False
    assert any(
        check.code == "verdict_event_binding" and not check.passed for check in result.checks
    )


def test_configuration_verdict_keeps_missing_trust_separate_from_integrity() -> None:
    verdict_bytes, bundle, artifacts, _ = _package()
    result = _verify(verdict_bytes, bundle, artifacts, TreeHeadTrustStore())

    assert result.valid is False
    assert result.integrity == "valid"
    assert result.trust == "untrusted"
    assert result.uncertainty == "verification_failure"


def test_configuration_verdict_can_authenticate_an_unknown_result() -> None:
    result = _verify(
        *_package(
            verdict="unknown",
            authorization="unknown",
            repair="unknown",
            uncertainties=("read-back checker exceeded its freshness window",),
        )
    )

    assert result.valid is True
    assert result.verdict == "unknown"
    assert result.uncertainty == "declared"


def test_repaired_verdict_cannot_hide_authorization_or_uncertainty() -> None:
    verdict_bytes, _, _, _ = _package()
    payload = json.loads(verdict_bytes)
    payload["authorization"] = "unknown"
    payload["uncertainties"] = tuple(payload["uncertainties"])
    payload["artifacts"] = tuple(payload["artifacts"])

    with pytest.raises(ValidationError, match="requires authorized and verified"):
        ConfigurationVerdictV1.model_validate(payload)


def test_configuration_verdict_cli_verifies_all_exported_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    verdict_bytes, bundle, artifacts, trust_store = _package()
    verdict_path = tmp_path / "verdict.json"
    bundle_path = tmp_path / "bundle.json"
    trust_path = tmp_path / "trust.json"
    verdict_path.write_bytes(verdict_bytes)
    bundle_path.write_text(bundle.model_dump_json(), encoding="utf-8")
    trust_path.write_text(trust_store.model_dump_json(), encoding="utf-8")
    arguments = [
        "configuration-verdict",
        str(verdict_path),
        str(bundle_path),
        "--trust-store",
        str(trust_path),
        "--expected-log-id",
        _LOG_ID,
    ]
    for artifact_id, raw in artifacts.items():
        path = tmp_path / f"{artifact_id}.json"
        path.write_bytes(raw)
        arguments.extend(("--artifact", f"{artifact_id}={path}"))

    assert main(arguments) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["claim_boundary"].startswith("bounded_configuration_package_integrity")
