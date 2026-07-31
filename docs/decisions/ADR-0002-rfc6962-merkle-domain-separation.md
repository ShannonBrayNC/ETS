# ADR-0002: RFC 6962 Merkle Domain Separation

## Status

Accepted for `v0.1.0-alpha` protocol recovery.

## Context

The canonical runtime in `ets/core/merkle.py` implements RFC 6962 Merkle Tree
Hash domain separation, but the original conformance vectors and two protocol
descriptions omitted the domain bytes. The stale vectors therefore disagreed
with the API, SDK, CLI, proof generator, and verifier runtime.

The disagreement must be resolved before deployment because roots and proofs
created under different hash profiles are cryptographically incompatible.

## Decision

ETS selects the profile identifier:

```text
ets.merkle.rfc6962_sha256.v1
```

The profile uses these normative operations, where `SHA256` returns 32 raw
bytes and `||` denotes byte concatenation:

```text
empty_root       = SHA256(empty byte string)
event_hash_bytes = hex_decode(lowercase_event_hash)
leaf_hash        = SHA256(0x00 || event_hash_bytes)
node_hash        = SHA256(0x01 || left_hash_bytes || right_hash_bytes)
```

Tree construction recursively splits `n > 1` leaves at the largest power of
two strictly smaller than `n`. A single-leaf tree root is its already
domain-separated leaf hash. Odd nodes are not duplicated.

Hexadecimal is a transport and display encoding only. Implementations MUST
decode a 64-character event or child hash to its raw 32-byte digest before
applying the formulas above.

The existing schemas `ets.inclusion_proof.v1`, `ets.consistency_proof.v1`, and
`ets.proof_bundle.v1` are normatively bound to this profile. Their JSON shape
does not change because the accepted runtime behavior does not change.

## Independently calculated reference hashes

These values were calculated by `scripts/verify_rfc6962_vectors.py`, which uses
only Python's `hashlib` and does not import the ETS implementation:

| Input | RFC 6962 result |
|---|---|
| Empty tree | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Event digest `8391362f...e3c9dfa8` | `35c8cb9455f8cdfe2cdb82a2cf34e7be27012172d16358aa63245a85d269696c` |
| Node of `00` x 32 and `11` x 32 | `a7b6a88afe611b23a8bb9836e3cd13ba706cb05d6de647d92bf05bb0aace72ee` |
| Three supplied leaf hashes | `5e02fbbdb83c92dac50c2f1461e135b45e6e7b7dc78fec5f4ada10413fb20d02` |
| Four supplied leaf hashes | `4cbfa20fd0506f9f071f52240028815b5659e185ebf74009657d38756069c174` |

The stale expected values identify the defect: `aa7824...` is
`SHA256(event_hash_bytes)` and `8878b1...` is `SHA256(left || right)`, both
without the required domain prefix.

## Compatibility and migration

- Current data produced by `ets/core/merkle.py`, including API, SDK, CLI, and
  SQLite-backed flows, already uses the accepted profile and needs no rewrite.
- The unversioned `ets/spec/test-vectors/merkle-vectors.json` path is replaced
  by `ets/spec/test-vectors/v0.1/merkle-vectors.json`.
- Roots, inclusion proofs, consistency proofs, proof bundles, or external
  checkpoints created from the stale no-prefix vectors are incompatible. They
  MUST be regenerated from the original ordered event hashes.
- A stored artifact without its ordered event hashes cannot be converted by
  rewriting the root; it must remain explicitly labeled legacy/incompatible.
- Verifiers MUST reject a bundle whose event hash, bundle leaf hash, and proof
  leaf hash do not bind under this profile.
- The legacy prototype under `src/` is not part of the installed runtime and is
  not a protocol authority.

## Verification impact

- API-generated proofs continue to round-trip through verification routes.
- SDK append and proof helpers continue to use the canonical core.
- CLI verification continues to consume v1 proof and bundle schemas.
- Offline bundle verification now explicitly checks the event-to-leaf and
  bundle-to-proof leaf bindings.
- The complete `python -m pytest` suite is the release gate before hosted work.
