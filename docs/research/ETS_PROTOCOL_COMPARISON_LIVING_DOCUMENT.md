# ETS Protocol Comparison Living Document

Status: living research document  
Audience: maintainers, protocol reviewers, architects, security reviewers, standards readers, and public transparency reviewers  
Scope: public-safe technical comparison only  
Last reviewed: 2026-07-28

ETS is the **Evidence Transparency System**. This document compares ETS with adjacent transparency, provenance, timestamping, policy, supply-chain, and audit protocols. The goal is not to claim that ETS replaces those systems. The goal is to show, with a transparent comparison process, where ETS overlaps, where it differs, where it should interoperate, where it is weaker, and where future work should focus.

This is a living document. Additions must preserve the ETS public claim boundary and must not include private patent filings, application numbers, USPTO receipts, claim charts, prior-art matrices, attorney-review notes, assignment strategy, production customer evidence, official election data, raw medical records, raw financial records, credentials, private keys, or secrets.

## 1. ETS baseline used for comparison

The comparison baseline is the public ETS architecture and implementation posture:

- Source systems may include AI agents, GitHub/repositories, SignalForge, Christina, OpsHelm, Lantern-Civic, emergency/sensor feeds, and human evidence.
- ETS core components include API, canonicalization, EvidenceEvent validation, append-only log, Merkle tree, proof generator, verifier, certificate generator, policy gate, audit replay, and explorer UI.
- Outputs include proof bundles, verification certificates, human review, automation approval, quarantine/reject, and archive/restrict release.
- EvidenceEvent lifecycle: receive event, validate schema, canonicalize payload, compute hash, append log, update Merkle root, generate proof, verify proof, generate certificate, and policy route.
- Canonical hashing flow: EvidenceEvent metadata plus content hash, deterministic canonical JSON, SHA-256, event hash, leaf hash, and append entry. Raw evidence bytes may remain outside the ETS storage boundary.
- Proof model: Merkle inclusion proof fields include schema version, tree size, leaf index, leaf hash, root hash, audit path, hash algorithm, and generation time. Verifiers recompute the path and accept only when the recomputed root matches the expected root.
- Tree-head comparison signals include accept progress, rollback suspicion, fork/equivocation, stale state, and reject root mismatch.
- Verification certificates include proof bundle, verifier result, claim boundary, verifier version, and machine-readable or human-readable outputs.
- Policy-gated routing considers evidence state, proof status, source system, tenant/workspace, requested action, sensitivity, rules, thresholds, and claim boundaries.
- ETS maintains a civic/election-adjacent boundary: ETS is not voting software, tabulation software, voter registration software, ballot software, election correctness software, or the vote of record unless separately certified and legally designated.
- Audit replay inputs include event metadata, canonical hash, inclusion proof, tree-head comparison, policy outcome, and certificate claim boundaries.
- Public claims should map to formal artifacts, implementation evidence, tests, workflows, release gates, and explicit non-claim boundaries.

## 2. Non-claim boundary

ETS verifies submitted-event metadata, content hashes, inclusion proofs, tree-head material, verification certificates, and policy-routing records.

ETS does **not** prove, by itself:

- real-world truth;
- legal sufficiency;
- official chain of custody;
- raw evidence authenticity;
- evidence completeness without an expected-event policy and independent observation process;
- election correctness;
- vote totals;
- ballot validity;
- voter eligibility;
- model correctness;
- software safety;
- regulatory compliance;
- production-grade trust-service status.

This boundary is mandatory. If a future guide, certificate, demo, or protocol extension uses stronger wording, the claim must be backed by formal model coverage, implementation evidence, tests, and release-gate approval.

## 3. Methodology

Each compared protocol is scored qualitatively, not mathematically. A score table is intentionally avoided because numeric scores often hide assumptions. Instead, each comparison records:

- purpose and operating domain;
- overlap with ETS;
- strengths;
- weaknesses or limitations relative to ETS goals;
- gaps that ETS can fill;
- gaps that ETS should not attempt to fill;
- interoperability opportunities;
- attack surface;
- optimization areas;
- claim-boundary warnings.

### Evidence confidence labels

Use these labels when updating this document:

