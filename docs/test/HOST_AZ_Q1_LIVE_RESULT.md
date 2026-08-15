# HOST-AZ-Q1 Live Azure Pilot Result

Parent: #355  
Qualification sprint: #361

## Current disposition

**NOT EXECUTED — live Azure qualification context required.**

The repository now contains the bounded live qualification workflow and client, but no live Azure run is recorded by this result document yet. Static CI, unit/integration tests, Bicep validation, and successful hosted-stack compilation are not substitutes for the #361 runtime sequence.

## Required live evidence before PASS

A future PASS record must reference one successful `Hosted Azure Live Pilot Qualification` workflow run and retain its sanitized artifact. That run must demonstrate:

- deployment into a new Azure resource group from an exact source SHA;
- an ephemeral no-ingress qualification client in the same Container Apps environment as ETS;
- internal `/health`, `/ready`, and `/version` success;
- ready state identifying Azure Table persistence, production JWKS authentication, and Azure Key Vault signing;
- synthetic event append with a PS256 signed tree head;
- inclusion proof verification both by the client-side ETS verifier and hosted verifier API;
- active ETS Container App revision restart;
- event/proof persistence and successful verification after restart;
- stable signing key identity across the controlled restart;
- deterministic duplicate-event rejection;
- deletion of the ephemeral qualification client after execution;
- sanitized evidence with no bearer token, credentials, private signing material, customer IDs, or raw customer evidence.

## Why this is not BLOCKED yet

The executable qualification package is complete enough to run once the protected Azure/GitHub environment, workload-identity permissions, and immutable Q1 image are available. The client executes inside the Container Apps environment, so the test does not require ETS internal ingress to be exposed publicly. If those prerequisites cannot be supplied, this row should be updated to **BLOCKED — no authorized live Azure qualification context** rather than treated as a product PASS or FAIL.

## Nonclaims

No live hosted-pilot availability, restart durability, Azure service availability, production readiness, HA/GA, legal admissibility, compliance, source truth/completeness, or OpsHelm production-integration claim is made by this pre-execution record.

## Update rule

Do not change this document to PASS from a static workflow result. Update it only from a completed live workflow run, and include the exact source SHA, run ID, artifact ID/digest, Azure deployment identifiers, same-environment client identity, and explicit nonclaims from that execution.
