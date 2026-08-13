# ETS Gateway GATE-G0 Test and Validation Plan

Status: GATE-G0 validation candidate
Date: 2026-08-13
Parent: #215

## 1. Purpose

G0 testing is an architecture-contract test, not a performance or production qualification. It verifies that the Gateway design is internally consistent, machine-readable, aligned with ETS invariants and incapable of silently enabling the highest-risk architectural mistakes before implementation begins.

## 2. Test layers

### Layer A — automated contract tests (run now)

Repository tests validate the checked-in `ets.gateway.reference.pilot.v1` profile and its schema-level invariants.

### Layer B — static design review (run at G0 review)

Independent reviewer verifies traceability, threat coverage, standards claims and consistency with ETS Core/Edge/product epics.

### Layer C — implementation tests (G1/G2)

Future runtime tests validate listener/auth/parser/queue/privacy/Core/sync behavior.

### Layer D — appliance/network tests (G3/G4/G6)

Future hardware tests validate TPM, Secure Boot, NIC isolation, throughput, storage, power loss, update/recovery and network failure behavior.

G0 passes only Layers A and B. It seeds mandatory tests for Layers C/D but does not claim they have passed.

## 3. Automated G0 contract tests

`tests/architecture/test_gateway_g0_contract.py` MUST verify at minimum:

1. profile identity is exactly `ets.gateway.reference.pilot.v1`;
2. profile is marked `pilot`, not `production`;
3. `collector` is default deployment mode;
4. `routed_inline` is present only as disabled/deferred;
5. IPv4 forwarding is false;
6. IPv6 forwarding is false;
7. NAT is false;
8. inter-zone bridging is false;
9. management, collection and upstream zones exist and are distinct;
10. optional observation zone has no default route and does not expose management/sync services;
11. raw evidence retention defaults false/not-retained;
12. pre-commit privacy/minimization is required;
13. content digest semantics explicitly refer to declared representation;
14. Gateway uses ETS Core public API and forbids protocol reimplementation;
15. local history is authoritative against upstream rewrite;
16. queues are bounded and backpressure is explicit;
17. TLS policy prohibits SSLv2/SSLv3/TLS1.0/TLS1.1;
18. TLS 1.2 is supported/allowed under compatibility policy;
19. TLS 1.3 is preferred;
20. preferred syslog transport is TLS;
21. UDP syslog is compatibility-only and declares lower assurance;
22. transport identity and syslog HOSTNAME are not automatically equated;
23. G0 does not claim full RFC 5425 implementation conformance;
24. production/reference signer requires hardware-backed/non-exportable key semantics;
25. UEFI Secure Boot capability is required for physical reference profile;
26. NTPv4 is supported and NTS is preferred where available;
27. clock quality is required;
28. node health is separate from evidence verification;
29. completeness/truth/compliance/legal claims are explicitly false;
30. throughput/capacity targets are marked non-SLA/unmeasured;
31. named G0 documents/ADRs and technical-edit record exist.

## 4. G0 design-review checklist

### Product boundary

- [ ] Out-of-band collector is normative default.
- [ ] Routed/inline is deferred and cannot be accidentally enabled by reference profile.
- [ ] Gateway is not described as SIEM/firewall/IDS/IPS/router.
- [ ] Loss of Gateway creates possible evidence gap, not network outage by design.
- [ ] Previously committed proof remains independently verifiable.

### Network architecture

- [ ] Trust-zone diagram includes management, collection, upstream and optional observation.
- [ ] No default forwarding/NAT/bridging between zones.
- [ ] Management bind boundary is explicit.
- [ ] Observation interface cannot become management or synchronization path.
- [ ] Host firewall posture is default-deny with explicit flows.

### Source identity

- [ ] Network location is not treated as sufficient identity.
- [ ] Transport peer identity and payload identity are distinct.
- [ ] Syslog TLS identity is not assumed to equal message HOSTNAME.
- [ ] RFC 5425 transport semantics are distinguished from a full conformance claim; current cryptography follows BCP 195.
- [ ] Tenant/workspace assignment is server-authorized.
- [ ] Connector credentials cannot reach signer/admin secrets.

