# ETS Gateway Threat Model

Status: GATE-G0 security design candidate
Date: 2026-08-13
Parent: #215
Architecture: `docs/architecture/ETS_GATEWAY_ARCHITECTURE.md`
Normative profile: `docs/spec/ETS_GATEWAY_PROFILE.md`

## 1. Objective

This threat model identifies security, privacy, availability and evidentiary risks introduced by placing ETS Gateway on an enterprise network. It intentionally distinguishes threats to **Gateway operation** from threats to the **meaning of evidence**. Cryptographic validity can establish declared integrity/provenance properties for committed material; it does not establish that the source was truthful, that the observation was complete, or that a real-world claim is correct.

## 2. Method

The model uses STRIDE categories plus evidence-specific failure classes:

- Spoofing;
- Tampering;
- Repudiation;
- Information disclosure;
- Denial of service;
- Elevation of privilege;
- Observation/completeness failure;
- Verification-boundary overclaim;
- Privacy/irreversible-commit failure;
- Supply-chain/platform failure.

Qualitative risk values are architecture-review priorities, not quantitative probabilities:

- **Critical** — unacceptable if uncontrolled; may invalidate product boundary or expose signing/trust material.
- **High** — must have a defined preventive/detective control before pilot.
- **Medium** — must be bounded, monitored and documented before pilot.
- **Low** — accepted only with documented rationale/monitoring.

## 3. Assets

### 3.1 Trust assets

- device identity key/certificate;
- evidence signing key and historical signer metadata;
- trust anchors and upstream identity configuration;
- enrollment/bootstrap material;
- approved software/update signing roots;
- capture policy and privacy policy;
- tenant/workspace authorization map.

### 3.2 Evidence assets

- canonical ETS event/evidence state;
- content digests and evidence references;
- Merkle state, inclusion/consistency proofs and signed checkpoints;
- synchronization journal and validated acknowledgements;
- connector cursors/reconciliation markers;
- transformation provenance;
- collection-gap records;
- administrative audit records.

### 3.3 Availability assets

- bounded ingress queues;
- local storage capacity/endurance;
- signer availability;
- clock/time synchronization state;
- DNS/upstream connectivity where required;
- update/recovery capability;
- Gateway process and host availability.

### 3.4 Sensitive data

- source telemetry contents;
- PII/PHI/credentials/secrets that may be present in telemetry;
- source and tenant identifiers;
- connector credentials/tokens;
- management session data;
- diagnostic bundles;
- hashes that could permit confirmation/dictionary attacks against low-entropy sensitive data.

## 4. Trust boundaries

### TB-1 Enterprise source -> collection listener

Untrusted until source authorization and policy evaluation complete. Network location is not sufficient identity.

### TB-2 Collection parser -> policy/privacy boundary

Hostile input may exploit parser/resource bugs. Input remains untrusted until bounded and classified.

### TB-3 Policy/privacy -> transformation/canonical evidence input

This is the irreversible-commit boundary. Prohibited material must be removed before canonical ETS commitment.

### TB-4 Gateway runtime -> ETS Core

Gateway may call only stable public Core interfaces. Product code cannot redefine canonical/proof semantics.

### TB-5 Gateway runtime -> signer provider

Application supplies a digest/signing request and receives a result. Production private keys do not cross this boundary as exportable bytes.

### TB-6 Local durable state -> synchronization transport

Only the versioned synchronization envelope is transmitted. Local history cannot be rewritten by upstream acknowledgement.

### TB-7 Gateway -> upstream ETS/fleet services

Remote endpoint is untrusted until identity/protocol verification succeeds.

### TB-8 Administrator -> management plane

Administrative identity, role, session and requested trust-changing action must be authorized and audited.

### TB-9 Update artifact -> boot/runtime platform

Update metadata/artifact is untrusted until signature/version policy checks complete.

### TB-10 Physical platform -> enterprise environment

Physical theft, tampering, malicious peripherals/firmware and storage removal are possible within the appliance threat model.

## 5. Threat register

### GW-T001 — Source identity spoofing

