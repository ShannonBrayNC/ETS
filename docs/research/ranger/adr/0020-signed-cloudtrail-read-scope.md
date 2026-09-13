# ADR 0020: Require a Signed CloudTrail Read Scope for Controlled Qualification

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0016, ADR 0017, ADR 0018, ADR 0019

## Context

ADR 0019 deliberately restricted the credential-isolated CloudTrail capture adapter to simulation.
The earlier AWS execution authorization establishes authority for the Object Lock qualification
sequence, not for later CloudTrail and S3 reads. Treating that execution authority as implicit
permission to enumerate keys, inspect selector configuration, or retrieve digest and log objects
would conflate separate effects and leave an avoidable authority gap.

## Decision

Add `ets.ranger.aws-cloudtrail-read-authorization.v1`, an Ed25519-signed, separately configured
read-scope manifest. It binds all of the following before the adapter receives either injected
client:

- the complete base execution-authorization record digest, base authorization ID, complete
  execution-receipt digest, receipt ID, and the exact Object Lock capture-plan digest;
- the exact canonical CloudTrail capture-plan digest, qualification ID, verifier challenge,
  environment, partition, account, Region, trail, digest location, public-key pins, evidence
  window, file/count/byte bounds, and event-time skew;
- the sole permitted operation profile: `ListPublicKeys`, `GetEventSelectors`, and `GetObject`;
  exactly two CloudTrail calls and no more S3 reads than the signed digest plus log-file limit;
- a validity interval, configured authorizer identity/key, canonical manifest digest, signature,
  and a bounded cost ceiling; and
- explicit cloud-read and spending assertions for `authorized_non_production` only.

An independently supplied policy pins the expected scope and base identities, challenge,
environment, authorizer and public key, verification time, lifetime, and cost limit. The extension
cannot choose its own trust anchor, freshness time, or budget ceiling. It must not become valid
before its bound execution receipt was issued.

The adapter verifies the existing execution receipt first and then verifies the exact signed read
scope before every injected CloudTrail or S3 client invocation. Simulation scopes keep cloud-read
and spending assertions false and still require explicitly marked test doubles. An
`authorized_non_production` scope requires both assertions to be true; it may use caller-injected
live-capable clients, but this module still neither creates nor discovers credentials and makes no
AWS call by itself.

## Consequences

- A missing, stale, future, forged, over-budget, wrong-key, altered-plan, altered-receipt,
  cross-account/Region, or pre-receipt scope fails before provider access.
- The capture bundle retains the signed-scope ID and complete-record digest alongside its provider
  observations; the signed manifest itself must be retained as a separate authorization artifact
  for reconstruction.
- The scope authorizes an intent under a configured key. It does not prove signer human identity,
  independent budget approval, effective AWS permissions, client identity, provider execution,
  selector continuity, CloudTrail completeness, physical custody, or physical Ranger outcome.
- ETS Core canonicalization and Gateway real-time behavior remain unchanged.

## Threat treatment

| Threat | Mitigation and detection | Required evidence / test |
| --- | --- | --- |
| Read-scope, receipt, or plan substitution | Canonical digests bind each record; configured key and policy verify before calls. | Complete signed scope, execution receipt, both plans, and substitution tests showing zero client calls. |
| Replay or premature read authority | Policy verification time, bounded lifetime, and receipt-before-read start are enforced. | Scope timestamps, policy inputs, receipt timestamp, and stale/pre-receipt rejection tests. |
| Broadened CloudTrail or S3 access | Fixed operation profile and exact call maxima bind the digest plus bounded referenced logs only. | Signed scope, capture plan, client-call assertions, and source review of injected interfaces. |
| Client or credential substitution | The module accepts no credential configuration; simulation requires marked stubs; live client identity remains unproven. | Caller-controlled identity evidence for a live trial; simulation marker-rejection tests. |
| False provider or selector claims | Key/selector observations remain explicit observations and retain their existing nonclaims. | Captured bytes, ADR 0018 verifier result, and independent trust-anchor/coverage evidence where available. |

## Rejected alternatives

### Reuse the Object Lock execution authorization unchanged

Rejected because it does not describe the CloudTrail trail, digest object, trust pins, read bounds,
or read-specific cost and validity constraints.

### Permit live injected clients whenever the base execution is non-production

Rejected because a live-capable client alone does not establish authority for the additional
provider reads or their scope.

### Embed credentials or an AWS SDK configuration in the evidence adapter

Rejected because it expands the trust boundary, increases accidental-execution risk, and mixes
credential selection with canonical evidence reconstruction.
