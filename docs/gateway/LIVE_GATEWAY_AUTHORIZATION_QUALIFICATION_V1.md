# Live Gateway authorization qualification v1

## Purpose

This gate runs only after the persistent live ETS Core and Microsoft Gateway resources have
successfully deployed. It proves the two independent authorization predicates required before the
SharePoint source-to-proof gate can begin:

1. the exact live Gateway managed identity can obtain an app-only Core token carrying the governed
   `evidence_producer` application role; and
2. an authenticated app-only principal that is mapped to the same ETS tenant/workspace but lacks
   `evidence.create` is denied ingestion with HTTP 403 and `ETS_AUTH_FORBIDDEN`.

The gate does not grant SharePoint access, create a Microsoft Graph subscription, claim Microsoft
source health, or start the 72-hour soak.

## Positive control

The same-environment qualification job attaches the exact pre-qualified Gateway UAMI
`ets-o23bf2d6oq44s-gw-id` as its runtime identity and the existing pull-only ACR identity only for
image retrieval. The job uses the authoritative immutable Q0 image already deployed by the live
Core/Gateway gate.

The client:

- obtains the configured Core `/.default` token through `ManagedIdentityCredential`;
- requires an app-only token whose application/client claim is the exact Gateway UAMI client ID;
- requires the token audience to equal the deployed Core application audience;
- requires the role set to contain exactly `evidence_producer`;
- submits one minimized synthetic authorization event without caller-supplied ETS scope headers;
- requires Core to accept the append; and
- retrieves and independently verifies the returned inclusion proof locally.

The short-lived bearer is never emitted to workflow logs or retained in an artifact.

## Negative control

The workflow creates one ephemeral Azure UAMI with no Core application-role assignment. Core's
server-owned app-to-ETS-scope map is temporarily extended with only that control client ID and the
same protected ETS tenant/workspace binding. This deliberately proves that scope selection is not
permission to create evidence.

The negative-control job must prove all of the following:

- a Core-audience app-only token can be acquired for the control identity;
- the token contains no ETS Core application roles;
- the token application/client claim matches the ephemeral control identity;
- the request is authenticated and scope-mapped by Core; and
- evidence ingestion is denied with HTTP 403 and `ETS_AUTH_FORBIDDEN`.

No `evidence_producer` grant is created for the control identity.

## Mandatory restoration

The original single-client app-to-ETS-scope map is a release invariant. An `always()` cleanup step
therefore:

1. restores the exact protected original map;
2. re-reads Core and requires semantic equality with that map;
3. requires the restored map to contain exactly the Gateway client ID;
4. deletes both ephemeral qualification jobs; and
5. deletes the negative-control UAMI.

The qualification cannot publish a success handoff unless restoration succeeds.

## Evidence boundary

Retained evidence contains only bounded boolean/status predicates, the already-public release image
identity, and the workflow source SHA. It does not retain:

- bearer tokens;
- Gateway or control client/principal IDs;
- ETS tenant/workspace IDs;
- SharePoint drive IDs;
- the temporary app-scope map; or
- reusable credentials.

The successful handoff may claim Core health/readiness during the authorization check, producer-token
acceptance, negative-control denial, proof verification, exact scope-map restoration, and ephemeral
identity removal. It must continue to state:

- full Gateway/Microsoft runtime health claimed: `false`;
- M365 source-to-proof claimed: `false`; and
- 72-hour soak clock started: `false`.

## Next gate

After this authorization qualification succeeds, proceed to #390:

1. grant the exact Gateway UAMI the approved EchoMedia `Sites.Selected` boundary;
2. create/register the real Graph subscription and governed health policy;
3. create or modify a controlled document in the designated SharePoint library;
4. retain one minimized Gateway event and synchronize it to Core;
5. independently verify the resulting ETS proof;
6. prove notification/delta recovery, duplicate suppression, unauthorized-site denial, revision
   evidence, and restart persistence; and
7. start the 72-hour soak only after the first retained source-to-proof probe succeeds.
