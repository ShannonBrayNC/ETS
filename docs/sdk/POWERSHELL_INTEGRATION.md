# PowerShell 7: REST capture and strict verifier integration

ETS does **not** currently ship a PowerShell SDK module or ETS-specific cmdlets.
These executable PowerShell 7 examples use the documented REST v1 API and existing
`ets-verify` CLI. They complement the Python/.NET/TypeScript Application SDKs without
inventing `New-EtsClient`, `Publish-EtsEvidence` or other nonexistent commands.
Status: alpha synthetic integration examples; no production or Store approval.

## Files and prerequisites

- [`new-synthetic-event.ps1`](../../examples/sdk/powershell/new-synthetic-event.ps1):
  prepare immutable synthetic JSON with an explicit event ID/time and content hash.
- [`quickstart.ps1`](../../examples/sdk/powershell/quickstart.ps1): health/API check,
  one capture, event/inclusion-proof/bundle retrieval, no-overwrite export and
  strict offline CLI report.
- [`test-quickstart.ps1`](../../examples/sdk/powershell/test-quickstart.ps1):
  deterministic transport/CLI smoke cases, including failure paths.

Install PowerShell 7 and either the Python test-kit wheel in an isolated Python
3.12+ environment or a complete reviewed frozen verifier. A frozen verifier does
not need Python; the existing desktop GUI separately needs WebView2. Neither this
script nor the npm/.NET SDK installs the verifier automatically. Package/dependency
installation may need network; once prepared, smoke tests make no HTTP requests.

## First run: synthetic smoke without a service

From the extracted test-kit root, use a new output directory:

```powershell
pwsh -NoProfile -File examples/sdk/powershell/test-quickstart.ps1 `
  -Fixture tests/fixtures/verifier/native-signed.json `
  -TrustStore tests/fixtures/verifier/native-trust.json `
  -OutputDirectory ./powershell-smoke `
  -PythonExecutable ./.venv/Scripts/python.exe
```

On Linux/macOS, use the venv's `.venv/bin/python`. This smoke uses the same public
synthetic signed fixture as the C# and TypeScript examples. It is not a new proof
minted by PowerShell and does not qualify a live endpoint. Checks include:

| Case | Expected script exit / evidence |
| --- | --- |
| Valid signed bundle, selected fixture trust | `0`; strict report `outcome.status=valid` |
| Modified fixture metadata | `1`; strict report `outcome.status=invalid` |
| Missing out-of-band trust | `2`; strict report `outcome.status=indeterminate` |
| Simulated HTTP 403 / malformed JSON | `3`; sanitized operational error; no invented verification verdict |
| Repeat existing output directory | `3`; original bundle SHA-256 unchanged |
| HTTP request construction | Exact synthetic origin, SDK/auth headers, no bearer scope headers, one capture, one event read and one proof retrieval |

The public fixture key is not a real issuer identity. A successful result is
checkpoint-only under the supplied key; it does not establish current revocation,
continuity, completeness or real-world truth. Never install sample trust as a
production trust anchor. The script preserves raw JSON through `JsonDocument`
rather than converting ISO timestamps into PowerShell date objects and reserializing
them, which could change signed event bytes.

For a single smoke run through a frozen CLI:

```powershell
pwsh -NoProfile -File examples/sdk/powershell/quickstart.ps1 `
  -Smoke -Fixture tests/fixtures/verifier/native-signed.json `
  -TrustStore tests/fixtures/verifier/native-trust.json `
  -ExpectedLogId ets-cli-golden-fixture -OutputDirectory ./ps-frozen-smoke `
  -VerifierExecutable 'C:\reviewed-runtime\ets-verify.exe'
```

Keep the whole frozen runtime directory together, not just its EXE. This path is
an explicit user choice; no installed execution alias is assumed.

## Prepare and retain an event before a real write

The following creates synthetic data only and makes no network call. Choose your
actual authorized **test** tenant/workspace, a stable unique application event ID,
and an explicit UTC timestamp. Do not rerun with a new ID/time after an uncertain
write merely to obtain a success response.

```powershell
pwsh -NoProfile -File examples/sdk/powershell/new-synthetic-event.ps1 `
  -EventId evt_ps_test_01 -CreatedAtUtc '2026-10-28T12:00:00Z' `
  -TenantId test-tenant -WorkspaceId test-workspace -OutputPath ./prepared-event.json
```

The content hash is SHA-256 of the exact UTF-8 bytes
`Synthetic SDK integration example\n`, not an ETS event-canonicalization
implementation. The prepared file retains the exact event ID/time/content. The
server validates event data and may apply its configured redaction policy. An
opaque scope field in the payload is not permission to access that scope.

To adapt to a real artifact, hash separately retained bytes, for example:

