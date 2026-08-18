# Microsoft Connector Lifecycle Runbook v1

Parent: #309  
Hosted Azure qualification: #361  
SharePoint live connector: #390

## Purpose

This runbook defines the governed deployment, upgrade, rollback, and offboarding sequence for the
P0 Microsoft SharePoint / OneDrive connector. It extends the existing HOST-AZ clean-deploy boundary
without changing ETS cryptographic verification semantics.

The connector management plane preserves revisioned configuration, runtime state, gap state, and
audit history. Offboarding therefore means **stop collection and revoke source access while retaining
historical ETS evidence and operational audit state**. It does not mean deleting prior evidence or
rewriting the append-only log.

## Preconditions

Before a live lifecycle operation, record:

- exact ETS source commit;
- immutable hosted image digest and image source SHA;
- Connector instance ID, revision, tenant, workspace, and authoritative source ID;
- Microsoft tenant ID, SharePoint hostname/site path, and managed-identity client ID;
- current Microsoft operational posture and active reconciliation outcome;
- source-scoped Gateway queue depth/failures/oldest-unsynchronized age;
- current Graph subscription expiration/status;
- current evidence-package schema versions; and
- operator/reviewer identities through the normal ETS/GitHub audit paths.

Reusable bearer tokens, Graph access tokens, client secrets, Key Vault private material, and raw
SharePoint document content must not be written into lifecycle evidence.

## Clean deployment

The existing HOST-AZ-Q1 live qualification remains authoritative for clean hosted deployment:

1. qualify the exact source SHA and immutable image digest;
2. deploy a new qualification resource group from retained Bicep;
3. preserve internal-only ingress and separated runtime/registry-pull identities;
4. require production JWKS and Azure Key Vault signing posture;
5. prove append, inclusion-proof generation, independent verification, restart persistence, and
   deterministic duplicate rejection; and
6. retain only sanitized qualification artifacts.

Microsoft source access is provisioned separately with
`scripts/m365/provision-echomedia-sharepoint-connector.ps1`. That script must resolve the authenticated
Entra tenant, require the expected verified domain, assign `Sites.Selected`, and grant only the
explicit approved SharePoint site.

A clean Azure deployment alone does not qualify Microsoft source collection. The connector must also
pass live source authorization, scoped Graph collection, notification/delta reconciliation, and proof
package generation.

## Upgrade sequence

1. Freeze the intended release source SHA and immutable image digest.
2. Capture the pre-upgrade connector revision, operational posture, queue posture, subscription state,
   reconciliation state, and a verifiable evidence package for a synthetic/non-sensitive source event.
3. Confirm no unexplained gap is open. If a known gap is open, preserve its explicit state/outcome
   instead of silently clearing it for the upgrade.
4. Deploy the new immutable image without changing tenant/workspace/source authority or broadening
   Graph permissions.
5. Require `/health`, `/ready`, `/version`, and Microsoft operational posture recovery.
6. Re-run a bounded Graph collection/reconciliation cycle from the preserved checkpoint.
7. Verify pre-upgrade evidence still verifies and new post-upgrade evidence produces a valid package.
8. Verify the source-scoped queue returns within policy limits and no unrelated tenant/source failure
   is attributed to this connector.
9. Retain the before/after source SHA, image digest, connector revision, posture, queue metrics,
   package verification, and reviewer evidence.

An upgrade is failed if it requires mutable-image substitution, scope broadening, checkpoint reset
without an explicit reconciliation gap, or suppression of a known operational failure.

## Rollback sequence

Rollback is a controlled deployment to the previously qualified immutable image, not a rewrite of
historical evidence.

1. Preserve the failed-upgrade source SHA/image digest and all observed gap/queue state.
2. Do not delete events, queue records, checkpoints, reconciliation records, or audit history created
   during the failed upgrade window.
3. Deploy the previously qualified immutable image digest.
4. Require hosted readiness and Microsoft operational posture recovery.
5. Reconcile from the durable checkpoint. If the source cursor is no longer valid, open/retain the
   appropriate Microsoft reconciliation gap rather than inventing continuity.
