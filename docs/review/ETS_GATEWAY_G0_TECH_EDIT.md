# ETS Gateway GATE-G0 Technical Edit and Research Validation

Status: GATE-G0 technical-review candidate
Date: 2026-08-13
Scope: `docs/architecture/ETS_GATEWAY_ARCHITECTURE.md`, `docs/spec/ETS_GATEWAY_PROFILE.md`, `docs/security/ETS_GATEWAY_THREAT_MODEL.md`, G0 ADRs, machine profile, and architecture-contract tests

## 1. Review objective

This record separates externally verifiable technical facts from ETS product decisions and from unmeasured engineering targets. It is intended to prevent standards citations, security mechanisms, or planned performance targets from being restated later as claims that the Gateway has already been benchmarked, certified, or proven complete.

The technical edit uses primary standards/publisher sources where a normative or factual statement depends on an external specification. ETS-specific architecture requirements remain ETS decisions even when they are informed by those sources.

## 2. Classification used in this review

Every material G0 statement is treated as one of the following:

- **External fact** — a statement directly supported by a current primary standard or publisher source.
- **ETS design decision** — a product/architecture choice made for the Gateway. It must not be represented as required by a cited standard unless the standard actually requires it.
- **Qualification objective** — an intentionally unmeasured target used to design later tests. It is not a supported performance, availability, security, or capacity claim.
- **Deferred claim** — a property that cannot be established during architecture-only G0 and requires implementation, hardware, operational, or independent validation evidence.

## 3. Standards and source validation

### 3.1 Network trust and identity

**External fact.** NIST SP 800-207 states that zero trust does not grant implicit trust solely because of physical/network location and treats subject/device authentication and authorization as discrete functions before resource access. NIST SP 800-207A further describes the shift from network-parameter-only controls toward application/service identity.

**G0 consequence / ETS decision.** Source IP, VLAN, subnet, interface, or ownership may be retained as evidence context but is not sufficient by itself to establish producer identity or tenant authorization. The Gateway therefore keeps transport identity, payload-declared identity, adapter identity, and server-authorized tenant/workspace scope distinct.

### 3.2 TLS version policy

**External fact.** RFC 9325 (BCP 195) prohibits negotiation of SSLv2, SSLv3, TLS 1.0, and TLS 1.1; requires TLS 1.2 support; recommends TLS 1.3 support; and requires implementations that support TLS 1.3 to prefer it over earlier versions. The BCP explicitly permits deployments with stricter policy when interoperability permits.

**Tech-edit correction.** G0 does **not** state that TLS 1.2 is obsolete or forbidden. The reference profile supports an approved TLS 1.2 compatibility configuration and prefers TLS 1.3. A future controlled environment can tighten the service policy to TLS 1.3-only after interoperability validation.

### 3.3 Syslog transport

**External fact.** RFC 5425 allocates TCP port 6514 as the default for syslog over TLS and states that the TLS transport-sender certificate identity is not necessarily related to the RFC 5424 message `HOSTNAME` field. RFC 5424 recommends TLS transport and permits UDP support.

**Tech-edit correction.** G0 uses the RFC 5425 **transport model and identity distinction**, but it does not claim full RFC 5425 implementation conformance. RFC 5425 was published in 2009 and includes historical TLS cipher requirements; current cryptographic configuration is governed by the current TLS BCP instead. G1 must define and test the exact interoperable syslog-TLS profile before any conformance statement is made.

**ETS decision.** UDP syslog is retained only as a compatibility input with lower transport assurance and explicit loss/reordering/completeness limitations.

### 3.4 OpenTelemetry Protocol

**External fact.** The reviewed OpenTelemetry OTLP specification identifies logs, metrics, and traces as stable signals and defines gRPC and HTTP transports with Protocol Buffers payload schemas. The specification requires resource limits for received messages, including decompressed payloads, and defines partial-success and retry behavior.

**ETS decision.** Gateway v0.1 selects OTLP/gRPC and OTLP/HTTP binary Protocol Buffers as its initial OTLP transport scope. The profiles signal is excluded because it is not stable in the reviewed OTLP specification. G1 must implement protocol-specific acceptance/partial-success semantics without converting partial acceptance into a false complete-collection state.

