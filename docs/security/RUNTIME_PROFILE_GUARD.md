# Runtime profile guard

ETS validates the selected runtime profile before launching the API process, including direct calls to `create_app_from_env()` and container startup.

Local demo settings are intentionally visible:

- `ETS_STORAGE_PROVIDER=in_memory`
- `ETS_AUTH_MODE=local_header`
- `ETS_SIGNING_MODE=local_unsigned`

These settings are useful for laptop demos, but they are not a hosted profile. Startup must set an explicit demo override when any local-only setting is used:

```bash
ETS_ALLOW_INSECURE_LOCAL=1
```

Without that override, the environment bootstrap fails before storage, signing, and authentication policies are constructed.

Hosted examples should use durable storage, signed tree heads, and token validation, for example:

- `ETS_STORAGE_PROVIDER=sqlite`
- `ETS_SIGNING_MODE=ed25519`
- `ETS_AUTH_MODE=production_jwks`

The guard is shared by the API package bootstrap and the container entrypoint so alternate startup paths cannot silently bypass the same runtime policy.
