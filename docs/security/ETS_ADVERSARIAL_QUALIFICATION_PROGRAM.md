# ETS Adversarial Qualification (EAQ) Program

Status: Research baseline / future release-gate design  
Owner: EchoMedia AI / ETS  
Scope: Systems owned or explicitly authorized for testing only

## 1. Purpose

ETS Adversarial Qualification (EAQ) makes adversarial security testing a first-class engineering discipline rather than a final penetration-test event. EAQ asks whether the security and evidence invariants claimed by a specific ETS build survive deliberate, authorized attempts to violate them.

EAQ is designed to complement, not replace, conventional CI, code review, dependency scanning, threat modeling, penetration testing, and independent assessment.

The central research proposition is:

> A security qualification result should itself be reproducible evidence.

An EAQ run therefore records the test authorization and scope, system-under-test identity, source revision, configuration, hypothesis, technique, observations, outcome, remediation linkage, and regression result as evidence artifacts suitable for later ETS ingestion and verification.

## 2. Governing principles

1. **Authorization first.** Testing is restricted to EchoMedia/ETS systems, isolated lab assets, or systems for which explicit authorization exists.
2. **Isolation by default.** Potentially disruptive tests execute in a dedicated range separated from production and unrelated third-party networks.
3. **Invariant-driven testing.** Every test names the security/evidence property it attempts to violate.
4. **Evidence over assertion.** Passing a test means retaining sufficient evidence to reproduce and independently evaluate the result.
5. **Assume component compromise.** Qualification includes malicious-node and stolen-credential scenarios, not merely malformed input.
6. **No silent exceptions.** Accepted risks and deferred findings are explicit, bounded, attributable, and reviewable.
7. **Regression is mandatory.** A remediated vulnerability becomes a permanent negative/regression test where practicable.
8. **Independent observation.** The attacker and system under test should not be the sole authorities for the qualification record.

## 3. Standards and research alignment

EAQ should maintain mappings to established defensive frameworks rather than inventing a private vocabulary:

- NIST SP 800-218 Secure Software Development Framework (SSDF), including preparation, software protection, well-secured software production, and vulnerability response.
- MITRE ATT&CK for adversary behavior vocabulary and adversary-emulation planning.
- OWASP Web Security Testing Guide (WSTG) for application/API security test design.
- Existing ETS component threat models under `docs/security/`.

Framework mappings describe coverage; they do not imply certification by NIST, MITRE, OWASP, or another organization.

## 4. EAQ architecture

```text
                ETS ADVERSARIAL QUALIFICATION RANGE

  +----------------------+       +-------------------------+
  | Attack / Emulation   |       | Independent Observer    |
  |                      |       |                         |
  | approved tools       |       | packet/log collection   |
  | scripted harnesses   |       | time/config capture     |
  | physical test gear   |       | evidence manifests      |
  +----------+-----------+       +------------+------------+
             |                                |
             v                                v
       +------------------------------------------------+
       |            Controlled Test Boundary             |
       |                                                 |
       | Edge | Gateway | Verifier | Connectors | APIs   |
       | Identity | Storage | Signing | Mobile | AI      |
       +------------------------+------------------------+
                                |
                                v
                    +-----------------------+
                    | EAQ Evidence Package  |
                    | + verification result |
                    +-----------------------+
```

The range should have a positive egress policy, resettable infrastructure, known test identities/keys, synchronized time sources, reproducible configuration, and a documented emergency-stop procedure for disruptive tests.

## 5. Qualification domains

### EAQ-IDENTITY — identity and authorization

Attempt to violate authentication, authorization, tenant/workspace isolation, token validation, role boundaries, key custody, service identity, and administrative separation.

Representative invariants:

- unauthenticated actors cannot acquire authenticated standing;
- tenant A cannot enumerate or retrieve tenant B evidence;
- a lower-privileged identity cannot perform privileged evidence operations;
- expired, malformed, incorrectly scoped, or incorrectly signed credentials fail closed.

### EAQ-EVIDENCE — evidence integrity and standing

