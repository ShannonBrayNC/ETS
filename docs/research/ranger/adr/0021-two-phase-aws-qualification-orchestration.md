# ADR 0021: Preserve the Post-Receipt Authority Boundary in AWS Qualification Orchestration

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0016, ADR 0017, ADR 0018, ADR 0019, ADR 0020

## Context

The Object Lock execution authorization can be verified before the first provider call. The
CloudTrail read authorization cannot be fully constructed or verified at that time because it
cryptographically binds the execution receipt, and the receipt binds provider-returned request and
object-version evidence that does not exist until the first stage completes.

Treating both authorizations as one pre-execution artifact would either fabricate a future receipt
or weaken the read scope so it no longer binds the actual first-stage result. A one-shot helper that
silently signs its own read authority would also collapse execution, authorization, and evidence
roles.

## Decision

Add `ets.ranger.aws-qualification-run.v1` and a two-phase orchestrator:

1. verify the configured Object Lock execution authorization and run the bounded first-stage
   adapter through injected S3 and IAM clients;
2. issue and independently verify the recorder-signed execution receipt;
3. present that exact package to a caller-supplied read-scope provider;
4. validate the returned receipt-bound read authorization and independent policy before any
   CloudTrail or evidence-object read; and
5. pass the exact captured CloudTrail bytes to the existing provider-boundary verifier.

The read-scope provider is an injected protocol, not a signing key or AWS client embedded in the
orchestrator. A successful result contains the execution package, CloudTrail capture bundle, and
verification finding. If a post-receipt stage fails, the typed orchestration error retains the
execution package so the caller can preserve evidence of the completed first stage rather than
mistaking the whole attempt for a no-effect failure.

## Consequences

- Receipt substitution and precomputed read authority fail before CloudTrail/S3 evidence reads.
- A forged or malformed post-receipt scope causes zero second-stage provider calls.
- A successful software run proves configured signatures and internal evidence binding only. It
  does not prove effective AWS permission, provider execution, completeness, signer independence,
  physical WORM custody, or any physical Ranger outcome.
- A first-stage provider failure can still occur after a subset of provider effects. The existing
  capture adapter's returned or provider-side evidence must be retained; this orchestrator cannot
  manufacture missing observations.
- ETS Core canonicalization and Gateway real-time behavior remain unchanged.

## Threat treatment

| Threat | Mitigation and detection | Required evidence / test |
| --- | --- | --- |
| Read authority precomputed for a different execution | Scope provider receives the newly verified package; existing scope verifier binds its receipt and plan digests. | Exact execution package, signed scope, both policies, and substitution tests. |
| Forged or broadened read scope | Configured Ed25519 trust anchor, fixed operation profile, resource/time/cost bounds, and verification before reads. | Forged-signature test proving zero second-stage client calls. |
| First-stage effects hidden by later failure | Post-receipt errors carry the verified execution package for caller retention. | Failure-path test and retained package/receipt. |
| Credential or client substitution | All clients are caller-injected; the orchestrator imports no AWS SDK and discovers no credentials. | Source review plus controlled workload-identity evidence for live use. |
| False end-to-end success | Invalid CloudTrail verification raises; result schema retains explicit nonclaims. | Deterministic successful and negative replay plus exact-head CI. |

## Rejected alternatives

### Sign both stages before execution

Rejected because the second authorization must bind a receipt that does not yet exist.

### Let the orchestrator hold the read-authorizer private key

Rejected because it would collapse execution and authorization roles and expand key custody.

### Report only a Boolean success value

Rejected because independent reconstruction requires the exact execution package, captured source
bytes, verification finding, and explicit claim limits.
