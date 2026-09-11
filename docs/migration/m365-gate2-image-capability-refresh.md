# M365 Gate 2 image capability refresh

## Confirmed blocker

The destination Gateway currently references an immutable image whose qualified source commit is `9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535`.

That source revision predates the cross-tenant federated managed-identity provider required by M365 Gate 2. Its `ets.connectors.credentials.azure_managed_identity` module contains the older managed-identity Graph provider but not:

- `AzureFederatedManagedIdentityCredentialProfile`
- `AzureFederatedManagedIdentityCredentialProvider`

The isolated Gate 2 runtime qualification therefore failed with sanitized reason `import_error`. Cleanup proof confirmed the temporary qualification job was deleted and the production Gateway returned to zero runtime.

## Required image capability gate

Before publishing any replacement image, the PR-only Hosted Azure Q0 image harness must build the exact Dockerfile locally and execute Python inside that built container. The container must import:

- `azure.identity.ClientAssertionCredential`
- `AzureFederatedManagedIdentityCredentialProfile`
- `AzureFederatedManagedIdentityCredentialProvider`

This local image check uses no Azure credentials and performs no registry push.

## Publication boundary

Passing the local image capability gate does not authorize publication, deployment, revision activation, or production Gateway mutation.

A replacement image must be published only through the protected immutable-image publication workflow, producing a digest-pinned image with existing SBOM, vulnerability, and attestation evidence. Publishing that image to an approved ACR is a separate Azure mutation and requires explicit authorization.

After publication, the new digest should first be exercised in the isolated Gate 2 qualification job while the production Gateway remains at zero active revisions and zero replicas. Production Gateway image replacement remains a later, separate authorization boundary.
