# Aetheris Guild Exchange: evidence and reward boundary

Status: **DRAFT design proposal, 2026-10-23. Not implemented or launch-approved.**

This proposal gives ETS-enabled game achievements an optional use in Aetheris
without treating exported gameplay as money or treating a valid proof as proof
of honest play. The names, economy details, and example rewards below are
recommended v1 design choices, not an existing service or commercial commitment.

## Product promise and non-goals

- Aetheris remains a complete offline adventure RPG: exploration, dungeons,
  builds, equipment, companions, and authored story outcomes. No story, ending,
  essential companion, or recovery route requires an account, online service,
  another game's purchase, or a cross-game achievement.
- Campaign gold and progression remain local to the campaign. They are not
  imported from another game's score, bankroll, or simulated winnings.
- The proposed online Guild Exchange may grant account-bound, nontransferable,
  noncash **Guild Marks** or direct entitlements for optional extras: guild
  cosmetics, supplementary lore, or nonessential challenge unlocks. No cash-out,
  player trading, wagering, or real-money value is proposed.
- Reward demonstrated mastery under a defined challenge policy, not raw match
  volume, farming, or simulated Blackjack winnings. Amounts, caps, achievements,
  and the catalog require separate product review before implementation.
- Offline imports may produce clearly labeled local souvenirs only. They never
  create a spendable shared balance, transferable entitlement, or later
  automatic credit. Online redemption and spending require the authority.

Start with **one source game, one achievement, one cosmetic**. A direct cosmetic
entitlement is enough to validate the end-to-end boundary before introducing a
general points balance. The implementation choice is deliberately open.

## Relationship to existing ETS guarantees

The existing [Chess SDK walkthrough](../../examples/sdk/chess/README.md)
demonstrates integrity and reproducibility of submitted telemetry, not that
every move occurred or that all moves were submitted. Its proof bundle is not
already an Aetheris redemption token.

Apply the existing
[evidence, standing, and consequence-custody boundary](../architecture/EVIDENCE_STANDING_CONSEQUENCE_CUSTODY.md):

| Layer | What it can establish | What it cannot establish alone |
| --- | --- | --- |
| Evidence integrity | Accepted canonical bytes match a digest, signature, chain, or verified log proof under stated trust assumptions | That the report is complete, gameplay was genuine, or a person played without assistance |
| Provenance | A configured key or issuer attested to the identified material | That the issuer is honest, uncompromised, or authorized for every reward |
| Gameplay validation | An approved server observed a qualifying event, or a bounded rules replay accepts the supplied state transitions | Human honesty, absence of bots, or events omitted before recording |
| Reward standing | Account, issuer, audience, challenge, rules, policy, limits, freshness, and unused eligibility permit this grant now | That a credit was actually committed |
| Consequence custody | The authoritative transaction prevents a grant or spend without current standing and records its outcome | Universal security outside the qualified build, policy, and threat model |

A hash chain or signature cannot upgrade a player-controlled narrative into
honest gameplay. An attacker can generate a consistent legal transcript. A
local client can be modified, its clock rolled back, and any bundled secret
extracted. **Never ship minting or trusted issuer secrets in a game client.**
Existing [local ETS modes](../security/local-vs-production-trust.md) are not
production reward authority. ETS inclusion and `standing_status=current_log`
must not be displayed as current reward entitlement.

## Trust boundaries and responsibilities

| Component | Responsibility and explicit limit |
| --- | --- |
| Source game client | Displays the challenge, records observations, and requests or exports a claim; untrusted for outcome, identity, reward amount, time, and balance |
| Approved source-game service | Owns canonical event identity and account binding; observes authoritative gameplay where available; attests only within its registered game and challenge scope |
| ETS evidence layer | Preserves and verifies the selected evidence material and its provenance; does not decide reward eligibility or mint currency |
| Guild Exchange authority | Authenticates the redeeming account, validates evidence and gameplay policy, computes rewards, enforces uniqueness and caps, and commits grants and spends |
| Aetheris client | Displays authority-issued entitlements when online; local caches and save files cannot authorize a grant, transfer, or spend |
| Operator/reviewer | Manages issuers, rules, revocation, incidents, reconciliation, and corrections through separately authorized, audited operations |

