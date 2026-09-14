# ETS Hardware Qualification Independent Verifier v1

Status: HQP-2 implementation candidate  
Tracking issue: #795  
Depends on: HQP-0 #790 and HQP-1 #794 / PR #802

## Purpose

HQP-2 is the clean-room verification layer for the ETS Hardware Qualification Profile. It consumes a profile descriptor, sealed HQP-1 run, deterministic HQP-1 report, and retained artifact bytes, then independently determines whether the package is structurally valid, cryptographically consistent where the contract supplies verifiable material, and eligible for its claimed disposition.

The verifier does **not** trust the device-under-test runtime, the producer narrative, or the producer-side `verifier_result` merely because those fields claim success.

## Inputs

A verification invocation requires:

- HQP v1 profile JSON;
- sealed `ets.hardware-qualification-run.v1` JSON;
- `ets.hardware-qualification-report.v1` JSON;
- artifact-ID-to-byte-payload mapping;
- immutable verifier identity and verifier build digest;
- an explicit statement that the invocation is executing in an independent context;
- optional challenge nonce.

## Verification layers

HQP-2 evaluates independent layers instead of treating one outer hash as sufficient.

1. **Profile schema conformance** — the runtime model mirrors the normative HQP-0 JSON Schema.
2. **Run/report schema conformance** — HQP-1 validators re-check sealed run and report digests and reference integrity.
3. **Profile binding** — profile ID, version, and canonical profile digest must match the run binding.
4. **Report projection** — the submitted report must exactly equal the deterministic projection rebuilt from the sealed run.
5. **Artifact presence** — required retained bytes must be supplied unless explicitly withheld, which produces an indeterminate rather than a silent pass.
6. **Artifact byte integrity** — supplied byte length and SHA-256 must match the retained manifest.
7. **Evidence Object binding** — referenced JSON Evidence Objects must parse under the ETS Evidence Object v1 contract, match the retained evidence ID, and reproduce the canonical object hash.
8. **Test completion** — run test inventory and required flags must match the profile; required cases may not disappear or become `not_run` while supporting a qualified claim.
9. **Observation/result linkage** — stimulus, observation, and resulting-state references must remain inside the correct test boundary; required stimulus and observation classes must be present.
10. **Deviation/waiver policy** — waivers must be permitted, retained, associated with the correct test, and unexpired at run completion.
11. **Disposition policy** — the final state must be allowed by the profile and all requirements for a qualified claim must be independently re-derived.

## Gating and non-gating findings

A **gating** failure makes the independent verification `invalid`. A gating `indeterminate` makes the overall result `indeterminate`. Non-gating findings preserve explicit contract limitations without converting a known modeling gap into a false failure or pass.

HQP-2 currently records two non-gating limitations inherited from HQP-1:

- HQP-1 `ResultingStateRecord` has an ID and canonical digest but does not carry a normative `resulting_state_class`; HQP-2 can prove test/result linkage and bytes, but cannot reconstruct profile-level resulting-state semantic labels from that field alone.
- HQP-1 does not define a generic signature envelope for retained artifacts. HQP-2 verifies SHA-256 integrity and reports generic signature verification as not independently decidable unless a later contract supplies explicit signature material.

These limitations are visible in every result trust boundary. They must not be described as successful semantic or signature verification.

## Output

Machine-readable results use:

`schemas/qualification/v1/hardware-qualification-verification.schema.json`

The result binds:

- verifier identity/build and independent-context declaration;
- profile/run/report identifiers and digests;
- claimed disposition and eligibility decision;
- ordered check results with gating semantics;
- verified, missing, and mismatched artifact IDs;
- verified and invalid Evidence Object IDs;
- explicit trust boundary;
- canonical `verification_digest_sha256`.

A deterministic text renderer is provided for operator/reviewer use.

## Clean-room invocation

From an installed ETS environment:

```text
python -m ets.hqp_verify \
  --profile docs/qualification/fixtures/hqp2/valid/profile.json \
  --run docs/qualification/fixtures/hqp2/valid/run.json \
  --report docs/qualification/fixtures/hqp2/valid/report.json \
  --artifact-map docs/qualification/fixtures/hqp2/valid/artifact-map.json \
  --verifier-id hqp2-clean-verifier \
  --verifier-build-digest <64-hex-sha256> \
  --independent \
  --format text
```

The CLI exits `0` only for an independently valid package. Invalid or indeterminate results exit `2`.

## Conformance fixtures

`docs/qualification/fixtures/hqp2/valid/` contains a complete retained positive package with real byte-level SHA-256 values and a canonical Evidence Object hash.

`docs/qualification/fixtures/hqp2/invalid/mutations.json` defines negative vectors for:

- retained artifact byte tampering;
- profile mutation after the run was sealed;
- verifier execution without an independent context.

Tests must reproduce the positive qualification and reject each negative vector at the expected gate.

## Claim boundary

A successful HQP-2 result means the supplied retained package was independently reproduced within the verifier's stated inputs and observability boundary. It does **not** prove complete observation, semantic truth of the physical world, legal admissibility, regulatory compliance, safety certification, general availability, or production readiness.