- Category: Spoofing
- Initial risk: High
- Scenario: attacker sends telemetry while claiming another source ID, tenant, hostname or device.
- Controls:
  - per-source authorization;
  - mTLS for high-assurance HTTPS/syslog/OTLP profiles;
  - tenant/workspace binding configured server-side;
  - preserve transport peer identity separately from message-declared identity;
  - never treat source IP/VLAN or syslog HOSTNAME alone as cryptographic identity;
  - stable reason codes for unauthorized source submissions.
- Residual: legacy UDP/syslog sources remain weakly attributable; provenance assurance must say so.

### GW-T002 — Syslog HOSTNAME/transport identity conflation

- Category: Spoofing / verification-boundary error
- Initial risk: High
- Scenario: a TLS-authenticated sender submits a syslog message whose HOSTNAME identifies another host; operator assumes TLS proves the message HOSTNAME.
- Controls:
  - store TLS peer identity and syslog HOSTNAME separately;
  - no automatic equality assumption;
  - evidence/provenance UI labels source assertions vs authenticated transport identity.
- Residual: intermediary relays may legitimately send records on behalf of other hosts; connector profile must define this chain.

### GW-T003 — Telemetry modification in transit

- Category: Tampering
- Initial risk: High
- Controls:
  - TLS transport for production HTTPS/OTLP/syslog-TLS;
  - TLS 1.3 preferred, approved TLS 1.2 compatibility only;
  - mTLS when source identity assurance requires it;
  - digest the declared evidence representation after policy transformation;
  - record transport/security profile used.
- Residual: UDP syslog can be modified/spoofed in transit and is explicitly lower assurance.

### GW-T004 — UDP syslog loss/reordering/duplication

- Category: Observation failure / DoS
- Initial risk: High
- Controls:
  - prefer syslog-TLS;
  - UDP is compatibility-only;
  - preserve receive order/receipt time but do not infer source sequence unless supplied;
  - expose socket/adapter drop counters where available;
  - do not claim completeness;
  - evidence gaps remain possible even when no local error is detected.
- Residual: UDP provides no end-to-end delivery guarantee; this cannot be eliminated by Gateway alone.

### GW-T005 — Replay or duplicate submission

- Category: Spoofing/Tampering
- Initial risk: High
- Controls:
  - bounded idempotency keys/source sequence where available;
  - replay windows/nonces for authenticated API profiles as appropriate;
  - deterministic duplicate handling;
  - conflicting content under the same immutable idempotency identity is a terminal conflict, not an overwrite.
- Residual: sources without stable sequence/idempotency can only receive best-effort duplicate analysis.

### GW-T006 — Tenant/workspace confusion

- Category: Elevation / information disclosure
- Initial risk: Critical
- Controls:
  - tenant/workspace determined from server-side source authorization, not trusted arbitrary payload headers alone;
  - per-tenant credential isolation;
  - server-side authorization for search/export/admin actions;
  - cross-tenant negative tests required in G1/G2.
- Residual: configuration error remains possible and requires audited change review.

### GW-T007 — Malicious parser payload

- Category: Elevation / DoS
- Initial risk: Critical
- Controls:
  - strict size/decompression/depth/time/concurrency limits;
  - memory-safe/library updates where available;
  - isolated adapter processes/containers where practical;
  - parser fuzzing/property tests in G1;
  - no signer-admin or management credentials exposed to adapter processes.
- Residual: parser/library zero-days remain possible; process isolation reduces blast radius.

### GW-T008 — Decompression bomb / oversized event

- Category: DoS
- Initial risk: High
- Controls:
  - compressed and decompressed size limits;
  - streaming read/hash where applicable;
  - request timeout and rate limit;
  - reject before durable commit when bounds are exceeded;
  - bounded diagnostic messages.

### GW-T009 — Queue exhaustion

- Category: DoS / observation failure
- Initial risk: High
- Controls:
  - bounded ingress/sync queues by item and byte count;
  - high/critical watermarks;
  - explicit backpressure and Retry-After where protocol supports it;
  - no silent drop after authoritative acknowledgement;
  - queue depth/age metrics.
- Residual: source behavior may ignore backpressure and create collection gaps.

### GW-T010 — Disk exhaustion or endurance failure

