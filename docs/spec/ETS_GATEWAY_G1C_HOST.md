# ETS Gateway G1C Host Qualification

## Status

This document qualifies the transport-host behavior layered around the G1C Gateway webhook service. It does not redefine `ets.capture.v1`, `ets.event.v1`, hashing, Merkle, proof, or verification semantics.

## Network role

The qualified host remains out-of-band. It is not a router, firewall, proxy, or mandatory network-availability dependency. Loss of the Gateway host may create an observation gap but cannot invalidate proof material committed previously.

## Request limits

The v1 host profile bounds header count, aggregate header bytes, per-header value size, concurrent admitted requests, admission wait, and body-read duration. Only identity content encoding is qualified. Compressed request bodies are rejected until a separately bounded compressed/decompressed profile is introduced.

## Timeout boundary

The body-read deadline is pre-commit and cancellable. It ends before `GatewayIngressService.ingest_json()` is called. The host does not return a request-timeout response while an authoritative append continues in untracked work. After the body has been accepted, local append and durable sync enqueue run to an explicit receipt or error state.

## Saturation

A bounded semaphore controls admitted webhook work. Requests that cannot obtain capacity within the admission window receive explicit `503` backpressure with `Retry-After`. The host does not create an unbounded waiting queue.

## TLS profile

The application TLS context permits TLS 1.2 through TLS 1.3 and disables TLS compression. TLS 1.3 is preferred operationally. Server credentials are loaded separately from the policy object. A client CA can be configured for mTLS profiles; authenticated transport identity remains distinct from payload-declared identity and tenant/workspace authorization remains server-side.

Equivalent TLS termination may occur at an approved upstream listener only when it enforces the same or stronger profile and preserves a trustworthy authenticated principal boundary into Gateway. Forwarded identity headers from arbitrary clients are not authoritative by default.

## Logging and privacy

The qualified profile does not log credential values or raw request payloads. Existing G1C privacy-before-digest and `contains_raw_evidence=false` behavior remains normative.

## Qualification boundary

This slice qualifies application-host limits and configuration. It does not claim high availability, inline failover, general decompression support, packet capture, or complete-observation guarantees.
