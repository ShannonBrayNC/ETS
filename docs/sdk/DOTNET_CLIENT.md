# .NET Application SDK: task guide and runnable quickstart

Source package: `LanternProtocol.ETS.Application` `0.1.0-alpha.1`, namespace
`Ets.Application`, target `net8.0`. Contract: `ets.application.sdk.v1`; REST `v1`.
This documents the current client, not an API promised by a proposed desktop app.
See [the release matrix](RELEASE_MATRIX.json) for version mapping and
[release gates](RELEASE.md) before publishing or installing a registry package.
Registry availability is not established by source/package metadata.

## Run the downloaded test kit first

From the extracted kit root, with .NET 8 SDK already installed, restore the
reviewed package from the kit into a new isolated cache (no registry publication):

```powershell
dotnet restore examples/sdk/dotnet/Quickstart.csproj --source ./packages/dotnet --packages ./.nuget-kit-cache
dotnet run --no-restore --project examples/sdk/dotnet/Quickstart.csproj -- `
  --smoke tests/fixtures/verifier/native-signed.json ./dotnet-bundle.json
```

Use a fresh extracted kit/cache when changing candidates. Continue with the
independent verification command below. The following build commands are only
for a repository checkout, not required to consume the delivered kit.

## Build and consume the actual NuGet artifact

From a reviewed checkout with the .NET 8 SDK installed:

```powershell
dotnet pack sdk/dotnet/Ets.Application/Ets.Application.csproj -c Release -o artifacts/dotnet
dotnet restore examples/sdk/dotnet/Quickstart.csproj --source ./artifacts/dotnet
# Use a NEW output filename. The source project consumes PackageReference, not ProjectReference.
dotnet run --no-restore --project examples/sdk/dotnet/Quickstart.csproj -- `
  --smoke tests/fixtures/verifier/native-signed.json ./dotnet-bundle.json
```

The package has no declared third-party NuGet package dependencies; a compatible
.NET SDK/framework still must be installed. For a new production project, add a
pinned `PackageReference` to the reviewed package version and use an approved local
feed or a verified registry release. Verify the release manifest, digest and
provenance before trusting downloaded artifacts. Do not assume a cached package
with the same version was built from the current commit: isolate or clear the
project-specific package cache when qualifying a candidate.

The [complete example](../../examples/sdk/dotnet/Program.cs) exercises health,
compatibility, capture, bundle retrieval and no-overwrite export through the real
`EtsClient`. `--smoke` injects deterministic HTTP responses, validates headers and
one capture attempt, and checks forbidden and malformed responses. It sends
**no network requests**. Its exported signed bundle is an existing public synthetic
fixture, not newly minted evidence or an attestation about a live endpoint.

Verify that exported fixture independently using the shared verifier:

Use the Python environment installed by the [test-kit procedure](TEST_KIT.md),
not an unrelated global executable. On macOS/Linux use `.venv/bin/python` instead.

```powershell
& ./.venv/Scripts/python.exe -I -m ets.verifier.cli offline ./dotnet-bundle.json `
  --trust-store tests/fixtures/verifier/native-trust.json `
  --expected-log-id ets-cli-golden-fixture `
  --report ./dotnet-verification.json
```

Expected fixture result: `valid=true`, `standing_status=checkpoint_only` under
explicit synthetic trust. The fixture key is not a real organization's identity.
The verifier is a separate executable/Python package; the .NET SDK does not install
or implement it. Choose a new report path. Offline trust selection does not prove
real-world truth, completeness or current revocation/continuity.

## Capture against an explicitly selected endpoint

Live mode performs a **real append**. Use only a test workspace for this example,
with a suitably authorized account. Supply these environment variables through
your approved secret/configuration mechanism:

| Variable | Meaning |
| --- | --- |
| `ETS_BASE_URL` | HTTPS endpoint ending in `/`; no embedded credentials, query or fragment |
| `ETS_BEARER_TOKEN` **or** `ETS_API_KEY` | Exactly one authentication mode; never commit or print its value |
| `ETS_TENANT_ID`, `ETS_WORKSPACE_ID` | Event payload scope, matching authenticated scope; production headers are not set by this example |
| `ETS_EVENT_ID` | Caller-controlled durable ID for this synthetic observation |
| `ETS_EVENT_TIME_UTC` | Explicit stable UTC observation timestamp, e.g. `2026-10-28T12:00:00Z`; retain with the event |

```powershell
dotnet run --no-restore --project examples/sdk/dotnet/Quickstart.csproj -- --live ./new-dotnet-bundle.json
```

The example hashes the exact UTF-8 bytes `Synthetic SDK integration example\n`
using SHA-256. That is a **content digest**, not local cross-language ETS event
canonicalization. It captures fictional metadata only and prints
`committed_local`, never “verified.” The server validates the event. Store the
exact event body, ID and timestamp in your application's durable outbox before
using the pattern in a real producer; this one-shot example is not an outbox.

For the optional [Docker Dev endpoint](DEV_ENVIRONMENT.md), explicitly set
`ETS_ALLOW_LOCAL_DEV=1`, use `http://127.0.0.1:8000/`, omit bearer authentication,
and use development tenant/workspace headers. This profile produces unsigned
checkpoints. Strict verifier output is therefore indeterminate, not a trusted
success; do not silently add `--allow-unsigned` to production verification.

