# ADR 0022: Require Complete Signed Records for Offline AWS Qualification Verification

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0016, ADR 0017, ADR 0018, ADR 0020, ADR 0021

## Context

`ets.ranger.aws-qualification-run.v1` preserves a signed execution package, a CloudTrail capture
bundle, and the provider-evidence finding produced during orchestration. It does not embed the two
complete signed authorization records or their independent trust policies. Consequently, a run
object cannot by itself establish who authorized either stage, whether the configured signatures
remain valid, or whether an authorization from another run was substituted during later review.

Trusting the stored Boolean finding would also make reconstruction depend on the original process
rather than the retained source evidence.

## Decision

Add an offline verifier that requires the run plus:

1. the complete signed execution authorization and exact S3 capture plan;
2. the execution-receipt policy, including its authorization and recorder trust anchors;
3. the complete signed CloudTrail read authorization and its independent policy; and
4. the exact CloudTrail capture plan.

The verifier replays the receipt verification, then verifies the read authorization against that
exact receipt and both plans. It requires the capture bundle's scope ID and canonical
complete-record digest to match the supplied read authorization. Finally, it reruns CloudTrail
provider-evidence verification from the retained bytes and requires exact equality with the stored
finding.

## Consequences

- A run is not independently verifiable when either complete signed authorization or either trust
  policy is unavailable.
- Cross-run receipt/read-scope substitution, changed plans, altered bundle bindings, and modified
  stored findings fail closed.
- Verification is offline and imports no AWS SDK, discovers no credentials, and invokes no
  provider client.
- A valid result proves configured signatures and internal evidence linkage only. Effective AWS
  permissions, provider execution, completeness, signer independence, physical WORM custody, and
  physical outcomes remain unproven.
- ETS Core canonicalization and Gateway real-time behavior remain unchanged.

## Threat treatment

| Threat | Mitigation and detection | Required evidence / test |
| --- | --- | --- |
| Cross-run identity or receipt substitution | Both signed scopes are replayed against the exact run receipt, qualification, challenge, and plan digests. | Complete authorization records, policies, plans, and a foreign receipt-bound scope rejection test. |
| Authorization record deletion | A run digest is insufficient; the API requires the complete signed record. | Custody inventory showing both records; missing input cannot produce a valid finding. |
| Capture-bundle substitution | Bundle scope ID and canonical full-record digest must match the verified read authorization. | Retained bundle and digest-mismatch negative test. |
| Forged or stale stored verification | Provider verification is recomputed from source bytes and compared exactly. | Source bytes, trust inputs, and stored-finding substitution test. |
| False provider or custody claim | Result schema fixes provider execution, completeness, signer independence, WORM, and physical-outcome claims false. | Schema validation and claim-boundary review. |

## Rejected alternatives

### Trust the finding stored in the run

Rejected because it does not independently reconstruct the verification from source evidence.

### Embed authorizations and trust policies in the run

Rejected because authorization custody and verifier trust configuration are separate governed
artifacts; silently copying them into an execution result would blur those boundaries.

### Accept authorization digests without complete records

Rejected because a digest can detect change only when the original signed record is available and
its signature and policy can be verified.
