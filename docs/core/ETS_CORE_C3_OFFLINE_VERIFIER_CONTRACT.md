# ETS Core C3 Offline Verifier Contract

Status: proposed

## Library API

The verifier library exposes pure functions accepting bytes or parsed protocol objects plus an explicit profile identifier and resource limits. It returns the C1 `VerificationResult` model and performs no network, storage, environment, telemetry, or policy lookup.

Required operations:

- `verify_event(...)`
- `verify_evidence_object(...)`
- `verify_inclusion_proof(...)`
- `verify_consistency_proof(...)`
- `verify_tree_head(...)`
- `verify_proof_bundle(...)`
- `verify_certificate(...)`
- `inspect_artifact(...)`

Profile inference is prohibited when more than one interpretation is possible.

## CLI contract

Executable: `ets-verify`

Commands:

```text
ets-verify inspect <path>
ets-verify event <path> --profile <id>
ets-verify object <path> --profile <id>
ets-verify proof <path>
ets-verify tree-head <path>
ets-verify bundle <path>
ets-verify certificate <path>
ets-verify conformance --manifest <path> --output <path>
```

Common options:

- `--format text|json`
- `--max-bytes`
- `--max-depth`
- `--max-items`
- `--timeout-seconds`
- `--strict`
- `--quiet`

## Process exit codes

- `0`: verification valid or conformance pass.
- `2`: artifact invalid.
- `3`: malformed input.
- `4`: unsupported profile or algorithm.
- `5`: unknown because required verification material is absent.
- `6`: resource limit exceeded.
- `70`: internal implementation error.

The JSON result remains authoritative; exit codes are an automation convenience.

## Input behavior

- Input is read as bytes and size-limited before parsing.
- JSON duplicate keys, non-finite numbers, invalid Unicode, and ambiguous encodings are rejected.
- Archives are not accepted by single-artifact commands.
- External URLs and content references are not dereferenced.
- Private keys are never accepted.

## Output behavior

Machine-readable output includes:

- result schema version;
- artifact type;
- declared and resolved profiles;
- verification status and reason code;
- bounded diagnostics;
- computed digests and roots when safe;
- implementation and verifier version;
- no claim beyond cryptographic and structural verification.

## Portability

Verification must continue after a customer subscription, hosted tenant, or vendor service is unavailable. Portable artifacts therefore include or reference all public keys, profile identifiers, proof nodes, tree heads, and certificates needed for offline verification, subject to documented trust-anchor handling.

## Trust anchors

The verifier distinguishes:

- cryptographic signature validity;
- key identity;
- key trust or authorization.

A valid signature does not imply that a key was authorized. Trust-anchor selection is explicit input or external policy and is reported separately from cryptographic validity.

## Determinism

Given identical artifact bytes, explicit profile, trust-anchor input, and limits, the verifier must return identical status, reason code, computed values, and normalized machine-readable output across runs.