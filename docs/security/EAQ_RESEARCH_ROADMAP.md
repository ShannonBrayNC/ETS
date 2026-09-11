# ETS Adversarial Qualification Research Roadmap

This roadmap converts the EAQ program into staged work without making the current ETS alpha dependent on unfinished cyber-range capabilities.

## Phase A — Foundation

- [ ] Extract security invariants from existing ETS threat models.
- [ ] Create invariant registry with component ownership and severity.
- [ ] Define authorization / rules-of-engagement template.
- [ ] Define machine-readable EAQ run manifest and result schema.
- [ ] Define PASS, FAIL, INCONCLUSIVE, and BLOCKED semantics.
- [ ] Define evidence-retention and sensitive-artifact handling policy.
- [ ] Establish finding lifecycle and regression requirement.

Exit: one complete paper exercise can be reconstructed from its retained artifacts.

## Phase B — Range

- [ ] Design isolated network topology.
- [ ] Define egress allowlist/deny-by-default policy.
- [ ] Define reset/rebuild procedure.
- [ ] Add independent observer/log collector.
- [ ] Capture source SHA, image/artifact digests, configuration digest, and time source.
- [ ] Define emergency stop and cleanup procedures.
- [ ] Document Azure/local cost boundaries before cloud-based disruptive tests.

Exit: test environment is reproducible and cannot accidentally target unrelated systems under normal operation.

## Phase C — Existing equipment inventory

Photograph and inventory existing Hak5 equipment before purchasing additional attack hardware.

For each device record:

- model/product family;
- hardware revision;
- firmware/version;
- serial/asset identifier kept privately where appropriate;
- network interfaces;
- supported operating modes;
- power requirements;
- accessories;
- intended EAQ role;
- isolation/safety requirements.

No device receives qualification credit until attached to a repeatable test case.

## Phase D — ETS-native adversarial suites

Priority order:

1. Evidence replay and freshness.
2. Evidence/proof substitution.
3. Sequence and tree-head inconsistency.
4. Tenant/workspace isolation.
5. Authentication/token negative cases.
6. Authorization/privilege boundaries.
7. Signing/key-identity boundaries.
8. Connector trust boundaries.
9. API/parser/state-machine robustness.
10. Supply-chain/build/deployment provenance.

Exit: the highest-value ETS invariants have automated negative tests and retained result manifests.

## Phase E — Adversary emulation and physical ingress

- [ ] Map selected scenarios to MITRE ATT&CK behavior rather than vendor-specific attack recipes.
- [ ] Exercise hostile-network assumptions.
- [ ] Exercise untrusted Ethernet and USB attachment assumptions.
- [ ] Validate monitoring/detection coverage as well as prevention.
- [ ] Introduce periodic human-led purple-team exercises.

Exit: EAQ tests chained behaviors and defensive observability, not only isolated malformed requests.

## Phase F — Release gate

- [ ] Define mandatory RC suite by component/risk.
- [ ] Add EAQ summary to release evidence.
- [ ] Require regression evidence for remediated high-impact findings.
- [ ] Define exception/risk-acceptance authority and expiration.
- [ ] Publish only non-sensitive qualification summaries appropriate for external assurance.

Exit: EAQ Level 2.

## Phase G — Mobile / Edge / AI / Ranger

Future work after ETS foundations mature:

- sensor and telemetry authenticity;
- offline/disconnected evidence reconciliation;
- subordinate-device identity;
- malicious/compromised node behavior;
- AI model/version provenance;
- confidence/policy decision evidence;
- spoofed/stale sensor input;
- communications-loss policy;
- cyber-physical fail-safe behavior;
- autonomous decision reconstruction.

This phase deliberately remains future-facing and must not delay the current ETS release path.

## Research references

Use authoritative/current sources during implementation:

- NIST SP 800-218 SSDF and subsequent revisions.
- MITRE ATT&CK adversary-emulation resources.
- OWASP Web Security Testing Guide with versioned scenario identifiers.
- Existing ETS security/threat-model documentation.

Framework references are mappings for engineering coverage and do not imply external certification.
