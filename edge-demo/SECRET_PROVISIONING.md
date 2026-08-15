# ETS Edge Virtual local credential provisioning

ETS Edge Virtual normally generates its local API key on first boot and persists
the private value at `/var/lib/ets/edge-local-api-key` with mode `0600`.
That Edge-owned file is intentionally **not** a cross-container secret volume.

For a controlled multi-container pilot, first boot may instead receive an
explicit credential through one of two mutually exclusive mechanisms:

- `ETS_LOCAL_API_KEY` — existing direct environment provisioning; or
- `ETS_LOCAL_API_KEY_FILE` — path to a mounted secret file.

The secret-file mechanism is preferred when a Compose/Docker secret is already
available. In this mode Edge reads the mounted secret at startup but does **not**
copy the plaintext credential into its persistent data volume. Instead it stores
only a SHA-256 verifier at `/var/lib/ets/edge-local-api-key.sha256`, allowing a
restart to reject unexpected credential drift without retaining the mounted
secret itself.

Because the secret is not copied, the same secret must remain mounted on every
startup of each service that needs it. A protected ingress or peer container
should receive its own mount of the same external secret and point its local
API-key file setting at that mount. It must not receive the ETS private data
volume merely to obtain an API credential.

## Fail-closed rules

- Configuring both environment and file provisioning fails startup.
- A missing, unreadable, empty, or too-short secret file fails startup.
- Secret-file mode persists only a SHA-256 verifier, never the plaintext API key.
- Once a verifier exists, supplying a different mounted key fails startup; this
  is not a rotation mechanism.
- Existing generated-key behavior is unchanged when no explicit provisioning
  source is configured.
- The credential value is never part of the public device identity and must not
  be written to logs, source control, issue text, screenshots, or retained test
  artifacts.

## Compose-secret pattern

A coordinating pilot may mount the same non-committed Compose secret independently
into ETS Edge and a client or protected ingress container. Each service receives
its own secret mount; the client does not receive the ETS data volume and cannot
read Edge signing material, SQLite state, or other private Edge state.

Example Edge-side environment:

```yaml
environment:
  ETS_LOCAL_API_KEY_FILE: /run/secrets/ets_edge_local_api_key
secrets:
  - ets_edge_local_api_key
```

A protected ingress using the same credential should mount the same external
secret independently and set its credential-file path to that mount, for example:

```yaml
environment:
  ETS_EDGE_API_KEY_FILE: /run/secrets/ets_edge_local_api_key
secrets:
  - ets_edge_local_api_key
```

This remains a local software-credential profile. The SHA-256 verifier is only a
restart-consistency control for a high-entropy API key; it is not encryption,
credential escrow, a rotation service, TPM/HSM custody, hardware attestation, or
production secret distribution.
