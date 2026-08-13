# ETS Gateway G1D Secure Syslog TLS Host Test Plan

## Status

This plan qualifies the concrete transport host tracked by #246. It is stacked on the G1D-B capture/commit contract from #242 and must not be used to declare G1D complete until #241 and #242 are merged.

## Architecture boundary

The TLS host is transport-only. It may authenticate a peer, apply connection/read/framing limits, assign a Gateway receipt identity, and pass complete RFC 5425 frames to `GatewayIngressService.ingest_syslog()`.

The host must not:

- derive tenant/workspace/source authorization from RFC 5424 message fields;
- redefine `ets.capture.v1`, `ets.event.v1`, hashing, proof, or synchronization semantics;
- hash or retain raw syslog content merely to create a transport identity;
- duplicate the Gateway local append, duplicate/conflict, backpressure, or durable-sync implementation;
- claim delivery completeness or exactly-once behavior that RFC 5425 does not provide.

## Secure transport profile

The qualified production listener uses RFC 5425 syslog over TLS with octet-counted framing.

- TLS 1.2 remains supported for interoperability.
- TLS 1.3 is supported and preferred when available.
- TLS 1.3 early data / 0-RTT is not enabled for the syslog profile.
- Client certificates are required for the qualified listener.
- The initial ETS transport-principal profile uses one unambiguous URI subjectAltName from the validated peer certificate.
- The resulting transport principal must resolve through the existing server-side `StaticSourceRegistry` / `SourceRegistration` boundary before evidence is accepted.
- RFC 5424 `HOSTNAME`, `APP-NAME`, `PROCID`, and `MSGID` remain message claims only.

## Receipt identity

RFC 5425 does not supply a trustworthy exactly-once delivery identifier. The qualified host therefore assigns a collector receipt identity for each complete frame using connection-local state. Message `MSGID` must not be promoted into an authorization or transport-delivery identity.

A reconnect may produce another receipt for a retransmitted source message. ETS must describe that limitation rather than silently claiming source-level exactly-once delivery.

## Bounds

The host must expose explicit positive bounds for:

- concurrent accepted connections;
- TLS handshake duration;
- connection admission duration;
- stream read / idle duration;
- read chunk bytes;
- frame prefix bytes;
- framed message bytes;
- retained incomplete-frame bytes;
- graceful shutdown / drain duration.

The listener uses the shared `OctetCountingFramer` and the Gateway service's configured syslog message limit. An advertised oversize frame must fail before its payload is buffered to the declared message size.

## Required integration qualification

Use loopback TLS sockets and test-only credentials generated during the test. No production credential material may be committed.

### TLS and identity

1. A client certificate chaining to the configured test CA completes a TLS 1.2 or TLS 1.3 connection.
2. A valid client certificate with one registered URI SAN maps to the corresponding server-authorized source registration.
3. A valid but unregistered URI SAN creates no evidence.
4. A peer without a required certificate cannot use the qualified listener.
5. A certificate with missing or ambiguous URI SAN identity fails closed.
6. A message-declared `HOSTNAME` that differs from the transport principal cannot alter tenant, workspace, source ID, or transport identity.

### Framing through the socket

7. A frame fragmented across several socket writes produces exactly one complete Gateway capture.
8. Several frames in one socket write produce separate captures in order.
9. A partial next frame is retained only within the configured framing bound and is completed by later input.
10. Invalid, zero-length, oversize, and incomplete frames create no partial evidence.
11. Closing a connection with an incomplete frame creates no evidence for that incomplete message.

### Evidence and privacy

12. Complete messages flow through `GatewayIngressService.ingest_syslog()` and therefore use the existing Core append and durable-sync path.
13. The event records the registered transport identity separately from RFC 5424 declared identity claims.
14. The initial G1D-B header-only profile remains explicitly lossy and does not claim original-byte hashing.
15. A raw marker present only in STRUCTURED-DATA or MSG is absent from committed event metadata, synchronization payloads, and captured operational output.
16. Source timestamp and collector receipt time remain distinct.

### Availability and shutdown

17. Connection saturation fails closed without committing unadmitted input.
18. Read/idle timeout closes an inactive connection without creating evidence.
19. Shutdown stops new accepts before waiting for admitted work.
20. Complete work already admitted before shutdown may finish within the drain bound.
21. When the drain bound expires, the host reports the timeout and closes remaining transport work without fabricating completed evidence.

## Exact-head gate

Before #246 can close:

- #241 and #242 are complete;
- all new unit/integration tests pass on the exact head;
- CI, Security Audit, Formal Specs, Benchmarks, Apalache, and Lean are green;
- any relevant Gateway host/integration workflows are green;
- independent LanternProtocol review approves the exact merge head.
