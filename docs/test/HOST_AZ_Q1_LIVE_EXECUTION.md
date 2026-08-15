# HOST-AZ-Q1 Live Azure Pilot Execution

Parent: #355  
Qualification sprint: #361  
Dependency stack: HOST-AZ-A #356, HOST-AZ-B #358, HOST-AZ-C #360  
Provisioning prerequisite: HOST-AZ-Q0 #372

## Purpose

This qualification is the first live hosted-Azure evidence gate. It is intentionally separate from unit/integration/Bicep qualification. A green repository CI run does not satisfy this gate; the workflow must execute against a newly deployed Azure resource group and retain sanitized runtime evidence.

## Execution topology

`.github/workflows/hosted-azure-live-qualification.yml` is manual-only. GitHub Actions performs Azure management-plane operations using workload identity, but it does **not** call the ETS API directly.

The ETS Container App keeps internal-only ingress. The workflow creates a short-lived qualification-client Container App in the **same Container Apps environment**. That client has no ingress, uses the same immutable Q1 image, and runs the qualification process through `az containerapp exec`. The client is deleted after the run.

This preserves the HOST-AZ-C network boundary instead of weakening ETS ingress for testing.

## Immutable image and private ACR boundary

The Q1 image must:

- be stored in the private Azure Container Registry provisioned/approved under #372;
- be referenced as `registry/repository@sha256:<64 hex>`, never only by mutable tag;
- have an `image_source_sha` exactly equal to the workflow's checked-out `GITHUB_SHA`;
- include `scripts/qualify_hosted_azure_live.py` at `/app/scripts/` without changing the normal ETS API command.

Before creating any qualification resource group, the workflow resolves the named ACR in the active subscription, validates its login server, requires ARM-audience authentication to be enabled for Container Apps managed-identity image pull, restricts the requested registry pull role to one of the two HOST-AZ-C-supported built-in IDs, and confirms that the image reference uses that exact registry server and immutable digest.

The accepted pull-role IDs are:

- RBAC-only ACR: `AcrPull` — `7f951dda-4ed3-4680-a7ca-43fe172d538d`;
- ABAC-enabled ACR: `Container Registry Repository Reader` — `b93aa761-3e63-49ed-ac28-beffa264f7ac`.

Q1 does not use ACR admin credentials, registry usernames/passwords, or `listCredentials`.

## Identity separation

HOST-AZ-C deploys two user-assigned identities:

1. the ETS runtime identity, which has the bounded Azure Table and Key Vault roles required by the hosted evidence service;
2. a separate registry-pull identity, which has only the selected registry-scoped image-pull role.

The ephemeral qualification client attaches **only** the registry-pull identity. It never attaches the ETS runtime identity. Therefore the client does not receive Azure Table or Key Vault data-plane privileges merely because it must pull the Q1 image.

The client is created from `infra/azure/ets-q1-client.bicep` rather than `az containerapp create`. This prevents the CLI from silently creating an extra registry role assignment. The client Bicep references the already-governed registry-pull identity and registry server; it contains no role-assignment resource.

The workflow reads the deployed client back from Azure and fails unless:

- exactly one user-assigned identity is attached;
- that identity is the HOST-AZ-C registry-pull identity;
- exactly one private registry binding exists;
- the registry binding uses that same pull identity and expected server;
- no ingress is configured.

## Protected bearer-token boundary

The production-JWKS bearer credential is supplied through the protected `ets-azure-q1` GitHub environment as `ETS_Q1_BEARER_TOKEN`. The workflow masks it and passes it to `ets-q1-client.bicep` as an ARM/Bicep `@secure()` parameter.

The temporary deployment-parameter file is created in the runner temporary directory with mode `0600`, deleted immediately after deployment, and never uploaded. The client deployment-history record is deleted immediately after the Container App is created. The bearer value exists only in protected GitHub secret context, the temporary secure deployment request, and the ephemeral client secret until client deletion. It is never written to qualification evidence.