- **Source-backed:** directly supported by an official specification, standard, or project documentation.
- **Research-backed:** supported by a peer-reviewed or preprint research paper, but not necessarily by the official project.
- **Inference:** ETS maintainer analysis based on comparing architectures. Inferences must be labeled.
- **Open question:** requires implementation testing, legal review, formal verification, or standards review.

## 4. Executive comparison matrix

| System / protocol | Primary domain | Closest overlap with ETS | ETS differentiation | Best interoperability path |
| --- | --- | --- | --- | --- |
| Certificate Transparency (CT, RFC 9162) | TLS certificate ecosystem | Append-only Merkle log, inclusion/consistency proofs, signed tree heads | ETS is not certificate-specific; ETS adds EvidenceEvent metadata, verification certificates, policy-gated routing, audit replay, and domain claim boundaries | Borrow tree-head monitoring, consistency verification, witness patterns |
| Trillian / Tessera-style general transparency logs | General-purpose verifiable logs | Merkle log infrastructure, multi-tree operation, inclusion/consistency proofs | ETS acts as a personality/protocol layer around evidence semantics, certificates, policy gates, and workflow routing | Use as storage/verifiable-log backend for ETS logs |
| Sigstore / Rekor | Software supply-chain signature transparency | Signed artifact metadata, immutable log, inclusion proof, public audit | ETS is broader than software artifacts and does not require identity-bound artifact signing for every event | Integrate Rekor for software evidence events and cross-link ETS proof bundles |
| SCITT / RFC 9943 | Transparent digital supply chains | Signed statements, receipts, registration policy, transparency service | ETS extends beyond supply-chain statements into cross-application evidence routing, certificate non-claims, human review, and domain-sensitive workflows | Map ETS EvidenceEvent to SCITT signed statement or transparent statement |
| C2PA / Content Credentials | Media provenance and authenticity | Signed claims, assertions, manifests, content binding, provenance chain | ETS is event/workflow/evidence centric, not media-asset centric | Store C2PA manifest hashes or validation summaries as ETS events |
| OpenTimestamps | Proof of existence / timestamping | Hash commitment, Merkle aggregation, external anchoring | ETS adds event schema, evidence states, certificate generation, policy routing, and replay | Anchor ETS tree heads or release bundles to OTS |
| W3C PROV / PROV-O | Semantic provenance modeling | Entities, activities, agents, derivations, responsibility | ETS adds cryptographic proof, append-only inclusion, policy routing, and replayable verification | Export EvidenceEvents as PROV bundles or attach PROV JSON-LD as metadata |
| in-toto / SLSA-style supply-chain metadata | Software supply-chain integrity | Signed layout, signed links, steps, artifact materials/products | ETS generalizes to evidence events and can gate workflows beyond software build pipelines | Record in-toto layout/link hashes as ETS evidence, or attach ETS proof to release gate |
| OPA / policy-as-code | Policy decisions | Policy gates, structured input, authorization decisions | ETS feeds policy with evidence states and proof results; OPA itself does not create proof bundles | Use OPA as ETS policy decision engine |
| SIEM / audit log platforms | Operational monitoring | Event collection, correlation, alerting, investigation | ETS provides portable cryptographic evidence packets and certificates; SIEMs provide monitoring/search | Forward ETS verification results into SIEM and ingest SIEM event hashes into ETS |
| Blockchain evidence systems | Tamper-evident ledgers / timestamping | Hash anchoring, immutable record claims, proof of existence | ETS avoids generic blockchain-only claims and emphasizes evidence-event semantics and policy gates | Use blockchains only as optional external anchors |

## 5. Certificate Transparency (RFC 9162)

### Purpose

Certificate Transparency is a public, auditable, append-only log architecture for TLS certificates and precertificates. RFC 9162 defines CT version 2.0 using binary Merkle trees, Signed Certificate Timestamps, signed tree heads, inclusion proofs, and consistency proofs.

### Overlap with ETS

- Append-only log semantics.
- Merkle tree inclusion proof.
- Tree-head comparison.
- Consistency verification.
- External monitoring.
- Tamper-evident audit model.

### Strengths

- Very mature transparency-log pattern.
- Clear public audit model.
- Browser and CA ecosystem experience.
- Efficient proofs over large logs.
- Concrete lessons around log monitoring, signed tree heads, maximum merge delay, and operator accountability.

