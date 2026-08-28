# Microsoft P0 protected live release sequence v1

Parent: #537

Live slices: #540 (RC1B), #539 (RC1C), and #541 (RC1D)

## Purpose

This sequence binds the separated Microsoft runtime, immutable image publication, private Azure deployment, protected RC1B/RC1C qualification, and RC1D pre-soak reconciliation to one exact approved `main` SHA. It does not authorize public ingress. RC1D does not freeze a candidate; candidate freeze and soak start occur only after a passing RC1D reconciliation.

## 1. Pre-create the separated identities

Run `.github/workflows/live-gateway-identity-bootstrap.yml` manually from `main` in the protected `ets-azure-q1` environment. Retain its sanitized artifact and #537 handoff. The SharePoint/Core, directory, and Purview UAMIs must be present and distinct; no application role is assigned by this workflow.

## 2. Preview and apply only the approved Microsoft roles

On a trusted operator workstation, run `scripts/azure/provision-microsoft-p0-connector-app-roles.ps1` without `-Apply`. Review the active tenant, verified domain, exact identities, resource applications, and complete assignment sets. Only after that review, repeat with `-Apply`.

The permitted result is exact:

- directory UAMI: Microsoft Graph `User.Read.All` and `Group.Read.All`;
- Purview UAMI: Office 365 Management APIs `ActivityFeed.Read`; and
- SharePoint/Core UAMI: unchanged by this bootstrap.

Any unexpected or duplicate role fails closed. No Graph file-wide role or subscription role is permitted.

## 3. Publish the exact Q0 image

Dispatch `.github/workflows/hosted-azure-q0-image.yml` from the intended current `main` SHA with:

- `container_registry_name=etsq1a352eb89`;
- `container_registry_resource_group=rg-ets-q1-eastus`; and
- `image_repository=ets/hosted-q1`.

Proceed only after the run succeeds and retains its exact immutable image, SPDX SBOM, provenance attestations, and passing fixable-HIGH/CRITICAL vulnerability gate. Record the workflow run ID, source SHA, and full `registry/repository@sha256:<digest>` reference.

## 4. Deploy the exact private runtime

Dispatch `.github/workflows/live-core-gateway-deployment.yml` from `main` with the exact Q0 `image_source_sha`, `container_image`, and `q0_workflow_run_id`.

Before Azure mutation the workflow requires the dispatch SHA to equal the Q0 source, verifies the successful Q0 run and retained evidence, and re-reads the three pre-created identities. After deployment it verifies:

- Core and Gateway use the same immutable image;
- ingress remains internal and both apps remain single-replica;
- SharePoint/Core, directory, and Purview identities use lifecycle `Main`;
- the distinct ACR pull identity uses lifecycle `None`;
- the server-owned tenant/workspace scope map remains exact; and
- Graph lifecycle configuration remains absent: no callback, clientState, lifecycle timing, or health policy is configured.

## 5. Run the protected RC1B and RC1C read-only preflights

Run both workflows from the unchanged `main` SHA with the same `image_source_sha`, `container_image`, and deployment-authoritative `connector_instance_id`:

1. `.github/workflows/live-microsoft-rc1b-preflight.yml` for the dedicated directory identity, bounded users/groups delta reachability, SharePoint negative control, query-only durable state, and the isolated users/groups/OneDrive polling fault matrix;
2. `.github/workflows/live-microsoft-rc1c-preflight.yml` for the dedicated Purview identity, exact Office 365 Management audience/role, read-only `Audit.General` subscription listing, query-only runtime state, and the accepted Graph deferral boundary.

Each workflow creates and removes only an ephemeral Azure Container Apps job and retains sanitized evidence. RC1B may set `rc1b_live_qualified=true` only when its live proof and all synthetic cursor/tombstone/replay/throttle/expired-cursor/evidence-loss predicates pass. RC1C read-only preflight remains a prerequisite to the protected subscription recovery gate.

## 6. Prove bounded Purview subscription mutation, start/stop/restart, and polling recovery

After both read-only preflights pass on the unchanged candidate, review and manually dispatch `.github/workflows/live-microsoft-rc1c-subscription-recovery.yml` with the same exact source, image, and connector instance. The protected input must include the exact confirmation `START_STOP_RESTART_AUDIT_GENERAL`.

