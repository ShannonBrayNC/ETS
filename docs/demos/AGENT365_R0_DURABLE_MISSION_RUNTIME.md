# Agent 365 + Ranger R0 durable mission runtime

## Purpose

PR #843 exposed verified `mission_id` reconstruction over HTTP but still required the
process to receive an already-built in-memory mission index. This P0 step removes that
fixture boundary.

The runtime now starts from retained evidence on disk:

```text
completed R0 Evidence Object v2 bundle
  -> SQLiteRangerR0MissionBundleStore.save(...)
  -> durable SQLite volume
  -> process restart
  -> hash-check retained envelope
  -> reconstruct typed Evidence Object v1 + v2 objects
  -> re-run Evidence Object v2 verification
  -> build RangerR0MissionIndex
  -> authenticated HTTP mission API
```

A mission is never admitted to the HTTP query index merely because a SQLite row exists.
The retained envelope hash and the complete Evidence Object v2 verification boundary must
both pass at startup and again during mission reconstruction.

## Durable storage contract

`ets/ranger/agent365_r0_mission_store.py` adds
`SQLiteRangerR0MissionBundleStore`.

The retained row contains the complete Step 5 bundle required by the demo:

- canonical `mission_id`;
- Evidence Object v2 JSON and its retained identity hash;
- Step 4 Ranger Decision Event;
- Evidence Object v1 JSON and retained object hash;
- evidence-bundle reference; and
- the exact retained source-artifact bytes encoded as base64 inside the durable envelope.

The complete envelope is serialized deterministically and committed by SHA-256. SQLite
uses WAL mode and `synchronous=FULL` for the local P0 profile.

### Retry semantics

Writing the exact same retained bundle for the same `mission_id` is idempotent. A retry
that presents different evidence for an already-retained `mission_id` fails closed with
`duplicate_mission_conflict`; it never overwrites history.

## Hosted runtime

`ets/ranger/agent365_r0_mission_runtime.py` composes the durable store and the HTTP API.
Start it with:

```bash
export ETS_AGENT365_R0_BUNDLE_DB=/var/lib/ets/agent365-r0-missions.db
export ETS_AUTH_MODE=local_api_key
export ETS_LOCAL_API_KEY='<development key of at least 16 characters>'
python -m ets.ranger.agent365_r0_mission_runtime
```

The default port is `8001`. Override it with `ETS_AGENT365_R0_PORT`.

`GET /ready` reports runtime readiness, storage profile, authentication mode, and the
number of verified missions loaded from retained state. `GET /health` remains the basic
service-liveness endpoint.

The mission endpoint remains:

```text
GET /api/v1/demos/agent365-r0/missions/{mission_id}
```

and still requires `evidence.read`.

## Entra / production-JWKS profile

For the Microsoft-facing integrated demo, the runtime also accepts the repository's
existing production JWKS authentication model:

```bash
export ETS_AUTH_MODE=production_jwks
export ETS_AUTH_ISSUER='https://login.microsoftonline.com/<tenant-id>/v2.0'
export ETS_AUTH_AUDIENCE='api://<ets-api-application-id>'
export ETS_AUTH_TENANT_ID='<tenant-id>'
export ETS_AUTH_JWKS_URL='<trusted tenant JWKS URL>'
```

If an app-only caller does not carry ETS tenant/workspace claims, use the existing
server-side application scope mapping:

```bash
export ETS_AUTH_APP_SCOPE_MAP_JSON='{
  "<agent-or-workload-client-id>": {
    "tenant_id": "<tenant-id>",
    "workspace_id": "agent365-r0-demo"
  }
}'
```

The Entra application role presented by the caller must resolve to an ETS role that has
`evidence.read`; authentication alone is not authorization to read evidence.

## Container / Azure deployment boundary

For the four-week demonstration, mount the SQLite database on durable storage and run the
mission runtime as a separate internal service beside the existing ETS Gateway/Core
services. The public Microsoft workflow should call the authenticated HTTPS ingress, not
mount or read the SQLite database directly.

A production scale-out store is intentionally outside this P0 change. SQLite provides the
fastest deterministic route to proving restart durability and end-to-end Microsoft -> ETS
query behavior without changing the evidence semantics. A later hosted-store adapter can
replace SQLite behind the same retained-bundle contract.

## Acceptance criteria

This step is complete when repository CI demonstrates that:

1. retained binary source artifacts survive a save/restart/load cycle byte-for-byte;
2. identical retry writes are idempotent;
3. conflicting evidence under an existing `mission_id` is rejected;
4. retained envelope tampering is detected before reconstruction;
5. runtime startup requires an explicit durable database path;
6. runtime startup fails closed on unsupported authentication configuration; and
7. `/ready` is emitted only after the durable store has successfully produced the mission index.

## Next P0 boundary

After this step merges, wire the actual frozen demo execution path to call
`SQLiteRangerR0MissionBundleStore.save(...)` immediately after Evidence Object v2 promotion,
then run one automated end-to-end mission through SharePoint / Agent 365 -> Gateway -> Ranger
R0 -> retained bundle -> hosted mission API. That becomes the repeatable demo qualification
harness rather than a collection of individually proven boundaries.