### Weaknesses relative to ETS goals

- Domain-specific to certificate/precertificate submissions.
- Does not model arbitrary evidence-event metadata.
- Does not generate claim-safe evidence certificates for heterogeneous workflows.
- Does not include policy-gated routing for downstream automation.
- Completeness depends on ecosystem enforcement and monitoring.

### ETS gap filled

ETS can adopt CT-style proof discipline while adding event semantics, certificates, policy gates, and audit replay for non-certificate evidence.

### Attack surface

- Split-view/forked log attacks.
- Delayed merge or withholding behavior.
- Insufficient monitoring.
- Root store governance errors.
- Overreliance on inclusion as proof of correctness.

### Optimization areas for ETS

- Implement CT-style consistency proofs as first-class public verifier checks.
- Add witness/cosigning support for ETS tree heads.
- Add maximum merge delay or maximum proof availability policy for public logs.
- Add monitor workflows that watch for unexpected identities, tenants, or source systems.

### Claim warning

ETS should not claim novelty for binary Merkle trees, signed tree heads, inclusion proofs, or consistency proofs. ETS should claim value in the evidence-event, certificate, policy, and replay layer around those primitives.

## 6. Trillian / Tessera-style general transparency logs

### Purpose

Trillian is a general-purpose, scalable, cryptographically verifiable data-store layer that implements Merkle-tree transparency logs. It is designed to support application-specific personalities above the core tree service.

### Overlap with ETS

- Verifiable log backend.
- Multi-tenant tree support.
- Inclusion and consistency proofs.
- Signed log root patterns.
- Separation between core log infrastructure and application-specific semantics.

### Strengths

- Mature backend architecture for large trees.
- Separates Merkle-tree mechanics from application personality logic.
- Useful mental model for ETS: ETS can be a personality over a transparency log.
- Strong operational lessons for signer, storage, queueing, and proof services.

### Weaknesses relative to ETS goals

- Provides infrastructure, not evidence-domain semantics.
- Requires application logic for admission criteria, canonicalization, external APIs, ACLs, and operational controls.
- Does not define ETS-style certificates, policy gates, civic boundaries, AI-agent accountability, or evidence replay.

### ETS gap filled

ETS can define the personality layer: admission criteria, EvidenceEvent schema, canonicalization, certificates, policy gates, and domain boundaries.

### Attack surface

- Storage-layer compromise.
- Signer compromise.
- queue or sequencing attacks.
- DoS on append/proof APIs.
- misconfigured tenant/tree boundaries.
- proof service returning stale or wrong roots.

### Optimization areas for ETS

- Design a storage abstraction so ETS can run in memory, SQLite, Postgres, or a Trillian/Tessera-style backend.
- Add pluggable tree backends with identical proof-bundle output.
- Add backend conformance tests: same EvidenceEvent produces same event hash and verifiable inclusion proof across backends.
- Add operational health checks for tree size, root freshness, pending queue depth, and signer status.

### Claim warning

If ETS adopts Trillian or Tessera in future, public materials must describe ETS as a protocol/application layer using a verifiable log backend, not as the inventor of the backend pattern.

## 7. Sigstore / Rekor

### Purpose

Sigstore improves software supply-chain security by helping developers sign and verify artifacts. Rekor is Sigstore's transparency log for recording signing metadata and making signing events publicly auditable.

### Overlap with ETS

- Immutable transparency log.
- Signed artifact metadata.
- Inclusion proof.
- Public auditability.
- CLI-based upload and verify workflow.
- Identity monitoring.

### Strengths

- Strong developer usability in the software supply-chain lane.
- Mature tooling around signing, verification, and identity.
- Public audit model for artifact signing events.
- Helpful model for ETS DevSecOps integrations.

### Weaknesses relative to ETS goals

- Optimized for software artifacts and signing events, not arbitrary evidence workflows.
- Does not provide ETS-style evidence-event routing across AI, civic, emergency, legal, HR, insurance, and sensor domains.
- Public log entry size and manifest constraints may not match broad evidence use cases.
- Trust depends on correct identity verification, log monitoring, and artifact signature validation.

### ETS gap filled

