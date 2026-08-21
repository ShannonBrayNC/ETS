# ETS AI Witness Test Plan

## Automated unit gates

The initial reference suite verifies:

1. Strict schema rejects undeclared raw prompt fields.
2. Model requests fail validation when required input digest evidence is absent.
3. Signed records verify with the correct Ed25519 key.
4. ETS `EvidenceEvent` projection binds the witness record digest and advertises the digest-only redaction profile.
5. Raw prompt content used to compute a test digest does not appear in the projected ETS event.
6. Two-record session chains verify when contiguous.
7. Previous-digest tampering invalidates the chain.
8. Non-contiguous sequence numbers fail closed.
9. Duplicate event identities fail closed.
10. Verification under the wrong public key fails.

## CI commands

```bash
python -m pytest tests/unit/test_ai_witness.py -q
python -m compileall -q ets/ai_witness
ruff check ets/ai_witness tests/unit/test_ai_witness.py
mypy ets/ai_witness
```

The repository's normal full CI/security/formal checks remain authoritative for merge. The local construction harness used during development executed the witness unit suite successfully at 6/6 tests and compiled the package; GitHub CI must additionally run the repository-pinned Ruff/Mypy/security checks.

## Follow-on appliance qualification

Before a physical pilot claim, add:

- TPM/non-exportable key tests and key rotation/revocation tests;
- secure-boot/measured-boot evidence collection;
- power-loss and filesystem-corruption recovery;
- seven-day bounded offline queue/replay;
- authenticated adapter tests for supported AI providers/runtimes;
- OpenTelemetry GenAI adapter conformance/minimization tests;
- clock rollback/skew tests;
- backpressure/queue saturation tests;
- witness bypass/gap detection;
- update signing/rollback/recovery tests;
- fuzz/property tests for schema, chain, canonicalization, and adapter boundaries;
- performance benchmarks with content hashing and signature overhead measured separately.

## Acceptance boundary

Passing this suite establishes the software reference contract only. It does not establish production availability, observation completeness, hardware tamper resistance, legal compliance, model correctness, or safety of an observed agent action.
