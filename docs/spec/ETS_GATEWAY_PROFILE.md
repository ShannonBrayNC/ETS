# ETS Gateway Profile v1

Status: GATE-G0 normative candidate
Profile identifier: `ets.gateway.profile.v1`
Reference implementation profile: `ets.gateway.reference.pilot.v1`
Date: 2026-08-13
Parent: #215

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY and OPTIONAL are used as normative engineering requirements in this document and are interpreted using the BCP 14 convention (RFC 2119/RFC 8174).

## 1. Purpose

This profile defines the minimum architectural contract that an ETS Gateway implementation must satisfy before G1 implementation can be considered conformant with G0. It defines product boundaries, deployment modes, trust zones, capture semantics, protocol/security floors, signer/time requirements, failure semantics and qualification labeling. It does not define a vendor-specific BOM or claim measured production performance.

## 2. Conformance classes

### 2.1 `development`

- MAY use software signing keys.
- MAY collapse logical zones onto fewer interfaces for local development.
- MUST still preserve logical service bindings and no-forwarding semantics in the reference config.
- MUST be visibly identified as non-production.

### 2.2 `pilot`

- MUST use the reference network-zone model.
- MUST prohibit routed/inline mode.
- MUST use an approved hardware-backed signer for physical appliance qualification; VM-only pilot qualification may use a virtual TPM or separately approved key service if explicitly documented.
- MUST pass G0 architecture contract tests plus later implementation security/recovery tests.

### 2.3 `production`

Reserved. G0 does not declare any implementation production-qualified. A future profile/version must define the additional security, operations, support, HA, lifecycle and validation requirements.

## 3. Requirement registry

### Product and availability boundary

- **GW-G0-001 MUST** define the Gateway as evidence infrastructure, not a firewall/SIEM/IDS/IPS/router replacement.
- **GW-G0-002 MUST** use `collector` as the default deployment mode.
- **GW-G0-003 MUST NOT** enable `routed_inline` in the v1 reference profile.
- **GW-G0-004 MUST** remain bypassable/non-authoritative for enterprise network availability.
- **GW-G0-005 MUST** preserve independent verification of proof material committed before Gateway/cloud loss.
- **GW-G0-006 MUST NOT** claim complete observation solely from collector health or event volume.

### Network zones

- **GW-G0-010 MUST** define separate logical `management`, `collection` and `upstream` zones.
- **GW-G0-011 MAY** define an `observation` zone for constrained passive mirror operation.
- **GW-G0-012 MUST** disable IPv4 forwarding in the normative profile.
- **GW-G0-013 MUST** disable IPv6 forwarding in the normative profile.
- **GW-G0-014 MUST NOT** define NAT/masquerade between Gateway trust zones.
- **GW-G0-015 MUST NOT** define a bridge spanning management, collection, upstream or observation zones in v1.
- **GW-G0-016 MUST** use default-deny host firewall semantics for unsolicited traffic except explicitly configured service flows.
- **GW-G0-017 MUST** bind management services only to management-zone addresses in pilot/production-like profiles.
- **GW-G0-018 MUST NOT** bind management services to the passive observation interface.
- **GW-G0-019 SHOULD** leave the passive observation interface without a Layer-3 address where the platform supports that deployment.
- **GW-G0-019A MUST NOT** expose management, synchronization, or application-layer ingestion service listeners on the passive observation interface; approved passive capture consumes the interface directly.

### Identity and authorization

- **GW-G0-020 MUST NOT** treat source network location alone as sufficient identity.
- **GW-G0-021 MUST** preserve authenticated transport peer identity separately from payload-declared identity where both exist.
- **GW-G0-022 MUST** resolve tenant/workspace authorization server-side from an approved source/credential mapping; payload assertions alone MUST NOT grant tenant access.
- **GW-G0-023 SHOULD** use mTLS for high-assurance source authentication on HTTPS/syslog-TLS/OTLP profiles.
- **GW-G0-024 MUST** isolate connector credentials from signer private-key material and management credentials.
- **GW-G0-025 MUST** audit enrollment, source authorization and trust-anchor changes.

### Transport security

- **GW-G0-030 MUST NOT** negotiate SSLv2, SSLv3, TLS 1.0 or TLS 1.1.
- **GW-G0-031 MUST** support an approved TLS 1.2 configuration for enterprise interoperability where the implementation exposes TLS application protocols.
- **GW-G0-032 SHOULD** support TLS 1.3 and MUST prefer TLS 1.3 when both peers support it.
- **GW-G0-033 MUST** use TLS-protected HTTPS/webhook endpoints in pilot/production-like profiles.
- **GW-G0-034 SHOULD** use RFC 5424 formatted syslog and RFC 5425-style TLS transport for the preferred syslog production profile.
- **GW-G0-035 MAY** support UDP syslog only as a compatibility profile whose assurance/completeness limitations are explicit.
- **GW-G0-036 MUST NOT** equate a syslog TLS peer certificate identity with the syslog HOSTNAME field without an explicit trusted mapping.
- **GW-G0-037 MAY** support OTLP/gRPC and OTLP/HTTP. The profile MUST identify which signal classes/transports are supported.
- **GW-G0-038 MUST NOT** claim full RFC 5425 conformance solely from using its syslog/TLS transport model; current TLS cryptographic policy follows BCP 195 and G1 must separately qualify the selected syslog-TLS interoperability profile.

