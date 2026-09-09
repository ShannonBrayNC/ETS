# Ranger R0.2 Governed Authority Acceptance

**Status:** executable verifier composition; stronger than legacy authority-history verification but
still registry/configuration relative

**Profile:** `ets.ranger.governed-authority-acceptance.v1`

**Tracks:** #605

## Objective

Require cryptographic evidence of administrative approval and configured trusted time before a
Ranger key-authority event can be presented under the stronger governed-acceptance claim.

The legacy `ets.ranger.key-authority-event.v1` contract remains unchanged. A legacy event is still
valid under its original authority-relative claim boundary. The governed profile is an additive
composition layer that requires more evidence before reporting stronger claims.

## Required evidence

A governed acceptance is built only from:

1. the complete authority-event history through the accepted event;
2. the existing signed authority event at the history head;
3. a valid `ets.ranger.administrative-approval.v1` over that event's exact key-binding request;
4. a valid `ets.ranger.trusted-time-attestation.v1` over the administrative approval digest; and
5. a second valid trusted-time attestation over the accepted authority-event digest.

Both time attestations must verify under the same configured time-authority key, source identity,
and signing-key identity.

## Temporal ordering rule

Each trusted-time attestation defines a bounded interval:

`observed_at_utc ± uncertainty_ms`

The governed profile requires the approval interval to end no later than the authority-event
interval begins. If the intervals overlap or invert, the verifier cannot prove that administrative
approval preceded authority acceptance and the stronger profile fails closed.

This does not prove globally correct UTC. It proves ordering only relative to the configured
time-authority evidence and its stated uncertainty.

## Acceptance manifest

`RangerGovernedAuthorityAcceptance` is a deterministic composition manifest. It binds:

- authority sequence and authority-event digest;
- canonical key-binding request digest;
- administrative approval digest;
- both trusted-time attestation digests;
- Ranger vehicle, tenant, and workspace scope;
- authority, administrator, and time-source identities;
- the bounded approval and acceptance intervals; and
- explicit positive and negative claim flags.

The manifest has a canonical SHA-256 digest, but it is not a new independent signature. Its stronger
claims come from successful verification of the referenced signed authority event, administrator
approval, and time attestations. Recomputing the manifest digest cannot manufacture those signed
inputs.

## Positive claims

A valid governed acceptance proves, relative to the configured keys and complete presented
authority history:

- authority-history integrity through the accepted event;
- authority acceptance of the exact key-binding request;
- configured administrator-key approval of that exact request;
- configured time-authority evidence for the approval and accepted event; and
- non-overlapping bounded intervals proving approval preceded acceptance.

## Explicitly unproven

The profile does **not** prove:

- human identity behind the administrator key;
- administrative independence;
- ETS Fleet operational authorization;
- global authority-history currentness;
- global UTC correctness or time-source independence;
- complete capture;
- semantic truth;
- actuator response; or
- physical outcome.

## Fail-closed conditions

The verifier rejects the stronger profile when any of the following occurs:

- authority history is invalid, truncated, reordered, forked, or signed by the wrong authority;
- approval targets a different request, scope, event kind, or administrator key;
- approval-time evidence targets a different approval;
- authority-event time evidence targets a different event or subject kind;
- either time signature is invalid;
- the two time attestations do not use the same configured time authority; or
- the bounded intervals overlap or invert.

## Architecture boundary

ETS Fleet remains the operational authorization plane. Gateway remains outside the real-time safety
loop. The governed verifier strengthens evidence about how an authority decision was approved and
timed; it does not authorize Ranger motion or change command, actuator, or physical-outcome
semantics.

## Next sequential slice

Require configured trusted-time evidence for retained authority-head and authority-bound custody
receipts in a stronger retained-verification profile, then evaluate immutable external publication
and rollback-resistant latest-head custody. Hardware-backed administrator, authority, registry, and
time keys remain production work.
