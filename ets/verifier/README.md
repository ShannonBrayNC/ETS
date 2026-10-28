# ETS Verifier

ETS provides both low-level proof helpers and production-oriented online/offline
verification modes.

## Verification modes

### Offline

`ets-verify offline` validates a downloaded `EvidenceProofBundle` without network
access. The strict path recomputes the canonical event hash, derives the Merkle
leaf from that hash, validates the inclusion proof, binds the proof root and tree
size to the checkpoint, and verifies the signed tree head against an out-of-band
trust store.

Offline verification proves inclusion at the trusted checkpoint. It deliberately
reports `standing_status=checkpoint_only`; it cannot prove that the checkpoint is
the current log state while disconnected.

### Online

`ets-verify online` retrieves the event bundle and current tree head from an ETS
service, performs all offline checks, validates the current signed tree head, and
then verifies append-only continuity from the bundle checkpoint to the current
head. If the tree grew, it retrieves and validates the ETS consistency proof.

A successful online result reports `standing_status=current_log`. This means the
evidence remains included in the current append-only log view. It does not by
itself assert that an external policy, authorization, consent, or decision still
has present standing; those predicates must be represented and evaluated as ETS
evidence/policy state.

## Trust store

Production verification keeps trust anchors outside the evidence bundle so an
attacker cannot replace both the proof and the key used to verify it.

```json
{
  "schema_version": "ets.verifier_trust.v1",
  "keys": [
    {
      "key_id": "https://example.vault.azure.net/keys/ets-tree-head/<version>",
      "signature_alg": "ps256",
      "public_key_hex": "<DER SubjectPublicKeyInfo encoded as hex>",
      "not_before_utc": "2026-08-01T00:00:00Z",
      "not_after_utc": "2027-08-01T00:00:00Z",
      "revoked_at_utc": null
    }
  ]
}
```

Ed25519 trust entries use the 32-byte raw public key encoded as 64 hex
characters. `revoked_at_utc` is a compromise/revocation boundary: checkpoints
signed at or after that time fail verification, while older signatures can still
be evaluated against the historical key validity window.

## SDK

Low-level helpers remain available:

```python
from ets.verifier import compare_tree_heads, compute_event_hash, verify_event_hash
from ets.verifier import verify_inclusion
```

Strict verifier orchestration is provided by `ets.verifier.service`:

```python
from ets.verifier.service import (
    TreeHeadTrustStore,
    VerifierPolicy,
    verify_offline_bundle,
    verify_online_event,
)
```

## CLI

Legacy proof commands remain supported:

```powershell
ets-verify event-hash .\event.json
ets-verify event-hash .\event.json --expected <sha256>
ets-verify inclusion-proof .\proof.json
ets-verify tree-head .\previous-head.json .\latest-head.json
```

Strict offline verification:

```powershell
ets-verify offline .\bundle.json `
  --trust-store .\ets-trust.json `
  --expected-log-id ets-production
```

Online verification:

```powershell
$env:ETS_VERIFY_BEARER_TOKEN = "<token>"
ets-verify online https://ets.example.com evt_123 `
  --trust-store .\ets-trust.json `
  --expected-log-id ets-production `
  --allowed-host ets.example.com
```

For local API-key mode, use `ETS_VERIFY_API_KEY` instead. Authentication secrets
are intentionally read from environment variables rather than CLI arguments to
reduce exposure through process listings and shell history.

`--allow-unsigned` and `--allow-http` exist only for local development. Neither
should be used for production verification.

The CLI prints JSON and exits with `0` for valid artifacts, `1` for invalid
verification results, and `2` for malformed input, unsafe configuration, or
transport failure.

## Local input limits and offline outcomes

Local JSON files are read in UTF-8 with a bounded read (limit plus one byte),
not an unbounded read following a size check. Limits are 4 MiB per artifact,
1 MiB per trust store, 64 nested containers, and 100,000 parsed nodes (including
object keys). Duplicate keys, non-finite numbers (including exponent overflow),
invalid UTF-8, escaped lone surrogates, and BOM-prefixed JSON are rejected.
These limits apply to CLI file input; they do not change the service/library API.

Strict `offline` output adds `status` and `reason_code`. Existing `valid`, checks,
and checkpoint-only claims remain available. Consumers must require `valid=true`
and must not treat a non-success status as evidence of validity.

| Status | Meaning | Exit code |
| --- | --- | --- |
| `valid` | All configured checks passed | 0 |
| `invalid` | A checked property failed, including a signature or trust-policy failure | 1 |
| `indeterminate` | Signature envelope or out-of-band trusted key is missing, with no other known failure | 2 if no trust-store argument was supplied; otherwise 1 |
| `unsupported` | Unknown bundle/event/inclusion schema version or checkpoint signature algorithm | 2 |
| `malformed` | Invalid JSON/schema or input/configuration error | 2 |
| `resource_limit` | Byte, nesting, or item limit exceeded | 2 |

The exit-code family remains 0/1/2; JSON carries the finer distinction. If
tampering is detected without a trust-store argument, the result is `invalid`
(exit 1) rather than stopping at the missing configuration (exit 2). Malformed
input and unsupported formats stop before verification. For a supported parsed
bundle, a failed non-signature check takes precedence over missing trust.

Supported strict-offline versions are `ets.proof_bundle.v1`, `ets.event.v1`,
and `ets.inclusion_proof.v1`; signature algorithms are Ed25519 and PS256.
Omitted schema fields retain the existing v1 model defaults for compatibility.
This is not implementation of the entire proposed C3 profile/exit-code contract.
Unknown content hash algorithms remain model-validation errors. Legacy commands
and online verification retain their existing verification semantics.

Missing trust never imports a key from the evidence bundle. `--allow-unsigned`
remains an explicit development-only policy and can still produce `valid` under
that policy; the consumer desktop UI must not expose it as trusted verification.
Validation errors omit Pydantic input excerpts to avoid echoing artifact content.

See `docs/spec/ETS_VERIFIER_V1.md` for the verifier contract, security model,
standards research, and test matrix.
