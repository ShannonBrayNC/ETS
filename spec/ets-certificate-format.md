# ETS Verification Certificate Format v0.1 Skeleton

Status: Draft
Scope: Public protocol certificate-format skeleton
Patent notice: ETS - Evidence Transparency System is patent pending. This public certificate-format material does not include USPTO receipts, application numbers, claim charts, prior-art matrices, assignment records, attorney-review notes, private drafts, customer evidence, secrets, or private Lantern-IP materials.

## 1. Purpose

The ETS verification certificate format defines a machine-readable and optionally human-readable record of validation, hashing, proof verification, tree-head comparison, policy-routing, and claim-boundary results.

A verification certificate is not a universal truth certificate. It records what an ETS verifier checked, which inputs were used, which version performed the verification, which boundaries apply, and which protocol-level result was produced.

## 2. Certificate goals

An ETS certificate should:

- identify the EvidenceEvent or evidence reference;
- identify the proof material used;
- identify the verifier and verifier version;
- state the verification result;
- state the tree-head and inclusion-proof result;
- state the policy-routing result;
- include claim-boundary statements;
- support audit replay; and
- be safe for public or restricted release according to its sensitivity profile.

## 3. Candidate certificate object

```json
{
  "schema_version": "ets.certificate.v0.1",
  "certificate_id": "cert-example-0001",
  "generated_at_utc": "2026-01-01T00:00:00Z",
  "verifier": {
    "name": "ets-verifier",
    "version": "0.1.0-draft",
    "profile": "ets-core-v0.1"
  },
  "event": {
    "event_id": "evt-example-0001",
    "evidence_id": "evd-example-0001",
    "event_hash": "sha256:example-event-hash-placeholder",
    "leaf_hash": "sha256:example-leaf-hash-placeholder"
  },
  "proof": {
    "proof_id": "proof-example-0001",
    "log_id": "ets-log-example",
    "tree_head_id": "tree-head-example-0001",
    "tree_size": 128,
    "leaf_index": 42,
    "root_hash": "sha256:example-root-hash-placeholder"
  },
  "verification_result": {
    "event_schema_valid": true,
    "canonicalization_verified": true,
    "event_hash_verified": true,
    "leaf_hash_verified": true,
    "inclusion_proof_verified": true,
    "tree_head_accepted": true,
    "overall_status": "verified"
  },
  "policy_result": {
    "route": "human_review",
    "evidence_states": ["Hash Verified", "Included", "Inclusion Proof Verified"],
    "sensitivity": ["internal"],
    "requested_action": "review_before_release"
  },
  "claim_boundaries": [
    "Verifies submitted-event metadata and proof material only.",
    "Does not prove real-world truth, legal sufficiency, or completeness without external policy and observation."
  ]
}
```

## 4. Certificate result vocabulary

Candidate overall_status values:

- verified;
- verified_with_warnings;
- invalid;
- incomplete;
- unsupported_profile;
- human_review_required;
- quarantined;
- rejected.

Candidate evidence states:

- Schema Valid;
- Canonicalized;
- Hash Verified;
- Leaf Hash Verified;
- Included;
- Inclusion Proof Verified;
- Tree Head Accepted;
- Tree Head Stale;
- Root Mismatch;
- Policy Routed;
- Requires Human Review;
- Public Release Restricted;
- Quarantined;
- Rejected;
- Replay Verified;
- Replay Diverged.

## 5. Human-readable certificate sections

A human-readable ETS certificate may include:

1. Certificate summary.
2. EvidenceEvent reference.
3. Hash summary.
4. Proof summary.
5. Tree-head summary.
6. Verification result.
7. Policy-routing result.
8. Claim-boundary statements.
9. Replay instructions.
10. Verifier version and profile.

## 6. Machine-readable certificate sections

The machine-readable form should preserve deterministic fields needed for audit replay:

- schema_version;
- certificate_id;
- generated_at_utc;
- verifier name, version, and profile;
- event_id and evidence_id;
- event_hash and leaf_hash;
- proof_id and tree_head_id;
- root_hash, tree_size, and leaf_index;
- validation booleans;
- policy route;
- evidence states;
- claim boundaries;
- replay references.

## 7. Claim-boundary requirements

Certificates should include claim boundaries whenever the output might be shown to humans, downstream automation, public reviewers, auditors, civic stakeholders, or agency personnel.

Candidate minimum boundary:

```text
This certificate verifies ETS protocol-level metadata, hashes, proof material, tree-head references, and policy-routing outputs for the submitted EvidenceEvent. It does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, vote totals, ballot validity, or completeness without external policy and observation.
```

## 8. Certificate profiles

Candidate profiles:

- ets-certificate-core-v0.1;
- ets-certificate-human-readable-v0.1;
- ets-certificate-machine-readable-v0.1;
- ets-certificate-public-safe-v0.1;
- ets-certificate-civic-boundary-v0.1;
- ets-certificate-internal-audit-v0.1.

## 9. Replay relationship

A certificate should contain enough references for an audit replay process to retrieve or reconstruct:

- EvidenceEvent metadata;
- canonical payload;
- event hash;
- leaf hash;
- inclusion proof;
- tree head;
- verifier profile;
- policy route;
- claim boundaries.

## 10. Serialization formats

Candidate formats:

- JSON;
- Markdown;
- HTML;
- PDF;
- signed JSON envelope in a later profile;
- JSON-LD in a later profile.

JSON should be the first-class conformance format. Other formats should be derived from the same machine-readable certificate object.

## 11. Test-vector requirements

Certificate test vectors should include:

- valid certificate from valid proof;
- certificate with warning from stale tree head;
- invalid certificate from root mismatch;
- public-safe certificate with civic/election boundary;
- restricted certificate with sensitivity labels;
- replay certificate with regenerated output;
- verifier version mismatch case.

## 12. Security considerations placeholder

The final certificate format must address:

- overclaiming;
- verifier impersonation;
- certificate substitution;
- stale proof material;
- presentation mismatch between machine-readable and human-readable outputs;
- omission of claim boundaries;
- privacy leakage through metadata;
- public release of sensitive evidence references; and
- false implication of legal, election, forensic, or official status.

## 13. Open issues

- Decide whether certificates are signed in v0.1 or later.
- Decide whether Markdown/HTML/PDF outputs are conformance-tested.
- Decide whether certificate_id is generated before or after policy routing.
- Decide minimum required claim boundaries.
- Decide whether public-safe profile is mandatory for civic/election-adjacent examples.
