# Runtime profile guard

ETS container startup now validates the selected runtime profile before launching the API process.

Local demo settings are intentionally visible:

- `ETS_STORAGE_PROVIDER=in_memory`
- `ETS_AUTH_MODE=local_header`
- `ETS_SIGNING_MODE=local_unsigned`

These settings are useful for laptop demos, but they are not a hosted profile. Container startup must set an explicit demo override when these local settings are used:

```bash
ETS_ALLOW_INSECURE_LOCAL=1
```

Hosted examples should use durable storage, signed tree heads, and token validation, for example:

- `ETS_STORAGE_PROVIDER=sqlite`
- `ETS_SIGNING_MODE=ed25519`
- `ETS_AUTH_MODE=production_jwks`

The runtime guard is intentionally small so it can be reused by container startup and, in a follow-up change, by `create_app_from_env()` directly.