ETS can ingest Rekor/Sigstore outputs as evidence events, then add enterprise policy routing, claim-safe certificates, and cross-system audit replay.

### Attack surface

- Key or identity compromise.
- Unexpected signing events not monitored by owner.
- Artifact/signature/certificate mismatch.
- Public log metadata leakage.
- Overclaiming that a signed artifact is safe because it was logged.

### Optimization areas for ETS

- Build a `rekor_entry_hash` EvidenceEvent adapter.
- Store Sigstore verification summary as a typed ETS metadata section.
- Generate certificates that distinguish: artifact signature valid, Rekor inclusion verified, source policy accepted, release approved.
- Add policy gates for unexpected identity, untrusted issuer, missing Rekor proof, or signature mismatch.

### Claim warning

ETS must not imply that logged/signature-verified software is safe. ETS can verify submitted signing evidence and route release actions accordingly.

## 8. SCITT / RFC 9943

### Purpose

SCITT defines an architecture for trustworthy and transparent digital supply chains. It focuses on signed statements, transparency services, receipts, registration policy, and scalable access to transparent statements.

### Overlap with ETS

- Signed statements.
- Transparency service.
- Receipts / verifiable proof material.
- Registration policy.
- Supply-chain evidence.
- Relying-party verification.

### Strengths

- Very close conceptual neighbor for ETS.
- Explicit separation of signed statements and transparent statements.
- Formalizes receipts and verifiable data-structure proofs.
- Clear registration-policy concept.
- Strong interoperability opportunity.

### Weaknesses relative to ETS goals

- Supply-chain framing is narrower than ETS's cross-application evidence mission.
- ETS needs richer policy-routed workflow states such as human review, quarantine, restrict release, and audit replay.
- SCITT does not by itself define ETS certificate language for real-world truth boundaries, civic/election-adjacent boundaries, or AI-agent accountability.

### ETS gap filled

ETS can use SCITT as a standards-aligned transparency substrate or interchange layer while adding EvidenceEvent-specific semantics, claim-safe certificates, policy routing, and domain adapters.

### Attack surface

- Weak registration policy.
- Ambiguous statement semantics.
- Receipt verification gaps.
- Relying parties accepting receipts without validating the statement meaning.
- Transparency service compromise.
- Missing monitor/witness strategy.

### Optimization areas for ETS

- Define an ETS-to-SCITT mapping:
  - EvidenceEvent -> signed statement payload.
  - ETS proof bundle -> transparent statement/receipt reference.
  - ETS certificate -> relying-party readable verification result.
  - ETS policy route -> downstream decision record.
- Add conformance examples that show ETS events exported as SCITT-compatible signed statements.
- Add receipt verification tests once a SCITT-compatible backend is used.

### Claim warning

SCITT is the closest standards-adjacent protocol. ETS public differentiation must stay concrete: cross-domain EvidenceEvent contracts, verification certificates with claim boundaries, and policy-gated automation routing.

## 9. C2PA / Content Credentials

### Purpose

C2PA defines manifests and Content Credentials for digital media provenance. A C2PA manifest contains assertions, claims, signatures, content bindings, and provenance information for assets and ingredients.

### Overlap with ETS

- Cryptographically verifiable provenance.
- Claims and signatures.
- Manifest-like metadata.
- Content binding.
- Provenance chains.
- Public user-facing trust explanation.

### Strengths

- Strong media-provenance focus.
- Useful vocabulary for assertions, claims, signatures, content binding, and manifests.
- Good fit for images, documents, video, and AI-generated or edited media evidence.
- Mature public conversation around content authenticity.

### Weaknesses relative to ETS goals

- Asset/media centric rather than workflow/evidence-event centric.
- Does not naturally model cross-application policy routing or audit replay.
- User trust may be difficult when manifests are stripped, redacted, or misunderstood.
- High-stakes use requires careful validation and explicit limits.

### ETS gap filled

ETS can ingest C2PA manifests or validation summaries as evidence events, then issue ETS certificates that explain exactly what was verified and what was not.

### Attack surface

- Manifest stripping.
- Misleading signer identity.
- Untrusted claim generator.
- Redaction ambiguity.
- Content binding confusion.
- Overclaiming authenticity where only provenance assertions were validated.

### Optimization areas for ETS

