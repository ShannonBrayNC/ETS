# ETS Core C5 Findings and Residual-Risk Policy

Status: Proposed

## 1. Finding severity

### Critical
A condition that permits undetected proof acceptance, reproducible protocol divergence, release-artifact compromise, secret exposure, or unauthorized release substitution.

Disposition: release blocked. No waiver.

### High
A condition that materially weakens deterministic verification, profile isolation, package integrity, interoperability, or supported security boundaries.

Disposition: release blocked unless remediated and independently revalidated. No time-limited waiver for v1 general release.

### Medium
A bounded defect with a practical workaround that does not invalidate normative artifacts or verification outcomes.

Disposition: remediate before release or document a named owner, compensating control, expiration, and approved follow-up issue.

### Low
A minor documentation, usability, diagnostics, or non-normative defect.

Disposition: document and schedule when appropriate.

### Informational
An observation or improvement without a current correctness or security impact.

## 2. Finding record

Every finding must contain:

- unique identifier;
- title and severity;
- affected profile, package, artifact, or workflow;
- reproduction steps;
- expected and actual result;
- security or interoperability impact;
- source commit and environment;
- owner;
- remediation or accepted disposition;
- verification evidence;
- closure approver.

## 3. Severity changes

Severity may change only with a written rationale and independent reviewer agreement. A severity reduction may not be used to avoid a release blocker without new technical evidence.

## 4. Residual-risk statement

The release record must explicitly document:

- supported profiles and environments;
- unsupported algorithms and platforms;
- compatibility behavior for historical alpha artifacts;
- resource limits;
- dependency and cryptographic-backend assumptions;
- known medium/low findings;
- untested conditions;
- operational controls outside `ets-core`;
- semantic claim limitations.

## 5. Waivers

Critical and high findings cannot be waived for v1 general release.

A medium finding waiver requires:

- demonstrated bounded impact;
- no effect on normative bytes, proof acceptance, or artifact identity;
- compensating controls;
- accountable owner;
- expiration date or release milestone;
- independent approval;
- public disclosure when relevant to users.

## 6. Revalidation

Any change to canonicalization, hash preimages, Merkle behavior, signature payloads, profile identifiers, verification result codes, schemas, vectors, package layout, or release workflow invalidates the affected prior evidence and requires scoped revalidation.