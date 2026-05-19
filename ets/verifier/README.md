# ETS Verifier

CLI and SDK tools to:

- verify event hashes
- validate inclusion proofs
- compare tree heads
- verify future signatures

## SDK

```python
from ets.verifier import compute_event_hash, verify_event_hash, verify_inclusion
```

## CLI

```powershell
ets-verify event-hash .\event.json
ets-verify event-hash .\event.json --expected <sha256>
ets-verify inclusion-proof .\proof.json
```

The CLI prints JSON and exits with `0` for valid artifacts, `1` for invalid
verification results, and `2` for unreadable or malformed input.