- Category: DoS/Tampering
- Initial risk: High
- Controls:
  - reserved capacity for atomic commit/recovery;
  - warning/critical/fail-closed thresholds;
  - high-endurance storage qualification in G3/G4;
  - storage-health telemetry;
  - crash/power-loss tests;
  - no partial success claim if complete authoritative transaction cannot be committed.

### GW-T011 — Local evidence/log database tampering

- Category: Tampering
- Initial risk: Critical
- Controls:
  - append/proof verification through ETS Core;
  - filesystem/storage access separation;
  - signed checkpoints;
  - startup/integrity checks;
  - backup/restore preserving verifiability;
  - tamper tests in later sprint.
- Residual: a fully privileged attacker can destroy availability; cryptographic commitments help detect unauthorized historical modification but do not prevent deletion.

### GW-T012 — Synchronization journal tampering

- Category: Tampering
- Initial risk: High
- Controls:
  - canonical envelope hashing/idempotency;
  - validated upstream acknowledgements;
  - local committed evidence remains authoritative;
  - restart recovery maps in-flight state to retryable state rather than assuming success;
  - conflicting acknowledgement is terminal/error state.

### GW-T013 — Upstream impersonation

- Category: Spoofing
- Initial risk: Critical
- Controls:
  - TLS peer validation against configured trust anchors;
  - mutual authentication for managed synchronization profile;
  - explicit upstream identity and protocol profile;
  - fail closed on identity/version mismatch;
  - local history is never rewritten to match remote state.

### GW-T014 — Malicious upstream acknowledgement

- Category: Tampering
- Initial risk: High
- Controls:
  - acknowledgement content validated against queued immutable identity/hash/index/checkpoint expectations;
  - acknowledgement itself hashed/recorded;
  - mismatch transitions to conflict rather than synchronized.

### GW-T015 — Gateway used as network pivot/router

- Category: Elevation / information disclosure
- Initial risk: Critical
- Controls:
  - IPv4/IPv6 forwarding disabled;
  - no bridge/NAT/masquerade across trust zones;
  - host firewall default-deny;
  - service binding by zone/interface;
  - passive observation interface has no default route and preferably no L3 address;
  - architecture tests/config checks gate normative profile.
- Residual: host-root compromise can alter network config; measured/secure boot and host hardening reduce but do not eliminate.

### GW-T016 — Management service exposed on collection/observation network

- Category: Elevation
- Initial risk: Critical
- Controls:
  - management bind addresses are explicit;
  - no wildcard binding in production unless firewall and interface policy are independently validated;
  - network tests assert management ports inaccessible from collection/observation zones.

### GW-T017 — Weak or stolen administrator credential

- Category: Spoofing/Elevation
- Initial risk: High
- Controls:
  - enterprise identity/MFA-capable management profile;
  - key/certificate-based break-glass access;
  - RBAC;
  - short-lived sessions/tokens;
  - audited privileged actions;
  - no default shared administrative password.

### GW-T018 — Credential leakage in logs/config/diagnostics

- Category: Information disclosure
- Initial risk: Critical
- Controls:
  - secrets stored via approved secret provider;
  - secret values forbidden in command-line args/logs;
  - diagnostic redaction;
  - automated secret scanning;
  - bounded exception serialization.

### GW-T019 — Raw telemetry privacy leak

- Category: Information disclosure/privacy
- Initial risk: Critical
- Controls:
  - raw bytes not retained by default;
  - pre-commit privacy classification/minimization;
  - source payloads absent from ordinary operational logs;
  - separate governed content-store profile if future retention is enabled;
  - access/jurisdiction/retention decisions outside default proof metadata.

### GW-T020 — Hash-based privacy confirmation attack

- Category: Privacy
- Initial risk: High
- Scenario: a digest of a low-entropy secret or known candidate value allows an observer to test guesses.
- Controls:
  - active privacy policy decides whether original-byte digests may be committed;
  - sensitive/low-entropy fields can be removed/tokenized before committed representation is hashed;
  - selective disclosure and access policy limit exposure of digests where applicable.
- Residual: hashes are not encryption; documentation must not describe them as confidentiality controls.

### GW-T021 — Irreversible commitment of prohibited data