Required protected environment secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ETS_Q1_BEARER_TOKEN`

The bearer token must represent an authorized synthetic qualification client and its tenant/workspace claims must match the non-customer `tenant_id` and `workspace_id` workflow inputs.

## Clean-deploy invariant

The workflow validates the pre-existing private ACR first, then fails if the requested qualification resource group already exists. It creates a new resource group and deploys `infra/azure/ets-hosted.bicep` from the exact checked-out qualification source SHA.

The ACR itself is intentionally outside the clean qualification resource group because it contains the immutable prebuilt Q1 image. All ETS runtime resources, identities, Table storage, Key Vault key, and Container Apps resources used as the system under test are newly deployed for the qualification window.

The ephemeral qualification client and its deployment-history record are automatically removed. Cleanup of the hosted ETS qualification resource group remains an operator action after evidence has been retained.

## Runtime sequence

The workflow performs the #361 sequence as follows:

1. assert the immutable image source SHA equals the checked-out workflow SHA;
2. authenticate to Azure using workload identity;
3. validate the existing private ACR, subscription, ARM-audience authentication, bounded pull role, login server, and immutable image reference;
4. require a new qualification resource group;
5. deploy the retained hosted-pilot Bicep with the validated registry parameters;
6. resolve the ETS Container App, its internal FQDN, environment, registry server, and dedicated registry-pull identity;
7. deploy a no-ingress ephemeral qualification client from `ets-q1-client.bicep` with only that pull identity;
8. remove the secure client deployment-parameter file and deployment-history record;
9. read the client back and verify the identity/registry/no-ingress boundary;
10. execute the pre-restart qualification process inside the ephemeral client;
11. require `/health`, `/ready`, and `/version` success from the internal ETS endpoint;
12. require `/ready` to identify `azure_table`, `production_jwks`, and `azure_key_vault`;
13. append one synthetic, non-sensitive `qualification.synthetic` event;
14. require a PS256 signed tree head with an Azure Key Vault key identifier;
15. fetch the inclusion proof;
16. verify that proof in the client-side ETS verifier and through the hosted verifier API;
17. return only a base64-encoded sanitized result marker to the Actions runner;
18. identify and restart the active ETS revision with `az containerapp revision restart`;
19. execute the post-restart qualification process inside the same environment;
20. wait for health/readiness recovery;
21. re-read the original event and require its event hash to remain unchanged;
22. regenerate and independently reverify the inclusion proof;
23. require the signing key identity to remain stable across the controlled restart;
24. submit the exact same synthetic event ID and require deterministic HTTP `409` rejection;
25. retain sanitized deployment, registry, client, revision, event, proof, verification, restart, and duplicate-response evidence;
26. delete the ephemeral qualification client and any remaining client deployment record.

The client-side verification process uses only returned proof material for inclusion verification; it does not query hidden ETS state to decide whether the proof is valid. Running the client inside the same environment is a network-placement requirement, not a source-truth or independence shortcut.

A later OpsHelm #98 run may add a named product-client path without changing this qualification's existing evidence.

## Evidence return boundary

The client emits one `ETS_Q1_RESULT_B64=` marker containing compact JSON with only sanitized qualification state/result material. The Actions runner extracts that marker, decodes it into retained JSON, and deletes the temporary `az containerapp exec` transcript.

The pre-restart result carries only synthetic state needed for the post-restart phase. That state is base64-encoded and passed back to the client after the ETS revision restart; it contains no bearer token, Azure credential, signing private material, registry credential, or customer data.

## Evidence retained

The artifact contains only synthetic or non-secret runtime metadata:

- exact source SHA, image source SHA, immutable image digest reference, and GitHub workflow run ID;
- ACR name/resource group/login server, selected pull-role ID, and ARM-audience-enabled status;
- sanitized Azure deployment outputs;
- registry-pull identity resource ID;
- ephemeral client metadata proving the pull-only identity and no-ingress configuration;
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
- registry usernames/passwords/admin credentials;
- signing private material;
- customer identifiers;
- raw customer evidence.

## Failure semantics

Any failed assertion or non-expected HTTP status fails the live qualification. A deployment or service outage is a qualification failure for that execution window, not evidence that Azure or ETS is universally unavailable.

A workflow that has never executed is **NOT EXECUTED**, not PASS. Missing #372 prerequisites are **BLOCKED — no authorized live Azure qualification context**, not a reason to expose ETS publicly or weaken registry/identity controls.

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
