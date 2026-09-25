# ETS Application SDK v1

Contract: `ets.application.sdk.v1`  
Status: SDK-1 frozen contract; remote transport implementation follows in SDK-2

## Purpose

The Application SDK is the stable developer-facing boundary for applications that
submit ETS evidence events, retrieve committed events and proof material, export
evidence bundles, and invoke verification.

It is distinct from the Connector SDK. Application code is not given connector
checkpoint/reconciliation responsibilities, and connector implementations are not
given ETS signing or proof authority.

## v1 surface

The application surface is organized around these logical operations:

- create/validate evidence;
- compute ETS hashes only in implementations that pass the conformance corpus;
- append/capture evidence through a configured local store or remote Gateway;
- retrieve events and list scoped events;
- obtain inclusion and consistency proofs;
- obtain portable evidence proof bundles;
- invoke offline or online verification;
- inspect service health/version and SDK compatibility.

The Python reference already supports local create/hash/append/proof/verification
helpers under `ets.sdk.local`. SDK-2 adds the remote client while preserving
these v1 semantics.

## Receipt boundary

`ets.sdk.event_commit_receipt.v1` describes a successful local event
commitment. Its `commitment_state` is exactly `committed_local`.

The receipt establishes that the event was accepted into the returned ETS log
view at the supplied index/hash/tree head. It does not by itself establish:

- upstream source truth;
- source completeness;
- synchronization to another ETS node;
- independent verification;
- authorization or policy standing;
- external anchoring;
- real-world consequence.

Those states must never be inferred from a successful append response.

## Hashing rule

Python remains the reference implementation of the currently deployed ETS
canonical JSON algorithm. A new language SDK MUST pass
`conformance/sdk/v1/` before computing authoritative ETS hashes client-side.

Until then, a language SDK may submit protocol objects and consume
server-produced hashes without claiming local hashing equivalence.

## Stability

Backward-incompatible changes to the public application contract require a new
contract identifier. Package versions and protocol contract versions are
independent; see `COMPATIBILITY.md`.
