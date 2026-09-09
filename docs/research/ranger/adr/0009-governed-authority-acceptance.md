# ADR 0009: Compose Governance Proofs into Governed Authority Acceptance

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-08
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

ADR 0008 added independent administrative-approval and trusted-time evidence primitives. Those
primitives intentionally did not change the acceptance semantics of
`ets.ranger.key-authority-event.v1`. A verifier could prove that an administrator approved a
request and that a configured time authority attested to evidence, but the stronger claims were not
yet composed with a concrete authority event.

Changing the legacy authority-event schema or verifier in place would retroactively strengthen the
meaning of already retained evidence and break versioned claim boundaries.

## Decision

Add `ets.ranger.governed-authority-acceptance.v1` as a deterministic composition profile.

The stronger verifier requires:

1. a valid complete authority history ending at the accepted event;
2. a valid configured-administrator approval of that event's exact key-binding request;
3. valid configured-time evidence over the approval;
4. valid configured-time evidence over the accepted authority-event digest;
5. one configured time-authority identity/key across both attestations; and
6. non-overlapping bounded intervals proving approval preceded authority acceptance.

The acceptance manifest receives a canonical digest but no new independent signature. The signed
authority event, administrator approval, and time attestations remain the cryptographic evidence.
The manifest is a deterministic binding and presentation surface for those proofs.

Keep legacy authority verification unchanged.

## Consequences

- A valid legacy authority event remains valid only under its original weaker claim boundary.
- A governed acceptance can explicitly report authenticated-administration and configured
  trusted-time claims without mutating the legacy event.
- Request substitution, event substitution, time-authority substitution, and ambiguous temporal
  ordering fail closed.
- The ordering proof is relative to one configured time authority and its uncertainty intervals; it
  is not a claim of globally correct UTC.
- The manifest itself is not an independent custody boundary. External immutable publication and
  rollback-resistant retained heads remain separate work.
- ETS Fleet authorization, administrative independence, hardware-backed key custody, semantic
  truth, completeness, and physical outcome remain unproven.

## Rejected alternatives

### Add governance fields to the legacy authority event

Rejected because it would silently change a versioned evidence contract and blur historical claim
semantics.

### Accept overlapping time intervals

Rejected because observed timestamps alone do not prove that approval preceded authority
acceptance when their stated uncertainty windows overlap.

### Sign the composition manifest with the authority key again

Deferred. The underlying authority event is already authority-signed, and the administrator/time
proofs are independently signed. A second signature would add another lifecycle and custody problem
without yet creating an independent trust boundary.

## Follow-on

The next retained-verification profile should require trusted-time attestations for retained
authority-head and authority-bound custody receipts. After that, R0.2 should address external
immutable publication, rollback-resistant latest-head custody, encrypted storage, and hardware-
backed identities.