This is the ETS-specific core. Attempt:

- evidence substitution;
- insertion and unauthorized append;
- deletion/concealment;
- replay;
- sequence reordering;
- timestamp manipulation;
- signer impersonation;
- policy downgrade;
- proof substitution;
- forged provenance;
- contradictory evidence injection;
- stale tree-head presentation;
- cross-tenant proof confusion.

The expected result is not always prevention. Some attacks may be possible against compromised storage or components; the required property may instead be reliable detection, loss-of-standing, or independently verifiable inconsistency.

### EAQ-API — application and protocol surfaces

Exercise input validation, object authorization, authentication, parser behavior, state transitions, concurrency, resource exhaustion boundaries, error disclosure, API schema assumptions, and protocol downgrade behavior. OWASP WSTG scenarios should be referenced by versioned identifier when incorporated into a formal test.

### EAQ-SUPPLY — software and build provenance

Exercise dependency, artifact, build, image, configuration, secret, and deployment assumptions. Qualification should verify that an untrusted artifact cannot silently become a trusted ETS release and that deployed artifacts can be related to the expected source/build evidence.

### EAQ-NET — network and physical-access assumptions

Evaluate hostile-network and untrusted-device conditions in the isolated range, including rogue network infrastructure, unexpected Ethernet/USB devices, segmentation assumptions, management-plane exposure, and recovery after communications disruption.

### EAQ-CONNECTOR — external-system trust boundaries

Treat connectors as potentially malicious or compromised. Test whether M365 and future adapters can manufacture provenance, exceed delegated authority, cross tenant/workspace boundaries, or cause externally sourced content to be mistaken for ETS-authenticated fact.

### EAQ-AI — AI Witness and model-mediated decisions

Exercise prompt/input manipulation, untrusted retrieved content, model/version substitution, confidence/policy boundary handling, provenance loss, contradictory observations, and attempts to cause model output to acquire evidence standing it did not earn.

### EAQ-PHYSICAL — future Edge/Mobile/Ranger systems

Reserved for cyber-physical qualification: sensor spoofing, stale telemetry, GNSS inconsistency, subordinate-device impersonation, communications loss, policy violation attempts, fail-safe transitions, and evidence reconstruction of autonomous decisions. Safety-critical tests require an additional physical safety plan and controlled environment.

## 6. Existing Hak5 equipment as lab instrumentation

Existing personally owned Hak5 equipment may be useful as controlled attack-injection instrumentation. Exact models/firmware must be inventoried before qualification credit is assigned.

Candidate roles include:

| Device family | EAQ research role |
| --- | --- |
| WiFi Pineapple | hostile/rogue wireless environment and wireless trust-boundary exercises |
| LAN Turtle | untrusted Ethernet device / physical network-access assumptions |
| Packet Squirrel | controlled network-path observation/manipulation experiments |
| Bash Bunny | unexpected USB/device-trust and endpoint-control assumptions |
| USB Rubber Ducky | authorized operator-workstation/device-control qualification |
| Shark Jack | exposed-port and unknown-network-device assumptions |

These devices are not themselves proof of security coverage. Each use must map to an approved EAQ test case, invariant, scope, expected result, and retained evidence.

## 7. EAQ test-case contract

Every formal test receives a stable identifier such as `EAQ-EVIDENCE-0001` and includes:

```yaml
id: EAQ-EVIDENCE-0001
title: Reject replayed evidence as a fresh append
authorization:
  owner: EchoMedia AI
  environment: isolated-eaq-range
scope:
  included: []
  excluded: []
sut:
  commit: <sha>
  artifact_digest: <digest>
  configuration_digest: <digest>
invariant: <property being challenged>
framework_mapping:
  nist_ssdf: []
  mitre_attack: []
  owasp_wstg: []
preconditions: []
procedure_summary: <controlled test description>
expected_result: <pass condition>
evidence_required: []
safety_controls: []
cleanup: []
```

Operational commands, credentials, exploit material, and sensitive artifacts should be retained only in appropriately restricted locations rather than public documentation.

