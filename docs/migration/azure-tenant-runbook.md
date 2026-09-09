# Controlled Azure migration — resumable record

## Checkpoint: 2026-09-06, ACCESS_BLOCKED

Scope: Lantern website, EchoMedia website, critical ETS. Parallel deployment is
the provisional method. Nothing has been deployed, backed up, cut over, stopped,
or deleted by this migration session. Source cost reduction is **not established**.

Inspected ETS main `f3b973aa63a3893437a2422a670278cf053b137e`, repository controls,
deployment workflows, infrastructure, Azure Table implementation, open Azure PRs,
and migration branch/PR searches. No existing Azure migration branch was found.
GitHub reports this repository as public despite the stale private classification
in `.repo-control/repo-profile.yml`. Keep protected operational records outside Git.

| Fact | Verification status |
| --- | --- |
| Source tenant/subscription | Live identity confirmation blocked; prior billing audit is only a discovery lead |
| Destination tenant/subscription | Unknown; intended account supplied by operator, not an Azure identifier |
| Destination billing account/profile/scope and offer | Unknown |
| Credit balance/expiry/spending limit | Operator reported $200 expiring 2026-12-02; current entitlement unverified |
| Azure status, roles, region availability, quotas | Not inventoried live |
| Microsoft billing-adjustment conditions | Unconfirmed; no written conditions retrieved |
| Source/destination costs and overlap | Unknown; no price or utilization basis yet |
| DNS provider, zone export, TTLs, live routing | Unverified; no DNS changes |
| Backups, restore, evidence verification | Not performed |

## Repository-derived mapping (not live inventory)

| Workload | Repository evidence | Dependencies and method | Validation and rollback | Cost |
| --- | --- | --- | --- | --- |
| Lantern apex/www, critical public site | `ops/lantern-site-backup/site`; `lantern-site-backup-deploy.yml`; Front Door workflows | Existing continuity Storage site in `rg-ets-live-eastus`; Front Door/DNS/TLS route must be discovered. Publish to isolated destination, keep source available. | Assets, dynamic `app.js`, forms, apex/www redirects, HTTPS; retain source version and original routes. | Unknown; price static hosting and routing separately |
| EchoMedia apex/www, critical public site | Separate website repository inspected; protected details retained there | Hosting-to-live-DNS mapping not established. Validate current host before classifying any Azure resource as redundant. | SPA deep links, assets, forms, HTTPS and apex/www; restore original route and build. | Unknown |
| ETS Core/Gateway, critical evidence service | `live-core-gateway-deployment.yml`, `infra/azure/ets-hosted.bicep`, `ets-gateway.bicep` | Existing workflow targets `rg-ets-live-eastus`, ACR `etsq1a352eb89` in `rg-ets-q1-eastus`, `ets-azure-q1` environment; all require live readback. Parallel infrastructure, immutable image, new identities, frozen state copy. | Auth positive/negative tests, ingestion, stored bytes, historical/new signatures, connectors and post-cutover write rollback. | Unknown; do not deploy full template until priced |

The existing Lantern README describes resource creation, but the current publish
workflow instead requires existing storage and deletes all `$web` blobs before
upload. Do not reuse it for a continuity-preserving migration. PR #589 addresses
dynamic website verification only; do not duplicate or merge it as migration work.

## Observed automation evidence

