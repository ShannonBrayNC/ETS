# ETS Gateway Architecture

Status: GATE-G0 architecture candidate
Date: 2026-08-13
Parent: GitHub issue #215
Related: #140, #143, #162, #213, #221
Normative profile: `docs/spec/ETS_GATEWAY_PROFILE.md`
Machine profile: `config/gateway/reference-profile.v1.json`
Threat model: `docs/security/ETS_GATEWAY_THREAT_MODEL.md`
Technical edit: `docs/review/ETS_GATEWAY_G0_TECH_EDIT.md`

## 1. Purpose

ETS Gateway is a network-resident evidence collection and commitment product. It receives approved enterprise telemetry or event material, applies an explicit capture policy, preserves provenance and transformation boundaries, commits the policy-approved representation through ETS Core, retains local proof/checkpoint state, and synchronizes verifiable records or checkpoints upstream.

The Gateway is designed so that enterprise application and network availability do not depend on the Gateway. The default product profile is therefore out-of-band. Failure or removal of the Gateway can create an evidence-collection gap, but it must not interrupt the observed service merely because ETS is unavailable, and it must not invalidate proof material committed before the failure.

## 2. Product boundaries

### 2.1 In scope

- authenticated or policy-authorized telemetry/event intake;
- source and adapter identity/context capture;
- source timestamp plus Gateway receipt timestamp;
- privacy classification and minimization before immutable ETS commitment;
- versioned normalization with transformation provenance;
- canonical ETS evidence creation through the public ETS Core API;
- append-only local evidence/proof state;
- signed checkpoints through a pluggable signer;
- bounded, durable, idempotent synchronization;
- explicit queue/backpressure and collection-gap states;
- network, source, signer, storage, time, and synchronization health;
- offline verification and proof export;
- local/fleet operational interfaces in later sprints.

### 2.2 Explicitly out of scope for Gateway v0.1

- firewall, router, NAT gateway, VPN concentrator, WAF, IDS/IPS, EDR, NDR or SIEM replacement;
- general-purpose packet capture or forensic acquisition;
- mandatory transparent proxying or TLS interception;
- autonomous remediation;
- semantic truth determination;
- proof of complete observation;
- automatic legal admissibility or regulatory certification;
- universal trust scores;
- changing ETS Core canonicalization, Merkle or verification semantics;
- high-availability claims before later qualification.

## 3. Architectural invariants

1. **Out-of-band by default.** `collector` is the normative v0.1 deployment mode. `passive_mirror` is constrained and optional. `routed_inline` is documented but disabled for v0.1.
2. **No forwarding by default.** The operating system must not route, bridge or NAT between collection, management and upstream trust zones in the normative profile.
3. **Gateway is not an availability authority.** Loss of the Gateway must not make the observed enterprise network or service unavailable solely because ETS is down.
4. **Previously committed proof remains independently verifiable.** Cloud, fleet or Gateway loss cannot retroactively invalidate valid local proof material.
5. **ETS Core owns protocol semantics.** Gateway consumes canonicalization, hashing, Merkle, proof and verification behavior through the stable public Core facade. Gateway code must not redefine those semantics.
6. **Raw content is outside the default ETS retention boundary.** Capture policy decides whether raw bytes are retained elsewhere. The default Gateway profile commits metadata/provenance/digests/proofs and does not retain raw evidence bytes.
7. **Privacy precedes immutable commitment.** Classification, minimization, tokenization/redaction and capture-tier decisions occur before the canonical ETS evidence object/event is committed.
8. **Normalization is not source truth.** A normalized record must identify its source representation and transformation profile. Lossy transformations must be marked as such.
9. **Identity is not inferred solely from network location or message fields.** Source IP, VLAN and syslog HOSTNAME can be evidence attributes but do not by themselves establish cryptographic identity.
10. **Time quality is explicit.** Source time, receipt time and clock-quality state are distinct. Clock rollback cannot rewrite append order.
11. **No silent loss.** Bounded-resource exhaustion results in explicit rejection/backpressure/gap state; the Gateway must not silently discard accepted authoritative records.
12. **No completeness overclaim.** Capture health and observed volume are not evidence that all source events were observed.
13. **Production private keys are non-exportable.** Application processes use a signer abstraction; production private key bytes are never returned to Gateway application code.
14. **Every trust-changing administrative action is auditable.** Enrollment, source authorization, policy, trust anchor, key, update and time-source changes create administrative evidence/audit records.

