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
| Overprivileged or substituted live client | Capture code writes or probes an unintended resource | Caller injects minimal S3/IAM capabilities; plan pins account, bucket, key, principal, and exact generated version; no client construction or credential discovery | Separate workload identity, resource policies, and non-production account controls | Client provenance and live-run authorization record | Stub records required parameters; future controlled negative run |
| Missing, stale, forged, or scope-shifted execution approval | A client call occurs without current authority or against another plan | Verify configured-authorizer Ed25519 signature, independent policy, validity interval, exact plan digest, resource identity, environment, and bounded cost before the first client call | Human identity, independent budget approval, effective IAM policy, and signer hardware attestation | Signed authorization plus independently supplied policy | Expiry, signature, plan-substitution, environment, and zero-client-call tests |
| Authorization/result separation or artifact substitution | A valid approval is presented beside artifacts from another run | A distinct recorder key signs the complete authorization-record digest, plan, shared object version, five canonical artifact digests, and bounded receipt time | Provider-signed observations, recorder attestation, and organizational independence | Authorization, receipt, exact five artifacts, plan, and independent policies | Swap authorization, artifact bytes, context, version, recorder key, or signature |
| Unscoped CloudTrail evidence reads or compressed-object expansion | A reused authorization reads unintended provider data or a gzip object exhausts memory | Existing receipt verifies before calls; simulation requires marked clients; account/Region/key/location/file bounds are pinned; decompression is output-bounded; live reads are disabled | Separately signed CloudTrail read scope and authorized live workload identity | Capture plan, authorization/receipt, client-call trace, key/selector observations, digest metadata, and exact referenced logs | Invalid receipt and live/unmarked clients produce zero calls; substitute key/signature; duplicate paths; exceed gzip output bound |
| Archive-body or credential retention by capture code | Sensitive material leaks into evidence output | Result contains only normalized metadata and SHA-256 bindings; credentials are never accepted; CI asserts archive bytes are absent from artifacts | Secret scanning and protected evidence-export path | Secret-free output inventory | Stubbed artifact serialization and repository scans |
| Compromised evidence issuer | Fabricated captures receive a valid ETS signature | Separate issuer key and explicit provider-authenticity nonclaim | Hardware-backed key, lifecycle, workload attestation, independent capture | Key attestation and signer history | Future live negative/control run |
| Clock manipulation | Retention interval is misstated | Exact ordered artifact/qualification timestamps; trusted-time remains false | Provider and external trusted-time attestations | Time-bearing provider responses and attestations | Substitute or reorder times |

## Test and live-run separation

Ordinary CI constructs the exact five versioned structures intended for a future adapter, signs
their digests through the provider-neutral record, and deterministically exercises positive and
mutation cases. It does not import `boto3`, use credentials, contact AWS, or fabricate a live-run
claim.

## Credential-isolated capture adapter

[`ets.ranger.aws_s3_object_lock_capture`](../../../ets/ranger/aws_s3_object_lock_capture.py)
now supplies the first live-run-facing boundary while remaining suitable for stubbed CI. It accepts
only caller-injected minimal S3 and IAM capabilities; it does not import an AWS SDK, read
environment variables, resolve profiles, construct clients, select endpoints, or retain
credentials. It accepts a pre-authorized, size-bounded synthetic archive and returns only the five
canonical, secret-free artifact types consumed by the verifier. The supplied archive bytes are
used for the put and retrieval digest check but never appear in the result.

The fixed sequence is: read bucket controls, put a synthetic COMPLIANCE-retained object version,
read its retention, simulate `s3:DeleteObjectVersion` for the pinned test principal, attempt an
exact-version delete with governance bypass disabled, and retrieve that exact version with checksum
mode enabled. A successful delete, missing/malformed response metadata, unbounded body, changed
retrieved bytes, stale retention deadline, or out-of-order observation plan fails before an
artifact package is returned.

This adapter does not make a cloud call by itself. It now requires a signed pre-execution
authorization and an independently supplied verification policy before it invokes even the first
injected client method. The returned version ID remains an observation for the run record; an
independent verifier policy must still pin the exact resource identity rather than trusting the
adapter result as its own authority.

## Signed pre-execution authorization

The `ets.ranger.aws-s3-execution-authorization.v1` manifest signs the exact capture-plan digest,
qualification/challenge identity, AWS account/region/bucket/key, delete-probe principal, archive
digest and size, retention deadline, execution environment, validity interval, and maximum cost
ceiling. The plan digest includes every planned observation timestamp and represents the archive
body only by SHA-256 and byte count. A caller must separately supply the expected authorization,
qualification, challenge, environment, authorizer/key, verification time, public key, and maximum
cost ceiling. The manifest therefore cannot supply its own trust anchor or freshness decision.

