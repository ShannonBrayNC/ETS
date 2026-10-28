# Application SDK task guide and capability reference

Reviewed against ETS `96c6ec8f` and the test-kit changes in this branch (2026-10-28).
Audience: application developers integrating evidence capture, retrieval and verification.
Status: **alpha SDK test kit**, not a production-service, sector compliance or Store approval.

## Start here

1. Run the [Python signed offline round trip](PYTHON_CLIENT.md#signed-offline-round-trip)
   without a server. It produces a sample artifact, event, signed bundle, separate
   public trust file, tampered variant and strict verification reports.
2. Run the [.NET quickstart](DOTNET_CLIENT.md) and
   [TypeScript quickstart](TYPESCRIPT_CLIENT.md) in their deterministic smoke modes.
   They exercise real SDK clients through simulated transports; that is not a live
   endpoint test. All languages hand exported bundles to the same strict verifier.
3. Choose a recipe in the [industry cookbook](INDUSTRY_COOKBOOK.md), replace only
   synthetic data in a controlled test workspace, then qualify your actual endpoint,
   identity, retention and retry behavior. No industry-specific connector is implied.
4. Follow the [test-kit procedure](TEST_KIT.md) for hashes, installation, expected
   outputs, installed-package smokes and the remaining release gates.

## What each language actually provides

Names below are real public methods. Package versions follow
[RELEASE_MATRIX.json](RELEASE_MATRIX.json); a package version is not a protocol version.

| Task | Python (`ETSClient`; async equivalent unless noted) | .NET (`EtsClient`) | TypeScript (`EtsClient`) |
| --- | --- | --- | --- |
| Health/version | `health()`, `version()` | `HealthAsync()`, `VersionAsync()` | `health()`, `version()` |
| Explicit API check | `check_compatibility()` | `CheckCompatibilityAsync()` | `checkCompatibility()` |
| Capture one event | `capture(evidence, correlation_id=...)` | `CaptureAsync(event, correlationId, cancellationToken)` | `capture(event, correlationId)` |
| Get one event | `get_event(event_id)` | `GetEventAsync(eventId)` | `getEvent(eventId)` |
| List bounded page | `list_events(limit=50, offset=0)`; 1–500 limit | **Not exposed** | **Not exposed** |
| Inclusion proof | `inclusion_proof(event_id)` | `GetInclusionProofAsync(eventId)` | `getInclusionProof(eventId)` |
| Consistency proof | `consistency_proof(from_size, to_size=...)` | `GetConsistencyProofAsync(fromSize, toSize)` | `getConsistencyProof(fromSize, toSize)` |
| Exportable bundle | `bundle(event_id)` | `GetBundleAsync(eventId)` | `getBundle(eventId)` |
| Strict verification | `verify_offline(...)`, `verify_online(...)` | **No native strict verifier**; common CLI | **No native strict verifier**; common CLI |
| Local authoring/store | `ets.sdk.local` facade + selected core store | No equivalent local store facade | No equivalent local store facade |
| Async/cancellation | `AsyncETSClient`; task cancellation; offline helper is synchronous | Task methods accept `CancellationToken` | Promises; no SDK timeout/signal option; inject a bounded `fetchImpl` |
| Batch/stream/webhook | **No SDK batch API, atomic bulk transaction, streaming feed or webhook API** | Same | Same |
| Idempotency/retries | **No automatic write retry or idempotency-key option** | Same | Same |

Python responses use typed models. .NET event/proof/bundle results are disposable
`JsonDocument` objects; TypeScript equivalents are `unknown`. Parsing a response
or receiving HTTP 200 is not independent verification. The Python library outcome
also differs from the CLI envelope: `VerifierOutcome` exposes `valid`, checks,
signature/continuity and standing; the CLI adds finer `status`/`reason_code` classes
and maps them to its 0/1/2 exit family. Do not access a nonexistent library `.status`.

The shared contracts are `ets.application.sdk.v1`, REST `v1`, `ets.event.v1`,
`ets.proof_bundle.v1`, `ets.verifier.v1` and
`ets.sdk.event_commit_receipt.v1`. Compatibility-check methods currently check
service API version, not every schema, server feature, authorization or trust key.

### PowerShell is an integration surface, not another SDK package

[PowerShell 7 examples](POWERSHELL_INTEGRATION.md) use the actual REST v1 routes
and the common strict CLI. There is no published ETS PowerShell module or separate
native verifier implied. Follow the same capture/receipt/bundle/trust/uncertain-write
rules; use explicit secrets/configuration and bounded transport behavior. The
PowerShell smoke tests are synthetic, not live tenant acceptance.

## Model an event correctly

Use the [EvidenceEvent source](../../ets/core/models.py) as the field authority.
For JSON files, Python `EvidenceEvent.model_validate_json(...)` handles the JSON
representation; an in-memory strict mapping should supply a timezone-aware
`datetime`, not assume a timestamp string is coerced by `create_evidence`.

| Field | Integration rule |
| --- | --- |
| `event_id` | Durable application-generated identifier for this exact observation; persist before the write. New revisions get a deliberate new event ID |
| `tenant_id`, `workspace_id` | Actual authorized scope; values in event data do not grant access |
| `evidence_id` | Reference to the represented artifact/observation; define revision semantics in your application |
| `event_type` | Bounded, documented application vocabulary; e.g. `manufacturing.inspection.recorded`, not a new ETS protocol |
| `subject_ref` | Required field, string or `null`; prefer opaque identifiers over personal data |
| `content_hash`, `content_hash_alg` | SHA-256 of a declared representation; algorithm exactly `sha256`. Hash exact artifact bytes for binary content; document canonicalization if hashing structured data |
| `metadata`, `external_refs` | JSON-native, each bounded to 64 KiB after canonicalization; only necessary non-secret data. External references are not fetched/verified automatically |
| `created_at_utc` | Timezone-aware observation/application timestamp; not an independently trusted timestamp by itself |
| Optional `source_system`, `actor_id`, `correlation_id`, `redaction_profile` | Context, not authentication or source-truth proof; keep pseudonyms and document the redaction policy |

The API event body limit is currently 256 KiB; this is not the verifier's artifact
limit. The strict CLI limits files to 4 MiB per artifact, 1 MiB per trust file,
64 nested containers and 100,000 parsed nodes. Python in-process SDK helpers do
not automatically impose those file-input bounds. Limit input before loading
untrusted content into your application.

**Two different hashes:** `content_hash` commits the external artifact representation;
`event_hash` commits the canonical ETS event. Strict bundle verification recomputes
the event/proof/checkpoint chain, but does not download external artifact bytes.
Separately hash retained original bytes and compare to the event's `content_hash`.
A digest does not establish ownership, source identity, anonymization or truth.

## Capture, custody and export workflow

1. Validate/minimize data; persist the immutable event and application outbox state.
2. Check API compatibility and authenticate with the least-privileged role.
3. Capture **one** event. Save the returned receipt and correlation identifier.
4. Treat `commitment_state=committed_local` as local commitment only. A receipt
   is not an independent verification, replicated durability or external anchor.
5. Retrieve the event/bundle and retain bytes with an application manifest/hash.
   Use a new output path; do not overwrite the source artifact or an earlier report.
6. Obtain public trust material through a verifier-controlled, out-of-band route;
   select expected log ID. Do not automatically trust a key carried with a bundle.
7. Run strict verification and retain the complete outcome, verifier version,
   policy and report. Offline success is checkpoint-only, not present standing.
8. Keep raw artifacts in separately authorized storage with access/retention,
   backup and deletion controls. ETS metadata export does not operate those controls.

The test kit's synthetic signer and fixed smoke key demonstrate mechanics only.
They are public/non-production trust, not instructions to embed signing secrets
in an SDK, client app, repository or end-user installer.

## Retry, duplicate detection and reconciliation

A timeout/cancellation can happen **after** the server accepted a write. SDKs do
not automatically retry it; neither event ID nor HTTP 409 means exactly-once API
semantics. The server returns `ETS_EVENT_DUPLICATE`, not a replayed successful
receipt. Use application-owned recovery:

| Observed state | Safe application action |
| --- | --- |
| Successful receipt | Persist receipt, then obtain/verify bundle |
| Timeout, connection loss or cancellation during capture | Mark outcome uncertain; retain same event ID and exact attempted payload; query that ID before deciding to retry |
| Event exists | Compare the committed content/event identity against the expected post-redaction representation; investigate conflicts, then obtain and verify its bundle |
| 409 duplicate | Reconcile the existing event; do not relabel 409 as success without checking it |
| 404 during reconciliation | Account for endpoint/replication/scope and operation timing; a single absence is not proof a prior write never committed. Apply a bounded documented recovery policy |
| Same ID but different content | Stop and surface a conflict; do not mint a replacement ID to conceal an uncertain operation |
| Intentional new revision | Generate a new event with an explicit prior-revision reference and application semantics |

Server redaction can alter committed fields. Do not compare a pre-redaction
client hash to the stored event as if transformations were impossible; qualify
and record the effective policy. For read-only retries, use bounded backoff/jitter
and cancellation. For writes, use a durable outbox and per-event reconciliation,
not an unbounded retry loop. There is no SDK outbox/queue implementation in this kit.

## Paging, concurrency and ingestion throughput

Python provides offset pages, not a snapshot cursor. Persist a high-water mark
and deduplicate by event ID if the log can change during a scan. Query only your
authorized scope; page totals are not proof of source completeness. .NET/TS users
must retain known IDs or implement a separately reviewed API adapter for listing;
do not invent `listEvents`/`ListEventsAsync`.

For multiple captures, bound concurrency and track one result/uncertain state per
event. Partial completion is expected; no batch rollback or cross-event atomicity
is supplied. Preserve source sequence numbers/correlation in minimized metadata,
but do not assume client task order equals committed log order. Consider the
Python async client or .NET tasks/TS promises with a semaphore/worker pool—not an
unbounded `gather`/`Promise.all` over an entire dataset. Rate limiting, queuing,
backpressure and retry budgets belong to the application/deployment.

## Authentication, network and secrets

- Configure **exactly one** API key or bearer token. Local tenant/workspace
  headers belong only to explicit development auth profiles; do not combine
  caller scope headers with bearer auth. Production scope comes from verified claims.
- HTTPS is the default. HTTP is accepted only through explicit loopback Dev
  opt-in; it is not a remote/LAN production exception. The Docker profile is
  unsigned and non-production. Do not use `--allow-unsigned` to make production
  tests appear green.
- ETS roles govern operations: producer capture, viewer reads, auditor
  verification/export as documented in [API authorization](../security/CORE_API_AUTHORIZATION.md).
  Check actual route/role combinations for the deployed server; a valid token
  does not grant every operation. SDK clients do not obtain or refresh tokens.
- Keep secrets in application/OS/managed secret storage, not source, CLI arguments,
  URLs, notebooks, sample output or logs. Log sanitized error class/status and
  correlation IDs rather than event bodies, raw server messages or credentials.
- Python disables redirects; TypeScript requests `redirect: "error"`. For .NET
  provide `HttpClientHandler { AllowAutoRedirect = false }`; the default SDK
  `HttpClient` does not establish this protection. Keep custom client BaseAddress
  aligned with `EtsClientOptions.BaseUri`. Review proxies/TLS/SSRF and host allowlists.
- Python's `max_response_bytes` is checked after the HTTP response is buffered,
  not a streaming memory bound. .NET/TS lack equivalent SDK response-size options;
  enforce limits in trusted transport/adapters before using hostile endpoints.

## Error handling and operational diagnostics

Use [ERROR_MODEL.md](ERROR_MODEL.md). The normalized code is operational state,
not a verification verdict. Never fabricate `valid=true` after an exception.

| Error class | Typical handling |
| --- | --- |
| `authentication_failed` / `authorization_failed` | Correct credential/role/scope; do not retry forever or relax policy |
| `validation_failed` / `request_too_large` | Fix/minimize input; do not split a semantic event silently |
| `not_found` | Confirm ID, scope and endpoint; distinguish absent from not-yet-visible |
| `conflict` | Reconcile immutable event identity/content |
| `transport_error` / `server_error` | Read retry or write reconciliation according to operation; preserve uncertainty |
| `unsafe_configuration` / `incompatible_version` | Stop and correct configuration or supported release |
| `unknown_error` | Retain sanitized status/correlation and investigate; HTTP 429 currently maps here, not a special rate-limit enum |

Python default timeout is 10 seconds (valid range >0 to 60) and default response
limit 4 MiB (configurable 1 KiB–16 MiB). .NET options include timeout and methods
accept cancellation. TS needs an injected timeout-capable fetch wrapper. None of
these implies that cancelling a write cancels a server commit. Exceptions outside
the normalized SDK class may still occur (JSON parsing, cancellation, caller
transport); include an outer sanitized failure boundary.

## Compatibility and test coverage before deployment

Run installed-package smokes, not only source imports. Pin and record Python,
.NET and npm artifact versions/hashes plus verifier version and schemas. Test:
valid signed bundle; changed event; missing/wrong/revoked key; wrong log;
unsupported schema; malformed/oversized input; write/export failure; retries and
uncertain capture; auth/scope denial; pagination boundaries; package update and
prior supported bundle. Current conformance vectors do not prove arbitrary
cross-language numeric/Unicode hashing parity or RFC 8785/JCS compliance.
Use integers/explicit decimal strings for financial quantities; do not invent a
custom canonicalizer for arbitrary payloads from these examples.

The test kit does not implement the planned Developer Edition authoring UI.
The existing desktop verifier can inspect supported exported bundles; Windows
installation, signing and Store certification retain their separate evidence gates.
A successful sample or CI job is not approval to run a production trust service.
