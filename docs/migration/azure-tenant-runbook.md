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