## 4. Deployment modes

### 4.1 Collector mode — normative v0.1

Source systems initiate delivery to a Gateway collection endpoint or the Gateway polls an approved source API through a connector. Typical inputs include HTTPS/webhook, syslog over TLS, OpenTelemetry Protocol, file/drop ingestion and approved enterprise connector APIs. The preferred syslog profile uses the RFC 5425 transport/port/identity model, but G0 does not claim full RFC 5425 implementation conformance; current TLS cryptographic policy follows BCP 195 and exact interoperability is a G1 qualification item.

Characteristics:

- no dependency on transit forwarding;
- source-to-Gateway authorization is explicit;
- transport identity and source payload identity remain separate evidence concepts;
- delivery failures produce observable backlog, retry or collection-gap state;
- source services continue operating when Gateway is unavailable unless the source product itself is configured to block on logging, which is outside ETS control.

### 4.2 Passive mirror mode — optional/experimental in v0.1

A dedicated observation interface can receive mirrored traffic from a SPAN/TAP or equivalent source, but v0.1 does not define a general packet-capture product. Only explicitly approved protocol parsers may consume mirrored material.

Requirements:

- observation interface has no default route;
- no forwarding from observation to any other interface;
- no management, synchronization, or application-layer ingestion service binds to the observation interface; approved passive capture consumes the interface directly;
- where platform capabilities allow, no Layer-3 address is assigned to the observation interface;
- capture policy bounds accepted protocol, byte rate, payload size and retention;
- SPAN/TAP observation must never be represented as proof of complete network observation.

### 4.3 Routed/inline mode — deferred

`routed_inline` is not permitted by the v0.1 reference profile. Supporting it would require a separate product/profile because it introduces link availability, fail-open/fail-closed behavior, bypass hardware, L2/L3 forwarding correctness, loop prevention, HA, latency and capacity obligations that conflict with the initial non-inline product boundary.

No v0.1 marketing, runbook or configuration may describe the Gateway as an inline enforcement device.

## 5. Logical architecture

```text
Enterprise sources
  |  HTTPS / syslog-TLS / OTLP / file / connector APIs
  v
+------------------------- COLLECTION PLANE --------------------------+
| Protocol listeners -> source authorization -> bounded ingress queue |
+------------------------------+--------------------------------------+
                               |
                               v
+---------------------- POLICY / PRIVACY PLANE -----------------------+
| classify -> capture policy -> minimize/redact -> representation     |
+------------------------------+--------------------------------------+
                               |
                               v
+----------------------- TRANSFORMATION PLANE ------------------------+
| normalize -> preserve source refs -> transformation provenance      |
+------------------------------+--------------------------------------+
                               |
                               v
+--------------------------- ETS CORE --------------------------------+
| public Core API -> canonicalize/hash -> append -> proof/tree head   |
+------------------------------+--------------------------------------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
     durable local state                 signer provider
     evidence/proofs/sync               software (lab)
              |                          TPM/HSM (production)
              v
     durable synchronization journal
              |
              v
+-------------------------- UPSTREAM PLANE ----------------------------+
| mutually authenticated synchronization / checkpoint exchange       |
+---------------------------------------------------------------------+

+------------------------- MANAGEMENT PLANE --------------------------+
| enrollment | RBAC | network | sources | policy | keys | update      |
| diagnostics | health | audit | backup/recovery | fleet integration  |
+---------------------------------------------------------------------+
```

