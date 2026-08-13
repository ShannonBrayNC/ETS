# ETS Gateway G1D Syslog Profile

## Status

This document defines the transport and parsing boundary for G1D. It does not redefine `ets.capture.v1`, `ets.event.v1`, hashing, Merkle, proof, or verification semantics.

## Standards profile

ETS Gateway uses RFC 5424 as the standardized syslog message format. The qualified production transport profile is syslog over TLS as described by RFC 5425.

The TLS profile uses octet-counted framing:

`MSG-LEN SP SYSLOG-MSG`

The declared message length is the number of octets in `SYSLOG-MSG`. A frame may span transport reads, and one transport read may contain multiple frames. Transport record boundaries are not message boundaries.

RFC 5425 requires receivers to process messages through 2048 octets and recommends support through 8192 octets. The initial ETS Gateway qualified policy therefore uses 8192 octets as the default maximum syslog message size while keeping the limit explicit and testable.

RFC 6587 describes legacy syslog over plain TCP and is Historic. It is not the qualified ETS production transport. If compatibility support is introduced later, it must be a separately declared lower-assurance profile.

## Product boundary

RFC 5424 parsing primitives belong to a neutral ETS namespace. Gateway modules must not import `ets.edge.*`. The existing Edge UDP pilot may consume neutral parsing primitives only through a compatibility wrapper that preserves its established public API and historical capture behavior.

Gateway must not reuse the Edge syslog event builder. The Edge pilot hashes exact received datagram bytes before parsing; Gateway commitment semantics remain governed by Gateway capture/privacy policy and must describe the representation actually committed.

## Identity boundary

Transport identity and message-declared identity are separate facts. For the qualified TLS profile, the authenticated transport peer is the authorization input. RFC 5424 `HOSTNAME`, `APP-NAME`, `PROCID`, and `MSGID` are message claims and cannot authorize tenant/workspace scope.

Source registration remains authoritative for source ID, tenant, workspace, adapter profile, and capture/privacy policy.

## Bounds

A receiving implementation must reject an advertised message length above policy before attempting to buffer the complete message. Prefix length, buffered bytes, connection concurrency, and read/idle duration must also be bounded by the concrete listener profile.

Tests cover message and framing limits at -1, exact, and +1 boundaries; fragmented frames; multiple frames per connection; invalid and zero lengths; truncation; and connection shutdown with incomplete framing.

## Privacy and evidence semantics

Raw syslog content is not retained by default. Parsing does not itself define the committed representation. G1D capture mapping must apply declared minimization/redaction before irreversible commitment and must state whether the committed representation is byte-lossless. Original-byte hashing is not implied by receipt of a syslog message.

Source timestamp and collector receipt time remain distinct. Missing or untrusted source time must not be invented.

## UDP compatibility

UDP is lower assurance and cannot support a completeness, ordering, delivery, or acknowledgement claim. Message `HOSTNAME` is not transport identity. A future UDP listener must obtain source scope from listener/policy configuration rather than trusting message fields.

## Exit boundary

This profile is not complete until executable framing, source authorization/capture mapping, concrete transport hosting, protocol-specific boundary tests, exact-head repository gates, and independent review are complete.
