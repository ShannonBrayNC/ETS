# ETS Proof Format v0.1 Skeleton

Status: Draft
Scope: Public protocol proof-format skeleton
Patent notice: ETS - Evidence Transparency System is patent pending. This public proof-format material does not include USPTO receipts, application numbers, claim charts, prior-art matrices, assignment records, attorney-review notes, private drafts, customer evidence, secrets, or private Lantern-IP materials.

## 1. Purpose

The ETS proof format defines the proof material needed to verify that an EvidenceEvent-derived leaf hash is included in a referenced append-only transparency log state.

The proof format supports independent verification, tree-head comparison, audit replay, certificate generation, and policy routing.

## 2. Proof model

ETS v0.1 uses a Merkle-style inclusion proof model:

1. An EvidenceEvent is validated.
2. A canonical payload is produced.
3. An event_hash is computed.
4. A leaf_hash is computed.
5. The leaf_hash is appended to a log.
6. A tree head identifies a log state.
7. An inclusion proof provides an audit path from the leaf to the root.
8. A verifier recomputes the root and compares it to the referenced tree head.

## 3. Candidate inclusion proof object

```json
{
  "schema_version": "ets.proof.inclusion.v0.1",
  "proof_id": "proof-example-0001",
  "log_id": "ets-log-example",
  "event_id": "evt-example-0001",
  "evidence_id": "evd-example-0001",
  "tree_size": 128,
  "leaf_index": 42,
  "event_hash": "sha256:example-event-hash-placeholder",
  "leaf_hash": "sha256:example-leaf-hash-placeholder",
  "root_hash": "sha256:example-root-hash-placeholder",
  "audit_path": [
    "sha256:example-sibling-00",
    "sha256:example-sibling-01",
    "sha256:example-sibling-02"
  ],
  "hash_alg": "sha256",
  "generated_at_utc": "2026-01-01T00:00:00Z",
  "tree_head_ref": "tree-head-example-0001"
}
```

## 4. Candidate tree-head object

```json
{
  "schema_version": "ets.tree_head.v0.1",
  "tree_head_id": "tree-head-example-0001",
  "log_id": "ets-log-example",
  "tree_size": 128,
  "root_hash": "sha256:example-root-hash-placeholder",
  "timestamp_utc": "2026-01-01T00:00:00Z",
  "signature_alg": "none-v0.1-local-profile",
  "signature": null,
  "operator_id": "example-log-operator"
}
```

## 5. Field catalog

| Field | Candidate requirement | Description |
| --- | --- | --- |
| schema_version | required | Proof or tree-head schema version. |
| proof_id | recommended | Unique proof identifier. |
| log_id | required | Log namespace or operator-defined log identifier. |
| event_id | required | EvidenceEvent identifier associated with the proof. |
| evidence_id | recommended | Evidence identifier associated with the proof. |
| tree_size | required | Number of leaves represented by the referenced tree head. |
| leaf_index | required | Zero-based or profile-declared leaf position. |
| event_hash | recommended | Event hash associated with the leaf. |
| leaf_hash | required | Leaf digest verified by the audit path. |
| root_hash | required | Expected root hash. |
| audit_path | required | Ordered sibling hashes. |
| hash_alg | required | Hash algorithm. |
| generated_at_utc | required | Proof generation timestamp. |
| tree_head_ref | recommended | Reference to the tree-head object. |

## 6. Verification procedure placeholder

A verifier should:

1. Validate the proof schema.
2. Validate the referenced tree-head schema.
3. Confirm log_id consistency.
4. Confirm hash algorithm support.
5. Recompute the leaf hash when the EvidenceEvent is available.
6. Recompute the Merkle path using leaf_index and audit_path.
7. Compare the recomputed root to root_hash.
8. Compare root_hash to the referenced tree-head root_hash.
9. Emit a proof result.

Candidate result values:

- proof_verified;
- proof_invalid;
- root_mismatch;
- missing_tree_head;
- unsupported_hash_algorithm;
- invalid_audit_path;
- stale_tree_head;
- log_id_mismatch;
- event_hash_mismatch;
- leaf_hash_mismatch.

## 7. Tree-head comparison

Tree-head comparison should support detection or routing for:

- normal progress;
- rollback suspicion;
- fork or equivocation suspicion;
- stale state;
- root mismatch;
- timestamp anomaly;
- log identifier mismatch.

Candidate comparison object:

```json
{
  "schema_version": "ets.tree_head_comparison.v0.1",
  "previous_tree_head_ref": "tree-head-previous",
  "latest_tree_head_ref": "tree-head-latest",
  "comparison_result": "accept_progress",
  "signals": [],
  "generated_at_utc": "2026-01-01T00:00:00Z"
}
```

## 8. Hash algorithm agility

ETS v0.1 starts with sha256 as the initial candidate algorithm. Future profiles may define additional algorithms.

Implementations should avoid silently accepting unknown algorithms. Unknown or unsupported algorithms should produce a deterministic failure result.

## 9. Canonical relation to EvidenceEvent

The proof format depends on the EvidenceEvent schema and canonicalization profile. A proof is incomplete for full replay unless the verifier has access to:

- the EvidenceEvent or canonical payload;
- the event_hash calculation rule;
- the leaf_hash calculation rule;
- the audit_path ordering rule;
- the tree-head root hash; and
- the proof verification profile.

## 10. Test-vector requirements

Proof test vectors should include:

- EvidenceEvent input;
- canonical payload;
- expected event_hash;
- expected leaf_hash;
- tree head;
- inclusion proof;
- expected verification result;
- invalid variants for root mismatch, leaf mismatch, wrong path ordering, unsupported hash algorithm, wrong tree size, and stale tree head.

## 11. Security considerations placeholder

The final proof format must address:

- ambiguous path ordering;
- log equivocation;
- stale tree heads;
- replay attacks;
- proof substitution;
- hash algorithm downgrade;
- unsigned local-mode tree heads;
- time-source ambiguity;
- verifier version drift; and
- mismatch between proof verification and certificate claims.

## 12. Open issues

- Decide exact leaf_hash construction.
- Decide zero-based vs. one-based leaf index semantics.
- Decide whether tree heads are signed in v0.1 or signed only in later conformance profiles.
- Decide whether consistency proofs are included in v0.1.
- Decide whether tree-head comparison is normative or advisory in v0.1.
