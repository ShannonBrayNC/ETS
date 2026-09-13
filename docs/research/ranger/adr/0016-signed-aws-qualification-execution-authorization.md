# ADR 0016: Require Signed Authorization Before AWS Qualification Capture

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0014, ADR 0015

## Context

The credential-isolated capture adapter accepts bounded inputs and minimal injected clients, but a
bounded plan is not evidence that anyone authorized its execution. Treating a caller-supplied plan
as “pre-authorized” would collapse intent, authenticated authority, budget permission, effective
cloud permissions, and observed execution into one unsupported claim.

## Decision

Require a versioned Ed25519-signed authorization manifest and an independently supplied policy at
the capture boundary. Bind the signature to the exact plan digest, qualification and verifier
challenge, AWS resource and principal scope, archive digest and size, retention deadline,
simulation or authorized-non-production environment, validity interval, and bounded cost ceiling.

Verify the configured authorizer identity/key, public-key fingerprint, freshness, expected
environment, independent cost limit, exact plan digest, explicit cloud/spending flags, canonical
digest, maximum lifetime, plan-time containment, and signature before invoking any injected client
method. Simulation manifests must keep cloud and spending authorization false and may invoke only
explicitly marked test doubles; authorized non-production manifests must set both flags true. The
test-double marker prevents accidental interchange but is not client attestation.

Preserve explicit nonclaims for human identity, independent budget approval, effective AWS
permissions, provider execution, and physical-media WORM. Do not include a live authorization,
private key, credentials, account selection, or expenditure approval in the repository.

## Consequences

- Missing, stale, forged, over-budget, or scope-shifted authorization fails with zero client calls.
- The authorization cannot self-select its trust anchor, expected challenge, environment, or cost
  ceiling.
- CI can exercise the identical boundary with a signed simulation manifest and injected stubs.
- A live run still needs an explicitly authorized isolated account, protected workload identity,
  human-approved budget and retention period, and separately retained authorization evidence.
- ETS Core canonicalization and Gateway real-time behavior remain unchanged.

## Rejected alternatives

### Treat the capture plan as authorization

Rejected because a resource description does not prove current authority to use it or incur cost.

### Verify authorization after the first provider call

Rejected because even a read can disclose resource state, consume permission, or create audit and
cost consequences. Verification must precede all client invocation.

### Let the manifest provide its own public key and expectations

Rejected because a forged record could become self-authenticating or redirect the run to a stale
challenge, substituted resource, broader environment, or higher cost limit.