## 6. Network trust zones and interface roles

The architecture defines logical trust zones, not a mandatory physical port count. The physical ETS Compute target in #215/#221 can provide four 1/2.5 GbE ports, but a virtual profile may realize zones using virtual NICs/VLANs.

### 6.1 Management zone (`management`)

Purpose: administrative API/UI, enrollment, diagnostics, update orchestration and break-glass maintenance.

Requirements:

- management services bind only to configured management addresses;
- no unauthenticated management endpoint;
- production remote administration uses enterprise identity or certificate/key-based access and RBAC;
- password-only remote root login is not part of the normative profile;
- management access is never accepted from passive observation interfaces;
- administrative events are audit/evidence candidates.

### 6.2 Collection zone (`collection`)

Purpose: source-initiated telemetry/event delivery.

Requirements:

- only configured ingestion protocols/listeners are exposed;
- source authorization is per listener/source profile;
- collectors cannot invoke management or signer-admin APIs;
- parsers operate under bounded CPU, memory, payload and concurrency policy;
- collection traffic is not forwarded to upstream or management networks.

### 6.3 Upstream synchronization zone (`upstream`)

Purpose: outbound synchronization/checkpoint exchange, fleet control where enabled, update metadata retrieval and optionally approved time/DNS services.

Requirements:

- least-privilege egress allowlist;
- stateful response traffic only unless a separately approved management callback is configured;
- upstream identity is pinned or validated against configured trust anchors;
- protocol/version mismatch fails closed for synchronization without rewriting local history.

### 6.4 Passive observation zone (`observation`, optional)

Purpose: receive mirrored traffic for approved protocol-specific observation.

Requirements:

- no default gateway;
- no inter-zone forwarding;
- no management listener;
- no upstream listener;
- preferred no Layer-3 address;
- strict protocol/size/rate policy.

### 6.5 Forwarding prohibition

The normative profile requires:

- IPv4 forwarding disabled;
- IPv6 forwarding disabled;
- no bridge spanning collection/management/upstream/observation interfaces;
- no NAT between zones;
- no transparent proxy mode;
- no IP masquerade;
- host firewall default-deny for unsolicited traffic not explicitly required by the active profile.

## 7. Ingestion protocol requirements

### 7.1 HTTPS/webhook

- TLS-protected endpoint only in production.
- TLS policy follows current BCP 195: TLS 1.2 supported for interoperability where required; TLS 1.3 supported and preferred; SSLv2, SSLv3, TLS 1.0 and TLS 1.1 prohibited.
- mTLS is the preferred high-assurance source-authentication profile.
- bearer/API credentials, when supported for compatibility, are source-scoped, rotatable, non-logged and stored via the approved secret provider.
- body, header, decompression, concurrency and request-duration limits are explicit.
- idempotency/correlation inputs are bounded and validated.

### 7.2 Syslog

- RFC 5424 structured syslog is the preferred message format.
- TLS transport is the preferred production transport.
- Syslog over TLS uses the RFC 5425 transport model, while deployed cryptographic policy follows current TLS best practice rather than relying on 2009-era cipher assumptions.
- TCP port 6514 is the registered/default RFC 5425 port; local policy may choose another port.
- UDP syslog is a constrained legacy compatibility profile. It provides neither reliable delivery nor cryptographic peer authentication by itself and cannot support completeness claims.
- TLS peer identity is not assumed to equal the syslog HOSTNAME field. Both are preserved separately when available.

### 7.3 OpenTelemetry Protocol

- OTLP-compatible intake may support OTLP/gRPC and OTLP/HTTP with Protocol Buffers.
- The Gateway preserves signal class (logs, metrics, traces; profiles only if explicitly supported by the implementation/profile).
- OTLP transport acceptance is not equivalent to ETS evidence commitment. OTLP material first passes source authorization and capture policy.
- partial success, rejection and backpressure must be surfaced using behavior compatible with the selected OTLP transport and mapped to Gateway operational metrics.

