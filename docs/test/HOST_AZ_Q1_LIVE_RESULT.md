# HOST-AZ-Q1 Live Azure Pilot Result

Parent: #355  
Qualification sprint: #361  
Provisioning prerequisite: #372

## Current disposition

**NOT EXECUTED — live Azure qualification context required.**

The repository contains the bounded live qualification workflow, pull-only ephemeral-client Bicep, and qualification client, but no live Azure run is recorded by this result document yet. Static CI, unit/integration tests, Bicep validation, and successful hosted-stack compilation are not substitutes for the #361 runtime sequence.

## Required live evidence before PASS

A future PASS record must reference one successful `Hosted Azure Live Pilot Qualification` workflow run and retain its sanitized artifact. That run must demonstrate:

- exact workflow/source SHA equal to the source SHA used to build the Q1 image;
- private ACR image reference pinned by `@sha256:<digest>` rather than mutable tag;
- selected ACR resolved in the active subscription with ARM-audience authentication enabled for Container Apps managed-identity pull;
- only the bounded HOST-AZ-C registry pull role selected for the ACR permissions mode;
- deployment into a new Azure resource group from the exact source SHA;
- an ephemeral no-ingress qualification client in the same Container Apps environment as ETS;
- the qualification client attaching only the dedicated registry-pull identity, not the ETS Table/Key Vault runtime identity;
- private-registry authentication by managed identity without registry username/password/admin credentials;
- secure bearer-token injection with no token value retained in deployment evidence or qualification artifacts;
- internal `/health`, `/ready`, and `/version` success;
- ready state identifying Azure Table persistence, production JWKS authentication, and Azure Key Vault signing;
- synthetic event append with a PS256 signed tree head;
- inclusion proof verification both by the client-side ETS verifier and hosted verifier API;
- active ETS Container App revision restart;
- event/proof persistence and successful verification after restart;
- stable signing key identity across the controlled restart;
- deterministic duplicate-event rejection;
- deletion of the ephemeral qualification client and its client deployment-history record;
- sanitized evidence with no bearer token, Azure credential, registry credential, private signing material, customer ID, or raw customer evidence.

## Why this is not BLOCKED yet

The executable qualification package is ready for static qualification. A live PASS still requires #372 to provide the protected Azure/GitHub environment, workload-identity permissions, approved private ACR, immutable Q1 image digest, and synthetic production-JWKS client context.

The client executes inside the Container Apps environment, so the test does not require ETS internal ingress to be exposed publicly. If those prerequisites cannot be supplied, this row must become **BLOCKED — no authorized live Azure qualification context** rather than being treated as a product PASS or FAIL.

## Nonclaims

No live hosted-pilot availability, restart durability, Azure service availability, production readiness, HA/GA, legal admissibility, compliance, source truth/completeness, hardware equivalence, or OpsHelm production-integration claim is made by this pre-execution record.

## Update rule

Do not change this document to PASS from a static workflow result. Update it only from a completed live workflow run and include the exact source SHA, image source SHA, immutable image digest reference, run ID, artifact ID/digest, sanitized Azure deployment/registry identifiers, registry-pull identity, same-environment client identity, selected bounded pull-role ID, and explicit nonclaims from that execution.