- Add C2PA adapter:
  - hash original asset;
  - hash manifest store;
  - record active manifest identity;
  - record validation result;
  - record redaction state;
  - generate ETS certificate with media-specific non-claims.
- Add public verifier labels: `media provenance checked`, `manifest absent`, `content binding failed`, `claim signature valid`, `claim signature invalid`, `redaction declared`.

### Claim warning

ETS should not claim that C2PA-provenanced media is true. It should claim that C2PA validation material was submitted, hashed, included, and routed under a certificate boundary.

## 10. OpenTimestamps and blockchain timestamping

### Purpose

OpenTimestamps provides a standard format for blockchain timestamping, with Bitcoin support and client/server libraries for stamping and verifying timestamp proofs. Hashes can be aggregated through Merkle trees and anchored externally.

### Overlap with ETS

- Hash commitment.
- Proof of existence.
- Merkle aggregation.
- External anchoring.
- Independent verification.

### Strengths

- Simple proof-of-existence model.
- Does not require storing raw evidence publicly.
- External anchoring can reduce trust in ETS operator timestamps.
- Useful for public release bundles, tree-head anchors, and legal/disclosure timing evidence.

### Weaknesses relative to ETS goals

- Timestamping alone does not define evidence semantics.
- Does not provide policy-gated routing.
- Does not verify source-system meaning or completeness.
- Blockchain time may be coarse or require careful interpretation.
- External anchoring can add cost, latency, and operational dependency.

### ETS gap filled

ETS can generate meaningful evidence records and then optionally anchor selected tree heads or release bundles externally.

### Attack surface

- Calendar server availability.
- Anchor confirmation delay.
- Misinterpreting timestamp as proof of truth.
- Weak hash or canonicalization upstream.
- Private evidence leaks if raw artifacts are accidentally submitted instead of hashes.

### Optimization areas for ETS

- Add optional `external_anchor` export for ETS tree heads.
- Anchor only roots, not raw evidence.
- Attach anchor proof references to ETS certificates.
- Add `anchor_not_required_for_verification` note so local proof validation remains clear.

### Claim warning

Timestamping proves a commitment existed no later than an interpreted time. It does not prove source authenticity, meaning, completeness, legal admissibility, or correctness.

## 11. W3C PROV / PROV-O

### Purpose

W3C PROV defines a conceptual data model and ontology for provenance, including entities, activities, agents, derivations, responsibility, bundles, and collections.

### Overlap with ETS

- Provenance metadata.
- Entity/activity/agent relationships.
- Responsibility mapping.
- Provenance bundles.
- Cross-domain interoperability.

### Strengths

- Strong semantic model.
- Mature vocabulary for provenance relationships.
- Good interoperability layer for auditors, data lineage tools, and knowledge graphs.
- Useful for AI-agent traceability and cross-application evidence graphs.

### Weaknesses relative to ETS goals

- PROV is semantic, not inherently cryptographic.
- Does not require append-only logs or inclusion proofs.
- Does not provide verification certificates or policy-gated routing.
- Completeness and truth remain external concerns.

### ETS gap filled

ETS can wrap PROV records with hashes, inclusion proofs, certificates, policy outcomes, and audit replay.

### Attack surface

- False provenance relationships.
- Omitted activities or agents.
- Ambiguous identifiers.
- Semantic drift between domains.
- Overclaiming that modeled provenance is verified provenance.

### Optimization areas for ETS

- Add `prov_bundle_hash` metadata field.
- Export EvidenceEvent metadata as PROV JSON-LD.
- Map ETS actor/source/workflow fields to PROV agents, activities, and entities.
- Use PROV bundles inside ETS certificates for explanation, not as replacement for cryptographic proof.

### Claim warning

A provenance graph can be internally coherent and still false or incomplete. ETS should only claim verification of submitted provenance material and proof bundles.

## 12. in-toto / SLSA-style supply-chain metadata

### Purpose

in-toto protects software supply-chain integrity through signed layouts and link metadata for steps performed by authorized functionaries. SLSA-style practices add provenance and build-integrity levels around build systems and artifacts.

### Overlap with ETS

- Step-level evidence.
- Signed metadata.
- Artifact hashes.
- Materials/products model.
- Verification against expected layout.
- Release-gate decision support.

