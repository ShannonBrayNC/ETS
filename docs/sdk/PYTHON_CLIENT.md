# ETS Python Application SDK

Contract: `ets.application.sdk.v1`

SDK-2 adds synchronous `ETSClient` and asynchronous `AsyncETSClient` remote
clients over the existing ETS v1 API.

## Supported operations

- service health and version;
- explicit API compatibility check;
- event capture;
- event lookup and bounded listing;
- inclusion proof retrieval;
- consistency proof retrieval;
- portable proof-bundle retrieval;
- strict offline verification using the existing verifier;
- strict online verification using the existing verifier transport and trust model.

The client performs no automatic retries. Evidence writes carry application
identity semantics, so callers must choose retry behavior deliberately rather
than allowing a transport library to repeat writes invisibly.

## HTTPS and development HTTP

HTTPS is the default requirement. Plain HTTP is accepted only for an explicitly
enabled loopback ETS Dev endpoint.

## Authentication

Use exactly one remote-authentication mode:

```python
ETSClient("https://ets.example", api_key="...")
```

or:

```python
ETSClient("https://ets.example", bearer_token="...")
```

Tenant/workspace headers are development-only. They can be configured with
local-header/local-API-key profiles, but cannot be configured together with a
bearer token.

## Receipt semantics

`capture()` returns `EventCommitReceiptV1`. The client converts the current
API append response into the frozen SDK receipt and assigns only
`commitment_state="committed_local"`.

That receipt is not a claim of verification, completeness, source truth,
authorization standing, synchronization, or external anchoring.

## Async

`AsyncETSClient` exposes the same remote operations. Online verification reuses
the hardened synchronous verifier in a worker thread so the event loop is not
blocked while preserving one verifier implementation and one trust model.
