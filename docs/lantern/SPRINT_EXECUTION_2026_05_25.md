# Lantern Sprint Execution - ETS

Date: 2026-05-25
Default branch: `main`

## Sprint slice

ETS owns Lantern proof, consent, provenance, tamper detection, and machine-readable verification outcomes.

This sprint confirms the next ETS Lantern lane against the existing ETS alpha scope: build the consent ledger and cross-system proof bundle so SignalForge can reject unverified, forged, tampered, expired, or revoked handoffs before Christina or a vertical adapter can act.

## Files reviewed

- `README.md`
- Open issue `#60` - Consent Ledger and cross-system proof bundles
- Open issue `#61` - injected recommendation tamper demo

## Required implementation target

Add or complete:

- `ConsentEvent` schema
- `LanternProofBundle` schema
- verification helper for Lantern recommendations/artifacts
- CLI/API path for consent-chain verification
- machine-readable reason codes

Recommended reason codes:

```text
valid
missing_proof
invalid_proof
hash_mismatch
consent_missing
consent_denied
consent_revoked
consent_expired
approval_missing
source_untrusted
replay_detected
tampered_payload
unsupported_event_type
```

## Validation target

The ETS Lantern validation suite should cover:

1. Valid recommendation passes.
2. Forged recommendation with missing proof fails.
3. Tampered recommendation with changed payload hash fails.
4. Revoked consent fails.
5. Expired consent fails.
6. Missing approval on approval-gated action fails.

## Test command for local/CI confirmation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```

## Result

Sprint status: ETS role confirmed, proof/consent validation lane documented, default branch synchronized with this execution record.

## Next repo handoff

Christina should consume ETS verification results through SignalForge and render verified, unverified, quarantined, blocked, approved, rejected, and needs-context states in a human approval inbox.