### Strengths

- Very strong model for software supply-chain step verification.
- Separates expected layout from step evidence.
- Good fit for GitHub, CI/CD, SBOM, release, deployment, and rollback events.

### Weaknesses relative to ETS goals

- Software supply-chain focus.
- Does not directly model civic, legal, HR, emergency, insurance, or general evidence workflows.
- Policy routing and claim-safe public certificates are not central output artifacts.

### ETS gap filled

ETS can record in-toto evidence as one class of EvidenceEvent while giving the organization a broader evidence transparency and policy-routing layer.

### Attack surface

- Trusted key compromise.
- Functionary identity compromise.
- Incomplete layouts.
- Unsigned or missing link metadata.
- Build environment compromise.
- Overclaiming secure output based on partial supply-chain verification.

### Optimization areas for ETS

- Add `in_toto_layout_hash` and `in_toto_link_hash` fields.
- Create DevSecOps adapters for materials/products summaries.
- Gate releases on ETS proof + in-toto verification + policy review.
- Attach ETS certificate to release artifacts.

### Claim warning

ETS should not replace in-toto for deep software supply-chain verification. ETS should integrate with it and provide cross-domain evidence routing.

## 13. OPA / policy-as-code

### Purpose

Open Policy Agent is a general-purpose policy engine that lets systems offload policy decisions using structured input and Rego policies.

### Overlap with ETS

- Policy gate.
- Structured decision input.
- Domain-agnostic policy rules.
- Enforcement integration points.

### Strengths

- Mature policy engine.
- Good separation of policy decision and application code.
- Strong fit for Kubernetes, APIs, CI/CD, microservices, and authorization decisions.
- Useful ETS policy backend candidate.

### Weaknesses relative to ETS goals

- OPA does not create evidence events, hashes, proof bundles, or certificates.
- Policy inputs are only as trustworthy as the caller supplies them.
- Does not inherently solve provenance, evidence completeness, replay, or proof verification.

### ETS gap filled

ETS can produce verified evidence-state inputs for OPA, and OPA can return policy decisions that ETS records as policy-routing events.

### Attack surface

- Bad input data.
- Policy bypass.
- Policy version drift.
- Decision/result mismatch.
- Overly broad allow rules.
- Missing audit record for the policy decision.

### Optimization areas for ETS

- Treat OPA as a pluggable policy backend.
- Include `policy_engine`, `policy_version`, `policy_input_hash`, `decision_id`, and `decision_hash` in ETS routing events.
- Record deny/allow/human-review outcomes as ETS evidence.
- Add regression tests for policy drift.

### Claim warning

ETS policy routing does not prove that a policy is correct. It records the evidence state, policy inputs, policy version, and route decision for review.

## 14. SIEM and operational audit platforms

### Purpose

SIEM and audit platforms aggregate, search, correlate, alert, and investigate logs and telemetry.

### Overlap with ETS

- Event collection.
- Investigation timelines.
- Audit trails.
- Alerting and routing.
- Operational evidence.

### Strengths

- Mature operational visibility.
- Strong search, correlation, detection, and alerting.
- Integrates with many enterprise systems.
- Good destination for ETS events and good source of hashable evidence.

### Weaknesses relative to ETS goals

- Logs may be mutable, vendor-bound, retention-limited, or environment-specific.
- SIEM exports are not automatically cryptographic proof bundles.
- Certificate claim boundaries are not standard SIEM outputs.
- Policy-gated automation may happen separately from evidence verification.

### ETS gap filled

ETS can create portable proof bundles and certificates for selected evidence events, then publish verification results into SIEM.

### Attack surface

- Log tampering before ingestion.
- Missing logs.
- Time skew.
- Alert fatigue.
- Correlation errors.
- Credential compromise.
- Public export of sensitive telemetry.

### Optimization areas for ETS

- Add SIEM adapter that hashes evidence exports and records query metadata without storing raw logs.
- Add certificates for incident timelines.
- Add expected-event policies for required telemetry sources.
- Add SIEM correlation ID mapping into EvidenceEvent metadata.

### Claim warning

ETS cannot prove that all relevant logs existed or were ingested unless paired with an expected-event and independent observation policy.

## 15. Blockchain chain-of-custody systems

