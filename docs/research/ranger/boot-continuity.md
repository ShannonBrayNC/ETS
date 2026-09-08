# Ranger R0.2 Clock-Qualified Boot Continuity

**Status:** executable software-reference contract; not trusted time or witnessed completeness

**Profile:** `ets.ranger.boot-checkpoint.v1`

**Tracks:** #605

## Objective

Link one boot-scoped Ranger custody chain to the next without pretending that a local clock is
externally trusted or that a locally retained head proves complete capture. The first custody
record of each participating boot is a signed checkpoint containing explicit clock source,
quality, and bounded uncertainty when one is available.

## Contract

A genesis checkpoint declares boot sequence one and has no predecessor. Each later checkpoint
binds the current vehicle, mission, boot identifier, boot sequence, recorded UTC start, clock
source and quality, and the prior boot identifier and signed custody-head digest. The checkpoint
is retained as the first source event in the new boot's ordinary signed custody chain.

`verify_boot_continuity` independently verifies both custody chains under the same expected
Ed25519 public key, then rejects missing checkpoints, identity changes, wrong predecessor heads,
changed signing-key identifiers, missing, duplicate, or reordered boot-sequence transitions, and
non-advancing recorded timestamps. A checkpoint is rejected anywhere except custody sequence one,
including when submitted through the generic append API. Stable-key verification is deliberate:
key rotation and revocation need a separately authorized handoff.

Clock semantics are explicit:

- `synchronized`, `estimated`, and `degraded` require a numeric uncertainty bound;
- `unknown` forbids a claimed uncertainty bound;
- the recorded timestamp must advance for continuity verification;
- no quality value converts the local record into proof of trusted external time.

## Threat coverage

| Threat | Attack surface | Impact | Existing mitigation / detection | Missing mitigation | Required evidence | Test strategy |
| --- | --- | --- | --- | --- | --- | --- |
| Boot identity substitution | Checkpoint fields or supplied chain selection | False cross-boot attribution | Signed vehicle, mission, boot, sequence, and predecessor binding; identity mismatch rejection | Hardware-rooted identity and measured boot | Both complete signed chains and expected public key | Substitute vehicle, mission, and previous boot identifiers |
| Deleted or substituted prior chain | Local database, export, or verifier input | A different history is presented as the predecessor | Current checkpoint names the exact verified prior signed head; the [verifier-retained profile](retained-checkpoints.md) records accepted heads separately | Replicated immutable checkpoint publication | Current checkpoint, prior chain, retained latest head, and expected keys | Delete a prior suffix or supply a different valid head |
| Clock or GNSS manipulation | Local wall clock, NTP/GNSS input, or clock-quality declaration | Misordered or falsely precise event time | Signed source, quality, uncertainty, and recorded-time order; unknown quality cannot claim a bound | Authenticated time, rollback-resistant state, and independent time witness | Clock-source identity, quality, bound, raw time evidence, and witness where available | Reject naive time, inconsistent quality/bounds, and non-advancing recorded time |
| Missing, duplicate, or reordered transition | Boot counter input or checkpoint ordering | Ambiguous supplied boot lineage | Checkpoint must be first and pairwise sequence must advance by exactly one | Hardware anti-rollback counter and durable mission registry | Adjacent checkpoints and retained sequence state | Try skipped, duplicate, reversed, and misplaced checkpoints |
| Replay of an otherwise valid pair or omitted historical boot | Verifier request or incomplete export | Old but valid lineage is presented as current | Pairwise verification alone cannot detect it; the verifier-retained profile rejects state older than its signed latest checkpoint | Authoritative multi-party latest-state discovery and hardware anti-rollback state | Registry history or separately retained latest checkpoint | Replay the same valid pair against a newer retained checkpoint |
| Signing-key or key-identity substitution | Public-key input, record envelope, or signer configuration | Unauthorized continuity or ambiguous key history | Both chains verify under one expected key and the signed key identifier must remain stable | Authorized rotation/revocation and trust-history evaluation | Trusted public key, signed key IDs, and handoff record when supported | Use a wrong key and reuse the correct key under a changed identifier |
| Compromised checkpoint producer | Ranger runtime or exported software key | False clock/head statements can still be validly signed | Explicit software-key and no-trusted-time claim boundaries | Non-exportable hardware key, measured boot, configuration provenance, and compromise response | Attestation, firmware/configuration digests, key history, and incident evidence | Deferred negative controls under the hardware-attestation profile |
| Current-chain suffix deletion | Local storage or export after checkpoint creation | Recent events disappear without an internal gap | A verifier-retained head detects truncation behind the retained record count | Replicated immutable checkpoint publication and expected-event policy | Later retained head or source completeness policy | Truncate current suffix before and after registry retention |

## Claim boundary

Successful verification proves that the provided chains are valid under the expected stable key
and stable key identifier, and that the new chain contains the stated link to the supplied prior
head. It does not prove
that either chain is complete, that the clock source is truthful, that the timestamp is externally
trusted, that a valid pair is fresh, that no intermediate boot existed, or that an external witness
retained either head. The separate verifier-retained profile can establish freshness only relative
to the registry state independently supplied to the verifier.

Gateway remains outside the real-time safety loop. Future Edge, Verifier, Witness, or Black Box
projection must preserve this source record and its limitations rather than upgrading its claims.
