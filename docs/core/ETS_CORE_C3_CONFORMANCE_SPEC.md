# ETS Core C3 Conformance Specification

Status: proposed engineering contract

## Objective

Define a public, deterministic, offline conformance system that allows any implementation to demonstrate compatibility with named ETS protocol profiles without access to Lantern services, private fixtures, customer data, or commercial entitlements.

## Conformance principles

1. All normative fixtures are public and versioned.
2. Every test names its protocol profile, vector-set version, expected status, and expected reason code.
3. Conformance verifies protocol behavior only. It does not certify truth, completeness, legal admissibility, regulatory compliance, organizational trust, or production security.
4. The runner performs no network access and requires no account.
5. Implementations may be tested as libraries, CLIs, or adapters through a documented harness.
6. A result is reproducible from the implementation identity, conformance manifest, vector set, and runner version.

## Distribution layout

```text
conformance/
  manifest.json
  schemas/
  profiles/
  vectors/
    canonical/
    event/
    evidence-object/
    merkle/
    proofs/
    tree-head/
    bundle/
    certificate/
    negative/
    resource/
  runner/
  reports/
  examples/
  clean-room/
```

## Required implementation profiles

- `ets.conformance.verifier.v1`: verifies supplied artifacts but does not generate them.
- `ets.conformance.producer.v1`: canonicalizes and hashes EvidenceEvent and EvidenceObject payloads.
- `ets.conformance.log.v1`: constructs RFC 6962 roots and inclusion/consistency proofs.
- `ets.conformance.edge-node.v1`: produces portable edge records and checkpoints using approved core profiles.
- `ets.conformance.sync-peer.v1`: validates checkpoint and consistency-proof exchange semantics.

Profiles are cumulative only where explicitly stated in the profile manifest.

## Result classes

- PASS: actual output matches the required deterministic output.
- FAIL: implementation executed but produced a conflicting result.
- ERROR: harness or implementation could not complete the test.
- SKIP: test is outside the declared implementation profile.
- UNSUPPORTED: implementation explicitly rejects an optional profile.

A mandatory test cannot be converted to SKIP or UNSUPPORTED.

## Conformance report identity

Every report records:

- report schema version;
- runner name and version;
- vector-set identifier and digest;
- implementation name, version, language, and build identifier;
- declared conformance profiles;
- operating system and architecture;
- start and completion timestamps;
- per-test result, expected result, actual result, and diagnostic code;
- totals by profile and result class;
- manifest and report digest.

## Offline verifier scope

The verifier must validate, as applicable:

- canonical JSON;
- EvidenceEvent hashes;
- EvidenceObject hashes;
- inclusion and consistency proofs;
- signed tree heads;
- proof-bundle linkage;
- certificate structure and bounded claims;
- profile conflicts and downgrade attempts;
- malformed, oversized, truncated, and ambiguous input.

## Compatibility marks

A compatibility statement must name the exact profile and vector set, for example:

`Conforms to ets.conformance.verifier.v1 using vector set ets-vectors-2026.1.`

The statement must not use terms such as certified evidence, trusted evidence, legally admissible, compliant, complete, or truthful unless a separate authorized assessment supports that claim.

## Security requirements

- Treat all fixtures and implementation output as untrusted input.
- Enforce configurable byte, depth, collection, proof-path, and execution-time limits.
- Do not resolve external references during verification.
- Do not load executable code from vector packages.
- Reject path traversal, archive bombs, duplicate identifiers, ambiguous profile declarations, and unsupported algorithms.
- Produce deterministic diagnostics without leaking secrets or raw private content.

## Exit criteria

C3 is complete only when the public vector package, runner, report schema, verifier library/CLI, implementation profiles, clean-room guide, and CI release gates are implemented and independently exercised.