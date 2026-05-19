# ETS Verifier

CLI and SDK tools to:

- verify event hashes
- validate inclusion proofs
- compare tree heads
- verify future signatures

## SDK

```python
from ets.verifier import compute_event_hash, verify_event_hash, verify_inclusion
from ets.verifier import compare_tree_heads
```

## CLI

```powershell
ets-verify event-hash .\event.json
ets-verify event-hash .\event.json --expected <sha256>
ets-verify inclusion-proof .\proof.json
ets-verify tree-head .\previous-head.json .\latest-head.json
```

The CLI prints JSON and exits with `0` for valid artifacts, `1` for invalid
verification results, and `2` for unreadable or malformed input.

Tree head comparison detects local checkpoint regressions: log ID mismatch,
tree size rollback, timestamp rollback, same-size root changes, and impossible
tree growth without a root change. It is a checkpoint sanity check, not a
replacement for a future cryptographic consistency proof.