### 3.5 Platform firmware and Secure Boot

**External fact.** NIST SP 800-193 describes platform-firmware resiliency in terms of protection, detection, and recovery from unauthorized/destructive change. UEFI 2.11 defines Secure Boot/image validation behavior; an enabled Secure Boot state causes firmware verification of applicable boot applications/drivers under UEFI image-validation policy.

**ETS decision.** A UEFI Secure Boot-capable platform is required for the physical reference appliance. Merely purchasing a capable platform is not evidence that Secure Boot is correctly enabled, enrolled, maintained, or resilient. G3/H3 must produce measured configuration and recovery evidence.

### 3.6 TPM

**External fact.** Trusted Computing Group identifies TPM 2.0 Library Specification Version 185 (March 2026) as the latest TPM 2.0 library specification at the G0 review date. TPM provides standardized cryptographic, authorization, and platform-service capabilities; exact semantics depend on how keys/objects and platform policies are provisioned.

**ETS decision.** The physical pilot reference requires TPM 2.0 or an explicitly approved conformance-equivalent hardware signer, and the Gateway application is not permitted to receive exportable production signing private-key bytes. This is an ETS key-custody requirement, not a blanket claim that TPM presence makes the appliance trustworthy.

### 3.7 Network time

**External fact.** RFC 8915 specifies Network Time Security (NTS) for NTP client-server mode using TLS for key establishment and authenticated encryption for NTP exchanges; it provides peer identity and message authentication properties.

**Tech-edit boundary.** Cryptographically authenticating a time server and its packets is not, by itself, evidence that the server's represented UTC value is physically/civilly correct. G0 therefore records source time, Gateway receipt time, clock-quality state, and rollback/degradation separately.

## 4. ETS-specific architecture decisions reviewed

The following are deliberate product decisions, not externally mandated facts:

1. Gateway v0.1 is **out-of-band by default** and is not an availability-authoritative inline router/proxy.
2. `collector` is the normative deployment mode; constrained passive mirror observation is experimental; `routed_inline` is deferred.
3. The normative host does not route, bridge, or NAT between management, collection, observation, and upstream zones.
4. Management, collection, and upstream are distinct logical trust zones; the reference physical appliance prefers four physical NICs, but a VM may implement equivalent logical separation.
5. The passive observation interface exposes no management, synchronization, or ingestion service listener. Approved capture code consumes the interface directly and the interface has no default route.
6. Privacy classification/minimization precedes irreversible ETS commitment.
7. Raw evidence bytes are outside the default Gateway retention boundary.
8. A committed digest identifies the explicitly declared evidence representation; it must not be described as the original source-byte digest when a transformation/minimization stage changed the representation.
9. Gateway consumes protocol primitives through `ets.core.api` and may not redefine canonicalization, hashing, Merkle, proof, signed-tree-head, or verification semantics.
10. Local append history cannot be rewritten to match an upstream service.
11. Acknowledgement/receipt states must distinguish network receipt, policy acceptance, local durable commitment, checkpoint signing, and upstream synchronization.
12. Node health is separate from evidence verification state; neither implies semantic truth or complete observation.

## 5. Qualification targets that are explicitly not facts

The reference machine profile currently carries the following benchmark-design objectives:

- 1,000 evidence events/second sustained;
- 5,000 evidence events/second for a 600-second bounded burst;
- 10 GiB maximum streamed-object hashing objective;
- seven days of offline synchronization backlog under a declared qualification workload.

These values are **unmeasured, non-SLA qualification objectives**. They must not appear in product collateral, funding material, customer proposals, capacity calculators, or supported-configuration documentation as achieved Gateway performance until a retained benchmark package identifies hardware, software revision, event distribution, payload sizes, capture tier, source mix, crypto profile, storage state, thermal state, and pass/fail criteria.

Similarly, 16 GiB minimum RAM, 32 GiB reference RAM, 1 TiB NVMe, four preferred physical NICs, TPM 2.0, and UEFI Secure Boot are reference-platform requirements/selection constraints. Except where a standard defines a mechanism, these are not evidence that a specific appliance implementation has been qualified.