### Purpose

Blockchain evidence systems typically hash documents or evidence packets and anchor them in a blockchain or hash-linked ledger to claim tamper evidence, proof of existence, or chain-of-custody continuity.

### Overlap with ETS

- Hashing.
- Immutable or append-only record claims.
- Timestamping or anchoring.
- Verifiable proof references.
- Evidence narrative.

### Strengths

- Strong public immutability story when implemented correctly.
- Decentralized anchoring can reduce trust in a single operator.
- Useful for proof-of-existence and release records.

### Weaknesses relative to ETS goals

- Many systems overclaim legal or real-world proof.
- Blockchain inclusion does not equal evidence authenticity.
- Chain-of-custody requires physical/process controls beyond hashing.
- Public ledgers can leak metadata.
- Latency and cost may be poor for high-volume events.

### ETS gap filled

ETS can use blockchain anchoring only as one optional evidence layer while preserving its own event schema, proof bundles, certificates, policy gates, and claim boundaries.

### Attack surface

- Private key compromise.
- Metadata leakage.
- Chain reorgs or timestamp ambiguity.
- Bad custody metadata.
- Raw evidence accidentally stored on-chain.
- Vendor lock-in.

### Optimization areas for ETS

- Anchor periodic ETS tree heads, not every event.
- Use multiple anchor providers or witness logs for resilience.
- Keep raw evidence and regulated data off-chain.
- Record anchor verification status in ETS certificates.

### Claim warning

Blockchain anchoring may strengthen proof-of-existence, but it does not prove evidence correctness, legal chain of custody, or completeness.

## 16. Attack surface across all protocols

The same sharp rocks appear in nearly every transparency system. ETS should track them as a living attack-surface inventory.

| Attack / failure mode | Description | ETS control | Remaining gap |
| --- | --- | --- | --- |
| False source metadata | A system submits incorrect metadata | Source identity, event schema, policy review | ETS cannot prove real-world truth |
| Omitted events | Relevant events are never submitted | Expected-event policy, monitor, gap reports | Requires external observation process |
| Tampered event | Event payload or metadata is altered after hashing | Canonical hash recomputation | Raw evidence authenticity remains external |
| Tampered proof | Inclusion proof path or root is altered | Verifier recomputes path | Verifier trust and root source must be controlled |
| Stale tree head | Verifier sees old root | freshness checks, tree-head comparison | Needs clock and monitor policy |
| Forked view | Different users see different roots | witness/cosigning, monitor gossip | Future work |
| Operator compromise | Log operator tampers, delays, or censors | signed tree heads, monitors, external anchors | Requires independent monitors/witnesses |
| Policy bypass | Downstream action ignores ETS result | gateway enforcement, route event recording | Needs integration discipline |
| Certificate overclaim | UI says proof means truth | claim-boundary regression tests | Human review remains necessary |
| Sensitive data leakage | raw data, secrets, PII, PHI, election data exposed | hash-only mode, redaction profiles, public-safe docs | Must be enforced in code and review |
| Tenant bleed | cross-tenant evidence exposure | tenant/workspace scoping, auth tests | Needs production hardening |
| Dependency compromise | signing, proof, API, or frontend dependency abused | SBOM, pinning, review, release gates | Continuous monitoring required |

## 17. ETS optimization backlog

### 17.1 Protocol optimization

- Canonicalization test vectors across Python, TypeScript, and Go.
- Stable EvidenceEvent v1 JSON schema with versioned extension fields.
- Pluggable hash algorithms with strict default policy.
- Versioned proof-bundle schema.
- Deterministic certificate rendering from the same proof bundle.
- Proof-bundle compression for public manifests.

### 17.2 Transparency optimization

- Consistency proof API.
- Tree-head freshness policy.
- Independent monitor process.
- Witness/cosigning design.
- External anchor exporter.
- Public transparency map for log IDs, tree sizes, root hashes, timestamps, and policy status.

### 17.3 Security optimization

- Signed tree-head enforcement in non-local mode.
- Key rotation playbook.
- JWKS-based auth for service-to-service mode.
- Per-tenant rate limits.
- Policy-bypass tests.
- public manifest redaction scanner.

### 17.4 Product optimization

