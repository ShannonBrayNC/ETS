# Fictional ETS Demo Artifacts

These artifacts are safe demo materials for `v0.1.0-alpha` walkthroughs.

They are intentionally fictional and contain no real customer evidence, secrets, private keys, tokens, personal data, or raw evidence bytes.

## Files

- `sample-event.json` is a fictional `EvidenceEvent` payload.
- `sample-proof-bundle.json` is a representative proof bundle shape for demo/reference use.
- `sample-certificate.md` is a Markdown verification certificate example.
- `sample-certificate.html` is an HTML verification certificate example.

## Regenerate from local API

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Append the sample event using `docs/api/local-requests.http`, then retrieve:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/bundles/evt_demo_001 `
  -Headers @{ "X-ETS-Tenant" = "tenant_demo"; "X-ETS-Workspace" = "workspace_alpha" } |
  ConvertTo-Json -Depth 100 |
  Set-Content ets/demos/fictional/sample-proof-bundle.generated.json
```

Then generate a certificate through `/reports/certificate` or the Explorer UI.

## Trust boundary note

These files are marketing/demo artifacts. They do not represent production trust, real evidence custody, or hosted identity assurance.
