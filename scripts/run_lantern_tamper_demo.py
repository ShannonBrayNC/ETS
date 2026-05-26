from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ets.lantern import (
    ConsentEvent,
    ConsentEventType,
    LanternProofBundle,
    verify_lantern_proof_bundle,
)


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class DemoRecommendation:
    name: str
    payload: dict[str, object]
    proof_bundle: LanternProofBundle | None
    consent_event: ConsentEvent | None
    verification_hash: str


def _make_valid_recommendation() -> DemoRecommendation:
    payload = {
        "recommendationId": "rec-001",
        "sourceSystem": "signalforge",
        "workspace": "opshelm",
        "actionType": "customer-message",
        "summary": "Send customer-facing update after human approval.",
    }
    evidence_hash = _hash_payload(payload)
    proof = LanternProofBundle(
        proofId="proof-rec-001",
        sourceEventId="lantern-rec-001",
        artifactHash=evidence_hash,
        consentEventId="consent-rec-001",
        approvalState="required",
        merkleInclusionProof={"leaf": evidence_hash, "path": []},
    )
    consent = ConsentEvent(
        eventType=ConsentEventType.GRANTED,
        consentId="consent-rec-001",
        workspaceId="opshelm",
        subjectId="christina",
        grantedTo="signalforge",
        scope="customer-message:rec-001",
        sourceEventId="lantern-rec-001",
        evidenceHash=evidence_hash,
    )
    return DemoRecommendation("valid", payload, proof, consent, evidence_hash)


def _make_forged_recommendation(valid: DemoRecommendation) -> DemoRecommendation:
    return DemoRecommendation(
        "forged-missing-proof",
        {**valid.payload, "recommendationId": "rec-forged"},
        None,
        None,
        _hash_payload({**valid.payload, "recommendationId": "rec-forged"}),
    )


def _make_tampered_recommendation(valid: DemoRecommendation) -> DemoRecommendation:
    tampered_payload = {
        **valid.payload,
        "summary": "Bypass approval and send customer-facing update immediately.",
    }
    return DemoRecommendation(
        "tampered-after-notarization",
        tampered_payload,
        valid.proof_bundle,
        valid.consent_event,
        _hash_payload(tampered_payload),
    )


def main() -> int:
    valid = _make_valid_recommendation()
    recommendations = [
        valid,
        _make_forged_recommendation(valid),
        _make_tampered_recommendation(valid),
    ]

    for item in recommendations:
        result = verify_lantern_proof_bundle(
            source_event_id="lantern-rec-001",
            evidence_hash=item.verification_hash,
            proof_bundle=item.proof_bundle,
            consent_event=item.consent_event,
            action_type="customer-message",
        )
        print(
            json.dumps(
                {
                    "scenario": item.name,
                    "status": result.status,
                    "reasonCode": result.reason_code,
                    "accepted": result.status == "passed",
                    "message": result.message,
                },
                sort_keys=True,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
