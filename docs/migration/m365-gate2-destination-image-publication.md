# M365 Gate 2 destination immutable image publication

## Purpose

The current destination Gateway image is pinned to immutable digest
`sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63`,
qualified from source commit `9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535`.
That source predates the federated cross-tenant managed-identity provider used by
M365 Gate 2 runtime qualification, and the isolated runtime qualification therefore
failed with sanitized reason `import_error`.

PR #691 added a local image capability gate and proved that current source can build
an image containing:

- `azure.identity.ClientAssertionCredential`;
- `AzureFederatedManagedIdentityCredentialProfile`;
- `AzureFederatedManagedIdentityCredentialProvider`.

This runbook publishes a new immutable image into the destination ACR only. It does
**not** update, activate, scale, or otherwise mutate the production Gateway.

## Fixed destination boundary

- Azure tenant: `0d20cf0f-3498-46c1-a0db-69b09c634cc2`
- Azure subscription: `5729a82b-8850-4868-b96c-96c3805cbb9d`
- Shared resource group: `rg-ets-shared-eastus`
- ACR: `etsprod7c8ab70380.azurecr.io`
- Repository: `ets/hosted-q1`
- GitHub environment: `ets-azure-migration-destination-image-publish`
- Publisher UAMI: `ets-gh-dst-image-publisher`

The publisher identity is separate from the destination read and restore identities.
Do not broaden `ets-gh-migration-dst-read` or `ets-gh-migration-dst-restore` for image
publication.

## 1. Bootstrap the dedicated publisher identity

Use an operator-authenticated Azure CLI session in the destination tenant/subscription.
The script is preview-only unless `-Apply` is supplied.

```powershell
az login --tenant '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
az account set --subscription '5729a82b-8850-4868-b96c-96c3805cbb9d'

.\scripts\azure\bootstrap-destination-image-publisher.ps1
```

The preview must verify the exact destination tenant/subscription and ACR. The bootstrap
intentionally fails closed if the registry is not using `LegacyRegistryPermissions`;
ABAC mode requires a separately reviewed repository-scoped role condition.

After review, apply the bounded identity/FIC/ACR-role mutations:

```powershell
.\scripts\azure\bootstrap-destination-image-publisher.ps1 -Apply
```

The apply path may create/reuse only:

- UAMI `ets-gh-dst-image-publisher` in `rg-ets-shared-eastus`;
- FIC subject `repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-image-publish`;
- direct ACR-scope `Container Registry Configuration Reader and Data Access Configuration Reader`;
- direct ACR-scope `AcrPush`.

It creates no client secret and must stop if the publisher already has Owner,
Contributor, User Access Administrator, or Role Based Access Control Administrator.

## 2. Configure the protected GitHub environment

Create/protect GitHub environment `ets-azure-migration-destination-image-publish`
with required reviewers and restricted deployment branches. Configure these environment
secrets from the bootstrap output:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

These values are identifiers, not reusable client secrets. No Azure client secret is
required or permitted.

## 3. Dispatch the destination publication workflow

Run workflow:

`Azure Migration Destination Immutable Image Publication`

from the reviewed `main` ref only.

The workflow has no registry/tenant/subscription inputs. Those values are hard-bound in
the workflow. It must verify the exact destination Azure context before any registry
write.

The publication flow:

1. checks out the exact dispatch SHA;
2. authenticates through GitHub OIDC;
3. verifies the destination tenant/subscription and exact ACR posture;
4. authenticates Docker through direct ACR OAuth exchange;
5. builds and pushes one image;
6. requires a canonical immutable SHA-256 digest;
7. runs the Gate 2 federated-provider import probe against the published digest;
8. generates SPDX SBOM and HIGH/CRITICAL Trivy evidence;
9. fails on fixable HIGH/CRITICAL findings;
10. creates GitHub provenance and SBOM attestations;
11. uploads non-secret publication evidence.

The temporary build tag is not an approved deployment reference. Only the emitted
`<registry>/<repository>@sha256:<digest>` immutable reference may be used in later
qualification/deployment work.

## 4. Stop after publication

Successful image publication does **not** authorize changing the destination Gateway.
Record the immutable digest and publication run ID, then stop at the next authorization
boundary.

The next phase is an isolated Gate 2 runtime qualification job using the newly published
digest while keeping the production Gateway at zero active revisions/replicas. Only
after that digest passes should a separate production Gateway image-update decision be
considered.