## 8. Evidence package

A completed run should emit a machine-readable manifest plus human-readable report. Candidate fields:

- EAQ test/run identifiers;
- authorization/scope digest;
- start/end timestamps;
- operator/test-agent identity;
- system-under-test commit and artifact digests;
- configuration and policy digests;
- tool identities and versions;
- invariant and expected result;
- observations and telemetry hashes;
- result: PASS / FAIL / INCONCLUSIVE / BLOCKED;
- finding identifier and severity when applicable;
- remediation issue/PR/commit references;
- regression-run reference;
- ETS Evidence Object identifiers after ingestion.

Large packet captures, video, memory images, or sensitive logs remain outside the core ETS storage boundary; ETS should bind them through hashes and custody metadata rather than requiring raw evidence storage.

## 9. Finding lifecycle

```text
Hypothesis
   -> authorized EAQ run
   -> observation
   -> finding
   -> triage
   -> issue
   -> remediation PR
   -> normal CI/qualification
   -> EAQ regression
   -> retained verification evidence
```

A finding is not considered remediated merely because code changed. Closure requires a successful regression attempt against the relevant invariant, unless the risk is explicitly accepted with rationale and expiration/review criteria.

## 10. Release-gate maturity

EAQ should be introduced incrementally so it does not destabilize the current alpha qualification program.

### Level 0 — Research

- document methodology;
- inventory attack surfaces and existing equipment;
- define authorization template;
- define evidence schema;
- no release blocking.

### Level 1 — Repeatable lab

- isolated range exists;
- initial identity/API/evidence suites are automated;
- reports and artifacts are reproducible;
- failures create tracked findings.

### Level 2 — Release candidate qualification

- defined high-risk EAQ suite required for RCs;
- unresolved critical/high findings require explicit release decision;
- remediation regression evidence retained.

### Level 3 — Continuous adversarial qualification

- safe subsets execute continuously or on security-relevant changes;
- threat-model changes trigger test-plan changes;
- coverage mapped to components/invariants/frameworks;
- periodic human-led adversary emulation supplements automation.

### Level 4 — Cyber-physical / multi-system qualification

- Mobile, Edge, AI Witness, Ranger, drones, and other authenticated devices participate in bounded adversarial scenarios;
- ETS records decision provenance and qualification evidence across systems.

## 11. Initial research backlog

1. Inventory current ETS trust boundaries from all existing threat models.
2. Create an EAQ invariant registry.
3. Define the EAQ authorization and rules-of-engagement template.
4. Define the EAQ run/evidence JSON schema.
5. Design an isolated local/Azure range with explicit cost and egress boundaries.
6. Inventory existing Hak5 hardware, model revisions, firmware, accessories, and supported interfaces.
7. Map each device to safe EAQ hypotheses; do not map by gadget name alone.
8. Build initial `EAQ-EVIDENCE` replay/substitution/reordering suite.
9. Build initial `EAQ-IDENTITY` tenant/workspace/authentication suite.
10. Map API tests to versioned OWASP WSTG scenarios.
11. Map adversary-emulation scenarios to MITRE ATT&CK behaviors.
12. Add machine-readable result manifests and ETS ingestion experiment.
13. Establish finding severity, remediation SLA targets, and risk-acceptance process.
14. Evaluate independent third-party assessment once internal EAQ reaches Level 2.
15. Preserve future hooks for Mobile and Ranger without making cyber-physical work an alpha blocker.

## 12. Success criteria

EAQ succeeds when ETS can answer, for a particular release:

- What security properties did we claim?
- Which of those properties did we deliberately challenge?
- Against exactly which build/configuration?
- Under whose authorization and scope?
- What happened?
- What evidence supports that conclusion?
- Which findings resulted?
- How were they remediated?
- Was the original attack attempted again?
- Can an independent verifier reproduce the evidence relationship?

That is the distinction between claiming that ETS was penetration tested and producing evidence that a defined ETS build survived a defined adversarial qualification program.