- Public verifier UX states with plain-language limits.
- Certificate badges that separate proof state from truth claims.
- Drill-down from certificate -> proof bundle -> tree head -> replay report.
- Exportable audit replay report.
- Guide-driven demos for AI, DevSecOps, elections, and emergency/sensor workflows.

### 17.5 Interoperability optimization

- SCITT export/import adapter.
- Rekor evidence adapter.
- C2PA manifest validation adapter.
- W3C PROV export adapter.
- OPA policy-engine adapter.
- OpenTimestamps tree-head anchor adapter.
- SIEM event summary adapter.

## 18. Gap analysis summary

### Gaps ETS can credibly fill

- Cross-domain evidence-event contract.
- Certificate language that avoids overclaiming.
- Policy-gated routing based on proof state and sensitivity.
- Audit replay across proof, certificate, and route decision.
- Domain adapters that wrap existing protocols without replacing them.
- Public-safe workflows for civic/election-adjacent transparency.
- AI-agent accountability records that combine prompts, context, tools, output hashes, reviewer decisions, and policy routes.

### Gaps ETS should not claim to fill alone

- Real-world truth.
- Legal admissibility.
- Official chain of custody.
- Election correctness.
- Software safety.
- Model correctness.
- Full source-system trustworthiness.
- Completeness without expected-event policy and independent observation.
- Decentralized consensus.
- Replacement of SCITT, Rekor, C2PA, PROV, OPA, in-toto, or SIEM platforms.

### Gaps requiring formal work

- Fork/equivocation resistance.
- Witness/cosigning design.
- Formal semantics of EvidenceEvent states.
- Multi-tenant isolation model.
- Certificate claim-boundary verification.
- Expected-event policy completeness model.
- Public manifest safety scanner.

## 19. Living document governance

### Update rules

Every update to this document must include:

1. Date of update.
2. Protocol or system reviewed.
3. Source used.
4. What changed.
5. Confidence label.
6. Whether the change affects ETS claims, implementation, attack surface, or interoperability.

### Required review triggers

Update this document when:

- ETS changes EvidenceEvent schema;
- ETS changes proof-bundle format;
- ETS changes certificate language;
- ETS adds a backend log implementation;
- ETS adds SCITT, Rekor, C2PA, PROV, OPA, OpenTimestamps, SIEM, or in-toto adapters;
- new research identifies attacks against transparency logs, provenance systems, C2PA, supply-chain signing, or policy engines;
- public documentation is about to make a stronger claim;
- ETS enters a regulated vertical demo.

### Change log

| Date | Change | Confidence | Claim impact |
| --- | --- | --- | --- |
| 2026-07-28 | Initial living comparison document added. | Source-backed + inference | Reinforces public non-claim boundary and interoperability posture. |

## 20. References for maintainers

Source URLs are recorded here so maintainers can re-check them during later updates.

- RFC 9162, Certificate Transparency Version 2.0: https://www.rfc-editor.org/info/rfc9162/
- Trillian general transparency documentation: https://google.github.io/trillian/
- Sigstore/Rekor documentation: https://docs.sigstore.dev/logging/overview/
- Sigstore security model: https://docs.sigstore.dev/about/security/
- RFC 9943, SCITT architecture: https://www.rfc-editor.org/info/rfc9943/
- C2PA technical specification: https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
- OpenTimestamps: https://opentimestamps.org/
- W3C PROV publications: https://www.w3.org/groups/wg/prov/publications/
- W3C PROV-DM: https://www.w3.org/2012/10/prov-dm
- in-toto specification: https://github.com/in-toto/docs/blob/master/in-toto-spec.md
- Open Policy Agent documentation: https://www.openpolicyagent.org/docs

## 21. Maintainer checklist

Before merging a future update to this document:

- [ ] No private IP materials are included.
- [ ] No official application numbers or USPTO receipts are included.
- [ ] No production customer data is included.
- [ ] No official election data is included unless already public and explicitly approved for the repo.
- [ ] Claims are separated from inferences.
- [ ] Strengths and weaknesses are both recorded.
- [ ] Attack surface changes are captured.
- [ ] Optimization backlog changes are captured.
- [ ] The non-claim boundary is preserved.
- [ ] README/index links are updated if a new comparison section becomes standalone documentation.
