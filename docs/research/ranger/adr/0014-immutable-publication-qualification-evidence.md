# ADR 0014: Bind Immutable-Publication Qualification to Raw Evidence

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-12
- **Decision owners:** ETS Ranger research program
- **Related:** #605, #626, #627, #630

## Context

Ranger can publish trusted-time-attested retained heads, retain the publication chain in a
logically append-only SQLite archive, audit later retrieval, and reconstruct publisher/custodian
key standing. Those controls do not qualify a separately administered immutable backend.

A provider name, object-lock configuration string, successful put, or client-observed deletion
error is individually insufficient. A verifier needs the exact object bytes, publication head,
configuration, delete capability, attempted deletion, post-denial retrieval, source-key history,
and the identity that captured the provider evidence.

## Decision

Introduce `ets.ranger.immutable-publication-qualification.v1` as an additive, provider-neutral
source record. Require five raw, content-addressed artifacts: configuration, retention put,
delete-capability preflight, delete attempt, and post-denial retrieval. Bind the record to the
canonical full publication archive bundle, expected publication head, custodian retrieval audit,
backend identity, verifier-pinned object key/version and deletion-probe principal, fresh verifier
challenge, and evidence-issuer key.

Verification composes the existing publication/custodian lifecycle contracts. Every publisher
receipt must have historical authority-relative key standing, while the retrieval audit must have
historical standing and be current relative to the full authority history presented to the
verifier. The verifier requires versioned compliance retention, no reported bypass, a policy-
bounded retention interval, retention-enforced delete denial, and exact post-denial content.

Simulation uses the identical record and artifact classes but cannot pass the provider-control-
plane result. A provider-control-plane result remains bounded to the configured signer and supplied
artifacts; physical WORM, independence, trusted time, availability, truth, and physical outcome
stay false.

## Consequences

- Evidence capture is designed alongside the storage behavior instead of reconstructed from logs
  later.
- Stale heads, key substitution, artifact deletion/modification, successful deletion, content
  substitution, and simulation/live confusion fail closed.
- Provider-specific SDKs and response semantics remain outside ETS Core and this generic module.
- A live adapter must preserve the same source record and raw artifact classes.
- A future provider-specific verifier is required before deployment qualification; this ADR does
  not select or approve a provider or expenditure.

## Rejected alternatives

### Treat a successful provider API call as proof of immutability

Rejected because it does not test deletion, bind later retrieval, enumerate bypasses, or preserve
the exact response evidence.

### Trust a storage-class or provider-name field

Rejected because names do not prove runtime configuration, administration, retention behavior, or
object identity.

### Use a different schema for simulation

Rejected because divergence would let simulation pass while a real adapter emits untested source
structures.

### Mark provider-control-plane conformance as physical WORM proof

Rejected because signed client observations and provider responses do not establish a universal
physical-media property or organizational independence.
