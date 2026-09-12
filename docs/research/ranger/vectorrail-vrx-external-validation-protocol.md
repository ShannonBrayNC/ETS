# VectorRail/VRX External Validation Protocol

Status: Proposed validation handoff  
Tracks: #723

## Purpose

This protocol tells an external reviewer how to validate the VectorRail/VRX portable consequence-custody artifact as a reproducible research result without relying on Lantern-hosted infrastructure or private implementation guidance.

The work is intentionally separated from implementation authorship. The validator's task is to determine whether the public contract is sufficient to reproduce the same bounded conclusions independently.

## Validation unit

A validation run must freeze and record:

- the exact ETS source commit or release tag under review;
- the portable-package schema version;
- the package digest presented for review;
- the clean-room verifier contract version;
- the challenge-manifest version;
- the independent verifier source/archive reference;
- the validation environment and toolchain.

A later source change, package change, or verifier change constitutes a new validation run.

## Validator independence

Before testing, the reviewer records:

- name or durable reviewer identity;
- organization or affiliation, when applicable;
- relationship to the implementation authoring path;
- material conflicts of interest;
- whether any ETS reference implementation source was inspected before the independent result was frozen;
- any clarifying questions asked and the public answer/source used.

A validator who authored the implementation under test may perform useful replication testing, but that run must not be labeled independent validation.

## Clean-room implementation phase

The reviewer implements a minimal verifier in a language or runtime independent from the Python reference path where practical. The implementation may consume only the public materials listed in `vectorrail-vrx-clean-room-verifier-contract.md` until the result is frozen.

The implementation must expose, at minimum:

1. package parsing and schema validation;
2. canonical SHA-256 calculation;
3. trial and acceptance record-binding checks;
4. deterministic Evidence Object projection checks;
5. dependency-graph reconstruction;
6. consequence-custody replay;
7. observability-boundary conservation;
8. stable package-level conclusion codes.

## Baseline replay

Using the canonical public baseline package, the validator must obtain:

- package result `VERIFIED_REPLAYABLE`;
- underlying chain result `VERIFIED_CONSISTENT`;
- `network_required = false`;
- `truth_claim_supported = false`.

Any mismatch is recorded verbatim rather than normalized away.

## Adversarial challenge run

The reviewer then executes every required case in:

`experiments/scenarios/vectorrail-vrx-clean-room-challenges.v0.1.json`

Each challenge describes a mutation, whether the outer package must be re-sealed to isolate the deeper layer, and the required high-level result.

A validation is not complete if only the nominal case passes. The challenge suite exists to demonstrate that the verifier detects integrity, record-binding, Evidence Object, dependency, replay, and epistemic-boundary failures at the intended layer.

## Environment capture

The report records:

- operating system and version;
- architecture;
- implementation language;
- compiler/interpreter/runtime version;
- dependency names and versions;
- build command or reproducible build reference;
- whether network access was used during verification;
- any platform-specific behavior observed.

Normative bytes, hashes, and conclusions must not vary by platform.

## Required evidence

The reviewer should retain or publish:

- independent verifier source or an immutable source archive;
- build instructions;
- machine-readable validation report conforming to `schemas/ranger/vectorrail-vrx-independent-validation-report.v0.1.schema.json`;
- terminal or CI transcript showing the baseline and challenge results;
- exact input package digest;
- findings and ambiguity log;
- limitations and residual-risk statement;
- signed or durable approval/rejection record.

## Acceptance criteria

A run is eligible for independent approval only when:

1. the validator's independence disclosure is complete;
2. the independent verifier was implemented from public contract material rather than copied reference source;
3. the baseline reproduces the expected package and chain conclusions;
4. every required adversarial challenge produces its expected classification;
5. no unresolved normative ambiguity affects bytes, hashes, dependency reconstruction, or conclusion codes;
6. the claim boundary remains explicit and unchanged;
7. the complete validation report is durable and attributable to the validator.

Any unresolved mismatch produces `REJECT` or `INDETERMINATE`; it must not be waived by narrative assertion.

## Post-freeze comparison

After the independent result is frozen, the reviewer may compare the clean-room implementation against the Python reference implementation to diagnose differences. Those comparisons are useful engineering evidence but must remain distinguishable from the clean-room implementation phase.

## Dissertation use

A completed validation packet can support claims that the ETS experiment is independently reproducible and that the published contract is sufficiently precise for an external implementation to reach the same bounded result.

It cannot support claims that the physical observations were objectively true, that the device was safe for arbitrary use, or that the evidence has legal sufficiency in a specific proceeding.
