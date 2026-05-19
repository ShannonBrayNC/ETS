# ETS Deployment Model

Local development can run directly with Uvicorn or with Docker Compose where
Docker is available.

Federation validation command:

```powershell
.\scripts\validate-docker-federation.ps1
```

The script starts the Compose cluster, checks all configured health endpoints,
and tears the cluster down. It requires Docker to be installed on the host.

Important environment variables are documented in `.env.example`, including
storage provider, SQLite path, auth mode, redaction profile, and signing mode.

Azure-ready hosted deployment is expected to use container hosting, managed
PostgreSQL, Key Vault, static UI hosting, and centralized logs. Hosted mode must
not reuse local unsigned tree heads or local header auth as production controls.
