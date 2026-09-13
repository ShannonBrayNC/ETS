# ADR 0017: Bind AWS Capture Results to Authorization with a Signed Receipt

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0015, ADR 0016

## Context

ADR 0016 prevents capture without a verified signed authorization. The returned five artifacts,
however, did not retain a tamper-evident link back to the complete authorization record. A valid
authorization could therefore be displayed beside artifacts from another run unless a verifier
separately reconstructed runtime state that was not preserved.

## Decision

After successful guarded capture, have a configured recorder key sign a versioned receipt binding
the complete authorization-record digest, authorization and plan digests, qualification,
challenge, environment, shared object version, all five canonical artifact digests, capture
interval, and receipt time. Issue no receipt when capture fails.

Require the recorder key to differ from the authorization key. Independent verification must rerun
authorization verification, pin both policies and the recorder key, validate each artifact context
against the plan, reconstruct all digests, enforce time bounds and maximum receipt delay, and
verify the canonical receipt signature.

Treat key separation as evidence of distinct cryptographic principals, not proof of different
humans, organizations, hardware, or administrative domains. Keep provider execution, capture
completeness, recorder independence, provider authenticity, and physical WORM explicitly false.

## Consequences

- Authorization and returned evidence can be reconstructed as one tamper-evident lineage.
- Swapped authorizations, artifacts, contexts, versions, keys, or signatures fail verification.
- A capture failure cannot yield a receipt through the guarded orchestration.
- CI remains credential-free and signs only an explicitly labeled simulation package.
- A controlled live trial still needs protected authorizer and recorder workloads, retained raw
  provider evidence, approved account/cost/retention scope, and independent operational review.
- ETS Core and Gateway behavior remain unchanged.

## Rejected alternatives

### Store only the authorization identifier

Rejected because an identifier does not bind the exact signed authorization bytes or signature.

### Let the authorization signer also issue the receipt

Rejected because one compromised key could rewrite both sides of the authority-to-result lineage.
Distinct keys reduce this failure mode without claiming organizational independence.

### Treat a valid receipt as proof of AWS execution

Rejected because the receipt authenticates the configured recorder's assertion over supplied
artifacts. Provider-origin authentication and independent observation remain separate evidence.
