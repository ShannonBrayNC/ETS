# ADR 0019: Credential-Isolated CloudTrail Evidence Capture

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0016, ADR 0017, ADR 0018

## Context

ADR 0018 verifies a supplied CloudTrail digest, its referenced log files, and correlation to the
seven AWS request IDs bound into the Ranger execution package. A controlled trial still needs a
bounded way to obtain those exact inputs without embedding AWS SDK setup, credentials, endpoints,
or provider discovery in the evidence implementation.

The capture boundary must not treat data returned by the same workload as its own trust anchor.
It must also preserve AWS's distinction between compressed S3 objects and the uncompressed bytes
whose SHA-256 values appear in CloudTrail digest records.

## Decision

Add a passive adapter that accepts capability-limited CloudTrail and S3 clients constructed by an
authorized caller. Before invoking either client it verifies the existing signed execution package.
This increment accepts only simulation authorization with explicit test-double markers. Live
authorization fails before any call because ADR 0016 does not sign the additional CloudTrail and
digest/log read scope.

An independent capture plan pins the account, Region, trail name, exact digest location, expected
public-key fingerprint and DER SHA-256, UTC window, file-count/size limits, and event-time skew. The
adapter retrieves one matching `ListPublicKeys` entry, the named trail's selector arrays, the exact
gzip digest object and its hexadecimal signature metadata, and only the gzip log objects referenced
by that digest. It returns the exact uncompressed bytes consumed by the ADR 0018 verifier plus
secret-free key/selector observations.

The adapter fails closed on pagination, ambiguous or substituted keys, invalid key validity,
missing or non-hex signature metadata, wrong signature algorithm, malformed gzip/JSON, duplicate or
empty references, and configured count/size overflow. It never lists buckets or objects and never
performs a write.

## Claim boundary

A successful capture establishes only that:

- the existing signed Ranger execution package verified before provider reads;
- the configured injected clients returned a key, selectors, digest, signature metadata, and the
  exact referenced log set matching the independent runtime plan; and
- the exact captured bytes were supplied to the ADR 0018 verifier.

It does not independently prove AWS key provenance, selector continuity or completeness, provider
execution, physical WORM custody, effective permissions, semantic truth, human identity, budget
approval, or physical Ranger outcome. The CloudTrail capture plan is not yet a separately signed
extension of the AWS execution authorization; that limitation remains explicit.

## Safety and cost consequences

Ordinary CI uses deterministic gzip objects, locally generated RSA keys, and marked test doubles.
Invalid receipt or simulation-client identity fails before any client call, and substituted key
material fails before any S3 read. No AWS SDK, credential, network call, cloud mutation, physical
action, purchase, retention commitment, or spending authorization is introduced.

The next live-read prerequisite is a signed scope extension binding the qualification/challenge,
trail, digest location, public-key pins, evidence window, read-only operations, file bounds, and
cost ceiling. Until that exists, this adapter cannot be used with live provider clients.
