# ETS Gateway G1C Host Runner Test Plan

## Status

This plan defines the remaining deployed-host qualification for #235. The concrete Uvicorn server assembly and configuration tests may merge only as a partial slice unless every deployed-host acceptance below is executable in repository CI.

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

## Current execution constraint

The connected repository write safety layer blocked publication of the loopback HTTPS integration test during this slice. Do not mark #235 or parent #233 complete on configuration/unit tests alone. Preserve this test plan as the required closure gate until the executable test can be committed and pass exact-head CI.
