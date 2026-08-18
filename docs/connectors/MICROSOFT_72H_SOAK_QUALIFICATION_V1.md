# Microsoft 72-Hour Soak Qualification v1

Parent: #309  
Hosted Azure qualification: #361  
SharePoint live connector: #390

## Purpose

This qualification demonstrates sustained Microsoft connector operation for one immutable ETS
release candidate without turning operational health into an ETS verification claim.

The soak is intentionally built from **short independent probes plus an offline aggregate**. A single
long-running CI process is not the system under test and is not required to remain alive for the full
window. Each probe is retained as an independent sanitized artifact so a CI interruption cannot erase
prior operational evidence or silently reset the soak clock.

## Release identity

Every probe in one qualification window must carry the same:

- ETS source SHA;
- immutable container image digest;
- connector instance ID;
- ETS tenant/workspace;
- authoritative Gateway source ID;
- Microsoft tenant and subscription ID; and
- Microsoft operational-health policy profile.

Any identity drift fails closed. An upgrade, rollback, connector recreation, subscription replacement,
or source/image change starts a new soak window unless the release qualification explicitly defines
and separately evaluates that transition.

## P0 policy

The checked-in profile is `config/qualification/microsoft-soak-p0-72h.json`.

It requires:

- at least 259,200 seconds of observed coverage;
- at least 73 retained probes;
- no probe interval greater than 5,400 seconds;
- Microsoft posture evaluation no more than 300 seconds from probe collection;
- `healthy` operational posture for every retained probe;
- zero terminal synchronization failures;
- successful independent ETS proof verification on every probe; and
- a healthy final operational posture.

The 90-minute maximum interval provides bounded scheduling tolerance around an hourly collection
cadence without treating an arbitrarily long monitoring gap as continuous soak evidence.

## Probe contract

One `ets.qualification.microsoft_soak_probe.v1` artifact records:

- exact source SHA and image digest;
- workflow/run correlation ID;
- collection timestamp;
- one complete `ets.connector.microsoft.operational_posture.v1` response;
- one bounded proof reference and the result of independent proof verification; and
- literal non-retention flags for reusable credentials and raw source payload.

A probe must not contain bearer tokens, Graph access tokens, client secrets, Key Vault private
material, raw SharePoint document content, or unrestricted Microsoft response bodies.

The operational posture remains authoritative for connector health. The soak harness does not
reimplement Microsoft subscription, lag, queue, authentication, or reconciliation policy.

## Probe execution sequence

A live probe should:

1. resolve the exact running ETS source/image identity;
2. call hosted `/health`, `/ready`, and `/version` through the existing qualification boundary;
3. fetch the read-only Microsoft operational posture for the server-authorized connector instance;
4. perform a bounded non-sensitive connector collection/reconciliation observation as defined by the
   live qualification environment;
5. obtain or create a non-sensitive ETS evidence/proof reference through the normal Gateway/Core
   path;
6. independently verify that proof using the existing verifier/package boundary;
7. construct one sanitized `MicrosoftSoakProbeV1`; and
8. upload that probe as an immutable run artifact.

A failed probe is evidence. Do not overwrite or delete it and restart the same soak clock merely to
produce a clean report.

## Aggregate qualification

`summarize_microsoft_soak()` consumes all retained probes for a candidate window, sorts them by
collection time, and fails closed on:

- duplicate probe timestamps;
- release/connector/subscription identity drift;
- stale operational-posture evaluation;
- insufficient total duration;
- insufficient probe count;
- an excessive probe interval;
- any degraded or failed Microsoft operational posture;
- any terminal synchronization failure; or
- any failed proof verification.

The output `ets.qualification.microsoft_soak_summary.v1` records coverage, probe counts, observed
health counts, proof/terminal-failure counts, blockers, and explicit nonclaim flags.

## Artifact retention and final report

The final #309 release report should reuse the structure of
`docs/test/ETS_INTEGRATED_PILOT_QUALIFICATION_REPORT.md`:

- immutable SUT identity;
- harness/policy identity;
- ordered probe inventory and retained artifact hashes;
- coverage/interval summary;
- Microsoft operational posture results;
- independent proof-verification results;
- defects/exclusions;
- residual risks and claim boundaries; and
- exact-head independent reviewer approval.

The final aggregate must be reproducible from the retained probe artifacts and checked-in policy.

## Relationship to fault injection

The 72-hour soak is a **steady-state release gate**. Controlled missed-notification, authorization,
throttling, queue, worker, delta-expiry, upgrade, rollback, and offboarding faults are qualified in
separate deterministic/live exercises. Those fault exercises must not be hidden inside the soak and
then averaged away as acceptable degradation.

If a real unexpected fault occurs during the soak, retain it and treat the affected probe as a soak
failure. Recovery evidence can still be valuable, but it does not retroactively convert that strict
P0 steady-state window into a pass.

## Nonclaims

A passing soak does not prove:

- Microsoft source truth;
- universal source or tenant completeness;
- legal admissibility;
- compliance certification;
- cross-region disaster recovery; or
- absence of defects outside the observed connector/Gateway/Core path.

`verification_claimed_by_soak`, `source_truth_claimed`, and `source_completeness_claimed` remain
literal `false` in the summary contract.
