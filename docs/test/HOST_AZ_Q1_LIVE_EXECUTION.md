# HOST-AZ-Q1 Live Azure Pilot Execution

Parent: #355  
Qualification sprint: #361  
Dependency stack: HOST-AZ-A #356, HOST-AZ-B #358, HOST-AZ-C #360

## Purpose

This qualification is the first live hosted-Azure evidence gate. It is intentionally separate from unit/integration/Bicep qualification. A green repository CI run does not satisfy this gate; the workflow must execute against a newly deployed Azure resource group and retain sanitized runtime evidence.

## Execution topology

`.github/workflows/hosted-azure-live-qualification.yml` is manual-only. GitHub Actions performs Azure management-plane operations using workload identity, but it does **not** call the ETS API directly.

The ETS Container App keeps internal-only ingress. Azure Container Apps internal app ingress is environment-scoped, so the workflow creates a short-lived qualification-client Container App in the **same Container Apps environment**. That client has no ingress, uses the same immutable Q1 image, and runs the qualification process through `az containerapp exec`. The client is deleted after the run.

This preserves the HOST-AZ-C network boundary instead of weakening ETS ingress for testing.

The Q1 image must include `scripts/qualify_hosted_azure_live.py`; the Q1 Dockerfile copies that script into `/app/scripts/` without changing the normal ETS API command.

The production-JWKS bearer credential is supplied through the protected `ets-azure-q1` GitHub environment as `ETS_Q1_BEARER_TOKEN`. The workflow masks it, injects it into the ephemeral client as a Container Apps secret, references that secret from the client environment, and deletes the client after execution. The bearer value is never written to retained evidence.

Required protected environment secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ETS_Q1_BEARER_TOKEN`

The bearer token must represent an authorized synthetic qualification client and its tenant/workspace claims must match the non-customer `tenant_id` and `workspace_id` workflow inputs.

## Clean-deploy invariant

The workflow fails if the requested resource group already exists. It then creates that resource group and deploys `infra/azure/ets-hosted.bicep` from the exact checked-out qualification source SHA.

This makes the deployment evidence attributable to one source commit and avoids silently reusing previously provisioned ETS runtime resources. The ephemeral qualification client is automatically deleted on exit; cleanup of the hosted ETS qualification resource group remains an operator action after evidence has been retained.

## Runtime sequence

The workflow performs the #361 sequence as follows:

1. authenticate to Azure using workload identity;
2. require a new resource group;
3. deploy the retained hosted-pilot Bicep;
4. resolve the ETS Container App, its internal FQDN, and its Container Apps environment;
5. create a no-ingress ephemeral qualification client in that same environment;
6. inject the bearer credential as an application secret referenced only by the client process;
7. execute the pre-restart qualification process inside the ephemeral client;
8. require `/health`, `/ready`, and `/version` success from the internal ETS endpoint;
9. require `/ready` to identify `azure_table`, `production_jwks`, and `azure_key_vault`;
10. append one synthetic, non-sensitive `qualification.synthetic` event;
11. require a PS256 signed tree head with an Azure Key Vault key identifier;
12. fetch the inclusion proof;
13. verify that proof in the client-side ETS verifier and through the hosted verifier API;
14. return only a base64-encoded sanitized result marker to the Actions runner;
15. identify the active ETS revision;
16. restart that revision with `az containerapp revision restart`;
17. execute the post-restart qualification process inside the same environment;
18. wait for health/readiness recovery;
19. re-read the original event and require the event hash to remain unchanged;
20. regenerate and independently reverify the inclusion proof;
21. require the signing key identity to remain stable across the controlled restart;
22. submit the exact same synthetic event ID and require deterministic HTTP `409` rejection;
23. retain sanitized deployment, client, revision, event, proof, verification, restart, and duplicate-response evidence;
24. delete the ephemeral qualification client.

The client-side verification process uses only the returned proof material for inclusion verification; it does not query hidden ETS state to decide whether the proof is valid. Running the client inside the same environment is a network-placement requirement, not a source-truth or independence shortcut.

A later OpsHelm #98 run may add a named product-client path without changing this qualification's existing evidence.

## Evidence return boundary

The client emits one `ETS_Q1_RESULT_B64=` marker containing compact JSON with only sanitized qualification state/result material. The Actions runner extracts that marker, decodes it into retained JSON, and deletes the temporary `az containerapp exec` transcript.

The pre-restart result carries only synthetic state needed for the post-restart phase. That state is base64-encoded and passed back to the client after the ETS revision restart; it contains no bearer token, Azure credential, signing private material, or customer data.

## Evidence retained

The artifact contains only synthetic or public/runtime metadata:

- exact source SHA and GitHub workflow run ID;
- sanitized Azure deployment outputs;
- ephemeral client metadata without secret values;
- health/readiness/version responses;
- synthetic event metadata and append receipt;
- pre/post-restart inclusion proofs;
- local and hosted verification results;
- active revision metadata before/after restart;
- restart timestamp;
- duplicate rejection response;
- qualification manifest.

The artifact must not contain:

- bearer tokens;
- Azure credentials;
- signing private material;
- customer identifiers;
- raw customer evidence.

## Failure semantics

Any failed assertion or non-expected HTTP status fails the live qualification. A deployment or service outage is a qualification failure for that execution window, not evidence that Azure or ETS is universally unavailable.

A workflow that has never executed is **NOT EXECUTED**, not PASS. Failure to create or execute the same-environment qualification client is **BLOCKED/FAIL for that live execution**, not a reason to expose ETS publicly.

## Nonclaims

Even a successful live run does not establish:

- source truth or source completeness;
- high availability or production GA;
- cross-region disaster recovery;
- external anchoring;
- legal admissibility or compliance certification;
- hardware appliance equivalence;
- correctness of every OpsHelm or enterprise source event.

## Exit rule

#361 can close only after one live run of this workflow completes successfully from the same-environment qualification client and the resulting sanitized artifact is retained and referenced in `HOST_AZ_Q1_LIVE_RESULT.md`.