- Category: Privacy/Tampering of policy intent
- Initial risk: Critical
- Controls:
  - classify/minimize/redact before canonical commitment;
  - policy/version recorded;
  - negative tests with prohibited fields;
  - adapters cannot bypass policy by directly mutating Merkle state/Core storage.

### GW-T022 — Lossy normalization represented as source-identical

- Category: Tampering/verification-boundary error
- Initial risk: High
- Controls:
  - transformation profile required when normalized;
  - explicit `lossless`/representation semantics;
  - source and derived representation identities distinct when necessary;
  - digest description states exactly what was hashed.

### GW-T023 — Evidence truth/completeness overclaim

- Category: Verification-boundary overclaim
- Initial risk: Critical
- Controls:
  - verification results state checked properties;
  - health state separate from evidence verification;
  - collection volume not mapped to completeness percentage;
  - no UI/API/docs claims that a valid signature proves source truth, completeness, legal admissibility or compliance.

### GW-T024 — Clock rollback/manipulation

- Category: Tampering/Repudiation
- Initial risk: High
- Controls:
  - separate source time and Gateway receipt time;
  - monotonic sequencing independent of wall-clock order;
  - NTPv4 support; NTS preferred where available;
  - record clock quality and rollback/step events;
  - degraded/unknown time is explicit.
- Residual: authenticated NTP/NTS does not prove the time server itself is correct.

### GW-T025 — Signer key extraction

- Category: Spoofing/Elevation
- Initial risk: Critical
- Controls:
  - TPM 2.0 or approved hardware signer in production reference profile;
  - non-exportable key configuration;
  - application only receives sign operation/result;
  - purpose-separated keys;
  - rotation/revocation;
  - physical/platform hardening in G3/G4.

### GW-T026 — Signer unavailable

- Category: DoS
- Initial risk: High
- Controls:
  - explicit readiness state;
  - receipt distinguishes local commit from signed checkpoint;
  - production policy defines bounded pending behavior vs fail-closed;
  - never label unsigned/pending state as signed/verified.

### GW-T027 — False assurance from TPM/attestation

- Category: Verification-boundary overclaim
- Initial risk: High
- Controls:
  - attestation results limited to measured claims and policy;
  - no statement that TPM presence proves entire runtime uncompromised;
  - verification report exposes attestation scope/dependencies.

### GW-T028 — Firmware/update tampering

- Category: Tampering/Elevation
- Initial risk: Critical
- Controls:
  - UEFI Secure Boot capable platform;
  - signed updates and verified metadata;
  - rollback protection/version policy;
  - known-good recovery;
  - update attempt/result audit;
  - platform qualification later.

### GW-T029 — Malicious/compromised software supply chain

- Category: Supply chain/Elevation
- Initial risk: Critical
- Controls:
  - reproducible/signed builds target;
  - dependency audit and secret scan;
  - SBOM/provenance in packaging sprint;
  - protected CI/release controls;
  - verified update artifacts;
  - SSDF-aligned engineering process.

### GW-T030 — Physical theft/storage removal

- Category: Information disclosure/DoS
- Initial risk: High
- Controls:
  - TPM-backed keys;
  - encrypted/protected storage target for appliance qualification;
  - recovery/decommission procedure;
  - no raw-content retention by default;
  - key revocation does not rewrite historical proof semantics.

### GW-T031 — Passive observation interface becomes exfiltration path

- Category: Information disclosure/Elevation
- Initial risk: Critical
- Controls:
  - no L3 address where feasible;
  - no routing/bridge/NAT;
  - no management or sync listener;
  - parser allowlist and rate bounds;
  - network validation tests.

### GW-T032 — SPAN/TAP assumed complete

- Category: Observation failure
- Initial risk: High
- Controls:
  - passive profile explicitly states no completeness guarantee;
  - record source of mirror configuration where available;
  - gaps/drops surfaced when detectable;
  - no event-count completeness score.

### GW-T033 — Connector cursor reset or subscription gap

- Category: Observation failure/Repudiation
- Initial risk: High
- Controls:
  - connector cursor separate from evidence log;
  - subscription renewal/reconciliation state auditable;
  - reset/reauthorization creates explicit gap/reconciliation event;
  - connectors cannot silently convert unknown interval to complete.

