# Election Merkle Proofs

Sprint 3 adds election-facing Merkle proof artifacts over the append-only
election evidence ledger.

ETS reuses the canonical core Merkle implementation:

- leaf hash: SHA-256 over the packet event hash bytes;
- parent hash: SHA-256 over left child bytes followed by right child bytes;
- odd levels duplicate the last node;
- proof verification is possible from exported proof data alone.

## Root Manifest

`ElectionRootManifest` is the public milestone root format. It contains:

- election ID;
- jurisdiction;
- milestone name;
- tree size;
- Merkle root;
- event IDs in append order;
- generation timestamp;
- hash algorithm.

It does not contain sealed payloads, private metadata, or signatures.

## Inclusion Proof Bundle

`ElectionInclusionProofBundle` contains the public-safe fields needed to verify
one packet:

- event ID;
- event type;
- privacy class;
- payload hash;
- event hash;
- leaf hash;
- root manifest;
- Merkle audit path.

The bundle validates membership without exposing sealed artifacts.

## Batch Proofs

`ElectionBatchProofBundle` groups multiple inclusion proof bundles under one
root manifest. This supports milestone publication for observers or auditors
who need to verify several packet IDs at the same checkpoint.

## CLI Verification

```powershell
.\.venv\Scripts\ets-verify.exe election-proof .\path\to\election-proof.json
```

The command exits `0` for valid proof bundles and non-zero for invalid or
tampered bundles.

## Observer Explanation

If the proof is valid, the packet hash was committed to the published milestone
root. If a leaf hash, path hash, root, or event hash is altered, verification
fails deterministically.

ETS proves inclusion in the published evidence ledger. It does not prove vote
totals, voter intent, or real-world completeness.