## Actual API surface

All network methods accept a final `CancellationToken`. Keep one client per
appropriate endpoint/authentication context; do not mutate a shared credential
context across tenants.

| Task | Current API | Result / important limit |
| --- | --- | --- |
| Health/version | `HealthAsync(token)`, `VersionAsync(token)` | Service-reported metadata, not a security or trust decision |
| API check | `CheckCompatibilityAsync(token)` | Checks advertised REST `api_version == "v1"`; not full schema/profile negotiation |
| Capture | `CaptureAsync(evidenceEvent, correlationId, token)` | `EventCommitReceipt`; `CommitmentState == "committed_local"` only |
| Retrieve event | `GetEventAsync(eventId, token)` | Caller-owned `JsonDocument`; inspect/dispose it |
| Export bundle | `GetBundleAsync(eventId, token)` | Caller-owned **unverified** `JsonDocument`; save and run the common verifier |
| Inclusion proof | `GetInclusionProofAsync(eventId, token)` | Unverified proof JSON, not a boolean verification result |
| Consistency proof | `GetConsistencyProofAsync(fromSize, toSize, token)` | Unverified JSON; compare trusted checkpoints through qualified verifier logic |
| List/pagination, batch capture | **Not provided** | Python has bounded event listing; explicit .NET application loops are not transactional batch support |
| Native offline/online verification | **Not provided** | Export bundle and invoke `ets-verify` as a separate process; do not invent `VerifyOfflineAsync` |
| Idempotency key / automatic retry | **Not provided** | A correlation ID is diagnostic linkage, not an idempotency key |

Dispose documents even when downstream processing fails:

```csharp
using JsonDocument bundle = await ets.GetBundleAsync(eventId, cancellationToken);
await using var output = new FileStream(newPath, FileMode.CreateNew, FileAccess.Write);
await JsonSerializer.SerializeAsync(output, bundle.RootElement, cancellationToken: cancellationToken);
```

This snippet saves server-supplied material; it does not independently verify it.
Apply input/output size limits and consider atomic publication/cleanup for your
application. The complete sample limits exported bundle size but the current SDK
has **no built-in response-byte cap**; use a bounded HTTP handler or separately
qualified transport before accepting arbitrary/untrusted large responses.

## Authentication, transport and cancellation

`EtsClientOptions` accepts `BaseUri`, `ApiKey` or `BearerToken`, optional development
`TenantId`/`WorkspaceId`, `AllowInsecureLoopbackHttp`, and a `Timeout` greater than
zero and at most 60 seconds. Bearer authentication rejects caller-controlled scope
headers. Authorization still requires server-assigned roles; a producer role is
needed for capture, while an auditor/read-only role does not imply write access.

For an injected `HttpClient`, set its `BaseAddress` to exactly the same reviewed
origin/path as `BaseUri`; the SDK does not override a non-null address. The complete
example disables redirects via `HttpClientHandler.AllowAutoRedirect=false`.
Do not rely on the default HTTP handler for a strict no-redirect policy. Use a
cancellation deadline across response-body reading as well as request startup;
the example uses a 30-second operation deadline and a 10-second client timeout.
Cancellation stops waiting; it does **not** prove a server-side append was canceled.

## Errors, uncertain writes and throughput

Catch `EtsApplicationException` for normalized `Code`, `StatusCode`, `ApiCode` and
`CorrelationId`. Common codes: `authentication_failed`, `authorization_failed`,
`not_found`, `conflict`, `validation_failed`, `request_too_large`, `server_error`,
`transport_error`, `unsafe_configuration`, `incompatible_version`, `unknown_error`.
Malformed success bodies may throw `JsonException`; cancellation/timeouts may
throw `OperationCanceledException`. Neither should be mistaken for a rejected
append. Do not log arbitrary response bodies or server error messages by default.

No retry occurs invisibly inside the client. For a timeout/disconnect after
capture, first reconcile the **same** event ID against your retained exact event;
`GetEventAsync` plus independently checked content/hash comparison can distinguish
an already committed event from conflicting reuse. A duplicate-ID HTTP 409 is not
a success receipt and does not guarantee equivalence. Never blindly regenerate IDs
or retry a write with changed timestamps/content. If uncertainty remains, stop and
surface it rather than claim exactly-once delivery.

For throughput, use an application-owned bounded queue/outbox, explicit concurrency,
per-event results and backpressure. There is no atomic batch API, bulk transaction,
client-side rate-limit scheduler or guaranteed ordering across concurrent requests.
Qualify cancellation/restart/replay and auth/tenant isolation with your endpoint.
[Cross-language conformance](CROSS_LANGUAGE.md) is bounded; do not widen
`ApplicationCanonicalizer` to arbitrary authoritative payloads without new vectors.
