# ETS AI Witness Threat Model

## Protected properties

1. Raw AI content is not retained by the base witness record.
2. A signed record cannot be modified without invalidating its digest/signature.
3. Session records cannot be silently reordered, duplicated, or removed from a supplied contiguous chain without chain verification failing.
4. Model/tool/human roles remain distinct; a proposed model action is not recorded as executed authority.
5. ETS projection uses stable Core semantics and cannot redefine proof behavior.

## Threats and controls

| Threat | Primary control |
|---|---|
| Prompt/output PII leakage into immutable evidence | `digest_only`, strict schema, no raw-content fields |
| Prompt injection causes dangerous tool action | tool disposition, requested scopes, policy reference, separate execution/result observation |
| Excessive agent privilege | scope evidence + external authorization boundary; witness does not grant authority |
| Faked model/provider metadata | signed observation preserves what was reported/observed but does not claim source truth; future authenticated provider adapter |
| Record tampering | canonical SHA-256 + Ed25519 signature |
| Record deletion/reordering in supplied session chain | sequence + previous-record digest |
| Duplicate/replay event | per-session `(session_id,event_id)` uniqueness and sequence enforcement |
| Signing-key compromise | purpose-separated key IDs; hardware-backed non-exportable keys and revocation policy required for higher assurance |
| Witness bypass/disablement | out-of-band health/gap evidence required in durable runtime; no completeness claim in v1 |
| Malicious/oversized metadata | strict bounded fields and collection lengths |
| Trace identifier injection | fixed-size hexadecimal trace/span validation |
| Policy spoofing | policy refs are evidence references, not authority; policy engine remains separate |
| Tool argument/result exfiltration | digests only; raw arguments/results excluded |
| Compromised witness software | Secure Boot, signed updates, measured/hardware-attested boot for future appliance profile |

## OWASP / MITRE coverage

The witness is evidence infrastructure supporting detection, investigation, and post-incident reconstruction for prompt injection, sensitive information disclosure, supply-chain change, improper output handling, excessive agency, poisoned retrieval/context, and agent/tool misuse. It does not replace prevention controls such as least privilege, capability allowlists, sandboxing, output validation, model/provider authentication, or red teaming.

## Residual risks

- A compromised source can lie before the witness receives metadata.
- A bypassed witness can miss events; cryptography cannot prove completeness without an independent expectation/observer boundary.
- Hashes can reveal equality and may enable guessing attacks against low-entropy content; tenants should salt/tokenize before hashing where equality leakage is unacceptable, with an explicit transformation profile.
- Software signing keys are not sufficient for a high-assurance physical appliance claim.
- Wall-clock accuracy remains dependent on configured time sources and should be represented by clock-quality state.