6. Independently verify evidence packages from before the upgrade, during the failure window when
   available, and after rollback.
7. Require source-scoped queue posture to return within the governed policy or record the remaining
   limitation as a release blocker/residual risk.

Rollback does not implicitly restore Microsoft permissions. If source access was revoked, access must
be explicitly re-provisioned through the governed provisioning script and requalified.

## Connector offboarding sequence

### 1. Freeze collection authority

Use the versioned connector-management API to disable the connector with its current expected
revision. The product currently preserves connector instances and runtime/audit history; this runbook
does not fabricate a destructive connector-delete operation.

After disablement:

- verify the instance remains disabled on reread;
- record the resulting revision/audit event;
- ensure no new collection lease is claimed for the disabled source; and
- inspect the source-scoped synchronization queue.

### 2. Resolve queued and continuity state

Drain already committed synchronization work where policy permits. Terminal/retryable failures or an
open source gap must be retained and explicitly declared; offboarding must not erase them to produce a
clean-looking result.

Capture a final Microsoft operational posture and, after the evidence-package contract is available,
a final evidence package containing source provenance and relevant gap declarations.

### 3. Preview Microsoft access revocation

Run:

```powershell
./scripts/m365/offboard-echomedia-sharepoint-connector.ps1 `
  -ResourceGroup <resource-group> `
  -ManagedIdentityName <identity-name> `
  -SharePointHostname <tenant>.sharepoint.com `
  -SitePath /sites/<approved-site>
```

Without `-Apply`, the script is read-only. Review the resolved tenant/domain, identity, site, current
site permission, and current `Sites.Selected` assignment before mutation.

### 4. Revoke the site-specific grant

Repeat the same command with `-Apply`. The script:

- requires the Azure/Graph tenant to match;
- requires the configured verified domain;
- requires an unambiguous managed-identity service principal;
- resolves the exact SharePoint site;
- fails closed if multiple matching site grants exist;
- refuses to delete a permission object that also grants another application;
- deletes only the target application's permission on that site; and
- rereads permissions and fails if the grant remains.

### 5. Optionally remove the Graph app-role assignment

`Sites.Selected` without a site-specific grant does not itself grant access to a SharePoint site.
If the managed identity is dedicated to this connector and the operator intends full Graph-role
removal, use both `-Apply` and `-RemoveSitesSelectedRole`.

Do not remove the app-role assignment merely to make an offboarding report look complete when the
same managed identity is intentionally reused by another governed connector/site. Shared-identity
reuse must be explicit and separately qualified.

### 6. Prove access loss

A live offboarding rehearsal must acquire a token through the actual managed-identity/runtime path and
prove that the former SharePoint target can no longer be read. Operator Graph credentials used to
perform revocation are not evidence of runtime access loss.

### 7. Preserve ETS history

Do not delete:

- historical ETS events or proofs;
- connector revision/audit records;
- reconciliation outcomes;
- retained release qualification packages; or
- required security/operations evidence.

Managed-identity resource deletion and Azure resource-group teardown are separate infrastructure
operations. The offboarding script intentionally reports `managedIdentityDeleted=false` and
`connectorHistoryDeleted=false`.

## Release evidence

Each deployment/upgrade/rollback/offboarding rehearsal must retain a bounded report containing:

- exact source/image identity;
- connector revision and authoritative tenant/workspace/source scope;
- pre/post operational posture;
- pre/post source-scoped queue posture;
- relevant reconciliation gap/outcome;
- sanitized Graph/site permission state;
- proof-package verification results where applicable;
- operation timestamps/outcome;
- residual risks or known limitations; and
- exact-head independent reviewer evidence.

## Nonclaims

Successful lifecycle qualification does not prove Microsoft source truth, universal source
completeness, legal admissibility, compliance certification, cross-region disaster recovery, or the
absence of events outside the connector's declared collection coverage.
