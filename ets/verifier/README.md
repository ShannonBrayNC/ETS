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

See `docs/spec/ETS_VERIFIER_V1.md` for the verifier contract, security model,
standards research, and test matrix.
