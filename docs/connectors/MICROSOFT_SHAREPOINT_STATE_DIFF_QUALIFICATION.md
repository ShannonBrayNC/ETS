# Microsoft SharePoint/OneDrive state-diff qualification

Status: G2E-DQ candidate  
Tracks: #331  
Depends on: merged #329

## Purpose

G2E-DQ extends the qualified metadata-only Microsoft Graph delta connector with bounded operational
prior-state, derived metadata transition claims, minimized sharing observations, notification-assisted
recollection, and explicit recovery behavior. It does not turn Graph delta into an audit history.

## Ordering invariant

For every collected metadata page, ETS applies this ordering:

1. collect the next bounded Graph delta page from the current source checkpoint;
2. normalize the observed metadata without authoritative tenant/workspace claims;
3. classify any derived transition against the last **committed** operational snapshot without
   mutating that snapshot;
4. commit the observed metadata plus the separately labeled derived-transition claim to ETS;
5. durably queue the committed observation for synchronization;
6. only after every page observation reaches queued state, release the new operational snapshots;
7. only after that release succeeds may the source checkpoint be persisted.

Backpressure, append-before-enqueue partial failure, or operational-state release failure therefore
cannot silently advance the SharePoint prior-state or source cursor.

## Derived transition claim

The derived claim is explicitly labeled
`ets.connector.microsoft.sharepoint.metadata_transition.v1`. Its basis is successive minimized
metadata observations and it contains only bounded transition kinds and prior/current metadata
fingerprints. The underlying observed metadata remains present in the committed connector metadata.

Supported classifications are:

- `baseline_observation`;
- `observed_deleted`;
- `created`;
- `updated`;
- `renamed`;
- `moved`;
- `deleted`;
- `restored`;
- `unchanged`.

These classifications are connector-derived claims. They are not Microsoft audit events and do not
attribute an actor.

## Sharing/privacy boundary

The approved delta metadata profile may retain only bounded sharing state surfaced in the collected
item metadata: sharing scope, sharing timestamp, and the source `sharedChanged` signal. Identity-bearing
`owner` and `sharedBy` material, email/display-name data, arbitrary permission objects, file content,
and download URLs are not retained by this profile.

## Notification-assisted recollection

The SharePoint layer reuses the qualified Microsoft Graph subscription/notification validation
boundary. A valid notification creates an operational recollection directive only. It does not create
ETS evidence and does not advance the delta checkpoint.

Duplicate notifications repeat the same recollection directive. `missed` and
`subscriptionRemoved` lifecycle signals mark a possible observation gap. Recollection resumes from
the exact preserved Graph delta checkpoint; polling/delta remains authoritative for progress.

## Inaccessible and unsupported source state

Authorization denial, terminal/unsupported source failure, and expired delta state remain explicit
operational outcomes. They produce no invented object observation and do not replace the last durable
checkpoint. Expired source state requires separately authorized recovery.

## Nonclaims

G2E-DQ does not claim complete SharePoint/OneDrive history, source truth or completeness, actor
attribution, raw-content custody, legal-hold semantics, or that Graph notifications themselves prove a
change occurred. The qualification target is bounded metadata observation and deterministic derived
state under the ordering invariant above.