If a game has only an offline client transcript and no trusted observation, its
profile must say so. It cannot receive shared rewards merely because a local
hash or client signature verifies. A future bounded replay-based profile needs
an explicit risk review, a server-issued challenge, and limits appropriate to
the fact that legal replay still does not prove honest human play.

## Proposed claim contract (not an API or schema release)

Treat every exported package as an untrusted **CLAIM**. The following are
requirements for a future versioned contract, not new fields in the existing
ETS core schema:

- Explicit type, format version, environment, destination audience, source game,
  trusted issuer identifier, and issuer key identifier.
- Pseudonymous source account binding and an authenticated destination-account
  linkage. Account linkage must require proof of control; a submitted username
  or editable account ID is not sufficient.
- Canonical source event ID, achievement family and instance, rules/build
  version, reward-policy version, and applicable server challenge reference.
- Challenge issuance and expiry from the authoritative service, bound to the
  account, game, rules, audience, and environment. A challenge nonce provides
  freshness and binding; it is not evidence of human play by itself.
- Evidence digest and bounded proof references; the accepted observation or
  deterministic rules-replay profile and its limitations; attestation time and
  expiry under a defined clock-skew policy.
- A signature or authenticated server retrieval mechanism whose keys and
  algorithm policy are configured independently of the submitted package.

The claim must not supply a trusted reward amount, price, balance, authority
role, arbitrary key URL, or executable validation logic. A claimed amount can
be ignored or rejected; only the server's approved policy computes a grant.
Do not place personal information, raw gameplay recordings, or account tokens
in public transparency records.

## Redemption state machine

The proposed flow is `received -> rejected | pending -> credited`, with
explicit terminal results and a stable receipt for an already credited claim.
Pending verification is not spendable credit.

1. **Bounded intake.** Authenticate and rate-limit the request. Limit package
   bytes, decompressed bytes, item count, nesting depth, string length, proof
   size, CPU, and validation time. Reject unsupported schemas, duplicate JSON
   keys, ambiguous encodings, unsafe archive paths, and unexpected fields.
   Parse data only: never execute imported code or follow arbitrary remote
   references. Any approved evidence retrieval uses allowlisted destinations
   and SSRF-safe transport. Quarantine malformed inputs without leaking data.
2. **Validate provenance.** Resolve the issuer from a server-managed allowlist;
   enforce its game, audience, environment, key scope, algorithm, validity
   window, and current revocation state. Verify canonicalization, signature,
   digest, chain, and log proofs required by that profile. An unknown or
   compromised issuer is not rescued by a mathematically valid signature.
3. **Bind the account and source event.** Verify authenticated account linkage.
   Resolve the source event from the approved service or retained authoritative
   record, not merely from its client-supplied ID. Match achievement, rules,
   challenge, destination, and event state. Reject cancelled or superseded
   events under the applicable policy.
4. **Validate gameplay.** Require the selected profile's server observation or
   approved bounded rules replay and relevant server challenge. Record the
   verifier version, inputs, findings, and remaining uncertainty. Evidence
   inclusion alone does not satisfy this step.
5. **Evaluate standing.** Apply current issuer/key status, account eligibility,
   award schedule, policy version, semantic uniqueness, and account/game/global
   caps. Freeze or reject when a required predicate cannot be established.
6. **Consume and credit atomically.** In one authoritative transaction, recheck
   mutable standing, reserve the unique eligibility keys, consume the claim,
   debit the applicable issuance budget, and credit the account or entitlement.
   Concurrent or repeated requests return the original committed result, not
   another award. A failure commits neither the consumption nor the credit.
7. **Record and reconcile.** Persist an immutable transaction identifier,
   evaluated policy and authority epoch, evidence reference, computed grant,
   balance/entitlement result, and reason. Publish any ETS audit receipt through
   a durable outbox with idempotent delivery; retrying publication must never
   repeat the reward. A receipt is evidence of a transaction, not a second
   bearer instrument.

Server-side authorization at execution time and binding authorization to the
specific transaction are informed by
[OWASP Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html).

### Two kinds of uniqueness

Transport idempotency is necessary but insufficient. Fresh export IDs, new
signatures, different encodings, or repeated ETS submissions must not turn the
same achievement into a new entitlement.