### GW-T034 — Excessive connector privilege

- Category: Elevation/Information disclosure
- Initial risk: Critical
- Controls:
  - least-privilege scopes;
  - credential broker/isolation;
  - per-connector documented permission set;
  - credential cannot access signer/admin internals;
  - offboarding revokes credentials.

### GW-T035 — Cross-interface data leakage

- Category: Information disclosure
- Initial risk: High
- Controls:
  - logical zone separation;
  - service binding and firewall policy;
  - no packet forwarding;
  - sync envelopes omit raw source payloads by default;
  - tests capture traffic on non-target interfaces during ingestion/sync.

### GW-T036 — Diagnostics or AI-derived analysis changes canonical evidence

- Category: Tampering
- Initial risk: High
- Controls:
  - derived analysis is a separate evidence/analysis object with provenance;
  - observability/diagnostics cannot mutate canonical source records;
  - AI analysis is not part of G0/G1 canonical commitment path.

### GW-T037 — Configuration rollback/downgrade

- Category: Tampering
- Initial risk: High
- Controls:
  - schema/versioned config;
  - signed/authorized policy changes;
  - downgrade protections for security-critical profile versions;
  - audit previous/new config digest and actor.

### GW-T038 — Evidence destruction mistaken for evidence modification protection

- Category: Verification-boundary error
- Initial risk: High
- Scenario: cryptographic append-only design is incorrectly assumed to prevent an attacker from deleting the whole device/database.
- Controls:
  - docs explicitly distinguish tamper detection from availability/destruction resistance;
  - upstream checkpoints/exports provide external corroboration;
  - backup/retention/resilience are separate controls.

## 6. Abuse cases required for later implementation testing

G1/G3/G4 must include at minimum:

1. unauthenticated webhook with forged tenant/source headers;
2. mTLS sender whose payload claims a different hostname/actor;
3. UDP syslog duplicates, reorder and drops;
4. oversized syslog and webhook payloads;
5. compressed body expanding beyond policy limit;
6. malformed JSON/protobuf/syslog parser corpus;
7. high-cardinality source IDs/idempotency keys attempting storage exhaustion;
8. queue fills during upstream outage;
9. disk reaches warning/critical thresholds mid-ingest;
10. restart with records marked in-flight;
11. conflicting upstream acknowledgement;
12. upstream certificate/identity mismatch;
13. protocol downgrade/version mismatch;
14. wall-clock rollback during capture;
15. NTP/NTS loss and recovery;
16. signer unavailable/locked/rotated;
17. attempted key export;
18. management access from collection network;
19. attempted routing/NAT between interfaces;
20. passive observation interface with accidental IP/default route;
21. secret values in exception/diagnostic paths;
22. policy forbids a field that hostile input tries to force into committed metadata;
23. lossy normalization with source-byte-digest claim mismatch;
24. connector cursor/subscription reset;
25. abrupt power loss during commit/sync/update;
26. signed update rollback attempt;
27. tampered local evidence/proof database;
28. cross-tenant query/export attempt.

## 7. Residual risks accepted at G0

G0 is an architecture gate, not pilot qualification. The following remain unresolved implementation/qualification risks and are explicitly deferred:

- measured throughput/capacity;
- actual hardware TPM/firmware behavior;
- storage endurance and power-loss behavior;
- parser sandbox effectiveness;
- real enterprise connector throttling/gap behavior;
- HA/failover design;
- update/recovery implementation;
- encryption-at-rest implementation and recovery-key operations;
- physical tamper resistance;
- OT environmental/safety certification;
- formal conformance of every transport implementation.

None of these may be represented as completed merely because G0 documents the requirement.

## 8. Security acceptance gate

G0 security review passes only when:

- every trust boundary is represented in architecture/profile docs;
- Critical/High threats have a planned control owner/sprint;
- routed/inline mode is disabled in v0.1;
- no-forwarding is a machine-testable profile invariant;
- raw-data and privacy commitment boundaries are explicit;
- identity/time/attestation claims are bounded;
- UDP/passive observation limitations are explicit;
- production signer/private-key boundary is explicit;
- no Gateway claim implies source truth or complete observation;
- independent reviewer records approval or specific blocking findings.
