# Microsoft Agent 365 A365-Q0 — Live Collector Slice

**Program:** ETS Microsoft Agent 365 Evidence Acquisition  
**Tracker:** #828  
**Gate:** A365-Q0 — Inventory and source preservation  
**Status:** implementation slice; not Q0 completion

## Objective

Move the Agent 365 workstream from source-schema fixtures to a credential-safe, read-only Microsoft Graph acquisition path while preserving the Evidence Architecture rule that Microsoft remains the attributed source of Microsoft observations.

The qualified API surface for this slice is:

```text
GET https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages
GET https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages/{id}
```

The least-privileged Microsoft Graph read permission documented for these operations is `CopilotPackages.Read.All`. Microsoft also documents Agent 365 licensing and administrative-role requirements for access to this surface. Authorization remains a deployment/tenant concern; ETS does not infer authorization from a successful HTTP connection alone.

## Implemented boundary

`ets/connectors/enterprise/microsoft_agent365_http.py` adds:

- a credential-safe GET-only Agent 365 HTTP client;
- exact response-byte capture before normalization;
- explicit `Accept: application/json` and bounded JSON content-type handling;
- token redaction in object representation;
- in-memory token zeroing on client close;
- redirect rejection for credential-bearing requests;
- bounded timeout and response-size policy;
- explicit handling for authentication, authorization, throttling, retryable source failures, and terminal source failures;
- strict validation of source-provided inventory pagination URLs;
- no host, scheme, API-version, port, fragment, or collection-path drift through `@odata.nextLink`;
- inventory response parsing and package-detail parsing through the existing A365-Q0 source contract;
- response-package identity verification for detail calls;
- SourceEnvelope creation for every successful inventory-page and package-detail response;
- acquisition sequence and previous-envelope chaining;
- bounded full-inventory traversal;
- pagination-cycle detection;
- bounded package inventory size;
- optional detail fan-out for each unique package ID;
- inline or digest-only retention policy at this stage.

## Source and evidence model

The collector path is:

```text
Microsoft Graph
      |
      | exact HTTP response bytes
      v
MicrosoftAgent365HttpResponse
      |
      +--> MicrosoftSourceEnvelopeV1
      |      - source = microsoft.agent365
      |      - exact-byte SHA-256
      |      - API version/maturity
      |      - request path
      |      - acquisition sequence
      |      - previous envelope hash
      |
      +--> bounded normalization
             - inventory page
             - package summary
             - package detail
             - configuration commitments
```

The normalized package record is not a replacement for the source response. The SourceEnvelope is created from the exact response bytes so future normalizers can reinterpret retained source material without pretending the earlier normalized schema captured every field.

## Pagination trust boundary

A source-provided `@odata.nextLink` is data, not automatically trusted navigation.

The collector currently permits only:

```text
scheme: https
host: graph.microsoft.com
port: default or 443
path: /v1.0/copilot/admin/catalog/packages
fragment: none
userinfo: none
query: source-provided and preserved without rewriting
```

The beta path is supported only when the client is explicitly instantiated for `beta`; a v1.0 acquisition cannot silently cross into beta and vice versa.

## Credential boundary

The collector accepts access-token bytes supplied by the existing deployment credential boundary. It does not acquire, refresh, persist, log, or expose the token.

The client:

- stores token material in a mutable byte array;
- never includes token contents in `repr` or raised errors;
- zeroes the byte array when `close()` is called;
- disables reuse after close;
- disables HTTP redirects so authorization headers cannot be forwarded to an unqualified destination.

Durable secret management remains outside this module.

## Failure semantics

The collector distinguishes:

- `MicrosoftAgent365AuthenticationError` — token rejected (`401`);
- `MicrosoftAgent365AuthorizationError` — package access denied (`403`);
- `MicrosoftAgent365ThrottleError` — rate limit (`429`) with bounded `Retry-After`;
- `MicrosoftAgent365RetryableError` — network/source transient failure or `5xx`;
- `MicrosoftAgent365ResponseTooLargeError` — body exceeds configured bound;
- `MicrosoftAgent365RedirectError` — redirect attempted;
- `MicrosoftAgent365PaginationError` — source pagination escaped the qualified boundary, cycled, or exceeded configured bounds;
- `MicrosoftAgent365TerminalError` — other non-retryable source/contract failures.

The collector does not automatically retry. Automatic retries can obscure acquisition chronology; retry policy should be implemented at the orchestrator with explicit attempt evidence.

## Qualification tests

`tests/test_microsoft_agent365_http.py` covers:

- accepted opaque Graph next links;
- scheme/host/version/path/userinfo/port/fragment rejection;
- GET-only inventory behavior;
- exact-byte preservation;
- malicious next-link rejection before following the URL;
- package-detail identity mismatch;
- two-page inventory plus detail fan-out;
- SourceEnvelope sequence/hash chaining;
- pagination-cycle detection;
- digest-only retention behavior;
- protected-reference refusal until a durable payload store exists;
- credential redaction and close behavior;
- response-size limits;
- content-type validation;
- HTTP authentication/authorization/retryable/terminal classification;
- bounded throttling metadata.

Repository CI remains authoritative for Ruff, mypy, and the full pytest suite.

## Explicit limitations / remaining A365-Q0 work

This slice intentionally does **not** declare A365-Q0 complete. Remaining work includes:

1. bind the collector to the hosted Gateway credential provider and managed/workload identity path;
2. add a durable SourceEnvelope store with idempotent write semantics;
3. add a protected raw-payload store so `protected_reference` can be qualified rather than rejected;
4. persist acquisition sequence/checkpoint state across process restarts;
5. add inventory reconciliation and configuration-change history;
6. define collector signing/key-custody behavior;
7. run live-tenant qualification using `CopilotPackages.Read.All`;
8. capture a retained, independently verifiable live inventory qualification bundle;
9. establish operational metrics without leaking source payload or credentials.

Only after those gates pass should A365-Q0 be marked complete and A365-Q1 identity/authority become the primary implementation gate.
