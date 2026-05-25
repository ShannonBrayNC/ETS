# Lantern Consent Ledger

## Purpose

The Lantern Consent Ledger extends ETS from evidence verification into consent-aware ecosystem verification.

Lantern systems may generate drafts, recommendations, artifacts, and action requests, but they must not silently act outside their authority. ETS records the evidence and consent chain so SignalForge and Christina can detect tampering, missing proof, revoked consent, and unauthorized cross-system recommendations.

## Consent event types

| Type | Meaning |
| --- | --- |
| `consent.requested` | A system or human requested scoped consent. |
| `consent.granted` | Consent was granted for a specific action scope. |
| `consent.denied` | Consent was explicitly denied. |
| `consent.revoked` | Previously granted consent was revoked. |
| `consent.expired` | Consent is no longer valid because its time or scope ended. |

## Consent event schema

```json
{
  "eventType": "consent.granted",
  "consentId": "consent-001",
  "workspaceId": "default",
  "subjectId": "human-owner",
  "grantedTo": "christina",
  "scope": "customer-message:ticket-12345",
  "sourceEventId": "evt-001",
  "evidenceHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "expiresAt": "2026-06-25T00:00:00Z",
  "createdAt": "2026-05-25T00:00:00Z"
}
```

## Proof bundle

A `LanternProofBundle` should link:

- source event ID,
- canonical payload or artifact hash,
- consent event ID,
- approval state,
- Merkle inclusion proof,
- verification result,
- verification reason code.

## Verification reason codes

| Code | Meaning |
| --- | --- |
| `ok` | Verification passed. |
| `missing-proof` | No proof reference was supplied. |
| `hash-mismatch` | Payload hash does not match proof. |
| `consent-missing` | Required consent is not present. |
| `consent-denied` | Consent was denied. |
| `consent-revoked` | Consent was revoked after grant. |
| `consent-expired` | Consent is outside its valid window. |
| `approval-required` | Human approval is required but absent. |
| `replay-detected` | Event nonce or proof was already used. |
| `unknown-source` | Source system is not registered. |

## Default behavior

- Valid proof and valid consent: pass.
- Missing proof for cross-system item: quarantine.
- Hash mismatch: block.
- Revoked, denied, or expired consent: block.
- Missing human approval for approval-gated action: hold for Christina.
- Unknown source: quarantine.

## Boundary statement

ETS proves that the recorded artifact, consent event, and proof chain have not changed since they were notarized. ETS does not prove that every real-world fact in an AI-generated recommendation is true. Source systems remain responsible for factual grounding and evidence capture.
