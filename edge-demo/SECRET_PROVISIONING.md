# ETS Edge Virtual local credential provisioning

ETS Edge Virtual normally generates its local API key on first boot and persists
the private value at `/var/lib/ets/edge-local-api-key` with mode `0600`.
That Edge-owned file is intentionally **not** a cross-container secret volume.

For a controlled multi-container pilot, first boot may instead receive an
explicit credential through one of two mutually exclusive mechanisms:

- `ETS_LOCAL_API_KEY` — existing direct environment provisioning; or
- `ETS_LOCAL_API_KEY_FILE` — path to a mounted secret file.

The secret-file mechanism is preferred when a Compose/Docker secret is already
available. The file is read once during Edge startup and the value is passed to
the existing durable-key helper. Edge then writes/uses its own private persisted
copy exactly as before.

## Fail-closed rules

- Configuring both environment and file provisioning fails startup.
- A missing, unreadable, empty, or too-short file fails startup.
- Once the durable Edge key exists, supplying a different value through either
  provisioning mechanism fails startup; this is not a rotation mechanism.
- When neither mechanism is configured, the existing generated-key behavior is
  unchanged.
- The credential value is never part of the public device identity and must not
  be written to logs, source control, issue text, screenshots, or retained test
  artifacts.

## Compose-secret pattern

A coordinating pilot may mount the same non-committed Compose secret independently
into ETS Edge and a client container. Each service receives its own secret mount;
the client does not receive the ETS data volume and cannot read Edge signing
material or other private Edge state.

Example Edge-side environment:

```yaml
environment:
  ETS_LOCAL_API_KEY_FILE: /run/secrets/ets_edge_local_api_key
secrets:
  - ets_edge_local_api_key
```

This remains a local software-credential profile. It does not provide TPM/HSM
custody, hardware attestation, production secret distribution, or key rotation.
