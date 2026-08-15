# ETS Edge Virtual local credential provisioning

ETS Edge Virtual supports local API-key authentication for the controlled pilot profile without
requiring clear-text credential persistence.

When no secret file is supplied, a generated or directly injected local API key is persisted as an
AES-256-GCM encrypted credential envelope at `/var/lib/ets/edge-local-api-key` with mode `0600`.
The encryption key is derived with HKDF domain separation from the appliance's existing software
Ed25519 signing key. This is a software-volume custody profile, not HSM/TPM-backed secret custody.
Existing legacy clear-text local API-key files are migrated in place to the encrypted envelope after
successful validation.

For a controlled multi-container pilot, an explicit credential may instead be supplied through one
of two mutually exclusive mechanisms:

- `ETS_LOCAL_API_KEY` — direct environment provisioning; or
- `ETS_LOCAL_API_KEY_FILE` — path to a mounted secret file.

The secret-file mechanism is preferred when a Compose/Docker secret is already available. In this
mode Edge reads the mounted secret at startup but does **not** copy the plaintext credential into its
persistent data volume. Instead it stores only a salted, memory-hard scrypt verifier at
`/var/lib/ets/edge-local-api-key.scrypt`, allowing a restart to reject unexpected credential drift
without retaining a recoverable copy of the mounted secret.

Because the secret is not copied in secret-file mode, the same secret must remain mounted on every
startup of each service that needs it. A protected ingress or peer container should receive its own
mount of the same external secret and point its local API-key file setting at that mount. It must not
receive the ETS private data volume merely to obtain an API credential.

## Fail-closed rules

- Configuring both environment and file provisioning fails startup.
- A missing, unreadable, empty, or too-short secret file fails startup.
- Secret-file mode persists only a salted scrypt verifier, never the plaintext API key.
- Once a verifier exists, supplying a different mounted key fails startup; this is not a rotation
  mechanism.
- Generated/direct local credentials are encrypted before durable storage; plaintext is not written
  to the credential storage file.
- An encrypted credential envelope that cannot be authenticated/decrypted with the appliance storage
  key fails closed.
- The credential value is never part of the public device identity and must not be written to logs,
  source control, issue text, screenshots, or retained test artifacts.

## Compose-secret pattern

A coordinating pilot may mount the same non-committed Compose secret independently into ETS Edge and
a client or protected ingress container. Each service receives its own secret mount; the client does
not need the ETS private data volume merely to obtain the API credential.

Example Edge-side environment:

```yaml
environment:
  ETS_LOCAL_API_KEY_FILE: /run/secrets/ets_edge_local_api_key
secrets:
  - ets_edge_local_api_key
```

A protected ingress using the same credential should mount the same external secret independently
and set its credential-file path to that mount, for example:

```yaml
environment:
  ETS_EDGE_API_KEY_FILE: /run/secrets/ets_edge_local_api_key
secrets:
  - ets_edge_local_api_key
```

This remains a local software-credential profile. The scrypt verifier is a restart-consistency
control, and the AES-GCM envelope protects recoverable local credentials from clear-text persistence.
Neither mechanism is credential escrow, a rotation service, TPM/HSM custody, hardware attestation,
or production secret distribution.