```powershell
$artifactDigest = (Get-FileHash -LiteralPath ./reviewed-artifact.pdf -Algorithm SHA256).Hash.ToLowerInvariant()
```

Then create/validate the intended event under your application's data policy.
Do not include secrets, regulated content or raw customer artifacts in metadata
or logs. A digest is not automatically anonymized data. Metadata/external refs
are bounded; see the [field/task guide](TASK_GUIDE.md#model-an-event-correctly).

## Capture/retrieve/export against an authorized test endpoint

This is a **real append**, unlike `-Smoke`. Configure an approved HTTPS root
endpoint via `ETS_BASE_URL`, and exactly one `ETS_BEARER_TOKEN` or `ETS_API_KEY`
through your approved secret mechanism. Never paste credentials into source,
arguments, URLs, recorded commands or chat. Production bearer scope headers are
not sent; the event body scope must match authenticated claims and a server-owned
role must authorize capture/read/export.

```powershell
# Set ETS_BASE_URL and ONE credential through your approved environment/secret setup.
pwsh -NoProfile -File examples/sdk/powershell/quickstart.ps1 `
  -EventPath ./prepared-event.json -OutputDirectory ./ps-test-capture `
  -TrustStore ./reviewed-test-issuer-trust.json -ExpectedLogId your-reviewed-log `
  -PythonExecutable ./.venv/Scripts/python.exe
```

The script uses these actual endpoints:

| Method/path | Purpose / limit |
| --- | --- |
| `GET /health` | Service health metadata, not trust proof |
| `GET /version` | Require advertised `api_version=v1`; not full feature/schema negotiation |
| `POST /api/v1/events` | One event capture; preserve the raw API append response |
| `GET /api/v1/events/{escaped-id}` | Retrieve the committed event record |
| `GET /api/v1/proofs/inclusion/{escaped-id}` | Retrieve unverified proof JSON |
| `GET /api/v1/bundles/{escaped-id}` | Retrieve bundle bytes for independent verification |

The raw REST append response does not contain the SDK-added
`ets.sdk.event_commit_receipt.v1`/`commitment_state` wrapper. The script labels the
operation as local commitment only; it does not fabricate an SDK receipt or a
verification result from HTTP success. Exported files are `attempted-event.json`,
`api-append-response.json`, `event-record.json`, `inclusion-proof.json`,
`bundle.json` and the newly computed strict `verification.json` report.

Optional `-AllowLocalDev` is limited to explicit HTTP loopback with development
scope headers and no bearer token. It is not an HTTP/LAN production exception.
The existing Docker Dev profile returns unsigned checkpoints, so strict verification
must remain indeterminate without appropriate signing/trust. Do not silently add
`--allow-unsigned` to change that conclusion.

## Error, timeout and retry behavior

- REST calls use a 10-second timeout, no automatic retries and no redirects.
  The 4 MiB response check happens after buffering; it is not a streaming memory
  protection for a hostile endpoint. File reads are byte-bounded; arbitrary JSON
  and external services require broader application threat review.
- The verifier is launched with an argument list, not shell concatenation, and a
  30-second process deadline. The Python path uses isolated mode and an installed
  package. Relevant API-token/Python lookup environment variables are removed from
  the verifier child. It never receives a remote URL for offline verification.
- CLI exits `0`, `1`, `2` are preserved. CLI/report JSON supplies finer distinctions.
  Script transport/configuration/export/process errors exit `3`; do not treat these
  as a strict verifier verdict. A report write failure can be CLI exit 2 even if
  the nested verification outcome is valid; inspect the result, not just a badge.
- HTTP 409 is duplicate/conflict, **not** exactly-once replay success. Persist the
  attempted event before capture, and reconcile the same event ID/content after
  timeouts/cancellation. A failed write response may have committed remotely.
  The example is not a durable retry queue or crash-recovery state machine.
- Capture, retrieval and verification are separate stages. A later failure does
  not undo the earlier append. An existing output directory is refused before
  capture, but external failures can still leave partial exported state.
- Log only sanitized class/status/correlation information, not arbitrary server
  error messages, raw event content or credentials. These samples use minimal
  diagnostics deliberately. Add reviewed operational logging in your application.

## Recipes and deployment boundaries

Use the [ten industry recipes](INDUSTRY_COOKBOOK.md) to choose minimized metadata
and negative tests; their Python generator can create bundles for this shared CLI
and the existing Desktop Verifier. PowerShell can orchestrate a controlled workflow,
but there is no native bulk SDK, atomic capture batch, token-refresh service,
connector framework or production signing authority in these scripts.

Test on your actual PowerShell/Windows version before broad use. CI smoke results
must be reported as simulated transport + installed CLI tests, not physical-device,
live-tenant, Windows desktop accessibility or Store certification evidence.
