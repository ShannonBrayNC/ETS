# PowerShell 7 REST and verifier examples

There is no native ETS PowerShell SDK module. These scripts demonstrate the actual
REST v1 endpoints and shared strict verifier, without inventing PowerShell cmdlets.
See the [integration guide](../../../docs/sdk/POWERSHELL_INTEGRATION.md).

From a prepared Python environment with `lanternprotocol-ets` installed:

```powershell
pwsh -NoProfile -File examples/sdk/powershell/test-quickstart.ps1 `
  -Fixture tests/fixtures/verifier/native-signed.json `
  -TrustStore tests/fixtures/verifier/native-trust.json `
  -OutputDirectory ./powershell-smoke `
  -PythonExecutable ./.venv/Scripts/python.exe
```

The directory must not exist. Smoke mode sends no HTTP requests. Test keys and
fixtures are synthetic, not production trust. `quickstart.ps1` without `-Smoke`
performs a real append to an explicitly configured endpoint; use only an authorized
test workspace and read the guide's timeout/reconciliation cautions first.
