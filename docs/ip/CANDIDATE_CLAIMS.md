# ETS Candidate Claim Areas

This file is for attorney review. It is not a patent filing and does not assert
that any claim is novel, allowable, or commercially useful.

## Candidate Area 1: Canonical Evidence Lifecycle

A system that receives heterogeneous operational evidence metadata, applies a
deterministic canonicalization profile, stores hash-only proof material, and
generates independently verifiable proof bundles while excluding raw sensitive
content by default.

## Candidate Area 2: Federated Verifier Architecture

A federation of independent verifiers that compare log roots, verify proof
bundles, incorporate witness observations, and produce threshold-based quorum
decisions for evidence acceptance or rejection.

## Candidate Area 3: Omission Suspicion Workflow

A workflow that accepts an externally defined expected event set, compares it
with observed transparency log entries, and emits omission findings without
claiming universal proof of completeness.

## Candidate Area 4: AI Evidence Reconstruction

A protocol for capturing AI operational evidence including prompt hash, output
hash, model metadata, policy version, reviewer action, and deployment context,
then reconstructing a verifiable evidence chain from proof bundles.

## Candidate Area 5: Selective Disclosure Verification

A proof workflow in which public verifiers can validate event inclusion,
signature status, and tree-head agreement without access to restricted raw
source records.

## Explicit Non-Claims

Do not claim:

- SHA-256 or generic hashing;
- generic Merkle trees;
- generic Ed25519 signatures;
- generic blockchains;
- generic logging or audit trails;
- generic OpenTelemetry traces;
- generic AI explainability.

Potential claim language must focus on ETS-specific protocol integration and
operational semantics.

## Implemented Claim-Supporting Artifact Candidates

The following artifacts may help counsel evaluate whether any claim language is
supported by implementation evidence:

- `ets.core.federation`: deterministic assessment of verifier-observed tree
  heads, quorum threshold, and same-view root conflicts;
- `/api/v1/federation/assess`: executable API surface for independent verifier
  federation experiments;
- `tests/unit/test_federation.py` and `tests/integration/test_api.py`:
  reproducible evidence that quorum and conflict behavior is implemented.

These artifacts should be framed as system-level evidence-verification
semantics. They should not be framed as ownership of threshold voting,
cryptographic signatures, Merkle proofs, or generic log replication.
