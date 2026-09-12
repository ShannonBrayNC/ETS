# Ranger R0.2 AWS S3 Object Lock Artifact Verification

**Status:** provider-specific verifier and deterministic fixtures; no AWS account, bucket, object,
or live qualification evidence is included

**Schemas:** `ets.ranger.aws-s3-object-lock.configuration.v1`,
`ets.ranger.aws-s3-object-lock.retention-put.v1`,
`ets.ranger.aws-iam.delete-capability.v1`,
`ets.ranger.aws-s3-object-lock.delete-attempt.v1`, and
`ets.ranger.aws-s3-object-lock.retrieval.v1`

**Tracks:** #605

## Objective

Add one provider-specific verification boundary behind the provider-neutral
`ets.ranger.immutable-publication-qualification.v1` profile. The verifier consumes five
canonical, content-addressed capture artifacts shaped for the AWS APIs a future live adapter must
call. It never contacts AWS and does not accept a provider name, bucket setting, SDK success, or
generic `AccessDenied` error as sufficient by itself.

Amazon S3 is a reference integration, not a procurement or deployment decision. AWS documents
that Object Lock applies to individual object versions, requires versioning, distinguishes
COMPLIANCE from bypassable GOVERNANCE mode, and returns a delete marker rather than deleting data
when `DeleteObject` omits a version ID. Those details make explicit version and request binding
essential. See the official [Object Lock guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html),
[PutObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html), and
[DeleteObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html).

## Composition boundary

`verify_aws_s3_object_lock_qualification` first runs the complete provider-neutral verifier. Only
after signature, source-key standing, publication-chain, archive-digest, retrieval-audit,
retention, delete-denial, and artifact-digest checks pass does it parse AWS artifacts. A
simulation record cannot pass this provider-specific path.

The independently supplied AWS policy pins:

- qualification identity and verifier challenge;
- generic backend instance and namespace;
- AWS partition, 12-digit account, region, bucket, and expected bucket owner;
- exact object key and non-null version ID;
- exact IAM delete-probe principal ARN; and
- exact archive-bundle SHA-256.

Every artifact repeats that context. Cross-account, cross-bucket, cross-object, cross-version,
cross-principal, stale-challenge, and cross-trial substitution therefore fail before provider
semantics are considered.

## Versioned capture artifacts

The artifacts are canonical ETS JSON captures produced from AWS SDK/API observations. They retain
the provider request IDs used for correlation but are signed assertions by the configured evidence
issuer; the verifier does not claim AWS signed the capture bytes.