### Capture/privacy/evidence boundary

- **GW-G0-040 MUST** record Gateway receipt time for accepted evidence candidates.
- **GW-G0-041 SHOULD** preserve source-provided observation time when available and valid under the source profile.
- **GW-G0-042 MUST** preserve adapter ID/version and source identifier/provenance.
- **GW-G0-043 MUST** apply classification/capture/privacy policy before immutable ETS commitment.
- **GW-G0-044 MUST** minimize/tokenize/redact prohibited fields before canonical commitment.
- **GW-G0-045 MUST** describe what representation a committed `content_digest` covers.
- **GW-G0-046 MUST NOT** claim a digest covers original source bytes when the committed representation was transformed/minimized.
- **GW-G0-047 MUST** record a transformation profile when normalization/transformation occurs.
- **GW-G0-048 MUST** distinguish lossy from lossless transformation.
- **GW-G0-049 MUST** default raw evidence retention to `not_retained` by ETS Gateway.
- **GW-G0-050 MUST** keep a separately governed managed-content store outside the base v1 requirement.

### ETS Core and append semantics

- **GW-G0-060 MUST** consume canonicalization, hashing, Merkle/proof, tree-head and verification semantics from the stable ETS Core public API.
- **GW-G0-061 MUST NOT** reimplement or fork canonical/proof semantics inside Gateway product code.
- **GW-G0-062 MUST** treat a required Core-internal import as an architectural boundary defect to resolve in Core.
- **GW-G0-063 MUST** preserve local append history; upstream synchronization MUST NOT rewrite local sequence/Merkle history.
- **GW-G0-064 MUST** use idempotent synchronization identities and reject conflicting immutable content under the same identity.
- **GW-G0-065 MUST** distinguish local commit, signed checkpoint and upstream synchronization states in receipts/status.

### Resource bounds and failure behavior

- **GW-G0-070 MUST** bound payload/message size.
- **GW-G0-071 MUST** bound decompressed size when compressed inputs are accepted.
- **GW-G0-072 MUST** bound parser/request duration and concurrent work.
- **GW-G0-073 MUST** bound ingress and synchronization queues by items and/or bytes.
- **GW-G0-074 MUST** use warning/critical storage watermarks.
- **GW-G0-075 MUST** return explicit backpressure/rejection rather than silently dropping an item already acknowledged as authoritative.
- **GW-G0-076 MUST** recover in-flight synchronization state deterministically after restart.
- **GW-G0-077 MUST** classify retryable vs terminal synchronization failures.
- **GW-G0-078 MUST** fail synchronization closed on upstream identity/protocol mismatch while preserving local history.
- **GW-G0-079 MUST** expose known collection gaps or unknown observation state rather than presenting them as complete.

### Device identity, signer, boot and update

- **GW-G0-080 MAY** use a software signer only in development/lab profiles.
- **GW-G0-081 MUST** mark software-signer mode as non-production.
- **GW-G0-082 MUST** require TPM 2.0 or a conformance-equivalent approved hardware signer capability for the physical reference pilot profile.
- **GW-G0-083 MUST NOT** expose exportable production evidence-signing private-key bytes to application code.
- **GW-G0-084 SHOULD** purpose-separate device identity, transport identity and evidence-signing keys.
- **GW-G0-085 MUST** define rotation/revocation without silently invalidating historical signatures outside their applicable verification policy.
- **GW-G0-086 MUST** require UEFI Secure Boot capability for the physical reference platform.
- **GW-G0-087 MUST** require signed-update, rollback-policy and recovery design before physical pilot qualification, but G0 MUST NOT claim those mechanisms are implemented merely because they are specified.

### Time

- **GW-G0-090 MUST** separate source-provided observation time from Gateway receipt time.
- **GW-G0-091 MUST** use monotonic time for local durations/retry scheduling where wall-clock rollback could otherwise corrupt behavior.
- **GW-G0-092 MUST** expose clock-quality state.
- **GW-G0-093 MUST** preserve append sequence through wall-clock rollback.
- **GW-G0-094 SHOULD** support NTPv4 for synchronization.
- **GW-G0-095 SHOULD** use Network Time Security where the enterprise time service supports it.
- **GW-G0-096 MUST NOT** claim authenticated time transport proves the upstream time source is semantically correct.

### Observability and claims