[Cleanup run 34002629018](https://github.com/ShannonBrayNC/ETS/actions/runs/34002629018),
2026-09-06 00:57 UTC: Azure OIDC login succeeded; `eligible_count=0`; protected-group
verification failed with `Forbidden`. This proves neither resource absence nor
adequate inventory permissions. No synthetic groups were selected in that run.

The source cleanup schedule is hourly and is not a provisioning job. The hourly
Microsoft soak controller also exists and can dispatch subordinate observations.
Do not disable an active evidence qualification or cleanup job without checking
its current state/dependencies. No workflows were disabled in this session.
Core/Gateway deployment is manual and release-gated. Do not rerun deployment jobs
to obtain discovery information or replace the source environment's credentials
with destination credentials.

## Resume: access and entitlement

1. Provide an authenticated Azure execution session accessible to the engineer.
   Sign in through the official Azure flow for the intended destination account
   and the authorized source principal; never share passwords, tokens or secrets.
   This Work session has GitHub access, no Azure CLI/session, and no discovered
   Azure integration. A local login elsewhere does not authenticate this session.
2. Initial discovery requires subscription Reader on both subscriptions and Cost
   Management Reader where supported. Billing-scope/credit visibility is separate:
   grant the appropriate offer-specific billing reader access or use the billing
   account owner's authenticated view. Record subscription linkage, remaining
   balance, currency, expiration, spending limit and overage rules in protected storage.
3. Use `az account list --all` in that authenticated environment to discover exact
   IDs. Verify the account-to-subscription relationship in the portal; email alone
   is insufficient. Run the collector separately for each explicitly verified pair:

   ```bash
   python scripts/azure_migration_discover.py \
     --tenant "$MIGRATION_TENANT_ID" \
     --subscription "$MIGRATION_SUBSCRIPTION_ID" \
     --output "$MIGRATION_PROTECTED_CAPTURE_DIR"
   ```

   Output must be a new protected directory outside Git. On Windows, configure
   an operator-only ACL on the parent; POSIX permissions alone do not set Windows
   ACLs. The collector reads metadata, never tokens, keys or application settings.
   Its hashes establish capture-file integrity only, not evidence completeness,
   Azure authenticity, backup success, billing entitlement or migration readiness.
   A blocked read exits nonzero and cannot be treated as an empty inventory.
4. Complete service-specific dependency inventory: exact resources/SKUs, runtimes,
   images, workers/jobs/leases, databases and table schema, blob versions/retention,
   queues, key versions and encryption dependencies, certificates, identities and
   grants, app registrations, OIDC subjects, callbacks, network/private DNS,
   monitoring, backup/restore and every DNS record including mail records.
   Inventory app settings only into protected storage; never expose secrets in CI.
5. For deployment, use destination resource-group Contributor and scoped RBAC
   administration only as needed, data-plane roles for the exact source/destination
   stores, and separately authorized Entra application administration. Source Reader
   alone cannot back up data or stop resources. Discover exact scopes before grants.

## Cost gate

Export posted source costs by resource ID, meter and day (last seven complete days
plus month-to-date); record ingestion lag and currency. Rank actual drivers before
stopping resources. Price destination SKUs for verified region, traffic, storage,
logs, requests, backups, networking and required security. Include source retention,
overlap and data egress. No fixed forecast is defensible before this inventory.

Planning arithmetic only: $200 over 87 days is about $2.30/day or $69 per 30 days,
assuming the full reported balance and expiration are confirmed. This is a budget
ceiling illustration, not a forecast or a claim that the workload fits. Runway is
remaining eligible credit divided by eligible daily spend, capped by credit expiry;
ineligible charges are separate. Never remove a spending limit or downgrade ETS
security to fit the credit without an explicit cost decision. Budget alerts are
not a substitute for verifying the subscription's spending behavior.

If minimal secure hosting exceeds credit, present itemized minimum viable choices
and continue offline preparation. Do not transfer a subscription's directory as a
billing migration. Azure resource moves across subscriptions require the same Entra
tenant; verify service-specific support before selecting any move operation.

## Data preservation and cutover gates

- Record a migration ID, actors, source/destination scopes, UTC times, tool versions,
  commit/image digests and hashes of protected manifests in the audit record.
- Back up and restore to isolated storage before modifying state. For Azure Table,
  preserve typed entities, partition/row keys, exact event JSON, event/leaf hashes,
  metadata, next index and event-ID indexes. Do not rebuild evidence by reinserting
  events through ingestion. Service-assigned ETags/timestamps can change on copy:
  retain originals in the backup manifest and do not rewrite historical event times.
- Inventory artifact bytes separately from Azure Table event records. Capture blob
  versions, metadata, legal holds/retention and encryption requirements. A successful
  transfer of current blobs alone does not preserve all historical versions.
- Keep original log IDs, identities and provenance. Retain historical public keys
  and exact versions; test old signatures using independently retained verification
  material. Nonexportable signing keys need a validated supported continuity or
  rotation strategy; preserve old key access where verification/decryption depends
  on it. Do not purge keys or invent rewritten historical identity references.
- Keep destination schedulers and consumers disabled. Establish exclusive writer
  ownership and a write freeze covering all API ingress, workers, webhooks and retry
  paths. Drain or capture queues, cursors, leases and dead letters. Take final sync,
  counts, hash comparisons and high-water marks before enabling one destination writer.
- Validate destination health, readiness, negative auth/authorization, end-to-end
  ingestion/storage/verification, old and new evidence, image deployment from intended
  repository, connectors, CORS/callbacks, monitoring and restore access.
- Export original DNS records/TTLs; prevalidate certificates and custom domains.
  Preserve MX/SPF/DKIM/DMARC/autodiscover and unrelated records. Keep registration,
  Entra domains and Microsoft 365 unchanged. Domain detachment needs separate approval.
- Cut over validated independent websites individually. Cut ETS consumers after its
  storage, signing, identity and APIs are ready. Record exact routing diffs and UTC
  timestamps. Do not claim readiness from HTTP 200 or a successful workflow alone.

## Rollback and source savings

Before destination writes: disable destination workers, restore captured routes,
and resume the source only after proving destination writer shutdown.

After destination writes: freeze destination and fence both writers; preserve a
complete post-cutover delta including evidence, custody, indexes, queues and side
effects. Validate a replay/import into the isolated source restoration using exact
evidence bytes and duplicate detection, preserving destination signing references.
Only switch back after reconciliation and validation. If that is unsupported, keep
writes paused and request a downtime/recovery decision; DNS reversal alone is unsafe.

Choose the observation period from actual DNS TTLs, queue drain and the longest
critical job cadence, plus traffic/auth/error/verification results. Then disable
source provisioning and redundant writers, stop/deallocate/scale down only confirmed
redundant resources with recoverable state. Retain rollback data, historical keys,
evidence and required backups. Check source traffic/write counters independently.

Itemize still-billable plans, Front Door/gateways, registries, DBs, disks, public IPs,
storage, snapshots and logs. Obtain separate approval for exact irreversible deletion
IDs, dependency analysis, retained backup references, retention obligations and
estimated savings. Never delete tenant/subscription, purge keys/evidence, transfer
registration or migrate mailboxes under this migration authorization.

## Billing-review factual record

2026-09-06: repository discovery and migration preparation completed. Live source
inventory and destination entitlement could not be verified from this execution
environment. No workload migration or source shutdown has occurred. No refund,
startup verification, credit approval or cost elimination is claimed. Append actual
resource actions/timestamps and posted billing evidence after execution; keep the
support case and Microsoft's exact written conditions in protected storage.

## Reference constraints checked 2026-09-06

Local validation: `python -m unittest discover -s tests -p
test_azure_migration_discover.py -v` passed four safety tests; CLI help and
`git diff --check` passed. Pytest is unavailable in this execution environment;
the full repository suite and Azure integration execution were not run.

- [Azure move prerequisites](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/move-resource-group-and-subscription)
- [Service move support](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/move-support-resources)
- [Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit)

## Resume checkpoint: awaiting destination sign-in

The continuation installed Azure CLI 2.90.0 in an isolated execution environment.
Microsoft sign-in and ARM endpoints are reachable. An official device login has
been initiated for the operator to select the intended destination account. Login
is not yet confirmed; no destination identifiers or entitlement have been verified.
Authentication codes and token caches are deliberately excluded from this record.
The earlier generic execution-access blocker is now a destination sign-in gate.

PR #611 initially failed Ruff E501 on the collector's output argument line. Commit
`c7c97e3e5e8af0606757264d9d80ccc5b55fdf2a` fixes that line; four local safety tests
still pass. Replacement CI is pending. No Azure resource, DNS, data, or billing
mutation has occurred. Continue by checking destination login completion, then
list accessible subscriptions without exposing tokens and verify billing linkage.

## Authentication checkpoint: 2026-09-06 05:54 UTC

Destination Microsoft-account authentication succeeded using the persisted device
handoff. Azure tenant discovery returned a Default Directory, but token acquisition
for that directory failed with AADSTS530035 (BlockedBySecurityDefaults). The empty
subscription result is therefore incomplete discovery, not proof of no subscription.
Exact directory identifiers and authentication state are kept in protected execution
storage. The common Microsoft-account token's tenant is not the deployment tenant.

Azure CLI recommends directory-specific interactive login for the failed tenant.
A saved, directory-specific login handoff has been initiated to allow the operator
to complete any tenant MFA/security requirements. No policy, security default, role,
resource, DNS record or evidence was changed. If the tenant rejects this interactive
flow, stop and use an administrator-approved authentication path; do not weaken policy.
Billing scope, subscription ID, entitlement and source cost reduction remain unverified.

## Confirmed device-flow block: 2026-09-06 05:58 UTC

Operator supplied a directory-specific Azure CLI denial with error 530035. Stop
all device-code retries. Microsoft Security Defaults documentation now explicitly
states that new tenants block device code flow starting 2026-07-01. This supersedes
the prior suggestion that tenant targeting alone might resolve the authentication
gate. Successful Microsoft-account authentication does not grant ARM access.

Next supported path: operator browser sign-in to Azure portal with the intended
account, complete required MFA, verify the directory and Subscriptions/credit billing
views. For execution, use browser/WAM Azure CLI authentication in an accessible
operator environment or an administrator-approved workload identity with scoped
roles. Do not disable Security Defaults, exempt the account, transfer session tokens,
or interpret this error as proof that a subscription does not exist. This Work
session has no authenticated browser-control capability or approved Azure workload
identity. No destination entitlement, deployment, cutover or source savings claimed.

Reference: https://learn.microsoft.com/en-us/entra/fundamentals/security-defaults#block-device-code-flow

## Portal observation: destination subscription identified

Operator supplied the subscription Overview screenshot on 2026-09-06. It shows
Azure subscription 1, Active, Owner, Azure Plan, and Default Directory. The displayed
directory is consistent with prior authenticated tenant discovery. Exact identifiers
are recorded in the protected destination-portal-observation.json checkpoint; this is
portal evidence, not successful ARM discovery from the Work execution environment.
The screenshot does not establish the credit-bearing billing scope, current balance,
expiry, or spending-limit state. Azure Plan must not be treated as proof of credits.

Next: verify subscription-to-billing-profile linkage and that profile's Azure credits
view, and use the operator's authenticated Cloud Shell (without storage if offered)
for read-only resource discovery. No additional device-code authentication attempts.
No resources deployed/stopped or traffic changed; source spending remains unverified.

## Billing account credit observation: 2026-09-06

Operator supplied a billing account Summary screenshot displaying $200.00 credits
remaining, $0.00 used of $200, $0.00 due and no charges reported this month. This
confirms the displayed account-level balance, not the credit expiration, spending
limit, eligibility rules, or linkage to the identified destination subscription.
Account details are recorded in the protected portal observation checkpoint. The
portal URL is truncated, so the full billing scope ID must not be reconstructed.
Next evidence: View credits for validity/terms and View billing subscriptions for
the exact destination subscription linkage. No deployment or source savings yet.

## Execution checkpoint: destination foundation and state inventory

Status at 2026-09-07T03:14:29Z: `AUTHORIZATION_BLOCKED`. The operator's
protected checkpoint supersedes the earlier discovery-only status. Exact tenant,
subscription, billing-scope, role-assignment, and key-version identifiers remain
in protected migration records outside this public repository.

Confirmed destination state:

- The ETS Protocol Azure tenant/subscription and its Microsoft Customer Agreement
  billing linkage were verified by the operator. The billing profile displayed
  $200 Azure credit and spending limit Off; this is not permission to create
  unnecessary resources.
- Resource groups for ETS production, ETS shared services, and Lantern web
  continuity exist in East US. Required providers for Container Apps,
  App Configuration, ACR, Key Vault, Storage, Managed Identity, Network,
  Operational Insights, and Insights are registered.
- Destination ACR exists at `etsprod7c8ab70380.azurecr.io`, Basic SKU, with
  its admin account disabled.
- The qualified ETS image was imported without rebuilding and independently
  verified at the identical immutable digest
  `sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63`.
  Qualified source commit:
  `9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535`.

Confirmed source state:

- The source tenant/subscription and critical resource groups were verified.
  Core/Gateway and Lantern continuity resources remain in
  `rg-ets-live-eastus`; the fleet/PostgreSQL group remains outside the current
  migration gate and must not be modified until Core/Gateway is safely proven.
- Core Azure Table `ETSEvents` contains 73 entities in one log partition:
  36 `entry`, 36 `event_index`, and one `metadata` entity. This is
  internally consistent with `AzureTableEventStore`. Evidence migration must
  preserve the exact typed entity representation and must not replay events
  through the API.
- The source tree-head key has exactly one observed historical version. Preserve
  its exact historical key ID and public verification material in protected
  records; a destination key starts a new continuity boundary and cannot replace
  the historical identity. Retain the source vault until independent old-evidence
  verification succeeds.
- Gateway storage has shares `ets-gateway-state-q1-v2` and
  `ets-gateway-state`. The active share is `ets-gateway-state-q1-v2`;
  observed use is 262144 bytes. The live Gateway mounts it at
  `/var/lib/ets` for single-replica SQLite compatibility.

Exact resume gate:

1. Verify the signed-in source operator has `Storage File Data Privileged Reader`
   at the `etsgwo23bf2d6oq44s` storage-account scope. Do not combine
   `az role assignment list --all` with `--scope`.
2. Using OAuth and `--backup-intent`, recursively inventory both Gateway shares
   and then create protected point-in-time source snapshots.
3. Verify and remove the temporary source ACR token
   `ets-migration-read-20260906` if it still exists; it was scoped only to the
   completed cross-tenant image import.
4. Export `ETSEvents` into protected storage with exact fields and Azure data
   types, plus independently hashed manifests. Do not commit protected data.

This Work continuation began from PR head
`495e06cef50e4f85ca8b72a31c03248f69a089bd`. Its transient container no
longer held the earlier Azure CLI installation or authentication cache. A fresh
destination portal authentication reached the ETS Protocol account's additional
email-verification boundary. The browser required submission of the complete
recovery email address before sending a code; that sensitive-data transmission
was not approved, so execution stopped before submission. No role assignment,
resource, secret, DNS, traffic, evidence, storage, key, or billing setting was
changed. The Gateway authorization check, share inventory/snapshots, source ACR
token cleanup, and table backup remain unexecuted in this continuation.

## Live destination verification: 2026-09-07

At 2026-09-07T03:39:53Z, interactive Azure portal authentication completed for
the confirmed ETS Protocol account with multifactor authentication. Azure Cloud
Shell was started in ephemeral mode; no persistent Cloud Shell storage was
created by this session.

Live ARM/portal verification established:

- `Azure subscription 1` is Enabled/Active in the confirmed destination tenant.
  The signed-in migration operator is Owner. The account's accessible-subscription
  list contains only this destination subscription.
- The Startups billing surface displays `$200 in credits - Exp Dec 2, 2026`.
  Treat this as a live display observation, not permission to create unnecessary
  resources or proof that every meter is credit eligible.
- Four destination resource groups exist and report Succeeded:
  `rg-ets-prod-eastus`, `rg-ets-shared-eastus`,
  `rg-lantern-web-eastus` in East US, plus pre-existing
  `rg-ets.protocol-3456` in West US 3.
- The pre-existing non-migration group contains one Foundry account, one Foundry
  project, and one Search service. They were not created, modified, classified
  as redundant, or deleted by this migration session.
- All required migration providers report Registered:
  `Microsoft.App`, `Microsoft.AppConfiguration`,
  `Microsoft.ContainerRegistry`, `Microsoft.KeyVault`,
  `Microsoft.Storage`, `Microsoft.ManagedIdentity`,
  `Microsoft.Network`, `Microsoft.OperationalInsights`, and
  `Microsoft.Insights`.
- ACR `etsprod7c8ab70380.azurecr.io` reports provisioning Succeeded, Basic SKU,
  and admin user disabled.
- Repository `ets/hosted-q1` contains the qualified immutable manifest
  `sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63`.
  It is untagged, consistent with digest-only deployment. Two additional untagged
  manifests are present and were not modified. No image was rebuilt, retagged,
  imported, or deleted.

The destination account has no access to the source subscription, so it cannot
perform the Gateway file-role check. Azure's account-selector flow is open for a
separate source-operator sign-in. Resume there, authenticate the authorized source
work account, verify the exact subscription/tenant before any write, and then
continue with `Storage File Data Privileged Reader` verification at the Gateway
storage-account scope. No Azure mutation occurred in this checkpoint.

## Source authorization checkpoint: 2026-09-07

At 2026-09-07T03:56:24Z, separate MFA-backed authentication completed for the
authorized Echo Media source operator. Cloud Shell confirmed the expected source
subscription and tenant as Enabled/default before any scoped operation.

The exact Gateway storage authorization gate was then evaluated without combining
`az role assignment list --all` with `--scope`:

- No direct `Storage File Data Privileged Reader` assignment was returned for
  the signed-in operator at the `etsgwo23bf2d6oq44s` storage-account scope.
- Repeating the check with `--include-inherited` returned no matching assignment.
- A scope-wide inherited query returned no matching role for any visible principal.
- OAuth listing of `ets-gateway-state-q1-v2` with `--backup-intent` reproduced
  the insufficient-permissions failure. Azure CLI suggested account-key fallback;
  it was deliberately not used.

The next bounded write is to grant `Storage File Data Privileged Reader` to the
signed-in source operator at only the Gateway storage-account scope. Browser safety
requires action-time approval for this permission change; approval was not returned,
so no role assignment was created. Both share inventories and snapshots remain
blocked. No account key, SAS, secret, file content, evidence, or mutable Azure
resource was exposed or changed.

## Gateway snapshots and protected evidence backup: 2026-09-07

The source operator approved and received the least-privilege
`Storage File Data Privileged Reader` role at only the Gateway storage-account
scope. Azure reports the assignment created at
`2026-09-07T04:10:54.159846Z`. No account key or SAS was used.

OAuth plus backup intent produced the following recursive inventory:

- Active share `ets-gateway-state-q1-v2`: root only, no directories, five files,
  299008 logical bytes at inventory time: `connector-runtime.db` (53248),
  `gateway-events.db` (143360), `gateway-sync.db` (69632),
  `gateway-sync.db-shm` (32768), and `gateway-sync.db-wal` (0).
  This supersedes the earlier 256 KiB observation because the live writer
  continued to update state.
- Legacy share `ets-gateway-state`: root only, no directories, one zero-byte
  `connector-runtime.db`.

Control-plane share snapshots were created without storage keys and read back
through OAuth plus backup intent:

- active share snapshot: `2026-09-07T04:12:12.0000000Z`;
- legacy share snapshot: `2026-09-07T04:12:22.0000000Z`.

Both snapshot listings match their source file sets and lengths. These are
storage point-in-time/crash-consistent captures while the Gateway remained live;
application-consistent SQLite restoration still requires an exclusive-writer
freeze/final sync before cutover.

The temporary source ACR token `ets-migration-read-20260906` was queried on
`etsq1a352eb89` and returned ResourceNotFound. No token deletion was necessary.

A protected Azure Tables REST capture of `ETSEvents` completed at
`2026-09-07T04:16:40Z` using
`Accept: application/json;odata=fullmetadata`. The 168122-byte payload contains
75 entities: 37 `entry`, 37 `event_index`, and one `metadata` row.
The metadata row reports `next_index=37`, `schema_version=1`, and log ID
`ets-live-primary`. Validation confirmed required fields and types, unique
partition/row keys, contiguous entry and event-index log indexes 0 through 36,
and agreement between metadata high-water mark and both row counts.

Payload SHA-256:
`fe93a5a27ddb4bd0e5c09f0b5f333de77bdbc44d37b58959d69194e45b2caa21`.
The protected archive is 19792 bytes with SHA-256
`8554fe8ab3ccb37464f09573260898879b782e1dba6415edf5df9ab202bcdc6c`.
It contains the full-metadata payload, manifest, and checksum file and is retained
outside this public repository. The source-to-protected-copy archive hash was
independently rechecked after download and matched exactly.

No production traffic, DNS, Core/Gateway deployment, writer ownership, source
resource availability, signing key, or fleet/PostgreSQL resource was changed.
Next safe gate: preserve independent historical public verification material for
the exact source key version, then adapt destination infrastructure and
cross-tenant identity handling before any no-traffic deployment.

## Historical signing verification material: 2026-09-08

At `2026-09-08T00:21:30Z`, MFA-backed source access reconfirmed the expected
Enabled/default source tenant and subscription. The source vault still reports
exactly one version of `ets-tree-head`, preserving the historical version ID
`9f578feb997d49abb0a42b5e41651996`.

Only public verification material was exported. No private key material, secret,
certificate private data, or signing operation was requested. The captured key
is enabled RSA with sign/verify operations, a 384-byte (3072-bit) modulus,
creation/update time `2026-08-19T03:43:15Z`, and recovery level
`Recoverable`.

Protected outputs retained outside Git include the versioned public JWK plus
metadata, a PEM public key, a continuity manifest, and checksums. Validation
confirmed the PEM parses as a public key and its decoded RSA modulus/exponent
exactly match the JWK. Recorded hashes:

- public JWK/metadata SHA-256:
  `26f84cb98eac5f74df0ddfef481c14a77e9fe1d45b18dce2dd9bbb9857728a38`;
- PEM SHA-256:
  `316823e13778e9514e498a9d0ecbb85aa02780aea99f4697d62a7fec54fbff32`;
- SubjectPublicKeyInfo DER SHA-256:
  `9b23ad8fa446dfd10fe09405dab607da69808c33d82b229ff61b9c050eec98ec`;
- 1864-byte protected archive SHA-256:
  `eee2efdc674967c5df81cb5002ef46e6417e2b90606a65e2f5d6abfd9c81476a`.

The archive hash matched after source-to-protected-storage transfer. Historical
signatures must continue to reference the exact source key-version ID. A
destination key is a new signing identity and cannot be represented as the
historical key. The source vault remains required until independent verification
of old evidence succeeds; no key or vault setting was changed.

Next executable gate is repository adaptation for separated Azure deployment
tenant and Microsoft/SharePoint directory tenant, followed by an isolated
destination infrastructure what-if before resource creation. No traffic, DNS,
writer ownership, source availability, or fleet/PostgreSQL resource changed in
this checkpoint.



## Destination identity adaptation and infrastructure what-if: 2026-09-08

Repository adaptation now separates the Azure deployment tenant from the
EchoMedia Microsoft resource tenant instead of replacing one tenant ID with the
other. The existing same-tenant managed-identity route remains the default for
the source deployment. A new fail-closed
`federated_managed_identity` route uses three distinct destination
user-assigned managed identities as assertions for three distinct multitenant
applications registered in the ETS Protocol tenant and provisioned into the
EchoMedia tenant. The runtime exchanges
`api://AzureADTokenExchange/.default` assertions through
`ClientAssertionCredential`; no application secret, certificate private key,
or cross-tenant managed-identity attachment is introduced.

The EchoMedia service principals must receive only their existing bounded
connector permissions: the approved SharePoint `Sites.Selected` grant for the
existing site/drive, `User.Read.All` plus `Group.Read.All` for directory
collection without `Directory.Read.All`, and the existing Office 365
Management Activity permission for Purview. No permission was granted and no
application or service principal was created in this checkpoint.

Both Core and Gateway Bicep templates now expose
`runtimeMinReplicas`, restricted to zero or one and defaulting to one.
Migration staging must pass zero explicitly. This prevents the destination
containers from starting or competing for writer ownership while storage,
identity, and authorization are prepared. Static tests cover the zero-replica
control and the separated application IDs. The legacy source path remains
backward compatible.

MFA-backed destination access was reconfirmed for subscription
`5729a82b-8850-4868-b96c-96c3805cbb9d` in tenant
`0d20cf0f-3498-46c1-a0db-69b09c634cc2`. The destination ACR was re-read in
`rg-ets-shared-eastus` with Basic SKU and its admin account disabled.
`rg-ets-prod-eastus` contained zero resources before the checks.

The exact PR templates compiled in ephemeral destination Cloud Shell. Azure
Resource Manager what-if then evaluated them against
`rg-ets-prod-eastus` using the qualified immutable image digest and
`runtimeMinReplicas=0`:

- Core: 17 resources predicted for creation and one unsupported prediction;
- Gateway: 12 resources predicted for creation and one unsupported prediction.

In both cases the unsupported item is the ACR pull role assignment whose
destination identity principal ID cannot be calculated until deployment. No
other diagnostic was reported. A post-what-if resource inventory again returned
zero resources, proving the operation did not create the destination stack.

GitHub Hosted Azure Bicep, the new unit tests, Ruff, mypy, CodeQL,
Security Audit, Formal Specs, and all other PR workflows completed successfully
for checkpoint `4c002af9118ce7872891464bc1f7bae793792f92`. The clean CI rerun
therefore clears the repository validation gate.

The zero-replica destination deployment gate was subsequently approved and
executed. Its read-back and safety results are recorded in the next checkpoint.


## Destination Core and Gateway zero-replica deployment: 2026-09-08

The approved destination deployment used the exact PR checkpoint
`4c002af9118ce7872891464bc1f7bae793792f92`, the existing Basic ACR
`etsprod7c8ab70380` with its admin account disabled, and the qualified
immutable image:

`etsprod7c8ab70380.azurecr.io/ets/hosted-q1@sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63`

No image rebuild, mutable tag, ACR admin credential, source subscription write,
traffic change, DNS change, or fleet/PostgreSQL change occurred.

The Core deployment `ets-migration-core-zero-20260908` initially reached all
resource creations except its four App Configuration key-value child resources.
The store correctly had local authentication disabled and ARM data-plane proxy
mode set to `Pass-through`; the remaining failure was the deployment caller's
missing data-plane role. The operator object
`f8a7dadf-a4a7-4ed6-8ebd-76abf97b8bb7` received
`App Configuration Data Owner` at only the destination store scope
`.../configurationStores/ets-v5j37z3xe76tm-cfg` (role assignment
`bff25385-49c9-4bf5-a2e0-35b01f0519b5`). After RBAC propagation, the same
idempotent deployment succeeded at `2026-09-08T15:06:48.810708Z`,
correlation ID `0af451f1-9160-46ad-8099-4cbbfcce30ac`. ARM operation
read-back reports `Succeeded` for all four non-secret settings:
`ETS_SIGNING_MODE`, `ETS_AZURE_MANAGED_IDENTITY_ENABLED`,
`ETS_AZURE_KEY_VAULT_URL`, and `ETS_AZURE_KEY_NAME`.

Created Core resources include:

- Container App `ets-v5j37z3xe76tm-api`;
- managed environment `ets-v5j37z3xe76tm-cae`;
- storage account `etsv5j37z3xe76tm`, table `ETSEvents`;
- Key Vault `ets-v5j37z3xe76tm-kv`;
- App Configuration `ets-v5j37z3xe76tm-cfg`;
- Application Insights `ets-v5j37z3xe76tm-appi`;
- runtime identity `ets-v5j37z3xe76tm-identity`;
- ACR pull identity `ets-v5j37z3xe76tm-pull`.

Core read-back at `2026-09-08T15:12:07Z` confirmed internal-only ingress,
`minReplicas=0`, `maxReplicas=1`, the exact immutable image digest, and one
healthy active revision with zero replicas. Scoped RBAC read-back confirmed
`Key Vault Crypto User` for the runtime identity at only the destination vault,
`Storage Table Data Contributor` at only the destination `ETSEvents` table,
and `AcrPull` for the pull identity at only the destination registry.

The destination signing key is a new identity created
`2026-09-08T14:47:14Z`:

`https://ets-v5j37z3xe76tm-kv.vault.azure.net/keys/ets-tree-head/ab08ef62e5d44637a3409d68cadd0bf1`

It must never be substituted for historical source key version
`9f578feb997d49abb0a42b5e41651996`. The protected source public-key archive
and source vault retention requirement remain unchanged.

The Gateway deployment `ets-migration-gateway-zero-20260908` succeeded at
`2026-09-08T15:02:37.952815Z`, correlation ID
`c987d982-3148-49d0-a427-d56836785abf`. It created:

- Container App `ets-oif5r5ydprrou-gw`;
- runtime, directory, Purview, and pull identities
  `ets-oif5r5ydprrou-gw-id`, `ets-oif5r5ydprrou-gw-dir-id`,
  `ets-oif5r5ydprrou-gw-pur-id`, and `ets-oif5r5ydprrou-gw-pull`;
- state storage `etsgwoif5r5ydprrou` and active share
  `ets-gateway-state-q1-v2`;
- Key Vault `ets-oif5r5ydprrou-gkv`.

Destination UAMI identifiers for guarded cross-tenant provisioning are:

| Identity | Client ID | Principal ID |
| --- | --- | --- |
| Gateway runtime | `5c4edb37-106e-4093-beda-fdafcf04479d` | `46a5589a-37dc-4d5e-8d61-d0582b7dce61` |
| Gateway directory | `6f657f0d-1fcb-450c-9985-919ed6adc5fe` | `51ef8c3b-a486-446e-9c89-14013d1cd167` |
| Gateway Purview | `f1a002e8-f22b-44d5-ba17-806d582b6695` | `fdfffcbc-13b9-4438-a35c-b882a59dc5e6` |
| Gateway ACR pull | `73e59a1f-2cba-4891-befb-3a70dc9bfc70` | `35b23aaf-a256-4194-9835-c3a5ddc75977` |
| Core runtime | `89a3822f-de30-45b0-bbb4-e527780e04ac` | `c8b20188-7514-48d0-bece-26504329c3c2` |
| Core ACR pull | `43478ec2-60a5-40b9-bf6b-1d039dfdeb78` | `e9848794-027b-4b99-a5f5-30f5e1db2af4` |

Gateway read-back confirmed internal-only ingress, `minReplicas=0`,
`maxReplicas=1`, and the exact immutable image. Azure started one transient
replica while provisioning revision `ets-oif5r5ydprrou-gw--zsyz55n`.
Although all Microsoft application, drive, tenant/workspace, and authorization
values were explicit non-production placeholders, the revision was immediately
deactivated. Final read-back reports `active=false` and `replicas=0`.
Core also remains at zero replicas. There are no destination writers and no
production traffic.

The next protected-state gate is to inventory the new Gateway share for any
initialization files left by the transient provisioning replica, verify the new
`ETSEvents` table, and then restore the protected source snapshots/exports
without replaying events. This requires narrowly scoped destination data-plane
operator roles and action-time approval before permission changes and protected
data transfer. Cross-tenant application registrations, federated credentials,
EchoMedia service principals/admin consent, and `Sites.Selected` grants remain
uncreated and require a separate guarded authorization checkpoint.


## Destination pre-restore data-plane inventory: 2026-09-08

After explicit action-time approval, destination operator
`f8a7dadf-a4a7-4ed6-8ebd-76abf97b8bb7` received two read-only data-plane
roles at the narrowest practical scopes:

- `Storage File Data Privileged Reader` on storage account
  `etsgwoif5r5ydprrou`, role assignment
  `4bc8063e-5339-4a33-a03a-caf5d1a4875a`;
- `Storage Table Data Reader` on only
  `etsv5j37z3xe76tm/tableServices/default/tables/ETSEvents`, role assignment
  `2d93f196-e358-4c36-af76-8ea1cfd2fe89`.

OAuth plus backup intent confirmed that the transient Gateway provisioning
replica initialized three files in destination share
`ets-gateway-state-q1-v2`:

| File | Bytes | Last modified | SHA-256 |
| --- | ---: | --- | --- |
| `connector-runtime.db` | 36864 | `2026-09-08T15:04:00Z` | `bccf48a25e87817107ef379f47b706a7517e36e252a91d735db1b15311c20e91` |
| `gateway-events.db` | 32768 | `2026-09-08T15:02:56Z` | `0d5224bc01e6ab193c7f577eb7556fdd1dfd77f5879435e3d7faa5872cbf9a67` |
| `gateway-sync.db` | 28672 | `2026-09-08T15:02:56Z` | `4d15ca448b106f4a4e001f38aefbcba418ed3dec5a30c45cd999925245bd5ab8` |

Python standard-library SQLite read-only checks returned `ok` for all three
files. The initialized event and sync queues are empty:
`artifact_records=0`, `events=0`, `sync_meta=0`, and `sync_queue=0`.
The connector database has one row each in `connector_instances`,
`connector_runtime`, and `connector_admin_audit`; these are the inert
placeholder initialization records, not migrated source state.

Before any overwrite, a non-destructive share snapshot was created at
`2026-09-08T16:06:59.0000000Z`. OAuth plus backup-intent read-back of that
snapshot matches the three live-share file names, byte lengths, and
last-modified values above.

The destination `ETSEvents` table contains exactly one initialized metadata
entity:

- `PartitionKey=log-bd744418f1f73463f9cf6ecf92bad9e3`;
- `RowKey=meta`, `kind=metadata`;
- `log_id=ets-live-primary`, `next_index=0`, `schema_version=1`;
- service timestamp `2026-09-08T14:48:24.267079Z`.

This is initialization state and not migrated evidence. Its partition key may
be deterministically derived from `ets-live-primary`; equality with the protected
source partition must be checked directly against the protected export before
restoration. The row must then be replaced by the protected metadata entity,
not treated as an additional event-log partition. No destination file or table entity was overwritten, updated,
or deleted in this checkpoint. Both Container Apps remain at zero replicas.

The next write gate requires a destination file contributor role, a destination
table contributor role, protected source artifact rehydration, and explicit
authorization to transmit the protected Gateway snapshot files and 75 ETS table
entities into the ETS Protocol subscription. The destination initialization
snapshot and recorded metadata provide rollback for that operation.

## Protected Core/Gateway state restored and verified: 2026-09-09

At `2026-09-09T12:21:31Z`, the fixed pre-cutover Core/Gateway checkpoint
was restored into the isolated ETS Protocol destination. No destination
Container App was started and no production traffic, DNS, source resource, fleet,
PostgreSQL resource, historical key, or Lantern route was changed.

After explicit authorization, destination operator
`f8a7dadf-a4a7-4ed6-8ebd-76abf97b8bb7` received:

- `Storage File Data Privileged Contributor` on
  `etsgwoif5r5ydprrou`, assignment
  `e5c6e1c0-e629-4dfb-bf06-78e9658d149d`;
- `Storage Table Data Contributor` on only
  `etsv5j37z3xe76tm/tableServices/default/tables/ETSEvents`, assignment
  `38d6bfba-1bf7-42be-82da-aff083d403d6`.

Protected inputs were rehydrated outside Git and verified before transfer:

| Protected input | SHA-256 |
| --- | --- |
| `ets-gateway-snapshot-20260907T041212Z.tar.gz` | `f7090e361a372dea23dc6abd57a46e643231b0187e06c69e278fd89067b2e508` |
| `ets-azure-table-backup-20260907T041640Z.tar.gz` | `8554fe8ab3ccb37464f09573260898879b782e1dba6415edf5df9ab202bcdc6c` |
| `ETSEvents.fullmetadata.json` | `fe93a5a27ddb4bd0e5c09f0b5f333de77bdbc44d37b58959d69194e45b2caa21` |
| evidence manifest | `465e75160fd9d7bbd51843ad750309dd6fae769b6b664cc2fe861ab2f30d0818` |

The Gateway active share `ets-gateway-state-q1-v2` was restored by OAuth
with Azure Files backup intent. The three initialization databases were replaced
and the source snapshot's SQLite companion files were added. Independent
download/read-back produced:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `connector-runtime.db` | 53248 | `e10bf7a367d6cc64ad91267cb505b3c11b9e05f9697575753419d1543a8d04ff` |
| `gateway-events.db` | 143360 | `719b3562d6eda3f5850c5f246059f5a034a5439915c64d36514e04116785b9ee` |
| `gateway-sync.db` | 69632 | `c73ff918b6522d1c3b742aaed5df67ce3a734b77be9d55820245b369411066aa` |
| `gateway-sync.db-shm` | 32768 | `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb` |
| `gateway-sync.db-wal` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Python standard-library SQLite read-back returned `ok` for all three
databases. A first combined upload command disconnected before changing the
share; a live size inventory proved the initialization files were still intact
before the successful bounded retry.

The protected `ETSEvents` export contained exactly 75 typed entities:
37 `entry`, 37 `event_index`, and one `metadata`. Its metadata
partition and row matched the destination initialization row, so no additional
row deletion was required. A guarded insert-or-replace restore removed only
service-assigned `Timestamp`/OData fields from request bodies; it retained every
application property, including keys, exact `event_json`, event and leaf
hashes, event-ID mappings, log indexes, log ID, schema version, and
`next_index`. The first REST attempt used update-only semantics and returned
HTTP 404 on the first nonexistent entity before any write. The corrected,
resumable attempt completed and canonical comparison of every preserved property
returned:

`3fc28604e15cd3bb132440f205f8b0432e035fd1735d50542e7116a5c8f6194a`

Independent Azure CLI read-back confirmed 75 total entities, 37 entries,
37 event indexes, one metadata row, and `next_index=37`. Service-assigned
timestamps and ETags are destination values; originals remain in the protected
full-metadata export and manifest.

Post-restore scale/read-back remains fenced:

- Core `ets-v5j37z3xe76tm-api`: `minReplicas=0`,
  active revision has zero replicas;
- Gateway `ets-oif5r5ydprrou-gw`: `minReplicas=0`, no active revisions.

The initialization rollback snapshot
`2026-09-08T16:06:59.0000000Z` remains available. A post-restore share
snapshot was not created: the CLI does not support OAuth for that operation and
the direct OAuth management request failed closed with
`FileOAuthManagementApiRestrictedToSrp`. No account key or SAS was obtained or
used.

This is a protected validation checkpoint, not a cutover checkpoint. Source
Core remained live and had advanced to 89 entities (44 entries, 44 event indexes,
one metadata row with `next_index=44`) when checked before restore. Therefore
the destination is seven events behind current source state. Do not start a
destination writer. Final synchronization requires an exclusive source write
freeze, a new exact typed export or validated seven-event delta, full
preserved-property comparison, and explicit writer ownership transfer.

Historical source signing version
`9f578feb997d49abb0a42b5e41651996` remains unchanged and retained. The
destination signing key remains a new continuity boundary, not a historical-key
replacement. The next executable gate is cross-tenant Microsoft identity
provisioning and connector qualification, followed by final freeze/sync; both
require their own scoped permission and consent checkpoint.

