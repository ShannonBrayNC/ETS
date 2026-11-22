# Configuration verdict profile v1

Status: VER-01 contract and reviewer-tooling milestone; live configuration qualification remains
open.

`ets.configuration_verdict.v1` binds one bounded configuration verdict to a case, target, approved
baseline, before-state, approval, tool result, and independent read-back. Each of the five exported
artifacts carries a byte length and SHA-256 digest. The verdict document is exported separately and
its exact bytes are hashed into an `EvidenceEvent` with:

- `event_type=configuration.verdict`;
- `evidence_id` equal to the verdict ID;
- `correlation_id` equal to the case ID;
- `subject_ref=configuration-target:<target_id>`; and
- `metadata.baseline_id` equal to the verdict baseline ID.

The event uses the existing ETS proof bundle and signed-tree-head profiles. No CMS profile or new
signature algorithm is introduced.

## Reviewer command

Use the strict CLI with all five separately exported artifacts and verifier-owned trust material:

```powershell
ets-verify configuration-verdict .\verdict.json .\bundle.json `
  --artifact baseline-1=.\baseline.json `
  --artifact before-1=.\before.json `
  --artifact approval-1=.\approval.json `
  --artifact tool-result-1=.\tool-result.json `
  --artifact read-back-1=.\read-back.json `
  --trust-store .\ets-trust.json `
  --expected-log-id ets-production
```

The command rehashes the verdict file and every artifact file from the bytes supplied to that
invocation. It verifies event/leaf/proof/checkpoint binding and the existing Ed25519 or PS256 signed
tree head against the external trust store. It refuses missing, additional, duplicate, oversized,
or digest-mismatched artifact inputs. Exit code `0` means the bounded package integrity and
checkpoint trust checks passed; `1` means a verification check failed; `2` means input or
configuration was malformed.

## Independent result dimensions

The result never collapses these dimensions into one generic "verified" label:

- `integrity`: exported byte, event binding, inclusion proof, and checkpoint consistency;
- `trust`: checkpoint signature validation against supplied out-of-band trust material;
- `authorization`: the signed verdict's `authorized`, `unauthorized`, `unknown`, or
  `not_applicable` assessment;
- `repair`: the signed verdict's `not_attempted`, `verified`, `failed`, or `unknown` assessment;
- `uncertainty`: declared verdict uncertainty versus verification failure.

A cryptographically valid package can authentically report `unknown`, `unauthorized`, or a failed
repair. Conversely, a claimed repaired verdict is not accepted by the schema unless it records
authorized and verified assessments without suppressing uncertainty.

## Claim boundary

This milestone qualifies deterministic reviewer tooling with positive and negative fixtures. It
does not independently prove that an approver held authority, a tool result was truthful, a target
changed in the real world, the read-back observer was independent, or a live tenant is qualified.
Those predicates require protected identity, source-runtime, execution, and live read-back evidence
under ID-01, DSC-01/M365-01/TCM-01, EXEC-01, and QUAL-01. Desktop presentation of this profile is not
implemented by this milestone; reviewers must use the supported CLI output without translating a
successful integrity result into a complete repair claim.
