# Evidence Object v2 compatibility and identity contract

Evidence Object v2 is additive. It does not replace or reinterpret
`ets.event.v1`, Evidence Object v1, historical Merkle leaves, or existing proof
bundles.

## Canonical identity

The hash profile is
`ets.evidence-object.identity.canonical-json.sha256.v2`. The preimage contains,
in contract order, `schema_id`, `identity`, `created_at`, `bindings`, `policies`,
`privacy`, and `extensions`. Values use the existing ETS canonical JSON rules.
Array order is significant. Optional `null` values are omitted.

`proof_material` is an attachment surface and is never part of the identity
preimage. Unknown proof types may be transported and retained without changing
object identity. If verification semantics must affect identity, the producer
must add a `verification` binding with a SHA-256 commitment to a separately
versioned verification contract. A verifier must not infer trust, truth, or
policy satisfaction merely from attached proof material.

## API and SDK adoption

- Existing event and Evidence Object v1 endpoints remain unchanged.
- A later API slice may expose v2 validation and identity hashing under a new
  versioned route; it must not silently dual-write or migrate stored v1 data.
- Python exports remain additive. Other SDKs consume the normative schema and
  reference vectors before advertising v2 compatibility.
- Historical records remain readable and verifiable with their original
  profiles. Migration creates a new v2 object that binds the historical event
  or v1 object by reference and commitment; it never rewrites the source.

This slice defines the contract only. Claim, provenance, relationship,
verification-boundary, and privacy semantics remain separately versioned work.
