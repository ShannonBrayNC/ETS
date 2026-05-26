# Lantern Injected Recommendation Tamper Demo

## Purpose

This demo shows why Lantern handoffs need ETS verification before Christina, OpsHelm, Content Engine, EchoLiving, or another downstream system acts on a recommendation.

The local script creates three recommendation paths:

1. A valid SignalForge recommendation with a matching ETS proof bundle and granted consent.
2. A forged recommendation with no proof bundle.
3. A tampered recommendation whose payload changed after notarization.

Only the valid recommendation should pass. The forged and tampered recommendations return machine-readable reason codes that a registry or approval inbox can use to quarantine or block the item.

## Run

```powershell
python scripts/run_lantern_tamper_demo.py
```

Expected outcomes:

| Scenario | Expected status | Expected reason code |
| --- | --- | --- |
| `valid` | `passed` | `ok` |
| `forged-missing-proof` | `quarantined` | `missing-proof` |
| `tampered-after-notarization` | `blocked` | `hash-mismatch` |

## API path

SignalForge or another local verifier can call:

```text
POST /api/v1/lantern/verify
```

The request includes:

- `source_event_id`
- `evidence_hash`
- `proof_bundle`
- `consent_event`
- `action_type`
- source trust and replay flags

The response includes `status`, `reasonCode`, `message`, and any matched proof or consent identifiers.

## Threat model

ETS verifies that the handoff payload hash, source event ID, proof bundle, consent event, approval state, and local trust flags are internally consistent. It catches missing proof, hash mismatch, revoked or expired consent, missing approval, untrusted source, and replay signals.

ETS does not prove that the recommendation text is factually correct, that every real-world source was complete, or that external systems captured all relevant context. Those remain source-system and governance responsibilities.
