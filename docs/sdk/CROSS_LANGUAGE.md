# ETS Application SDK cross-language compatibility

Status: SDK-3

The Python, .NET, and TypeScript Application SDKs share the frozen
`ets.application.sdk.v1` contract.

## Package boundaries

- Python: `ets.sdk.ETSClient` / `AsyncETSClient`
- .NET: `Ets.Application.EtsClient`
- TypeScript: `@lanternprotocol/ets-sdk` `EtsClient`

The pre-existing `Ets.Evidence` package remains a separate Evidence Object
canonicalization library. It is not renamed or conflated with the Application SDK.

## Required compatibility behavior

All language clients:

- advertise `X-ETS-SDK-Contract: ets.application.sdk.v1`;
- expose an explicit service/API compatibility check;
- return an immutable semantic `committed_local` receipt for a successful append;
- preserve the distinction between local commitment and independent verification;
- refuse tenant/workspace headers when bearer authentication is configured;
- require HTTPS except for an explicitly authorized loopback ETS Dev endpoint;
- do not implement invisible automatic retries on evidence writes.

## Canonicalization

The shared `conformance/sdk/v1` corpus is executed by Python, .NET, and
TypeScript.

Passing the current corpus establishes compatibility only for the covered
vectors. It is not a claim of RFC 8785/JCS conformance. Before widening
authoritative client-side hashing to arbitrary cross-language payloads, the
corpus must be expanded for numeric edge cases, Unicode ordering, rejected
non-finite values, nesting limits, and full proof/bundle vectors.

## Release gate

`.github/workflows/sdk-cross-language.yml` builds and tests both the .NET and
TypeScript Application SDKs whenever their source or shared conformance vectors
change.
