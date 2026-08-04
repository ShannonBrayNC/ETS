# ADR-003: ETS Edge MVP Baseline, Deployment, and Evidence Boundary

Status: Proposed for independent approval
Date: 2026-08-01
Decision owners: ETS protocol owner and independent reviewer

## Context

ETS requires one stable baseline before edge implementation. The repository contains alpha hardening, protocol-governance, Evidence Object, Azure-hosting, public-release, and edge-planning branches with different scopes and readiness levels. Treating an unmerged branch as authoritative would make protocol, API, security, and release evidence ambiguous.

## Decision

1. The only authoritative implementation baseline is protected `main` after issue #157 completes and records one exact merged-main commit.
2. The primary MVP deployment is an x86-64 Ubuntu LTS appliance or VM. OCI is the secondary development and integration profile.
3. The MVP composes the existing versioned canonical event and RFC 6962 domain-separated Merkle behavior. It does not silently replace the current alpha event protocol with the developing Evidence Object Model.
4. Edge input is represented by the versioned `ets.edge.capture.v1` envelope. An adapter transforms that envelope into the existing append contract while preserving transformation provenance.
5. Raw evidence bytes remain outside the default ETS storage boundary. ETS retains metadata, digests, evidence references, proofs, checkpoints, receipts, and administrative records.
6. Local commit and local history remain authoritative for an edge node. Upstream synchronization is resumable and idempotent but cannot rewrite local sequence or Merkle history.
7. The local portal operates one node, the central portal operates tenant-scoped fleet and synchronized usage, and the public portal verifies supplied public-safe proof material only.
8. MVP claims are restricted to declared cryptographic properties. Semantic truth, complete observation, legal admissibility, compliance certification, and source-system security remain outside the claim boundary.

## Consequences

- Edge implementation is blocked until #157 is complete and this ADR receives independent approval.
- PR #159 may continue as additive semantic-model research and implementation, but it is not a prerequisite for the first edge MVP and cannot rewrite historical alpha logs.
- Azure hosted-signing and configurator work may be harvested later through narrowly scoped PRs, but it is not the edge MVP baseline.
- ARM, Raspberry Pi, rugged hardware, AI analysis, universal trust scoring, and advanced compliance portals are deferred.
- Any change to capture-envelope hash-relevant fields, Merkle semantics, signed tree-head payloads, or synchronization invariants requires a new version and ADR.

## Validation required before acceptance

- JSON Schema validation and negative fixtures for the capture envelope.
- Mapping tests from capture envelope to current `EvidenceEvent` without changing historical vectors.
- Protocol and security review.
- Independent submitted approval.
- Post-merge `main` validation.
