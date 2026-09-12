# ADR 0015: Verify AWS S3 Object Lock Captures Behind the Generic Qualification

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-12
- **Decision owners:** ETS Ranger research program
- **Related:** #605, #710, ADR 0014

## Context

ADR 0014 defines five provider-neutral immutable-publication artifacts, but deliberately does not
interpret provider API semantics. A record labeled `provider_control_plane` can therefore attest
only that its configured issuer signed the supplied bytes. Deployment qualification requires a
provider-specific parser that detects resource substitution, weak retention, meaningless delete
tests, simple-delete markers, and post-denial content substitution.

## Decision

Add a pure verifier for canonical AWS S3 Object Lock capture structures. It composes rather than
replaces the complete provider-neutral verifier and accepts only a provider-control-plane record.
An independent policy pins the AWS account, partition, region, bucket, object key/version,
delete-probe principal, verifier challenge, backend identity, and archive digest.

Require enabled S3 versioning and Object Lock, explicit object-version COMPLIANCE retention,
full-object SHA-256 on put and retrieval, a complete IAM identity-policy simulation that reports
`s3:DeleteObjectVersion` allowed, an exact-version HTTP 403 `AccessDenied` without governance
bypass, and exact-version retrieval after denial. Reject duplicated request IDs and ambiguous or
noncanonical JSON.

Keep provider-authenticity, full effective authorization, retention causality, physical WORM,
independence, trusted time, availability, authorization, truth, and physical outcome false.

## Consequences

- Arbitrary artifact bytes can still satisfy the generic profile, but cannot satisfy the composed
  AWS profile.
- CI remains credential-free and hardware-independent while using the same versioned captures a
  future adapter must emit.
- AWS request IDs are correlators, not signatures or proof that AWS generated a capture.
- A controlled live adapter/run and independent review remain required before any backend is
  operationally qualified.
- No provider, account, hardware, or expenditure is approved.

## Rejected alternatives

### Accept bucket-level Object Lock alone

Rejected because retention applies to versions and a later object version or delete marker can
hide the intended evidence.

### Accept any `AccessDenied` delete error

Rejected because authorization failure can occur for reasons unrelated to retention. The bounded
profile also requires a delete-capability report, current COMPLIANCE retention, exact version, and
post-denial retrieval while preserving a causality nonclaim.

### Let provider fields supply expected identity

Rejected because a substituted account, bucket, object, version, principal, or stale challenge
could become self-authenticating. Expected values must come from verifier policy.

### Add AWS SDK calls to ordinary CI

Rejected because credentials and network behavior would make the core regression suite
nondeterministic. Live capture belongs in a protected, explicitly authorized qualification run.
