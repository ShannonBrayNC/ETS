# ADR-004: ETS Core Package Boundary

- Status: Proposed
- Date: 2026-08-01
- Decision owners: ETS protocol owner and independent protocol reviewer
- Related: #162, #163, #157, #158, #161

## Context

The current `ets` distribution combines deterministic protocol primitives, reference storage, API hosting, reports, SDK facades, federation experiments, artifact workflows, and product integrations. ETS Edge and Cloud require a stable protocol library, while third parties must be able to implement and verify ETS without inheriting product or hosting dependencies.

Immediately splitting repositories would create additional versioning and integration risk before the alpha freeze and Edge MVP baseline are finalized. Leaving the package boundary undefined would allow product concerns to influence canonical protocol behavior.

## Decision

Establish `ets-core` as an independently releasable distribution within the current monorepo first.

The normative core consists of deterministic serialization, versioned evidence contracts, hashing profiles, Merkle construction, inclusion and consistency proofs, signed tree-head payloads and verification, portable proof bundles, deterministic verification outcomes, approved schemas, vectors, and offline verifier behavior.

Reference storage, FastAPI hosting, authentication, portals, Edge lifecycle, synchronization transport, hosted signing providers, reports, federation experiments, billing, entitlements, AI, and hardware are outside the normative core.

The package must support explicit version/profile selection. It must not silently infer incompatible legacy profiles. The active Merkle profile uses RFC 6962 domain separation. Legacy unprefixed alpha vectors are verification-only under a named compatibility profile.

Evidence Object v1 is additive and enters the stable core only after its schema, canonicalization, hash preimage, cross-language vectors, and migration behavior pass Sprint C2 gates.

## Dependency direction

Allowed:

`product or reference implementation -> ets-core`

Prohibited:

`ets-core -> API, Edge, Cloud, portal, Azure, AI, billing, connector, or environment-specific runtime`

Import-boundary tests will enforce this rule.

## Packaging sequence

1. Freeze the C0 contract and classification.
2. Harden pure APIs and profiles in C1.
3. Complete Evidence Object v1 in C2.
4. Publish conformance artifacts in C3.
5. Build the independent `ets-core` distribution in C4.
6. Consider repository extraction only after release ownership and consumer migration are demonstrated.

## Consequences

### Positive

- Edge, Cloud, SDKs, and third parties share one deterministic trust foundation.
- Core verification remains offline and vendor neutral.
- Product release cadence cannot silently change protocol semantics.
- Dependency and supply-chain surface is reduced.
- Historical artifacts remain verifiable through explicit compatibility profiles.

### Costs

- Existing broad imports from `ets.core` will require migration or compatibility shims.
- Storage, report, anchor, federation, and artifact features require clearer extension packages.
- Coordinated versioning is required during the monorepo transition.

## Rejected alternatives

### Keep one undifferentiated `ets` package

Rejected because protocol and product dependencies would remain coupled and third-party adoption would inherit unnecessary runtime concerns.

### Split into multiple repositories immediately

Rejected for C0 because the alpha, Evidence Object, and Edge baselines are still active. Physical separation before semantic and dependency separation would add risk without establishing a stable contract.

### Put all existing `ets.core` exports in the stable API

Rejected because the current facade includes reference storage and experimental/optional capabilities that are not part of the normative protocol.

## Approval gates

- Independent protocol review.
- Dependency/import analysis.
- Compatibility matrix review.
- Exact-head CI.
- No merge before #157 establishes the authoritative alpha baseline, or explicit rebase/reconciliation against that baseline.
