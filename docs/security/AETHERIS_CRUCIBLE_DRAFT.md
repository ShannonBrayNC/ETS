# Aetheris Crucible: isolated reward-security challenge proposal

Status: **DRAFT ONLY — not active testing authorization, not a live program,
not a bounty offer, and not a promise of legal safe harbor.**

This document proposes a bounded way to challenge the future
[Guild Exchange](../integrations/AETHERIS_GUILD_EXCHANGE.md). It does not
authorize testing any existing ETS, Aetheris, production, third-party, or
other-player system. No challenge endpoints are currently listed as in scope.

## Purpose

Exercise the real validation, uniqueness, credit, and spending code under
adversarial inputs while keeping the consequences synthetic. The useful
outcome is reproducible evidence about particular invariants and fixes, not a
claim that participation or a period without findings "proves security."

The name refers to this proposed Aetheris reward sandbox. It does not expand
the authorization or scope of any other project named Crucible.

## Activation gate: owners must complete this before inviting tests

An authorized owner must publish a separate, dated activation policy that
specifies all of the following. Until then, the challenge remains inactive.

| Required item | Current state |
| --- | --- |
| Exact sandbox hostnames, routes, downloadable build hashes, and permitted versions | Not designated |
| Named operator and verified authority to authorize testing of every included component | Not designated |
| Start/end times, participant access, test-account allocation, rate and concurrency budgets | Not designated |
| Allowed test cases, explicit exclusions, stop conditions, and emergency contact | Proposed below; not activated |
| Private report channel, acknowledgement expectations, disclosure coordination, and retention rules | Not designated |
| Any safe-harbor terms and bounty/reward terms, if separately approved | None offered by this draft |

The scope should identify only operator-controlled assets whose testing can be
authorized. Linked infrastructure and vendor services are not implicitly in
scope. This scope discipline is informed by the
[CISA vulnerability disclosure policy template](https://github.com/cisagov/cyber.dhs.gov/blob/master/pages/20-01-vdp-template.md).
Its federal-agency obligations are not adopted as obligations for this game.

## Isolation requirements

- Use the intended validation and ledger implementation at a pinned build,
  with sandbox configuration and documented differences from any later
  production deployment. Do not quietly substitute permissive mock logic.
- Use isolated issuer keys, signing keys, accounts, storage, evidence logs,
  service identities, and synthetic data. Production credentials and player
  records must never be present.
- Mark the environment in every challenge, claim, receipt, and key policy.
  Production validators must reject sandbox artifacts, and vice versa.
- Use fake balances and cosmetics with **no conversion to production currency,
  real value, or production entitlement**, including through exports, account
  linking, resets, migrations, or reconciliation.
- Provide two or more assigned synthetic accounts for cross-account controls,
  a deliberately scoped compromised-issuer fixture, and reset tooling. Reset
  privileges are separate from participant roles and fully logged.
- Bound concurrency, request volume, input size, resource use, and test duration;
  provide an operator kill switch and restore procedure. Resource-exhaustion
  studies require a separately approved isolated harness, not a public service.

## Proposed allowed tests after activation

Only assigned accounts and the explicitly listed sandbox targets would be used.
Each test needs a valid positive control and an expected ledger/evidence result.

| Test | Invariant to verify |
| --- | --- |
| Alter a claim, digest, proof, signature, audience, environment, or rules version | Invalid or wrong-scope material produces no credit |
| Submit an unknown/revoked key or issuer, or out-of-scope achievement | Cryptographic validity cannot bypass current issuer standing |
| Replay a claim, re-export it with a new ID/signature, or reorder retries | One canonical event and one semantic eligibility produce at most one award |
| Submit bounded simultaneous redemption requests | Consume, budget debit, and credit commit atomically exactly once |
| Submit bounded simultaneous purchases or stale balances | No negative balance, duplicate entitlement, or overspend |
| Attempt account substitution or redeem an assigned account's claim to another assigned account | Authenticated source/destination binding holds; no cross-account award |
| Use an expired, reused, wrong-account, or wrong-game server challenge | Freshness and challenge binding hold; a nonce alone is not gameplay proof |
| Supply a fabricated but internally legal gameplay transcript | The selected profile's observation requirements hold; legal rules replay is not labeled honest human play |
| Supply bounded malformed, ambiguous, oversized, or deeply nested packages | Parser/schema/resource limits fail safely without execution or arbitrary fetch |
| Restart or restore a controlled snapshot with operator assistance | Consumed events, semantic eligibility, balance, budgets, and outbox reconcile without reminting |
| Use the intentionally compromised sandbox issuer within fixture limits | Per-game cap and circuit breaker bound exposure; revocation blocks later grants |
| Race fixture revocation or budget exhaustion with a bounded grant | Mutable standing is checked at the binding transaction, not only at intake |
| Interrupt a response or audit-receipt delivery after commit | Retry returns the original transaction; audit publication never repeats credit |

Test implementations should also cover boundary values, arithmetic overflow,
negative quantities, policy migrations, and account unlink/relink without
resetting achievement eligibility. Details and safe load limits must be part of
the activated test plan, not inferred from this table.

## Explicit exclusions

Production systems, production keys, other players, unassigned accounts,
third-party services, payment systems, and unrelated ETS/Lantern applications
are out of scope. No phishing, social engineering, credential theft, persistence,
lateral movement, data exfiltration, malware, denial of service, or disruptive
high-volume activity is proposed or authorized. Discovery of a link or shared
dependency does not authorize following it into another system.

If an unexpected production connection, real credential, sensitive record, or
service disruption appears, stop the test and report through the activated
private channel. Preserve only the minimum evidence needed; do not publish
secrets or player data. Unclear scope requires owner clarification before
testing, not an assumption of permission.

## Reporting and retest record

Each report should identify:

1. Scope-policy version, sandbox build/commit and configuration, test window,
   assigned synthetic identities, and allowed test case.
2. Security invariant, prerequisites, sanitized input/evidence references,
   minimal reproduction, expected result, and observed result.
3. Ledger and entitlement state before/after, transaction IDs, verification
   decisions, and whether an unauthorized consequence actually bound.
4. Impact within the tested scope, uncertainty, untested paths, and suggested
   mitigation; do not generalize to production without evidence.
5. Triage, fix commit, regression test, exact-build retest outcome, and remaining
   risk. Distinguish fixed, not reproduced, inconclusive, and accepted risk.

Publish a sanitized summary only under the approved disclosure process, with
reporter consent for attribution and informed consent for any raw replay
publication. Reports should say "these controls passed on this build under
these conditions," not "unhackable" or "security proven." This draft activates
no public challenge and performs no attacks.
