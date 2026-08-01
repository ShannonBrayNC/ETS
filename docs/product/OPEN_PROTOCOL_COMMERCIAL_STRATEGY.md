# ETS Open Protocol and Commercial Platform Strategy

Status: Approved strategic direction; implementation tracked by GitHub epic #146 and sprint issues #147–#152.

## 1. Strategic objective

ETS will be offered publicly as an open evidence-transparency protocol and reference implementation. The objective is broad, low-friction global adoption of interoperable evidence proofs while Lantern Protocol builds a sustainable business around production implementations, edge appliances, managed cloud operations, assurance, support, integrations, and professional services.

The protocol is the adoption layer. Commercial ETS products are the operational scale and assurance layer.

## 2. Non-negotiable principles

1. Independent verification must remain possible without a Lantern account, paid license, proprietary cloud dependency, or undisclosed algorithm.
2. Public protocol artifacts include schemas, proof formats, canonicalization rules, conformance vectors, versioning behavior, and security considerations.
3. Commercial controls must not invalidate, conceal, or prevent verification of a valid ETS proof.
4. ETS proves declared cryptographic properties for submitted records. It does not independently prove semantic truth, complete observation, legal admissibility, or regulatory compliance.
5. AI output is derived evidence and cannot modify canonical source records, hashes, Merkle state, or signed checkpoints.
6. Public disclosure of potentially new inventive subject matter requires an IP review before publication.

## 3. Product architecture

### Open and free

- ETS Protocol specification
- public schemas and conformance vectors
- reference runtime for local/single-node use
- verifier CLI and libraries
- public REST API specification
- priority-language SDKs and examples
- Docker quick start and synthetic demo
- basic local operator interface
- public/offline proof-bundle verification
- community documentation and contribution workflow

### Commercial

- ETS Professional
- ETS Business
- ETS Enterprise
- ETS Government/Critical Infrastructure
- ETS Edge Virtual, Compact, and Enterprise appliances
- ETS Cloud fleet and synchronization services
- enterprise SSO, RBAC, policy, tenant isolation, and high availability
- supported and premium connectors
- long-term support and signed release channels
- evidence-retention and archive services
- managed ETS operations
- assurance, conformance, deployment, and evidence-process assessments
- training, certification, OEM, and partner programs

## 4. Monetization doctrine

Lantern Protocol charges for scale, operational responsibility, managed infrastructure, assurance, support, advanced integrations, lifecycle management, and contractual commitments. It does not charge merely for understanding or independently implementing the public proof definition.

Pricing should use predictable units such as managed nodes, supported deployment topology, proof-data retention, connector class, support tier, regional requirements, and service responsibility. Raw event-volume pricing should not create incentives to suppress evidence collection or produce uncontrollable bills.

Initial pricing ranges are hypotheses that require design-partner validation:

- Professional: approximately $49–$149 monthly or $500–$1,500 annually.
- Business: approximately $500–$2,000 monthly.
- Enterprise software and support: approximately $25,000–$150,000+ annually.
- Government and critical infrastructure: scoped contracts beginning near $100,000 and potentially reaching seven figures.
- Four-week paid proof of concept: approximately $10,000–$25,000, potentially credited toward an annual agreement.

These ranges are not approved public pricing until unit economics and willingness-to-pay evidence are retained.

## 5. Service catalog

- Evidence architecture and readiness assessment
- fixed-scope proof of concept
- implementation and migration
- custom adapter engineering
- identity, signing, TPM/HSM, and key-management integration
- edge and fleet deployment
- managed ETS operations
- retention and archive architecture
- investigation and evidence-workflow enablement
- partner and operator training
- premium support and technical account management
- conformance and deployment assurance
- OEM and embedded licensing

## 6. Patent, licensing, and disclosure posture

The open-protocol direction does not itself amend the filed patent application. It changes the publication and licensing program around the invention.

Before public release, material must be classified as:

- already disclosed in the filed application;
- non-inventive interoperability detail;
- confidential operational know-how or trade secret; or
- potentially patentable improvement requiring review before disclosure.

The public repository must not contain patent application identifiers, filing receipts, claim charts, attorney communications, prosecution strategy, confidential prior-art analysis, or unapproved invention disclosures.

Protocol licensing, implementation licensing, documentation licensing, trademark rights, patent rights, and contribution terms are separate decisions and must not be conflated.

## 7. Delivery program

### Sprint A0 — Governance and IP boundary

Define licenses, contribution terms, trademark policy, compatibility marks, publication review, protocol governance, and product taxonomy.

### Sprint A1 — Open protocol and conformance

Publish normative protocol behavior, versioned schemas, golden/negative vectors, implementation profiles, and a vendor-neutral conformance runner.

### Sprint A2 — Community adoption

Deliver the free runtime, verifier, SDKs, public verification, quick start, examples, and documentation needed for independent adoption.

### Sprint A3 — Commercial offers

Define editions, pricing units, entitlements, support levels, service catalog, contracts, pilot terms, and unit-economics requirements.

### Sprint A4 — Edge, cloud, and partners

Productize qualified virtual and physical edge configurations, fleet/cloud operations, partner delivery, warranty, updates, and lifecycle support.

### Sprint A5 — Launch and validate

Release the public protocol and community implementation, run paid design-partner pilots, measure adoption and economics, and make an evidence-based general-availability decision.

## 8. Program dependencies

- ETS Edge productization epic #140 and sprint issues #141–#145
- Open protocol commercialization epic #146 and sprint issues #147–#152
- Public repository governance issue #134
- Production trust-service deployment gate #122
- Current protocol recovery, alpha hardening, CI, security, and release blockers

## 9. Success measures

### Adoption

- successful community installations
- conformance runs completed
- time to first verified proof
- independent implementations or integration commitments
- active contributors and adapter submissions

### Commercial

- qualified design partners
- paid pilots and conversion rate
- annual recurring revenue
- deployment effort and support burden
- appliance and cloud gross margin
- connector demand and partner pipeline

### Trust and quality

- protocol compatibility across versions
- proof verification success and failure diagnostics
- retained security and resilience evidence
- no unsupported truth, completeness, compliance, or admissibility claims
- controlled disclosure of new inventions

## 10. General-availability gate

General availability requires retained evidence that:

- the protocol and verifier are stable and independently usable;
- qualified edge and cloud configurations survive defined outage, recovery, upgrade, and tamper scenarios;
- tenant and operator boundaries are tested;
- support ownership and escalation are operational;
- unit economics are understood;
- pricing and packaging have been validated with customers; and
- no unresolved critical security, protocol, legal, IP, or operational blocker remains.

A public launch or successful demo does not by itself satisfy this gate.
