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

## Example

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

See `docs/spec/ETS_AI_WITNESS_PROFILE.md`, `docs/architecture/ETS_AI_WITNESS_ARCHITECTURE.md`, `docs/security/ETS_AI_WITNESS_THREAT_MODEL.md`, and `docs/test/ETS_AI_WITNESS_TEST_PLAN.md`.