### 7.4 File/drop ingestion

- files are streamed; whole-file memory residency is not required;
- maximum object size and path/source policy are explicit;
- symlink/path traversal and race handling are implementation requirements for G1;
- raw file bytes are not retained by default after the policy-approved commitment is produced;
- the evidence reference identifies source custody when available.

### 7.5 Enterprise connectors

Connectors run behind a versioned adapter contract and credential broker. G0 defines the boundary; connector-specific semantics are G2 work.

Connector requirements include:

- least-privilege credentials;
- source cursor/checkpoint state separate from ETS Merkle state;
- reconciliation or explicit gap state when delivery may have been missed;
- source API response identity/version/context preserved;
- tenant/workspace scoping enforced server-side;
- connector process cannot access production signing private keys.

## 8. Capture and evidence boundary

### 8.1 Capture stages

The normative conceptual sequence is:

1. receive bytes/message/reference;
2. apply resource bounds and syntactic validation;
3. resolve source authorization and tenant/workspace scope;
4. record Gateway receipt time and source-provided observation time when present;
5. classify content/metadata under the active privacy/capture policy;
6. minimize, tokenize or redact prohibited material before immutable ETS commitment;
7. select the representation that is permitted to be committed;
8. compute content digest for that representation;
9. normalize without overwriting source provenance;
10. record transformation profile and whether it is lossless/lossy;
11. construct the versioned ETS evidence/event input;
12. canonicalize and append through the ETS Core public API;
13. generate/persist proof material and checkpoint state;
14. enqueue the synchronization envelope using a stable idempotency key;
15. return a receipt whose state distinguishes local commit from upstream synchronization.

### 8.2 Digest semantics

`content_digest` means the digest of the explicitly declared evidence representation. It must not be described as a digest of original source bytes unless the active capture profile actually committed the original-byte representation.

This distinction is required because privacy-preserving capture may deliberately transform or minimize the source before immutable commitment. A lossy/minimized representation must carry transformation provenance.

### 8.3 Raw-content retention

Default: `not_retained` by ETS Gateway.

A future managed content store must be separately governed for encryption, access, retention, deletion, jurisdiction, breach response and custody. Enabling such a store is not a G0 acceptance requirement.

### 8.4 Completeness and gaps

The Gateway records what it observed within its declared observation boundary. It does not infer that absent events never existed.

Operational state must distinguish at least:

- `healthy_observation` — configured collector is operating within known bounds;
- `degraded_observation` — source/transport/clock/resource condition reduces assurance;
- `collection_gap` — a known interval or cursor range may be incomplete;
- `unknown_observation` — completeness cannot be evaluated.

These are observation-health states, not cryptographic verification results.

## 9. ETS Core boundary

Gateway must consume ETS Core through the stable public API boundary established by #162/#188.

Gateway may own:

- transport listeners;
- adapter SDK/runtime;
- authorization and tenant routing;
- capture policy orchestration;
- local operational queueing;
- synchronization transport;
- device operations.

Gateway must not own or redefine:

- canonical JSON/serialization;
- canonical evidence identity rules;
- hash profiles;
- Merkle leaf/node construction;
- inclusion/consistency proof semantics;
- signed-tree-head canonical payload;
- verification result semantics;
- historical compatibility profiles.

Any required internal Core import is treated as an architectural defect in the public Core boundary, not justification for Gateway to bind to internals.

## 10. Durable state and acknowledgement semantics

Logical durable stores are separated even when one physical device is used:

- canonical evidence/log state;
- proof/checkpoint state;
- synchronization journal;
- connector cursors/reconciliation state;
- configuration/policy state;
- administrative audit state;
- operational logs/metrics.

Raw content is not part of the default Gateway durable state.

A receipt must distinguish:

- accepted by ingress;
- committed locally;
- checkpoint/signature pending;
- checkpoint signed;
- synchronization pending;
- synchronized;
- terminally rejected/dead-lettered.

No response may claim successful upstream synchronization before the upstream acknowledgement has been validated.

## 11. Bounded-resource model

Every untrusted input path has bounded:

- payload/message size;
- decompressed size where compression is accepted;
- parse depth/complexity;
- request duration;
- concurrent connections/requests;
- queue items and queue bytes;
- retry count and retry age;
- connector page/batch size;
- disk high/critical watermarks;
- diagnostics/log field size.

At capacity boundaries the Gateway returns explicit backpressure/rejection or transitions to a documented degraded state. It must not silently drop an item after acknowledging it as authoritatively committed.

## 12. Device identity, signer and attestation

### 12.1 Development profile

A software signer is allowed only in development/lab and must be visibly classified as non-production.

### 12.2 Production profile

- TPM 2.0 or a conformance-equivalent approved hardware signer is required by the reference appliance profile;
- application code receives signing operations/results, not exportable private key material;
- device identity, TLS identity and evidence signing keys are logically purpose-separated;
- rotation/revocation history is preserved so historical signatures remain evaluable under their applicable verification policy;
- a revoked current credential does not mechanically rewrite or delete historical evidence.

### 12.3 Attestation boundary

Hardware/workload attestation, when implemented, establishes only the measurements/claims verified against an attestation policy. It does not prove that every runtime component is uncompromised or that source evidence is true.

## 13. Boot, update and recovery architecture

The physical reference profile requires UEFI Secure Boot capability and TPM 2.0. G3/G4 will qualify actual hardware and update implementation.

The target update architecture must provide:

- signed update artifacts;
- verified update metadata;
- version/rollback policy;
- staged deployment capability;
- known-good recovery path;
- audit records for update attempt/result;
- no update process access to exportable production signing keys.

This aligns with platform resiliency principles of protection, detection and recovery; G0 does not claim hardware qualification before those tests occur.

## 14. Time architecture

Gateway stores source-provided observation time separately from Gateway receipt time.

Requirements:

- UTC timestamps for externally represented wall-clock time;
- monotonic clock for durations, retry scheduling and local sequencing decisions;
- NTPv4 is a supported synchronization mechanism;
- Network Time Security (NTS) is preferred where enterprise infrastructure supports it;
- authenticated time transport does not by itself prove the upstream clock is semantically correct;
- clock source, synchronization state, offset/dispersion where available and rollback events contribute to `clock_quality`;
- wall-clock rollback never rewrites local append sequence or previous timestamps;
- unsynchronized/degraded time lowers time assurance rather than fabricating precision.

## 15. Security and privacy logging

Gateway operational logging must not become a secondary raw-evidence leak.

Rules:

- secrets, private keys, bearer tokens and credential material are never logged;
- raw source payloads are not logged by default;
- diagnostic bundles minimize tenant/event identifiers and redact credentials;
- security-relevant administrative changes are audited;
- rejected/oversized/malformed events log bounded reason codes and source context without copying unbounded hostile input;
- node health is distinct from evidence verification state.

## 16. Hardware capability profile for later qualification

G0 defines required capabilities, not a vendor/BOM selection.

Reference ETS Compute Gateway capability target:

- x86-64 processor, minimum four physical/logical cores; eight-core class recommended for standard pilot testing;
- 16 GiB RAM minimum; 32 GiB reference target; 64 GiB supported target for higher-volume profile;
- high-endurance NVMe, 1 TB reference minimum for Gateway pilot qualification;
- TPM 2.0;
- UEFI Secure Boot capable firmware;
- four 1/2.5 GbE-class interfaces preferred for physical segmentation;
- optional 10 GbE performance tier;
- RTC and watchdog capability;
- health telemetry for storage and thermal state where exposed by hardware.

These are procurement/qualification inputs. They are not a statement of measured throughput or environmental certification.

## 17. Qualification objectives — not SLAs

