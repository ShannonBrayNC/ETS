# ETS AI Witness

ETS AI Witness is a digest-first evidence observer for AI and agentic workloads. The v1 reference implementation records bounded metadata and SHA-256 digests for model inputs, outputs, retrieval material, tool calls, policy references, and human oversight decisions. It does not store raw prompts, raw model outputs, tool arguments, or retrieved content.

The reference `AIWitnessLedger` signs each observation with Ed25519 and maintains an independent hash chain per AI session. A signed record can be projected into the stable ETS `EvidenceEvent` contract and committed through the existing ETS transparency pipeline.

## Security boundary

- `content_capture` is fixed to `digest_only` in v1.
- Unknown fields are rejected by strict Pydantic contracts.
- Model request/response events require model identity and the relevant content digest.
- Tool calls capture argument/result digests, requested scopes, authorization policy reference, and disposition.
- Human decisions capture reviewer reference, disposition, policy reference, and optional reason digest.
- Session sequence numbers must be contiguous; duplicates and gaps fail closed.
- Each record binds the previous record digest and is signed with Ed25519.
- The base implementation makes no completeness, semantic-correctness, fairness, or regulatory-compliance claim.

## Software reference example

```python
from datetime import UTC, datetime
import hashlib

from ets.ai_witness import AIWitnessEvent, AIWitnessLedger, DigestRef, ModelIdentity, WitnessEventKind

prompt = b"customer supplied prompt"
ledger = AIWitnessLedger(
    witness_id="ets-aiw:demo-01",
    signing_key_id="aiw-demo-key-01",
    private_key_hex="<32-byte-ed25519-private-key-hex>",
)

event = AIWitnessEvent(
    witness_id="ets-aiw:demo-01",
    session_id="session-001",
    event_id="request-001",
    sequence=0,
    kind=WitnessEventKind.MODEL_REQUEST,
    workload_ref="workload:assistant-demo",
    occurred_at=datetime.now(UTC),
    observed_at=datetime.now(UTC),
    model=ModelIdentity(provider="provider", model="model-name"),
    input_digests=(DigestRef(digest=hashlib.sha256(prompt).hexdigest()),),
)

record = ledger.record(event)
assert ledger.verify_record(record, ledger.public_key_hex)
```

## Physical appliance pilot API

The physical pilot profile adds machine-assurance and durable-operation contracts without changing the base Witness event format.

The public package now exposes:

- `HardwareKeyEvidence` and `HardwareKeyPurpose` for purpose-separated TPM-backed signing and queue-sealing keys;
- `TPMAttestationEvidence` and `PCRMeasurement` for nonce-bound quote/event-log appraisal inputs;
- `BootEvidence` for Secure Boot and measured-boot state;
- `ClockEvidence` for time source, protocol, offset, uncertainty, and synchronization state;
- `RuntimeAdapterIdentity` for authenticated AI/runtime source identity and enrolled tenant/workspace scope;
- `FleetEnrollment` plus verifier-owned enrollment expectations for signed Gateway/fleet bindings;
- `UpdateManifest` plus verifier-owned update trust policy and target verification for signed, expiring, rollback-resistant pilot updates;
- `EncryptedWitnessQueue` for AES-256-GCM encrypted, SQLite/WAL durable buffering;
- `assess_pilot_readiness` for bounded policy evaluation of the supplied appliance evidence.

### TPM/provider boundary

The current `AIWitnessLedger` accepts raw Ed25519 private key bytes because it is the software reference implementation. The **physical pilot MUST NOT supply a production TPM private key as hex**. The appliance runtime must use a signer-provider boundary that performs signing inside hardware-backed/non-exportable key custody.

A second constraint is algorithm compatibility: the PC Client TPM profile guarantees interoperable ECDSA capability on mandatory NIST curves, while the current Witness record implementation is Ed25519-only. Ed25519 must therefore not be assumed to exist in a generic PC Client TPM. Sealing an Ed25519 private key and later exposing those bytes to Python would not satisfy the physical profile's non-exportable signing-key requirement.

Physical qualification is consequently gated on an algorithm-agile signed-record/signer-provider slice. The reference hardware baseline will use TPM-native ECDSA P-256 with SHA-256 unless a named qualification TPM demonstrates another approved native algorithm. Existing Ed25519 v1 records must remain independently verifiable after that extension.

Likewise, the software queue accepts 32-byte key material for deterministic CI testing. The physical pilot must derive/unseal that queue material from a purpose-separated TPM-sealed key and must not persist a plaintext queue key file.

### Qualification state

`assess_pilot_readiness` consumes evidence declarations; it is not itself a TPM quote verifier or RIM appraisal engine. A physical device becomes qualified only after the hardware test plan verifies the signer algorithm/capability, quote, nonce, PCR/event-log reconstruction, reference baseline, Secure Boot state, key attributes, power-loss behavior, update/recovery behavior, clock quality, enrollment, and soak results.

## Documentation

Software Witness v1:

- `docs/spec/ETS_AI_WITNESS_PROFILE.md`
- `docs/architecture/ETS_AI_WITNESS_ARCHITECTURE.md`
- `docs/security/ETS_AI_WITNESS_THREAT_MODEL.md`
- `docs/test/ETS_AI_WITNESS_TEST_PLAN.md`

Physical appliance pilot:

- `docs/spec/ETS_AI_WITNESS_APPLIANCE_PROFILE.md`
- `docs/architecture/ETS_AI_WITNESS_APPLIANCE_ARCHITECTURE.md`
- `docs/security/ETS_AI_WITNESS_APPLIANCE_THREAT_MODEL.md`
- `docs/test/ETS_AI_WITNESS_APPLIANCE_TEST_PLAN.md`