### Capture/privacy

- [ ] Privacy/minimization occurs before immutable commitment.
- [ ] Digest semantics state which representation was hashed.
- [ ] Lossy transformations are explicit.
- [ ] Raw content is not retained by default.
- [ ] Hashes are not described as encryption/confidentiality.
- [ ] Gaps/unknown completeness are representable.

### Protocol/Core boundary

- [ ] Gateway consumes stable Core public API.
- [ ] No product-specific canonicalization/Merkle semantics are defined.
- [ ] Local history cannot be rewritten by upstream sync.
- [ ] Receipt states distinguish commit/sign/sync phases.

### Time

- [ ] Source time and Gateway receipt time are distinct.
- [ ] Monotonic sequencing survives wall-clock rollback.
- [ ] Clock quality is explicit.
- [ ] NTS is recommended where available but not described as proof of correct UTC.

### Device/signer/platform

- [ ] software signer limited to lab/development;
- [ ] TPM 2.0 or approved hardware signer required for physical pilot reference;
- [ ] production private key bytes are non-exportable to application code;
- [ ] UEFI Secure Boot is a capability requirement, not an untested implementation claim;
- [ ] update signing/rollback/recovery are requirements for later qualification.

### Claims discipline

- [ ] No truth claim.
- [ ] No completeness claim.
- [ ] No automatic compliance claim.
- [ ] No legal-admissibility claim.
- [ ] No production throughput claim.
- [ ] No claim TPM/attestation proves entire runtime uncompromised.

## 5. Mandatory G1 implementation tests derived from G0

### 5.1 Ingress/authentication

- reject missing/invalid source authorization;
- reject tenant/workspace override outside source authorization mapping;
- mTLS identity captured separately from declared payload identity;
- token credentials never appear in logs/errors;
- replay/duplicate/idempotency conflict behavior deterministic.

### 5.2 Resource boundaries

- body/message size boundary -1, exact, +1;
- compressed and decompressed size boundaries;
- parser timeout/depth/complexity corpus;
- connection concurrency limit;
- queue item/byte limits;
- disk high/critical threshold behavior;
- no success acknowledgement before required local transaction completes.

### 5.3 Privacy/canonicalization

- prohibited field removed before committed representation;
- raw payload absent from default durable state/logs/sync envelope;
- transformed representation digest matches declared representation;
- lossy transform never marked lossless/source-identical;
- Core public API only dependency scan.

### 5.4 Synchronization

- upstream outage at every request phase;
- restart with in-flight items;
- retryable HTTP/network failure;
- terminal rejection;
- conflicting acknowledgement;
- upstream TLS identity mismatch;
- protocol version mismatch;
- local history unchanged by all failures.

### 5.5 Time

- source timestamp absent/malformed/future/past;
- local clock rollback;
- NTP sync loss/recovery;
- receipt sequence monotonic despite wall-clock movement;
- clock-quality downgrade visible.

## 6. Mandatory protocol-specific tests

### HTTPS/webhook

- TLS-only production endpoint;
- supported TLS 1.2/1.3 policy tests;
- prohibit older TLS versions;
- mTLS success/failure where enabled;
- content type validation;
- idempotency bounds;
- malformed JSON/binary input depending profile.

### Syslog

- RFC 5424 valid/invalid corpus;
- syslog-TLS framing/certificate behavior;
- TLS peer identity different from HOSTNAME retained separately;
- UDP duplicate/reorder/load behavior;
- explicit lower-assurance state for UDP source;
- no completeness claim from UDP listener health.

### OTLP

- declared transport(s) only;
- logs/metrics/traces signal class preserved;
- malformed protobuf/JSON if enabled;
- partial rejection/backpressure mapping;
- auth scope and tenant routing;
- OTLP receipt not automatically marked ETS committed.

## 7. Mandatory G3/G4 appliance/network tests

### Network isolation