G0 establishes test targets to size G1/G3 work. They are explicitly not supported-product claims until measured and approved.

Standard pilot objectives:

- 1,000 committed evidence records/second sustained under the defined synthetic small-event workload;
- 5,000 records/second bounded burst for ten minutes;
- streaming hash path for objects up to 10 GiB under the file profile;
- seven days of synchronization backlog under a separately documented workload/capacity model;
- restart recovery without unexplained committed-record loss;
- deterministic backpressure before disk/queue exhaustion;
- upstream outage does not invalidate local proofs.

The benchmark specification in later work must define payload distribution, proof/checkpoint cadence, signing provider, storage hardware, TLS mode, connector mix and success criteria before any result is externally claimed.

## 18. Failure semantics

| Condition | Required architectural behavior |
|---|---|
| Upstream unavailable | continue local operation within policy/capacity; queue durable sync work; expose lag |
| Collection source unavailable | mark source degraded/gap as appropriate; do not infer zero events |
| Queue near capacity | backpressure and warning before exhaustion |
| Disk critical | reject before incomplete commit; preserve existing committed state |
| Signer unavailable | do not claim signed checkpoint; use explicit pending/degraded/fail-closed policy |
| Clock unsynchronized | preserve received sequence; mark time quality degraded/unknown |
| Duplicate delivery | idempotent acceptance or explicit conflict; never silently create conflicting identity |
| Upstream identity/version mismatch | fail sync closed; preserve local history |
| Process restart | recover in-flight queue state deterministically |
| Physical theft | encrypted/protected storage and hardware-backed keys are later appliance controls; historical trust assessment remains policy-bound |
| Update failure | return to known-good state without rewriting committed evidence |

## 19. Standards and authoritative references

G0 was technically edited against primary specifications/guidance current on 2026-08-13:

- NIST SP 800-207, *Zero Trust Architecture* — no implicit trust based solely on network location; authenticate/authorize subjects/devices/resources.
- NIST SP 800-207A — application/service identity and granular policy in cloud-native/multi-cloud environments.
- NIST SP 800-193, *Platform Firmware Resiliency Guidelines* — protect, detect and recover platform firmware.
- NIST SP 800-218 v1.1, *Secure Software Development Framework* — secure development and delivery practices. A v1.2 draft exists; G0 does not cite draft text as final normative guidance.
- NIST SP 800-82 Rev. 3, *Guide to Operational Technology Security* — security controls must account for OT reliability/safety constraints; Gateway OT profiles require separate qualification.
- NIST SP 800-92 (final) and SP 800-92 Rev. 1 (draft) — enterprise log-management planning/background; the draft is not treated as final normative requirements.
- RFC 5424, *The Syslog Protocol*.
- RFC 5425, *TLS Transport Mapping for Syslog*.
- RFC 9325 / BCP 195, current TLS/DTLS deployment recommendations.
- OpenTelemetry OTLP Specification 1.11.0 — stable trace, metric and log transport semantics; profiles signal remains development at the time of review.
- RFC 5905, NTPv4.
- RFC 8915, Network Time Security for NTP.
- Trusted Computing Group TPM 2.0 Library Specification, Version 185 (March 2026).
- UEFI Specification 2.11 (December 2024).

## 20. G0 exit criteria

GATE-G0 exits only when:

- architecture, profile, threat model and ADRs are reviewed together;
- machine-readable reference profile passes architecture contract tests;
- routed/inline operation remains disabled in v0.1;
- trust zones and no-forwarding invariant are explicit;
- capture/privacy/digest semantics are explicit;
- Core ownership boundary is explicit;
- time, identity, signer and key boundaries are explicit;
- known failure semantics and residual risks are documented;
- qualification targets are labeled non-SLA;
- no statement implies truth, complete observation, legal admissibility, compliance or production performance without evidence;
- independent technical/security review is recorded before G1 implementation treats the profile as approved.