- **GW-G0-100 MUST** separate node/service health from cryptographic evidence verification state.
- **GW-G0-101 MUST NOT** log secrets/private keys/bearer tokens.
- **GW-G0-102 MUST NOT** log raw source payloads by default.
- **GW-G0-103 MUST** expose bounded metrics for source/queue/storage/signer/time/sync health.
- **GW-G0-104 MUST NOT** claim truth, complete observation, legal admissibility, regulatory compliance or security of the source system merely from ETS verification.
- **GW-G0-105 MUST** label all G0 throughput/capacity numbers as qualification objectives, not SLAs or measured claims.

## 4. Reference network profile

Logical zones:

| Zone | Primary role | Inbound | Outbound | Forwarding |
|---|---|---|---|---|
| management | admin/enrollment/diagnostics | explicit admin only | approved identity/update/DNS/time as configured | prohibited |
| collection | HTTPS/syslog/OTLP/file-facing services | approved source flows | responses only; no routed transit | prohibited |
| upstream | sync/fleet/checkpoint egress | stateful return/explicit approved callbacks only | explicit ETS/trust/update/time/DNS allowlist | prohibited |
| observation | optional mirrored protocol observation | mirrored traffic | none by default | prohibited |

A physical 4-NIC appliance can map one NIC per zone. A virtual deployment may map multiple logical zones to virtual interfaces/VLANs, but MUST preserve the same logical policy and service-binding rules.

## 5. Reference protocol profile

### HTTPS/webhook

- production-like transport: TLS required;
- authentication: mTLS preferred; source-scoped token profile MAY exist;
- TLS: 1.2 allowed under approved config; 1.3 preferred; earlier prohibited;
- default content type and maximum body are implementation parameters tested in G1.

### Syslog

- preferred format: RFC 5424;
- preferred secure transport: TLS/RFC 5425 model;
- default RFC 5425 port: 6514 unless local policy changes it;
- UDP compatibility: MAY be enabled only with explicit lower-assurance declaration;
- sender transport identity and message HOSTNAME remain separate provenance fields;
- G0 does not claim full RFC 5425 implementation conformance; exact G1 cipher/protocol interoperability is qualified against current BCP 195.

### OTLP

At minimum G1 SHOULD implement one standard OTLP transport. If both are supported, the profile may expose:

- OTLP/gRPC;
- OTLP/HTTP with Protocol Buffers.

Supported signal classes MUST be declared. OTLP receipt is an ingestion event, not automatic ETS commitment.

## 6. Observation state model

The Gateway operational model MUST support states equivalent to:

- `healthy_observation`;
- `degraded_observation`;
- `collection_gap`;
- `unknown_observation`.

The names may evolve through a versioned contract, but the semantics MUST distinguish known degradation/gaps/unknown state from complete observation.

## 7. Clock-quality model

The Gateway MUST preserve a bounded state compatible with the existing Edge concept:

- synchronized;
- estimated;
- degraded;
- unknown.

Additional detail MAY be added outside canonical v1 fields (source, offset, dispersion, last sync, NTS authenticated, rollback event), provided it does not silently change existing canonical identity semantics.

## 8. Hardware capability profile

The G0 reference physical capability profile is vendor-neutral:

- architecture: x86-64;
- memory: >=16 GiB; 32 GiB reference pilot target;
- storage: >=1 TB high-endurance NVMe reference pilot target;
- TPM 2.0 capability required;
- UEFI Secure Boot capability required;
- >=3 logical network zones; four physical 1/2.5 GbE-class interfaces preferred;
- optional 10 GbE performance tier;
- RTC/watchdog capability preferred/required as finalized by G3 hardware qualification.

G0 does not certify a specific motherboard, NIC, SSD, enclosure, thermal envelope, MTBF, EMC, environmental rating or power design.

## 9. Qualification objectives (non-SLA)

The reference machine profile carries non-SLA targets for later benchmark design:

- sustained event objective: 1,000 records/s under defined synthetic workload;
- burst objective: 5,000 records/s for 600 seconds;
- stream hash object objective: 10 GiB;
- disconnected sync backlog objective: 7 days under a separately documented workload;
- restart objective: no unexplained loss of acknowledged committed records;
- upstream loss objective: local proofs remain verifiable.

No implementation may advertise these values as measured/supportable until G4/G6 benchmark evidence exists for a named hardware/software/profile combination.

## 10. Required G0 artifacts

- `docs/architecture/ETS_GATEWAY_ARCHITECTURE.md`;
- `docs/security/ETS_GATEWAY_THREAT_MODEL.md`;
- this profile;
- `docs/test/ETS_GATEWAY_G0_TEST_PLAN.md`;
- ADRs covering non-inline deployment, network zones, capture/privacy boundary and identity/time/signer boundaries;
- machine-readable schema/profile;
- architecture contract tests;
- `docs/review/ETS_GATEWAY_G0_TECH_EDIT.md`.

## 11. G0 approval

Passing automated profile tests is necessary but insufficient. G0 requires independent architecture/security review because the tests validate declared invariants, not the correctness of future runtime/network/hardware behavior.