| Artifact | Required AWS observation | Provider-specific checks |
| --- | --- | --- |
| Configuration | `GetBucketVersioning` and `GetObjectLockConfiguration` | Both calls returned HTTP 200 with S3 request/extended-request IDs; versioning and Object Lock both report `Enabled`. |
| Retention put | `PutObject` followed by version-pinned `GetObjectRetention` | Request and response contain a full-object SHA-256 matching the exact archive bundle; returned version matches policy; requested and observed mode are `COMPLIANCE`; retain-until timestamps match the signed qualification. |
| Delete capability | IAM `SimulatePrincipalPolicy` for `s3:DeleteObjectVersion` | The exact account principal and object ARN report a complete, non-truncated `allowed` identity-policy evaluation. This is not proof of runtime effective authorization. See [SimulatePrincipalPolicy](https://docs.aws.amazon.com/IAM/latest/APIReference/API_SimulatePrincipalPolicy.html). |
| Delete attempt | version-specific `DeleteObject` | The exact version is supplied, governance bypass is false, and S3 reports HTTP 403 `AccessDenied` with request IDs while retention is current. The generic error does not prove causality. |
| Retrieval | version-specific `GetObject` with checksum mode enabled | HTTP 200, returned version, body SHA-256, provider SHA-256, and `FULL_OBJECT` checksum type all bind to the exact archive bundle after denial. See [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html). |

`GetObjectRetention` is version-pinned and must report the same COMPLIANCE deadline used by the
signed qualification. See the official
[GetObjectRetention API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectRetention.html).
All seven captured AWS request IDs must be nonempty and distinct. JSON with duplicate members,
unknown fields, non-finite values, non-UTF-8 bytes, non-object roots, noncanonical encoding, or a
payload over 1 MiB fails closed.

## Claims and nonclaims

A successful result establishes that:

- the existing signed provider-neutral qualification passed;
- the supplied canonical artifacts match the qualification's five content digests;
- the artifacts carry one policy-pinned AWS resource/trial identity;
- the captures report enabled bucket controls and exact object-version COMPLIANCE retention;
- an IAM identity-policy simulation reports delete-version capability;
- a version-specific delete reports `AccessDenied` during the retained interval; and
- the exact version and full-object archive digest are reported retrievable after denial.

It does **not** establish that AWS generated the captured bytes, that the evidence issuer was
uncompromised, that IAM simulation covered resource policies, permissions boundaries, session
policies, service-control policies, VPC endpoint policies, or later policy changes, or that Object
Lock caused a generic `AccessDenied`. It also does not establish physical-media WORM, independent
administration, hardware-backed identity/anti-rollback, trusted time, global currentness,
continued availability, operational authorization, complete capture, semantic truth, actuator
response, or physical outcome.

## Threat model

| Threat / attack surface | Impact | Existing or added mitigation and detection | Missing mitigation | Required evidence | Test strategy |
| --- | --- | --- | --- | --- | --- |
| Bucket/account/object/version substitution | Unrelated storage appears qualified | Independent policy plus repeated context and exact version checks | Provider-signed resource inventory | Five bound captures and expected policy | Mutate each identity independently |
| Simple delete without `versionId` | A delete marker is mistaken for destruction resistance | Only version-specific deletion is accepted | Live request trace attestation | Delete request and exact version | Replace version with `null` or another version |
| GOVERNANCE substituted for COMPLIANCE | Privileged bypass can remove evidence | Requested and observed mode must both be `COMPLIANCE`; bypass flag must be false | Independent policy/role review | Put request and `GetObjectRetention` | Substitute mode, bypass, or deadline |
| Incapable delete principal | `AccessDenied` is misattributed to retention | Exact principal/resource IAM simulation must report `allowed` and complete | Full effective authorization graph and control-object test | IAM simulation capture | Denied or truncated simulation |
| Forged or ambiguous delete denial | Generic 403 is treated as proof of causality | Require current retention, capable-principal report, version-specific request, provider IDs, and explicit causality nonclaim | Provider-signed denial reason or controlled comparison object | Delete error plus surrounding artifacts | Change status, error, version, or request ID |
| Content/version substitution on retrieval | Different bytes survive while the intended archive is lost | Body and provider full-object SHA-256 plus exact version must match the archive digest | Independent re-retrieval and replication | Get response and body digest | Mutate checksum, body digest, checksum type, or version |
| Replayed or mixed trial artifacts | Old evidence passes a new challenge | Challenge, qualification/resource identity, exact times, distinct request IDs, and signed content digests | Trusted-time attestations and protected live-run identity | All five artifacts and verifier policy | Replay request ID or change challenge/time |
| Evidence deletion/modification | Qualification cannot be reconstructed | Complete five-kind set, strict schemas, canonical bytes, and signed digest binding | Separate immutable custody of the evidence package | All artifact bytes | Missing, malformed, duplicate-member, extra-field, and noncanonical JSON tests |
| Compromised evidence issuer | Fabricated captures receive a valid ETS signature | Separate issuer key and explicit provider-authenticity nonclaim | Hardware-backed key, lifecycle, workload attestation, independent capture | Key attestation and signer history | Future live negative/control run |
| Clock manipulation | Retention interval is misstated | Exact ordered artifact/qualification timestamps; trusted-time remains false | Provider and external trusted-time attestations | Time-bearing provider responses and attestations | Substitute or reorder times |

## Test and live-run separation

Ordinary CI constructs the exact five versioned structures intended for a future adapter, signs
their digests through the provider-neutral record, and deterministically exercises positive and
mutation cases. It does not import `boto3`, use credentials, contact AWS, or fabricate a live-run
claim.

A controlled live trial remains separate work. It must run in an explicitly authorized,
non-production qualification account/namespace with a fresh verifier challenge, a small synthetic
archive bundle, minimum approved retention, exact versioned delete, post-denial retrieval, and
secret-free evidence export. The run must retain raw SDK/error details needed to produce these
canonical captures and must not label the backend physically WORM or independent merely because
the software verifier passes.

## Cost and alternatives

This implementation and CI path cost $0 and select no provider. Before a live run, compare:

- a local S3-compatible emulator for free interface experiments, which cannot establish AWS or
  physical retention behavior;
- a small AWS S3 Object Lock qualification object, whose storage/request/KMS/logging charges must
  be estimated from the chosen region and current account pricing before approval; and
- separately administered or replicated custody, which adds account, transfer, evidence-export,
  and operational overhead but can test stronger separation and availability hypotheses.

No purchase, cloud account creation, retention commitment, or spending approval is implied.

## IP note

The composition of authority-relative publisher/custodian standing, verifier-pinned live challenge
and AWS object version, content-addressed provider captures, capability-qualified negative delete,
and full-object post-denial retrieval may be differentiating. No novelty search was completed, no
closest prior art was established, and patentability requires counsel review.
