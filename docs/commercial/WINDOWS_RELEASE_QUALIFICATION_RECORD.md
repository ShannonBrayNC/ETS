# Windows release qualification record

Status: **TEMPLATE — NOT EXECUTED — NO RELEASE APPROVAL**

Copy this record for one specific candidate. Do not turn engineering CI results
into client qualification claims. Use PASS, FAIL or NOT RUN for every gate; a blank
or unavailable result is NOT RUN. No gate below is preapproved. This record does
not replace the repository's existing release/security/IP approvals.

## Candidate and accountable reviewers

| Field | Value to record |
| --- | --- |
| Candidate source commit and repository | NOT RECORDED |
| Build workflow/run and retained evidence location | NOT RECORDED |
| Unsigned MSIX filename, version and SHA-256 | NOT RECORDED |
| Signed MSIX filename and SHA-256 | NOT RECORDED |
| Package identity, publisher and architecture | NOT RECORDED |
| Public signing certificate thumbprint and validity | NOT RECORDED; never record private keys/passwords |
| Signing owner | UNASSIGNED |
| Client tester and test date | UNASSIGNED |
| License/security reviewer | UNASSIGNED |
| Release approver | UNASSIGNED |
| Clean Windows 11 build, VM snapshot and account type | NOT RECORDED |
| WebView2 version and provisioning method | NOT RECORDED |
| Network isolation method | NOT RECORDED |
| Previous version used for upgrade/downgrade tests | NOT RECORDED |

Do not reuse development package identity as the production identity. Record exact
Partner Center values when that stage is reached. Changing candidate bytes, package
identity, runtime version or relevant environment requires assessment and repetition
of the affected gates; a prior record is evidence only for its stated candidate.

## Gate results

For each result, link a log/report/screenshot, test date, operator and any defect.
Use synthetic fixtures; keep customer evidence and credentials out of attachments.

| Gate | Status | Required evidence / evidence location |
| --- | --- | --- |
| Repository qualification | NOT RUN | Exact-commit required checks; retained source/frozen/native/browser results and package hash validation |
| Development signature | NOT RUN | Successful signing and signature verification; unsigned/signed digests; approved public certificate metadata |
| Client preparation | NOT RUN | Clean OS snapshot, standard-user account, absent developer tools, documented runtime/trust preparation |
| WebView2 provisioning | NOT RUN | Chosen supported provisioning method and startup evidence on clean client |
| Per-user installation | NOT RUN | Registration/version/publisher match; no app elevation requirement |
| Package-identity launch | NOT RUN | Start-menu launch of installed app, not unpacked EXE |
| Real-dialog offline verification | NOT RUN | Valid, tampered, missing-trust, unsupported and malformed cases with network disabled |
| Report export | NOT RUN | JSON/Markdown/HTML match displayed outcome; cancellation and no-overwrite behavior; report digests |
| Keyboard/Narrator/scaling | NOT RUN | Full workflow, focus/labels, 200% scaling; defects fixed and retested |
| Upgrade and downgrade | NOT RUN | Version advancement, older-version rejection, working verification, external user-file hash comparison |
| Uninstall and reinstall | NOT RUN | Registration removal, preserved external inputs/reports, successful clean reinstall |
| Runtime licenses and notices | NOT RUN | Actual shipped component mapping, missing-license resolutions, reviewed customer notices and reviewer decision |
| Runtime SBOM and security | NOT RUN | Runtime SBOM, applicable vulnerability results and disposition; build-environment inventory alone is insufficient |
| Production identity and listing | NOT RUN | Verified Partner Center identity, approved branding, accurate feature/privacy/support statements |
| WACK and Store review | NOT RUN | Exact candidate certification results and Store decision |
| Existing release/IP approvals | NOT RUN | Required repository approvals for declared distribution scope |

## Release decision

- Requested distribution scope: NOT RECORDED (internal engineering, bounded beta,
  or Store release; never imply one authorizes the others).
- Open failures / unexecuted gates and owners: NOT RECORDED.
- Candidate changes since evidence collection: NOT RECORDED.
- Decision and rationale: **NOT APPROVED**.
- Approver and date: UNASSIGNED.

A candidate with unexecuted client gates remains an engineering candidate. A Store
release additionally requires all Store gates and existing approvals. An automated
agent or green CI run must not fill the approver field on someone's behalf.

## Execution references

- [Current engineering evidence and remaining gates](WINDOWS_VERIFIER_READINESS.md)
- [Development signing and client lifecycle procedure](WINDOWS_SIGNING_QUALIFICATION.md)
- [Desktop smoke and network-test scope](WINDOWS_DESKTOP_CANDIDATE.md)
- [Dependency evidence and review limits](WINDOWS_DEPENDENCY_EVIDENCE.md)
