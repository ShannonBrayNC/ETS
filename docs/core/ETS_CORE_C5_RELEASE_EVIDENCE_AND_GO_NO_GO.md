# ETS Core C5 Release Evidence and Go/No-Go Procedure

Status: Proposed

## 1. Release evidence index

Every `ets-core` v1 release candidate must have one immutable evidence index containing:

- release-candidate identifier and version;
- exact source commit and merged-main commit;
- pull requests and submitted approvals;
- required workflow names and run URLs;
- public API manifest digest;
- profile-registry digest;
- schema archive digest;
- vector-set identifier and digest;
- reference conformance report digest;
- independent conformance report digest;
- artifact reproduction report digest;
- wheel and sdist digests;
- SBOM digest;
- provenance digest;
- signature verification record;
- findings-register digest;
- limitations/residual-risk statement digest;
- decision record and approvers.

Missing evidence is a no-go condition, not an implied pass.

## 2. Mandatory go/no-go gates

A release decision may be `GO`, `NO-GO`, or `DEFER`.

### GO requires

- C0-C4 approved and merged;
- exact-head CI green;
- merged-main validation green;
- reference implementation passes every mandatory vector;
- independent implementation passes every mandatory vector;
- no unexplained interoperability mismatch;
- reproducible artifacts verified;
- wheel/sdist allowlists pass;
- SBOM, provenance, and signatures verify;
- no open critical or high finding;
- medium findings have approved bounded dispositions;
- independent protocol and supply-chain approvals submitted;
- limitations and claim boundaries published;
- promotion uses approved candidate bytes without rebuild.

### NO-GO conditions include

- unresolved critical/high finding;
- missing independent implementation evidence;
- normative vector mismatch;
- unexplained artifact-reproduction difference;
- failed signature or provenance check;
- stale approval after material changes;
- missing required workflow evidence;
- release claims exceeding verified boundaries.

### DEFER

Use when evidence is incomplete but no failure has yet been established. Deferred candidates cannot be published as approved releases.

## 3. Decision record

The record must state:

- decision and UTC timestamp;
- candidate version and exact commit;
- evidence-index digest;
- unresolved findings;
- explicit limitations;
- approver identities and roles;
- whether publication is authorized;
- rollback or withdrawal trigger.

## 4. Publication and post-release verification

After publication, automation and an independent operator must download public artifacts and reverify:

- artifact digests;
- signatures;
- provenance source and builder identity;
- package installation in a clean environment;
- mandatory offline verifier vectors;
- public metadata and version consistency.

Track 1 is not complete until post-release verification evidence is linked from the release record.

## 5. Withdrawal and incident response

A release must be withdrawn, yanked, or prominently warned when a newly discovered defect can cause incorrect verification, protocol divergence, artifact substitution, exposed secrets, or materially false compatibility claims.

The response record must preserve the affected release evidence, publish bounded impact, identify safe versions or mitigations, and avoid silently replacing artifacts under an existing version.