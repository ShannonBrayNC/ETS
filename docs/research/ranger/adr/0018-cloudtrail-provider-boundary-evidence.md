# ADR 0018: Correlate AWS Execution Evidence with Signed CloudTrail Integrity Records

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0015, ADR 0016, ADR 0017

## Context

ADR 0017 binds a verified pre-execution authorization to the exact five artifacts returned by the
configured Ranger AWS recorder. That prevents transport-time authorization/artifact substitution,
but the recorder remains the historian of the captured AWS responses. Its signed receipt therefore
must not be promoted into proof that AWS independently observed the same requests.

AWS CloudTrail log-file integrity validation provides a useful additional evidence source. CloudTrail
digest files bind delivered log files by SHA-256, carry the previous digest signature for chaining,
and are signed with a Region-specific RSA key. The current digest signature is retained as S3 object
metadata. CloudTrail events also expose request IDs, event source/name, account, Region, time, and
request parameters that can be correlated with the request IDs already retained in Ranger's AWS
capture artifacts.

## Decision

Add a software-only CloudTrail provider-boundary verifier that composes only after the ADR 0017
execution receipt verifies. For a bounded evidence window it must:

1. pin the expected digest S3 location and CloudTrail public-key fingerprint independently;
2. pin the SHA-256 of the exact DER public-key bytes supplied to the verifier;
3. validate the digest RSA/SHA-256 signature over the documented CloudTrail signing string;
4. require every log file referenced by the supplied digest and reject unreferenced extras;
5. hash each uncompressed log file and compare it with the digest's SHA-256 reference;
6. correlate each required Ranger capture request ID exactly once to the expected CloudTrail event;
7. pin account, Region, bucket, object key, version ID where applicable, bounded event time, and the
   captured delete-denial error code; and
8. fail closed on mutation, substitution, ambiguity, missing records, wrong keys, or wrong context.

The first profile correlates the two S3 configuration reads, retained-object put, retention read,
IAM policy simulation, exact-version delete attempt, and exact-version retrieval. A future live
qualification must configure CloudTrail to retain the management events and S3 data events needed
for those observations.

## Claim boundary

A passing verifier supports the following bounded statement:

> The supplied execution receipt is valid, the supplied CloudTrail digest is valid under the exact
> independently pinned public-key bytes, the supplied uncompressed logs match that digest, and the
> logs contain one context-consistent event for each request ID preserved by the Ranger capture.

It does **not** by itself establish:

- how the CloudTrail public key was obtained or that it was independently fetched from AWS;
- completeness of CloudTrail configuration or delivery outside the supplied digest window;
- that every effective authorization layer was represented by IAM policy simulation;
- retention causality for an `AccessDenied` response;
- physical WORM media properties or independent custody;
- semantic truth of the application-level claim; or
- a physical Ranger outcome.

Accordingly `provider_execution_independently_proven` remains false in this increment. The new
positive claim is narrower: a cryptographically validated, receipt-correlated CloudTrail
observation profile was supplied under independently pinned verifier inputs.

## Security consequences

- A modified log file fails its digest hash.
- A modified digest fails the RSA signature.
- A substituted RSA key fails the independently pinned DER SHA-256 before signature validation.
- A different AWS operation, account, Region, bucket, key, version, time window, or request ID fails
  request correlation.
- A validly re-signed log set with different request IDs still fails correlation to the ADR 0017
  receipt-bound capture.
- No AWS SDK, credential lookup, network call, cloud mutation, or physical actuation is introduced.

## Operational follow-on

The controlled live trial remains separately authorized work. Before any claim can be strengthened,
preserve the CloudTrail `ListPublicKeys` response or equivalent trust-anchor evidence independently
of the capture workload, retain the digest object's signature metadata, validate the relevant digest
chain rather than only one supplied digest, and prove the intended management/data event selectors
were active for the qualification interval.
