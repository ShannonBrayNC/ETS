# ETS Threat Model

ETS is designed to detect tampering with recorded evidence metadata and proof
artifacts. It does not prove that an omitted real-world event happened unless a
workflow completeness policy exists.

## Threats And Status

- Evidence tampering: mitigated by canonical event hashes and proof validation.
- Record deletion: detectable through tree-head checkpoints, size changes, and
  future witness publication.
- Log forking: RC fork simulation detects conflicting roots for the same size.
- Selective disclosure: content-proof separation avoids publishing raw content.
- Metadata leakage: mitigated by redaction profiles and audit-log hygiene.
- Tenant leakage: scoped lookup/list/proof routes avoid cross-tenant data return.
- Missing-event attacks: documented and partially explored through omission
  detection experiments; not overclaimed as proof-of-completeness.
- API abuse: local request limits exist; hosted rate limiting remains future.
- Asynchronous network adversaries: bounded seeded simulations exist for delay
  and packet loss, but ETS does not prove Internet-scale liveness.
- Byzantine consensus adversaries: ETS can report root disagreement and quorum
  policy results, but it does not prove BFT safety or liveness.
- Governance disputes: deterministic escalation semantics exist, but legal,
  organizational, and ethical decisions remain external controls.