- scan each interface from each zone;
- management service unreachable from collection/observation;
- sync service/endpoint not exposed as listener where not required;
- `ip_forward` false for IPv4 and IPv6;
- no NAT/masquerade rules;
- no cross-zone bridge;
- packet capture confirms ingest payload does not appear on upstream interface except approved minimized/sync representation;
- passive observation interface has no default route and preferably no L3 address.

### TPM/signer

- provision key;
- sign/verify;
- attempted export fails by provider design;
- restart retains identity according to profile;
- rotation preserves historical verification;
- revocation affects current authorization without rewriting historical evidence;
- signer unavailable yields explicit state.

### Secure Boot/update/recovery

- Secure Boot enabled/validated;
- unsigned boot/update rejected according to platform policy;
- valid signed update succeeds;
- tampered update fails;
- rollback attempt fails when prohibited;
- power loss during update returns to known-good state;
- recovery does not delete/rewrite committed evidence silently.

### Storage/power

- hard power loss during commit;
- hard power loss during sync;
- disk full before/during transaction;
- filesystem/database corruption fixture;
- storage device health warning;
- recovery/restore with proof verification.

## 8. Performance qualification methodology

G0 numbers are test objectives, not performance facts. Later benchmark reports MUST identify:

- exact Gateway software commit/version;
- Core protocol/profile version;
- hardware SKU/CPU/RAM/NVMe/NIC;
- OS/kernel/filesystem;
- signer provider and signing/checkpoint cadence;
- TLS version/auth mode;
- adapter mix;
- payload-size distribution;
- number of tenants/sources;
- local proof/export behavior;
- upstream network latency/bandwidth;
- retention/sync queue policy;
- run duration and warm-up;
- CPU, memory, disk, network and thermal observations;
- accepted/rejected/lost/conflicted counts;
- p50/p95/p99 ingest/commit/checkpoint latency;
- exact definition of an "event per second" result.

The benchmark MUST separate protocol processing from upstream/network latency and MUST retain raw benchmark output sufficient to reproduce the published summary.

## 9. Standards verification matrix

| Area | Primary reference | G0 interpretation |
|---|---|---|
| Zero trust | NIST SP 800-207 / 800-207A | no implicit trust from network location; explicit identities/policy |
| Syslog message | RFC 5424 | structured syslog format; TLS transport recommended by RFC |
| Syslog TLS | RFC 5425 + RFC 9325/BCP 195 | transport model and default port 6514; sender cert identity distinct from HOSTNAME; current TLS crypto policy follows BCP 195; full RFC 5425 conformance not claimed in G0 |
| TLS deployment | RFC 9325 / BCP 195 | prohibit obsolete versions; TLS 1.2 interoperability support; TLS 1.3 preferred |
| OTLP | OpenTelemetry OTLP 1.11.0 | gRPC/HTTP transport; logs/metrics/traces stable at review date |
| Time | RFC 5905 | NTPv4 synchronization |
| Secure time | RFC 8915 | NTS authenticates NTP client/server synchronization in client-server mode |
| TPM | TCG TPM 2.0 Library v185 | hardware-backed key/attestation capability; exact platform implementation remains vendor-specific |
| Firmware resilience | NIST SP 800-193 | protect/detect/recover platform firmware |
| Secure development | NIST SP 800-218 v1.1 | secure software development/delivery practices |
| UEFI | UEFI 2.11 | current UEFI specification baseline located during review; Secure Boot capability used by appliance profile |
| OT security | NIST SP 800-82 Rev. 3 | OT deployment must account for reliability/safety and requires separate qualification |

## 10. G0 evidence package

Before G0 is approved, retain:

- exact base commit;
- PR/branch containing G0 artifacts;
- automated test result;
- review comments/resolution;
- final approved profile digest/commit;
- known limitations/residual risks;
- explicit go/no-go record for G1.

## G0 technical-edit record

The factual/design/qualification classification and standards corrections are recorded in `docs/review/ETS_GATEWAY_G0_TECH_EDIT.md`. This record is a required G0 artifact and must be updated when a standards-dependent requirement changes.