- Enforce canonical source-event consumption across re-exports and across
  accounts. The service owns the source-event identity and validates it.
- Separately enforce semantic achievement eligibility, for example
  `(destination account, source game, achievement family, eligibility window)`.
  A once-per-account achievement has a lifetime window. Any repeatable window
  must be an explicit product policy, not a client-selected value.
- A rules version, key rotation, account unlink/relink, or reward-policy change
  does not reset eligibility unless an authorized migration explicitly grants
  a new, separately audited entitlement.
- Store uniqueness in durable database constraints, not only in memory or
  request middleware. A retry with the same idempotency key but a different
  payload is a conflict, not an update.

The business-invariant approach, atomic critical sections, and independent
server calculation are informed by
[OWASP Business Logic Security](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html).

## Spending, recovery, and incident limits

Every spend is online and authoritative. Authenticate the account, recheck item
availability and entitlement, derive the price server-side, then atomically
enforce a nonnegative balance and apply a unique purchase/entitlement result.
Concurrent requests, negative quantities, overflow, retries, local save edits,
or older cached balances must not permit overspending or repeated delivery.

Use per-game issuance ceilings and account limits even for valid issuers, plus
an independently controlled circuit breaker. Issuer compromise can produce
valid-looking lies: quarantine that issuer, revoke keys, stop new grants,
preserve evidence, and review affected transactions. Revocation and budget
updates must be serialized with grants or checked through a transactional
authority epoch so a stale precheck cannot race the credit.

Backups, restore, and failover must preserve consumed-event records, semantic
eligibility, budgets, balances, purchases, and audit/outbox state together.
Reconcile ledger totals and entitlements before reopening redemption after a
rollback; a stale restored database must not remint prior awards. Corrections
are authorized, append-only adjustments referencing the original transaction,
with reasons and review history, not silent deletion or rewriting of evidence.
Define fair handling and an appeal path for affected players before launch.

## Privacy and honest labels

Minimize retained personal data. Prefer scoped pseudonymous IDs and necessary
digests; hashes and pseudonyms can still reveal relationships and are not
automatically anonymous. Keep account-link mapping and raw replay material
access-controlled with explicit retention/deletion rules. Never publish a raw
replay without informed consent. Sanitized public reports should identify the
tested build and invariants, not expose players' data.

Keep UI labels distinct: **imported local souvenir**, **claim pending**,
**evidence verified**, **reward approved**, **credited**, and **rejected**.
Do not use a single green "verified" badge for all these meanings.

## Qualification and decisions still required

Before any shared reward launch, require a threat model, approved issuer and
identity model, reviewed claim schema, bounded parser, account-link protocol,
transactional storage design, key custody/revocation plan, incident controls,
restore/reconciliation evidence, privacy review, and published reward policy.
Test the actual validation and transaction code, not a substitute mock, in the
isolated [Aetheris Crucible draft](../security/AETHERIS_CRUCIBLE_DRAFT.md).

Minimum evidence includes a valid one-time award and spend, every negative and
concurrent control in that draft, and recovery without duplicate credit. Keep
rejected and inconclusive findings visible. Neither a successful demonstration
nor an open challenge proves the system secure or unhackable.

No blockchain or JWT is required by this proposal. Choose a minimal reviewed
protocol. If JWT is selected, follow
[RFC 8725](https://www.rfc-editor.org/rfc/rfc8725), including fixed algorithm
policy, issuer/audience validation, explicit token typing, and separation of
validation rules for different token purposes; a JWT alone is not anti-replay
or a ledger. Protocol and deployment approval remain separate work.

## Repository ownership

- EchoMedia owns the PC narrative and Academy-to-PC product integration contract.
- Lantern-Protocol/aetheris retains its separate Living Covenant RPG prototype
  and alignment/design discussion; this document does not merge the games.
- ETS owns the evidence vocabulary and this proposed verification boundary.
- The future Guild Exchange authority owns entitlement decisions and balances;
  its placement and deployment are not selected by this documentation change.

This proposal preserves the PC Watchtower Mystery's Publish or Seal decision
and does not convert Aetheris into a governance dashboard. Cross-game extras
support adventuring; they do not replace the campaign.