## 6. Claims removed or bounded during technical edit

The G0 set deliberately avoids or bounds the following claims:

- **No TLS 1.3-only requirement.** TLS 1.2 remains a compatibility requirement under current BCP 195.
- **No full RFC 5425 conformance claim.** G0 uses its transport/port/identity model while current crypto policy follows BCP 195.
- **No SPAN/TAP completeness claim.** A mirror source can omit or drop traffic and does not establish complete observation.
- **No TPM-equals-trusted claim.** Hardware key protection and attestation are bounded properties, not universal system trust.
- **No Secure-Boot-capable-equals-enabled claim.** G3 must verify actual state/configuration.
- **No NTS-equals-correct-UTC claim.** Authentication and time correctness are separate assertions.
- **No hash-equals-confidentiality claim.** Hashing is not encryption and can reveal equality/permit guessing of low-entropy values.
- **No OTLP HTTP-200-equals-complete-acceptance claim.** OTLP can report partial success; accepted/rejected counts and diagnostics must be preserved.
- **No event-volume-equals-completeness claim.** Collection health is not proof all source events existed or were observed.
- **No benchmark claim.** G0 performance/capacity figures are unmeasured objectives only.

## 7. Deferred evidence required before later readiness claims

G0 cannot establish and therefore does not claim:

- actual TPM key non-exportability on selected production hardware;
- actual Secure Boot configuration, key enrollment, revocation, or rollback behavior;
- actual NIC isolation under hypervisor/driver/hardware failure;
- measured throughput, latency, CPU, storage amplification, endurance, thermals, or power behavior;
- packet/record loss characteristics under overload;
- connector completeness for M365/Azure/AWS/Kubernetes/GitHub/ServiceNow;
- HA behavior;
- signed update and recovery behavior;
- firmware supply-chain properties;
- regulated-industry certification/compliance;
- OT/industrial safety/environmental qualification;
- general availability or SLA suitability.

These are G1-G4/H0-H4 implementation and qualification obligations.

## 8. Technical-edit conclusion

The G0 architecture is technically coherent for implementation if the machine-profile tests remain green and the architecture/security package receives independent review. The current evidence supports an **architecture-ready** designation only. It does not support a production-ready, certified, benchmarked, compliant, or generally available Gateway claim.

## 9. Primary sources reviewed

- NIST SP 800-207, Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/final
- NIST SP 800-207A, Zero Trust Architecture Model for Cloud-Native Applications: https://csrc.nist.gov/pubs/sp/800/207/a/final
- RFC 9325 / BCP 195, Recommendations for Secure Use of TLS and DTLS: https://www.rfc-editor.org/rfc/rfc9325.html
- RFC 5424, The Syslog Protocol: https://www.rfc-editor.org/rfc/rfc5424.html
- RFC 5425, TLS Transport Mapping for Syslog: https://www.rfc-editor.org/rfc/rfc5425.html
- OpenTelemetry OTLP Specification 1.11.0 (reviewed current publication): https://opentelemetry.io/docs/specs/otlp/
- RFC 5905, NTPv4: https://www.rfc-editor.org/rfc/rfc5905.html
- RFC 8915, Network Time Security for NTP: https://www.rfc-editor.org/rfc/rfc8915.html
- Trusted Computing Group TPM 2.0 Library Specification, Version 185 (March 2026): https://trustedcomputinggroup.org/resource/tpm-library-specification/
- UEFI Specification 2.11: https://uefi.org/specs/UEFI/2.11/
- NIST SP 800-193, Platform Firmware Resiliency Guidelines: https://csrc.nist.gov/pubs/sp/800/193/final
- NIST SP 800-218 v1.1, Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
- NIST SP 800-82 Rev. 3, Guide to Operational Technology Security: https://csrc.nist.gov/pubs/sp/800/82/r3/final

Source-status note: this review deliberately cites NIST SP 800-218 v1.1 as the final SSDF baseline rather than treating later draft revision work as final. OT/industrial Gateway deployment remains separately qualified because NIST SP 800-82 Rev. 3 emphasizes OT-specific performance, reliability, and safety constraints.
