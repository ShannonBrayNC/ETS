# ETS SDK conformance

Cross-language conformance is a release gate for SDKs that implement ETS
canonicalization, hashing, Merkle, or verification behavior locally.

## SDK-1

The first corpus lives at `conformance/sdk/v1/` and covers:

1. deterministic canonical JSON bytes;
2. SHA-256 over those exact bytes;
3. an `ets.event.v1` hashable payload.

The Python unit suite consumes the same files that future .NET and TypeScript
suites must consume.

## Required expansion before client-side hashing in .NET/TypeScript

Add vectors for:

- ASCII and Unicode ordering/encoding;
- integer and supported floating-point representations;
- empty/null/boolean values;
- deeply nested arrays and mappings within protocol bounds;
- maximum-bound strings and mappings;
- invalid non-string map keys;
- rejected NaN and infinities;
- full event model serialization;
- Merkle leaf derivation;
- inclusion proofs;
- consistency proofs;
- signed tree-head verification;
- portable proof bundles.

A language implementation that has not passed the relevant vector family must
delegate that security-sensitive behavior to ETS rather than claim local
equivalence.
