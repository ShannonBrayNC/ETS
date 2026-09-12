# VectorRail/VRX External Validation Release v0.1.0

This directory is a frozen, self-contained handoff for independent review of the ETS VectorRail/VRX consequence-custody experiment. It is intended to let a university reviewer or other external validator reproduce the bounded verification result without private Lantern guidance.

## Frozen subject

- Repository: `ShannonBrayNC/ETS`
- Frozen subject commit: `a50720ab5ba451c6c97008da63b401fcaf28b34f` (merge of PR #724)
- Bundle version: `0.1.0`
- Canonical portable-package digest: `sha256:ae2e40b9a272f077cbe139930d353e7610212b2b1877f51e9fb1a87691b312c0`
- Expected package conclusion: `VERIFIED_REPLAYABLE`
- Expected chain conclusion: `VERIFIED_CONSISTENT`
- Network required for verification: `false`
- Truth claim supported: `false`

The repository may continue to evolve after the frozen subject commit. Those later changes are outside this validation subject unless a new release bundle is issued.

## Start here

1. Verify every distributed payload with `SHA256SUMS`. The checksum file follows the normal non-recursive convention and does not list itself.
2. Decompress `baseline/vectorrail-vrx-baseline-portable-package.json.gz` to `vectorrail-vrx-baseline-portable-package.json`. The uncompressed canonical file SHA-256 is `a87bffbbf613ccf079b3be5eea07bc3ec0cce68aeb16976f730a29150540372c`; its internal ETS package digest is the `sha256:ae2e40...` value above.
3. Before freezing the clean-room result, do **not** copy or rely on the Python reference implementation under `ets/ranger/`. Use only the materials in this bundle and other public normative materials explicitly identified by the clean-room verifier contract.
4. Implement the language-neutral verifier contract in `docs/vectorrail-vrx-clean-room-verifier-contract.md`.
5. Replay the canonical baseline package. A conforming result is package `VERIFIED_REPLAYABLE`, chain `VERIFIED_CONSISTENT`, `network_required=false`, and `truth_claim_supported=false`.
6. Execute every required mutation in `manifests/vectorrail-vrx-clean-room-challenges.v0.1.json`. A nominal-only pass is not sufficient.
7. Complete `templates/independent-validation-report.template.json`, retain the verifier source/archive, build instructions, environment details, terminal or CI transcript, findings, limitations, and durable approval/rejection record.
8. Freeze the result before comparing the independent implementation with ETS reference source.

On Unix-like systems, the baseline can be extracted with:

```text
gzip -dc baseline/vectorrail-vrx-baseline-portable-package.json.gz > vectorrail-vrx-baseline-portable-package.json
sha256sum -c SHA256SUMS
```

Equivalent SHA-256 and gzip tooling may be used on other platforms. Normative bytes, hashes, and conclusions must not depend on platform.

## Bundle map

- `RELEASE.json` — frozen subject metadata and expected identifiers.
- `baseline/` — canonical package payload plus the exact trial and acceptance source fixtures from the frozen subject commit.
- `schemas/` — package, trial, acceptance, Evidence Object v1, and independent-validation-report schemas.
- `manifests/` — deterministic replay and adversarial challenge manifests.
- `docs/` — portable-package description, clean-room verifier contract, and external validation protocol.
- `templates/` — blank machine-readable validation report.
- `SHA256SUMS` — file-level SHA-256 inventory for every other distributed bundle file.

## Independence gate

This release prepares an external validation target; it does **not** constitute independent validation. Implementation authors, Lantern personnel who authored the implementation under test, and automated agents may perform replication testing, but those runs do not satisfy the independent-human approval gate. The final report must identify the human validator, disclose conflicts, state whether reference source was inspected before freeze, and provide a durable source/archive reference for the independent implementation.

## Claim boundary

A passing external validation supports reproducibility, deterministic integrity checks, dependency reconstruction, and bounded protocol interpretation of the presented evidence package. It does **not** establish sensor correctness, objective physical truth, electromagnetic-model correctness, optimal action, legal admissibility, regulatory approval, or production safety certification.