`simulation` manifests must deny cloud execution and spending. `authorized_non_production`
manifests must explicitly assert both flags. A missing, malformed, expired, not-yet-valid,
wrong-key, wrong-environment, over-budget, bad-signature, or plan-substituted manifest fails before
any S3 or IAM method is called. Policy also caps authorization lifetime and requires all planned
observation times to remain within the authorized interval. Simulation execution accepts only
clients carrying an explicit test-double marker, preventing an ordinary injected provider client
from being used under a simulation manifest. The marker is a misuse guard, not client attestation.
This is an authenticated configured-key authorization assertion, not proof of the human signer,
independent budget approval, effective AWS permissions, provider execution, correct clock, or
workload identity. No live manifest or signing key is included.

## Signed execution receipt

[`ets.ranger.aws_s3_object_lock_execution`](../../../ets/ranger/aws_s3_object_lock_execution.py)
adds `ets.ranger.aws-s3-execution-receipt.v1`. The guarded orchestration calls the authorized
capture adapter first and issues no receipt if capture fails. After successful capture, a recorder
key distinct from the authorization key signs:

- the complete signed authorization-record digest and its internal authorization digest;
- the exact capture-plan digest, qualification, verifier challenge, and environment;
- the returned object version shared by all five artifacts;
- the canonical SHA-256 of configuration, retention-put, delete-capability, delete-attempt, and
  retrieval artifacts; and
- the declared capture interval and bounded receipt-issuance time.

Independent verification reruns authorization verification, reconstructs the exact plan and
artifact digests, checks every artifact context against that plan, pins the recorder identity and
public key, enforces key separation and maximum receipt delay, then verifies the canonical receipt
digest and signature. Authorization or artifact substitution, mixed versions, context changes,
stale receipts, same-key authorization/recording, and forged signatures fail closed.

The receipt proves that a configured recorder key bound the supplied authorization, plan, and
artifacts. It does not independently prove that AWS executed the calls, that AWS produced the
captured fields, that capture was complete, that the recorder was uncompromised or organizationally
independent, or that storage is physically WORM. The simulation fixture therefore remains a
simulation even though both configured signatures verify.

## Credential-isolated CloudTrail evidence capture

[`ets.ranger.aws_cloudtrail_capture`](../../../ets/ranger/aws_cloudtrail_capture.py) passively
collects the inputs required by the CloudTrail provider-boundary verifier through caller-injected
CloudTrail and S3 clients. It does not import an AWS SDK, resolve credentials or profiles, select
endpoints, or construct clients. The signed AWS execution package and a separately signed
CloudTrail read scope are verified before either client can be invoked.

The capture plan independently pins the account, Region, trail, exact digest object, CloudTrail
public-key fingerprint and DER SHA-256, UTC window, maximum file count, maximum uncompressed file
size, and event-time skew. The adapter then performs a bounded sequence:

1. `ListPublicKeys` for the exact UTC window, requiring one matching fingerprint and DER digest;
2. `GetEventSelectors` for the named trail, retaining canonical digests of both selector arrays;
3. version-neutral read of the exact pinned digest object, retaining its hexadecimal signature and
   `SHA256withRSA` metadata; and
4. read and bounded gzip decompression of exactly the log objects referenced by that digest.

Pagination, ambiguous keys, invalid validity intervals, changed key bytes, absent signature
metadata, invalid gzip/JSON, duplicate log paths, empty references, or count/size overflow fails
closed. The composed helper passes those exact captured bytes into the independent verifier rather
than reconstructing or normalizing signed content.

The adapter records the provider request IDs for key and selector lookups, but does not retain
credentials or raw response envelopes. Selector-array digests establish what the injected client
returned; they do not prove the selectors were continuously effective or complete. Likewise,
`ListPublicKeys` capture does not independently authenticate AWS as the key source. Public-key
provenance, complete coverage, and provider execution remain false even when the read-scope
signature verifies.

## Signed CloudTrail read scope

`ets.ranger.aws-cloudtrail-read-authorization.v1` is a dedicated Ed25519 manifest that binds the
complete base execution authorization and execution receipt, both exact plan digests,
qualification/challenge, account/Region/trail/digest/key pins, historical evidence window, and
file/count/byte bounds. Its sole provider profile permits exactly two CloudTrail calls
(`ListPublicKeys`, `GetEventSelectors`) and at most one digest plus the signed maximum number of
referenced S3 log reads. It also binds validity, configured signer identity/key, a cost ceiling,
and explicit read/spending flags.

An independently supplied policy pins the expected scope and base identities, configured signer,
verification time, maximum lifetime, environment, and cost limit. The scope must begin no earlier
than the bound execution receipt. Missing, stale, forged, over-budget, wrong-environment,
wrong-key, changed receipt, changed plan, altered resource, or expanded read scope fails before any
injected client call. The capture result retains the scope ID and complete signed-record digest; the
complete signed scope remains a separately retained authorization artifact.

The capture bundle is therefore `ets.ranger.aws-cloudtrail-capture.v2`; v1's unsigned-scope
nonclaim is not silently reinterpreted as evidence of this new authorization boundary.

Simulation scopes retain false cloud-read/spending flags and require marked test doubles. For a
controlled `authorized_non_production` qualification, both flags must be true and the caller may
inject a least-privilege client. This code does not supply credentials, choose an account, create a
provider client, run a live trial, or establish effective AWS permission. See [ADR 0020](adr/0020-signed-cloudtrail-read-scope.md).

