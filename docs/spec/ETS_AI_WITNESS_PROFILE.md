# ETS AI Witness Profile v1

Status: implementation candidate
Profile identifier: `ets.ai-witness.profile.v1`
Date: 2026-08-21

## 1. Purpose

ETS AI Witness is an evidence-producing device/service boundary for observing AI and agentic system activity without becoming the AI decision-maker. It creates independently verifiable evidence describing which model/workload was observed, which hashed inputs and outputs participated, which retrieval/tool/policy/human-oversight events occurred, and how those observations were chained and attested.

AI Witness is not a model firewall, prompt-injection detector, model evaluator, fairness oracle, content moderation engine, SIEM, autonomous remediation engine, or proof that all AI activity was observed.

## 2. External requirements baseline

The v1 design is informed by:

- NIST AI RMF 1.0 and NIST AI 600-1 Generative AI Profile: provenance, data/content lineage, evaluation of data/content flows, and lifecycle risk management.
- EU AI Act Regulation (EU) 2024/1689 Articles 12 and 19: automatic event logging for high-risk systems and retention of automatically generated logs where under provider control.
- OpenTelemetry GenAI semantic conventions: model/provider/operation, input/output message, retrieval, and trace correlation concepts; input/output content is explicitly treated as potentially sensitive.
- OWASP GenAI/LLM Top 10 2026: prompt injection, sensitive-information disclosure, supply-chain, improper output handling, and excessive-agency risks.
- MITRE ATLAS: adversary tactics and techniques targeting predictive, generative, and agentic AI systems.

These references shape collection fields and threat coverage. ETS does not claim conformance or certification merely by implementing this profile.

## 3. Normative requirements

### Evidence and privacy

- **AIW-001 MUST** default to `digest_only` capture.
- **AIW-002 MUST NOT** retain raw prompts, raw model output, raw retrieved documents, raw tool arguments, or raw tool results in the base v1 record.
- **AIW-003 MUST** use SHA-256 digest references for content-bearing material.
- **AIW-004 MUST** preserve byte length/media type/source reference only when supplied and policy-permitted.
- **AIW-005 MUST** reject undeclared fields in normative records.
- **AIW-006 MUST NOT** infer that a digest proves semantic truth, correctness, fairness, safety, or completeness.

### Identity and provenance

- **AIW-010 MUST** identify the witness, AI session, event, workload, sequence, occurrence time, and witness observation time.
- **AIW-011 MUST** preserve model provider and model identifier for model request/response events.
- **AIW-012 SHOULD** preserve model revision/deployment reference when exposed by the provider.
- **AIW-013 SHOULD** preserve W3C/OpenTelemetry-compatible trace and span identifiers when available.
- **AIW-014 MUST** separate source/model identity from witness device identity.

### AI execution context

- **AIW-020 MUST** support session start/end, model request/response, retrieval, tool call, human decision, and action result event classes.
- **AIW-021 MUST** require at least one input digest for `model_request`.
- **AIW-022 MUST** require at least one output digest for `model_response`.
- **AIW-023 MUST** require retrieval digest material for `retrieval` events.
- **AIW-024 MUST** capture bounded generation parameters only when supplied (temperature, top-p, seed, maximum output tokens).
- **AIW-025 SHOULD** capture the system-instruction digest separately when the provider exposes system instructions separately.
- **AIW-026 MUST** preserve policy references used to govern the invocation/action when available.

### Agent/tool activity

- **AIW-030 MUST** record tool name and a digest of the tool-call identifier and arguments for tool-call events.
- **AIW-031 SHOULD** record the tool version when available.
- **AIW-032 MUST** record tool disposition (`proposed`, `allowed`, `denied`, `executed`, or `failed`).
- **AIW-033 SHOULD** record requested capability scopes and authorization-policy reference.
- **AIW-034 SHOULD** record a digest of the tool result when a result exists.
- **AIW-035 MUST NOT** treat a model-generated tool request as proof that the action was authorized or executed.

### Human oversight

- **AIW-040 MUST** support explicit approved/denied/modified human decisions.
- **AIW-041 MUST** preserve a reviewer reference and MAY preserve a digest of the reason instead of raw reason text.
- **AIW-042 SHOULD** preserve the policy reference governing the review.

### Integrity and device attestation

- **AIW-050 MUST** deterministically canonicalize the signed record payload using the stable ETS Core canonicalization boundary.
- **AIW-051 MUST** SHA-256 hash the canonical signed-record payload.
- **AIW-052 MUST** bind every non-initial session record to the previous signed-record digest.
- **AIW-053 MUST** reject duplicate event identities within a session.
- **AIW-054 MUST** reject non-contiguous session sequence numbers.
- **AIW-055 MUST** sign each record with Ed25519 in the reference software profile.
- **AIW-056 MUST** fail verification on content, chain, signature, or key mismatch.
- **AIW-057 SHOULD** use purpose-separated hardware-backed signing keys for physical pilot/production-like devices.
- **AIW-058 MUST NOT** make a production hardware-attestation claim for the current software-key reference implementation.

### ETS integration

- **AIW-060 MUST** project witnessed observations through the stable ETS Core `EvidenceEvent` contract rather than fork hashing/Merkle/proof semantics.
- **AIW-061 MUST** use the witness record digest as the ETS content hash for the projected observation.
- **AIW-062 MUST** identify the redaction/minimization profile as `ets.ai-witness.digest-only.v1`.
- **AIW-063 MUST** preserve AI session correlation in the projected ETS event.
- **AIW-064 MUST NOT** allow the witness to rewrite ETS append history after commitment.

### Resource and failure behavior

- **AIW-070 MUST** bound identifiers, references, digest collections, scopes, and policy references.
- **AIW-071 MUST** fail closed on malformed cryptographic material.
- **AIW-072 MUST** fail closed when required event-kind context is absent.
- **AIW-073 SHOULD** support durable local queueing and later upstream synchronization in a physical device profile.
- **AIW-074 MUST** expose collection gaps/unknown state separately from successful observations in a future durable runtime; v1 in-memory records do not claim completeness.

## 4. Device profile recommendation

Pilot physical reference:

- x86-64 or ARM64 Linux appliance;
- 4+ CPU cores, 16 GiB RAM, 512 GB+ high-endurance NVMe;
- TPM 2.0 or approved equivalent for device/evidence signing keys;
- UEFI Secure Boot where the platform supports UEFI;
- management and workload-observation interfaces logically separated;
- default-deny inbound management policy;
- signed update/recovery path;
- local encrypted state and bounded offline queue;
- NTPv4/NTS where supported, with explicit clock-quality state.

An NVIDIA Jetson class device is appropriate only when local AI inference/inspection is intentionally added. The base Witness function is cryptographic capture and provenance; it does not require a GPU.

## 5. Claims boundary

A valid AI Witness record proves that a configured witness key attested to a specific bounded observation record and, for chained records, that the supplied record sequence is cryptographically linked. It does not prove that the model was correct, the action was safe, every invocation was captured, the source metadata was truthful, or the deployment complies with a law or standard.
