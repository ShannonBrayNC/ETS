# Verifier Golden Fixtures

This folder contains deterministic, fictional, metadata-only verifier fixtures used by CLI regression tests and demos.

## Files

- `event.json` — canonical `EvidenceEvent` for `ets-verify event-hash`.
- `inclusion-proof.json` — valid inclusion proof for `ets-verify inclusion-proof` and `ets-verify verify-proof`.
- `consistency-proof.json` — valid consistency proof for `ets-verify consistency-proof`.
- `bundle.json` — valid `EvidenceProofBundle` for `ets-verify bundle` and `ets-verify certificate`.
- `tree-head-previous.json` — previous local checkpoint for `ets-verify tree-head`.
- `tree-head-latest.json` — later local checkpoint for `ets-verify tree-head`.
- `election-proof.json` — fictional election evidence metadata proof for `ets-verify election-proof`.

## Boundaries

All fixture content is fictional and small. These fixtures do not contain raw evidence bytes, customer data, real voter data, real ballot data, real tabulation data, or official election results. They prove verifier behavior only; they do not prove evidence authenticity, evidence legality, evidence completeness, election correctness, ballot validity, or tabulation accuracy.
