# ETS Gateway G1C Host Runner Test Plan

## Status

This plan records the deployed-host qualification completed by #235 and merged in PR #236. The concrete Uvicorn server assembly and the deployed-host acceptance below are executable in repository CI.

## Required deployed-host test

Run the Gateway on loopback HTTPS with ephemeral test-only credentials and the production-like host assembly.

The test must prove:

1. TLS negotiation is limited to the qualified TLS 1.2 through TLS 1.3 profile.
2. The Uvicorn host uses the custom Gateway `SSLContext` rather than unconstrained TLS defaults.
3. Implicit proxy-header trust is disabled.
4. Server connection concurrency is aligned with `GatewayHostPolicy.max_concurrent_requests`.
5. A request containing caller-controlled tenant/workspace headers still commits the server-authorized tenant/workspace from the source registry.
6. An unauthenticated or unauthorized source fails closed and creates no event.
7. Process shutdown begins one-way Gateway drain before transport termination and waits for admitted work within the bounded graceful-shutdown interval.
8. Credential values and raw request payload content are absent from captured logs.

## Failure handling

A failed authentication, authorization, TLS, scope, drain, or logging assertion is a release blocker for #235. The test must not use a mock transport in place of the loopback HTTPS socket for these acceptance claims.

## Completion evidence

The loopback HTTPS integration test was committed before PR #236 merged and passed exact-head CI. PR #236 merged exact head `0235379b3eb980b8970fcd4416efaaa8d3b7c344` to `main` as `db4a0567cd8acd9b9dcf1484473d3960e5726173` after independent LanternProtocol approval. Issues #235, #233, and #231 are complete.
