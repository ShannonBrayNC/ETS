# ETS v0.1 Test Vectors

This directory contains the initial public test-vector set for ETS Protocol v0.1.

The purpose of these vectors is to make ETS independently testable. A conforming implementation should be able to load the vector inputs, apply the ETS canonicalization and validation rules, reproduce the expected hashes for valid vectors, reject invalid vectors with the expected error class, and produce the expected verification and policy-route outcomes.

## Public boundary

These vectors are public-safe examples. They do not contain real customer evidence, secrets, credentials, personally identifiable evidence, USPTO filing material, claim charts, prior-art matrices, attorney notes, or private Lantern-IP material.

## Categories

- `valid/` contains EvidenceEvent examples that should validate and hash successfully.
- `invalid/` contains EvidenceEvent examples that should fail validation.
- `edge-cases/` contains valid examples designed to exercise Unicode, redaction, external references, and claim-boundary handling.

## Canonicalization profile

Initial ETS v0.1 vectors use the `ets-json-c14n-v0.1` profile:

1. UTF-8 JSON serialization.
2. Object keys sorted lexicographically.
3. No insignificant whitespace.
4. Hashable EvidenceEvent payloads exclude future server-generated proof fields.
5. Hashes use SHA-256 and are represented as `sha256:<64 lowercase hex characters>`.

The v0.1 canonicalization profile is intentionally narrow. Later protocol drafts may align this profile more explicitly with established JSON canonicalization standards.

## Hash expectations

The manifest records:

- `event_hash`: SHA-256 over canonical EvidenceEvent bytes.
- `leaf_hash`: SHA-256 over the raw bytes represented by the event hash hex value.
- `proof_verified`: whether a basic inclusion-proof verifier should accept the vector.
- `policy_route`: the expected policy-routing outcome for the vector.

## Conformance use

A future conformance runner should support a command similar to:

```bash
ets-conformance run \
  --profile ets-core-v0.1 \
  --vectors ./test-vectors
```

A conforming implementation should not require Lantern, EchoMedia, Christina, SignalForge, or OpsHelm to pass these vectors. Those systems may be ETS adopters or integrations, but the protocol must remain independently implementable.