The protected Purview subscription mutation exercise performs an idempotent `Audit.General` start/stop/restart sequence with bounded content listing and no webhook. A protected retry may begin enabled only when retained prior failure and later read-only preflight evidence prove the exact guarded resume state. The same release image then runs the isolated RC1C polling fault matrix against synthetic fixtures and temporary durable state. It must finish enabled; any failure after mutation triggers bounded restoration.

Passing fixes `rc1c_live_qualified=true` and `soak_clock_started=false`.

## 7. Prove shared Gateway durable-state and recovery state

Before reconciliation, run the hardened protected Gateway evidence paths from the same unchanged `main` SHA and deployed image:

1. `.github/workflows/live-sharepoint-state-boundary-probe.yml` must retain a healthy terminal delta checkpoint and synchronized synthetic marker with no open gap or failed marker queue state;
2. `.github/workflows/live-sharepoint-relay-recovery.yml` must prove the bounded relay/gap recovery path, finish healthy, leave no terminal or retryable relay rows, reconcile the marker, and retain no customer identifiers, reusable credentials, event identifiers/hashes, or Core payload.

These runs are evidence inputs to RC1D; they do not freeze the candidate or start soak.

## 8. Reconcile RC1D and prepare the freeze-ready candidate

Dispatch `.github/workflows/live-microsoft-rc1d-pre-soak-reconciliation.yml` with the exact Q0, RC1B, RC1C, Gateway state, and Gateway recovery workflow run IDs plus the exact immutable image.

The gate verifies every selected run is a completed successful manual run from `main` at the reconciliation SHA and downloads only the exact retained artifacts from those runs. It fails closed on source/image drift, schema drift, incomplete supply-chain evidence, failed RC1B/RC1C predicates, unhealthy Gateway state, incomplete Gateway recovery, Graph-deferral violations, credential/customer-identifier retention, or an already-started soak clock.

A successful run emits `ets.live_microsoft.rc1d_pre_soak_candidate.v1` with `pre_soak_reconciliation_passed=true`, `freeze_ready=true`, `candidate_frozen=false`, and `soak_clock_started=false`. See [`MICROSOFT_P0_RC1D_PRE_SOAK_RECONCILIATION_V1.md`](./MICROSOFT_P0_RC1D_PRE_SOAK_RECONCILIATION_V1.md).

## 9. Freeze and start the new governed 72-hour soak

Only after RC1D passes may the exact source/image pair named by its retained artifact be frozen. Any source, image, identity, permission, configuration, or out-of-contract state mutation after freeze invalidates the candidate and requires a new Q0 and RC1D reconciliation.

Dispatch `.github/workflows/live-m365-source-to-proof-soak.yml` from that unchanged `main` SHA with:

- `rc1d_workflow_run_id=<successful RC1D run>`;
- `start_confirmation=START_72_HOUR_MICROSOFT_P0_SOAK`;
- the bounded synthetic `marker`; and
- `restart_active=false` for a normal new attempt.

The coordinator downloads the exact RC1D artifact and derives the frozen source/image from it; arbitrary workflow input cannot choose a different release candidate. The first successful governed observation records the freeze and starts the clock in #541.

Hourly observations are non-destructive and cover the complete P0 family: parameterized SharePoint source-to-proof, RC1B Entra/OneDrive read-only qualification, RC1C Purview read-only qualification with `Audit.General` still enabled, and Gateway durable state. The coordinator never runs Purview subscription mutation/recovery after freeze. It requires at least 72 elapsed hours and 72 successful governed observations, with no monitoring gap over 110 minutes.

See [`MICROSOFT_P0_RC1D_SOAK_V1.md`](./MICROSOFT_P0_RC1D_SOAK_V1.md) for the freeze, invalidation, privacy, and completion contract. The invalidated #479 attempt is never resumed or counted.

## Stop conditions

Stop without advancing if `main` moves, the image or Q0 evidence differs, any identity/permission set drifts, the Gateway is public or outside its qualified replica posture, Graph lifecycle state/configuration appears, a protected gate fails, recovery evidence is incomplete, or public evidence would retain a credential or customer identifier.
