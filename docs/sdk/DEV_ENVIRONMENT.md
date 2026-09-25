# ETS SDK Dev environment

Status: SDK-2 local developer profile  
Trust level: non-production

The SDK Dev profile gives application developers a durable local ETS endpoint
without production signing or production identity dependencies.

## Start

```powershell
docker compose -f compose.sdk-dev.yml up --build
```

The API is bound only to the host loopback interface:

```text
http://127.0.0.1:8000
```

The profile uses:

- SQLite persistence in a Docker named volume;
- `local_header` development authorization;
- unsigned local tree heads;
- log id `ets-sdk-dev`;
- no production signing keys;
- no production identity claims.

It is deliberately unsuitable for production evidence claims.

## Python client

```python
from ets.sdk import ETSClient

client = ETSClient(
    "http://127.0.0.1:8000",
    tenant_id="dev-tenant",
    workspace_id="default",
    allow_insecure_http=True,
)

client.check_compatibility()
```

The Python client permits plaintext HTTP only when the caller explicitly enables
it and the destination is a loopback host. Hosted ETS endpoints must use HTTPS.

## Authentication boundary

For `local_header` and `local_api_key` development profiles, the SDK may send
`X-ETS-Tenant` and `X-ETS-Workspace`.

When a bearer token is configured, the SDK refuses tenant/workspace header
configuration. Production ETS derives scope from authenticated token claims and
the server rejects caller-controlled scope headers.

## Stop

```powershell
docker compose -f compose.sdk-dev.yml down
```

To remove the retained development ledger as well:

```powershell
docker compose -f compose.sdk-dev.yml down --volumes
```
