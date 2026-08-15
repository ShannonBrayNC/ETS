# HOST-AZ-Q0A Immutable Q1 Image Publication

Parent: #372 / #355  
Repository sprint: #373  
Cloud prerequisite: #374

## Current disposition

**NOT EXECUTED — Azure OIDC/ACR context required.**

The repository contains a credential-free PR harness and a protected manual publication workflow. The manual workflow cannot produce a qualified image until #374 provisions the authorized Azure workload identity, approved private Azure Container Registry permissions, and protected `ets-azure-q1` environment values.

A green PR harness means only that the Q1 Docker image builds locally and that the workflow preserves the declared OIDC/registry/supply-chain boundaries. It is not evidence that Azure publication succeeded.

## Publication workflow

`.github/workflows/hosted-azure-q0-image.yml` runs only by manual `workflow_dispatch` under the protected `ets-azure-q1` GitHub environment.

The workflow:

1. checks out the exact workflow/source SHA and asserts `HEAD == GITHUB_SHA`;
2. requires the source to contain the Q1-capable Dockerfile and live qualification client;
3. authenticates to Azure with GitHub OIDC through `azure/login` using client, tenant, and subscription IDs from the protected environment;
4. resolves the selected private ACR and requires it to be in the active subscription;
5. requires ACR admin-user authentication to be disabled;
6. requires ACR ARM-audience authentication to be enabled;
7. obtains an ACR-audience Entra access token and exchanges it directly at the registry `/oauth2/exchange` endpoint for a short-lived ACR refresh token;
8. authenticates Docker with the documented all-zero GUID username and the refresh token through `--password-stdin`, without calling `az acr login`, placing either token in process arguments, or writing either token to disk;
9. builds and pushes the hosted image with Docker Buildx;
10. generates BuildKit provenance and SBOM attestations during the build;
11. requires the resulting image digest to be exactly `sha256:<64 lowercase hex>`;
12. verifies the immutable `registry/repository@sha256:<digest>` subject through Buildx;
13. generates a retained SPDX JSON SBOM with Syft/Anchore;
14. generates a retained Trivy JSON report limited to HIGH/CRITICAL OS/library vulnerabilities;
15. records counts and fails closed after evidence upload if any HIGH/CRITICAL finding is retained;
16. creates GitHub build-provenance and SBOM attestations for the exact image digest and requests registry publication of the attestations;
17. uploads only non-secret image evidence;
18. logs Docker out from ACR before the final vulnerability decision.

## ACR authentication boundary

Q0A deliberately does **not** use `az acr login`. On ABAC-enabled registries, Microsoft documents that `az acr login` can require the registry-wide `Container Registry Contributor and Data Access Configuration Administrator` role, which includes registry create/update/delete and configuration authority. That is broader than an image publisher requires.

Instead, the workflow uses the ACR OAuth exchange directly:

- request an Entra token for `https://containerregistry.azure.net/.default`;
- hold that token only in the environment of the short-lived exchange process;
- exchange it in-process at `https://<login-server>/oauth2/exchange`;
- keep the returned short-lived ACR refresh token only in process memory;
- pipe the refresh token directly to `docker login --password-stdin` with username `00000000-0000-0000-0000-000000000000`;
- unset the shell Entra-token environment immediately after the exchange/login process exits;
- never write either token to retained evidence or a temporary token file;
- log Docker out after image/attestation publication.

This permits Q0B to keep ACR control-plane access read-only while granting only the mode-appropriate repository write data-plane role. The intended read-only control-plane role is **Container Registry Configuration Reader and Data Access Configuration Reader** (`69b07be0-09bf-439a-b9a6-e73de851bd59`).

## Mutable tag vs immutable qualification reference

The workflow may push a source/run-derived tag for operator discovery. That tag is **not** the Q1 qualification identity.

The authoritative output is:

`<acr-login-server>/<image-repository>@sha256:<digest>`

HOST-AZ-Q1 must receive that immutable digest reference and a source SHA equal to the exact Q1 workflow source SHA. A mutable tag alone is insufficient for qualification.

## Retained evidence

The Q0A artifact retains:

- exact source SHA;
- workflow run ID;
- ACR name/resource group/login server;
- non-customer image repository;
- ACR admin-user-disabled and ARM-auth-enabled posture;
- authentication mode `direct_acr_oauth_exchange`;
- immutable image reference and digest;
- SPDX JSON SBOM;
- HIGH/CRITICAL Trivy JSON report;
- vulnerability gate counts/result;
- publication manifest.

The retained evidence must not contain:

- Azure access tokens;
- ACR refresh/access tokens;
- Azure client secrets;
- ACR usernames/passwords/admin credentials;
- bearer tokens;
- signing private material;
- customer identifiers;
- raw customer evidence.

## Vulnerability gate

The workflow deliberately separates evidence retention from the vulnerability decision. Trivy writes the complete configured HIGH/CRITICAL JSON report with exit code `0`. The workflow then counts retained HIGH/CRITICAL findings, writes a compact gate record, uploads the evidence with `if: always()`, and only then fails if the gate is not `PASS`.

This preserves forensic evidence for a blocked image while preventing that image from being represented as Q0-qualified.

## Attestation boundary

BuildKit-native `provenance` and `sbom` attestations are enabled for the image build. The workflow also uses GitHub artifact attestations tied to the fully qualified subject name and exact image digest, including a separate SBOM attestation derived from the retained SPDX JSON document.

An attestation establishes provenance/inventory for the built image. It does not establish that future events emitted by the running image are true, complete, or independently verified.

## Cloud prerequisite boundary

#374 must provide the actual Azure/GitHub administrative state:

- private ACR in the Q1 subscription;
- ACR admin user disabled;
- ARM-audience authentication enabled;
- GitHub Actions workload-identity federation scoped to this repository and protected environment;
- read-only ACR configuration access using `69b07be0-09bf-439a-b9a6-e73de851bd59`;
- bounded ACR repository push permission appropriate to RBAC-only vs ABAC mode;
- bounded resource-management/RBAC-assignment permission for Q1;
- protected environment IDs/token values;
- synthetic production-JWKS client context.

This repository sprint does not create or fabricate that external state.

## PR qualification

`.github/workflows/hosted-azure-q0-image-harness.yml` requires no Azure credentials. It checks the workflow contract and builds the exact Q1 Dockerfile locally, confirming that the publication automation is structurally ready without publishing an image.

## Exit rule

#373 can merge after exact-head repository/static qualification and independent review. It closes as repository automation complete, not as live publication complete.

#372/#374 remain open until an authorized execution produces an immutable private-ACR image with retained SBOM, vulnerability, and attestation evidence. #361 remains open until that image is used in a successful live hosted Q1 run.
