# Microsoft P0 protected live release sequence v1

Parent: #537

Live slices: #540 (RC1B) and #539 (RC1C)

## Purpose

This sequence binds the separated Microsoft runtime, immutable image publication, private Azure
deployment, and the RC1B/RC1C read-only preflights to one exact approved `main` SHA. It does not
freeze a candidate, authorize Purview subscription mutation, start the 72-hour soak, or activate
public ingress.

## 1. Pre-create the separated identities

Run `.github/workflows/live-gateway-identity-bootstrap.yml` manually from `main` in the protected
`ets-azure-q1` environment. Retain its sanitized artifact and #537 handoff. The SharePoint/Core,
directory, and Purview UAMIs must be present and distinct; no application role is assigned by this
workflow.

## 2. Preview and apply only the approved Microsoft roles

On a trusted operator workstation, run
`scripts/azure/provision-microsoft-p0-connector-app-roles.ps1` without `-Apply`. Review the active
tenant, verified domain, exact identities, resource applications, and complete assignment sets.
Only after that review, repeat with `-Apply`.

The permitted result is exact:

- directory UAMI: Microsoft Graph `User.Read.All` and `Group.Read.All`;
- Purview UAMI: Office 365 Management APIs `ActivityFeed.Read`; and
- SharePoint/Core UAMI: unchanged by this bootstrap.

Any unexpected or duplicate role fails closed. No Graph file-wide role or subscription role is
permitted.

## 3. Publish the exact Q0 image

Dispatch `.github/workflows/hosted-azure-q0-image.yml` from the intended current `main` SHA with:

- `container_registry_name=etsq1a352eb89`;
- `container_registry_resource_group=rg-ets-q1-eastus`; and
- `image_repository=ets/hosted-q1`.

Proceed only after the run succeeds and retains its exact immutable image, SPDX SBOM, provenance
attestations, and passing fixable-HIGH/CRITICAL vulnerability gate. Record the workflow run ID,
source SHA, and full `registry/repository@sha256:<digest>` reference.

## 4. Deploy the exact private runtime

Dispatch `.github/workflows/live-core-gateway-deployment.yml` from `main` with the exact Q0
`image_source_sha`, `container_image`, and `q0_workflow_run_id`.

Before Azure mutation the workflow requires the dispatch SHA to equal the Q0 source, verifies the
successful Q0 run and retained evidence, and re-reads the three pre-created identities. After
deployment it verifies:

- Core and Gateway use the same immutable image;
- ingress remains internal and both apps remain single-replica;
- SharePoint/Core, directory, and Purview identities use lifecycle `Main`;
- the distinct ACR pull identity uses lifecycle `None`;
- the server-owned tenant/workspace scope map remains exact; and
- Graph lifecycle configuration remains absent: no callback, clientState, lifecycle timing, or
  health policy is configured.

## 5. Run the protected read-only preflights

Run both workflows from the unchanged `main` SHA with the same `image_source_sha`,
`container_image`, and deployment-authoritative `connector_instance_id`:

1. `.github/workflows/live-microsoft-rc1b-preflight.yml` for the dedicated directory identity,
   bounded users/groups delta reachability, SharePoint negative control, and query-only durable
   state;
2. `.github/workflows/live-microsoft-rc1c-preflight.yml` for the dedicated Purview identity,
   exact Office 365 Management audience/role, read-only `Audit.General` subscription listing,
   query-only runtime state, and the accepted Graph deferral boundary.

Each workflow creates and removes only an ephemeral Azure Container Apps job and retains sanitized
evidence. A passing preflight still fixes `rc1b_live_qualified=false` or
`rc1c_live_qualified=false` because the broader tombstone/replay/throttle/recovery and Purview
mutation/recovery matrices remain separate gates.

## Stop conditions

Stop without advancing if `main` moves, the image or Q0 evidence differs, any identity/permission
set drifts, the Gateway is public or multi-replica, Graph lifecycle state/configuration appears, a
preflight fails, or public evidence would retain a credential or customer identifier. Do not reuse
the invalidated #479 soak attempt.