## Two-phase qualification orchestration

[`ets.ranger.aws_qualification_orchestrator`](../../../ets/ranger/aws_qualification_orchestrator.py)
composes the guarded Object Lock execution and CloudTrail verification paths without erasing the
authority boundary between them. The first stage produces and verifies its execution receipt. Only
then does an injected read-scope provider receive that exact package and return the separately
signed CloudTrail authorization and independent policy. The existing capture adapter verifies that
scope before any second-stage provider read.

This order is mandatory: a CloudTrail read scope cannot honestly bind an execution receipt before
that receipt exists. The orchestrator therefore neither precomputes the scope nor holds its signing
key. A successful `ets.ranger.aws-qualification-run.v1` result retains the execution package,
CloudTrail capture bundle, and provider-boundary verification. A post-receipt orchestration error
retains the execution package for caller preservation so a later failure is not represented as if
the first-stage effects never occurred.

The composed result is not evidence of effective AWS permission, actual provider execution,
complete CloudTrail coverage, signer independence, physical WORM custody, or physical outcome.
See [ADR 0021](adr/0021-two-phase-aws-qualification-orchestration.md).

## Offline qualification-run verification

[`ets.ranger.aws_qualification_run_verifier`](../../../ets/ranger/aws_qualification_run_verifier.py)
independently replays an `ets.ranger.aws-qualification-run.v1` without provider access. The caller
must supply the complete signed execution authorization, complete signed CloudTrail read
authorization, both independent verification policies, and both exact capture plans. A run alone
is intentionally insufficient because it retains digests and findings, not the separately governed
authorization records or verifier trust configuration.

The verifier reruns the execution-receipt signature and artifact binding, verifies the read scope
against that exact receipt and both plans, matches the capture bundle to the canonical digest of
the complete signed read authorization, and recomputes the CloudTrail provider-evidence finding
from the retained source bytes. It then requires the stored finding to equal that replay result.
Mixing an authorization, receipt, plan, capture bundle, or stored finding from another run fails
closed rather than producing a partially valid aggregate.

The resulting `ets.ranger.aws-qualification-run-verification.v1` finding preserves separate flags
for each verified boundary and explicit false claims for permissions, provider execution,
completeness, signer independence, physical WORM custody, and physical outcome. See
[ADR 0022](adr/0022-offline-aws-qualification-run-verification.md).

## Secret-free qualification evidence manifest

[`ets.ranger.aws_qualification_evidence_manifest`](../../../ets/ranger/aws_qualification_evidence_manifest.py)
defines `ets.ranger.aws-qualification-evidence-manifest.v1`, a portable inventory for controlled
qualification evidence. The manifest carries only the package, qualification, challenge, and
authorization/receipt identifiers plus canonical SHA-256 digests for eight separately retained
artifacts:

1. complete signed execution authorization;
2. exact S3 capture plan;
3. execution-receipt policy and configured public trust anchors;
4. exact CloudTrail capture plan;
5. complete signed CloudTrail read authorization;
6. CloudTrail read-authorization policy and configured public trust anchor;
7. qualification run with captured provider-evidence bytes; and
8. independently replayed qualification-run verification.

The manifest does not copy credentials, private keys, archive contents, provider-evidence bytes,
or trust material. Verification requires the caller to supply all eight originals, reruns the
offline qualification verifier, recomputes every role-tagged canonical digest, and requires an
exact manifest match. Missing, duplicate, reordered, or substituted roles fail closed.

The manifest's self-digest detects mutation only when compared with a retained expected value; it
is not a signature and does not establish provenance or authenticity. Effective permission,
provider execution, completeness, physical WORM custody, and physical outcome remain unproven.
See [ADR 0023](adr/0023-secret-free-aws-qualification-evidence-manifest.md).

## Signed manifest custody acceptance

[`ets.ranger.aws_qualification_manifest_custody`](../../../ets/ranger/aws_qualification_manifest_custody.py)
defines `ets.ranger.aws-qualification-manifest-custody-receipt.v1`. A configured custodian signs
the exact manifest record, its successful verification finding, package and qualification
identifiers, a verifier-controlled custody-target identifier, the acceptance time, and the
requested retention deadline. The receipt therefore prevents a valid signature for one package,
verification finding, target, or retention request from being reused for another.

Issuance requires a self-consistent manifest and a successful complete manifest-verification
finding. Offline verification checks the complete record digests, Ed25519 signature and key
fingerprint against a configured policy, including the expected custodian identity, key, target,
acceptance window, and minimum retention deadline. The target identifier is deliberately an
opaque policy value rather than a credential-bearing provider URL.

This proves only that the configured key accepted the exact verified manifest for the declared
target and retention request. It does not prove a storage write, continued retention,
organizational independence, trusted custodian time, physical WORM behavior, provider execution,
or a physical outcome. Those claims require separate provider and custody observations. See
[ADR 0024](adr/0024-signed-aws-qualification-manifest-custody.md).

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
