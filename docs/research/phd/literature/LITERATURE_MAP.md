# ETS Doctoral Literature Map

**Status:** expanded application-grade map; not yet a systematic review  
**Purpose:** organize the major scholarly/standards domains surrounding ETS, record what each domain already establishes, and isolate the narrower research questions that remain defensible.

This map must not be used alone to claim novelty. Candidate novelty remains subject to systematic review, closest-work analysis, peer review and possible revision/refutation.

## Domain summary

| Domain | Canonical/seed work | What it establishes | ETS question constrained |
|---|---|---|---|
| General provenance | W3C PROV | interoperable entity/activity/agent provenance and relationships | RQ2, RQ3 |
| Public append-only auditability | Certificate Transparency, RFC 6962 | Merkle inclusion/consistency, signed tree heads, detectable conflicting views | RQ1, RQ3, RQ4 |
| Software supply-chain integrity | in-toto | signed authorized-step metadata, materials/products, expected layouts | RQ1, RQ2, RQ3 |
| Software artifact provenance | SLSA Provenance | verifiable where/when/how build/source artifacts were produced | RQ1, RQ2, RQ3 |
| Media provenance/authenticity | C2PA Content Credentials | signed manifests/assertions, content binding, provenance history under trust model | RQ1, RQ2, RQ3, RQ5 |
| Digital forensics / evidence management | NIST and scholarly chain-of-custody literature | integrity, custody, validated methods, repeatability, reporting | RQ1, RQ3, RQ7 |
| Tamper-evident audit logs | Schneier/Kelsey and successors | forward integrity, compromise-bounded log protection, tamper detection | RQ3, RQ4, RQ7 |
| Database/data provenance | provenance semirings and lineage research | query/data derivation semantics and lineage reasoning | RQ2, RQ3 |
| Remote attestation / TEEs | attestation literature and standards | measured state, platform identity, trust roots, attested execution claims | RQ3, RQ5, RQ6 |
| Knowledge/provenance graph verification | expansion required | graph semantics, uncertainty/trust/claim propagation | RQ2, RQ3 |
| AI accountability/provenance | responsible-ML logging, LLM audit trails | model/data/runtime lineage, governance and decision logging | RQ5, RQ7 |
| Cyber-physical/robotics assurance | assured autonomy, runtime assurance, CPS dependability | sensing/decision/command assurance under dynamic systems | RQ6, RQ7, RQ8 |
| Assurance cases / dependability arguments | safety/security assurance literature | structured claims, arguments and evidence supporting assurance | RQ3, RQ6, RQ7 |
| Formal verification | ETS TLA+/Alloy plus broader formal-methods literature | safety/liveness/model-bound correctness and refinement | RQ3, RQ4, RQ7 |

## 1. Provenance representation — W3C PROV

### Core sources

- W3C PROV Overview: <https://www.w3.org/TR/prov-overview/>
- W3C PROV Primer: <https://www.w3.org/TR/prov-primer/>
- W3C PROV-N: <https://www.w3.org/TR/prov-n/>

### Established contribution

W3C PROV defines a general interoperable provenance model based on entities, activities and agents, with relations for derivation, attribution, generation/use, bundles and provenance-of-provenance. It also provides constraints, serializations and formal semantics.

### ETS novelty exclusions

ETS must **not** claim novelty merely for:

- representing provenance as a graph;
- typed relationships among entities/activities/agents;
- derivation/history relationships;
- provenance-of-provenance;
- interoperable interchange of provenance descriptions.

### Candidate gap for investigation

Whether a provenance structure can be extended with separately attributable evidentiary claims, explicit verification states, trust dependencies, authority/policy context, contradiction/uncertainty and consequence custody in a way that lets an independent verifier distinguish what is asserted from what is independently checkable.

This remains a hypothesis.

---

## 2. Public append-only transparency and auditability

### Seed source

- Certificate Transparency, RFC 6962: <https://www.rfc-editor.org/rfc/rfc6962.html>

### Established contribution

Transparency-log designs show how Merkle-tree structures, signed tree heads and inclusion/consistency proofs can support append-only public auditability and detection of inconsistent views under stated assumptions.

### ETS novelty exclusions

ETS must not claim novelty for Merkle inclusion proofs, append-only consistency proofs, signed checkpoints or fork detection as primitives.

### Candidate gap for investigation

How transparency primitives should compose with evidence semantics when the object of interest is not merely inclusion in a log but the bounded meaning of a consequential action and its resulting state.

---

## 3. Secure and tamper-evident audit logging

### Core source

Bruce Schneier and John Kelsey, **Secure Audit Logs to Support Computer Forensics**, ACM Transactions on Information and System Security, 1999. Public author page: <https://www.schneier.com/academic/archives/1999/05/secure_audit_logs_to.html>

Related implementation research has strengthened secure logging using tamper-resistant hardware and offline operation.

### Established contribution

Secure-logging research demonstrates that cryptographic mechanisms can make historical log entries difficult to alter or destroy without detection after defined compromise events and can protect confidentiality/integrity under specific attacker assumptions.

### ETS novelty exclusions

ETS must **not** equate tamper evidence with:

- completeness;
- semantic truth;
- correct authorization;
- proof that a commanded action executed;
- proof of resulting state.

### Candidate gap for investigation

Whether tamper-evident records can be composed with independent observation, authority/policy evidence and consequence evidence so that a verifier reports bounded conclusions rather than a monolithic `valid log` result.

---

## 4. Software supply-chain provenance and attestations

### Seed sources

- in-toto specifications: <https://in-toto.io/docs/specs/>
- SLSA Provenance: <https://slsa.dev/spec/v1.2/provenance>

### Established contribution

Modern software-supply-chain systems record artifact identity, build steps, materials/products, attestations and policy-relevant metadata. They provide strong examples of signed provenance and attester/verifier separation around artifact production.

### ETS novelty exclusions

ETS must not claim novelty merely for signed build metadata, statement envelopes, authorized-step layouts or attester/verifier separation.

### Candidate gap for investigation

Whether similar verification discipline can be generalized beyond artifact production to runtime machine actions and resulting states while preserving the distinction between evidence of process and truth about external consequences.

---

## 5. Media provenance and authenticity

### Seed source

- C2PA Content Credentials: <https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html>

### Established contribution

C2PA demonstrates signed manifests/assertions, content binding and provenance histories under a defined trust model for digital media.

### ETS implication

C2PA is strong adjacent work for signed assertions, manifests and provenance lineage. ETS must avoid rebranding those mechanisms as novel.

### Candidate gap for investigation

Whether a similar evidence discipline can operate across machine decisions and physical/digital consequences where source assertions, independent observations and authority evidence may conflict.

---

## 6. Digital forensics and chain of custody

### Seed sources

- NIST Digital Forensics glossary: <https://csrc.nist.gov/glossary/term/digital_forensics>
- NIST Evidence Management: <https://www.nist.gov/forensic-science/interdisciplinary-topics/evidence-management>

### Established contribution

Digital-forensics practice emphasizes acquisition integrity, preservation, documentation, custody, validated methods, repeatability of examination and reporting. Chain-of-custody concepts provide procedural evidence about handling and control.

### ETS implication

Custody is one evidentiary dimension. It does not substitute for provenance, semantic truth, authority, completeness or consequence.

### Candidate gap for investigation

Whether machine-generated evidence can preserve cryptographic and procedural custody metadata in a representation suitable for independent verification while explicitly retaining uncertainty about source truth and capture completeness.

---

## 7. Database/data provenance

### Established contribution

Database provenance and provenance-semiring research provide formal machinery for expressing how query results depend on source tuples and transformations.

### ETS implication

ETS must treat formal lineage semantics as mature prior art rather than claim novelty for dependency graphs or derivation annotations.

### Candidate gap for investigation

Whether those lineage concepts can be reconciled with evidentiary attribution, trust state, conflicting claims, policy/authority context and physical consequence without conflating derivation with truth.

---

## 8. Remote attestation and trusted execution

### Established contribution

Remote attestation and trusted-execution mechanisms can provide evidence about measured software/hardware state under defined roots of trust and verifier policies.

### ETS implication

Attestation establishes bounded measured claims. It does not independently prove source-data truth, capture completeness, correct semantic interpretation or external consequence.

### Candidate gap for investigation

How attestation claims should enter an Evidence Graph without allowing a verified platform measurement to be promoted into stronger claims than the attestation actually supports.

---

## 9. Distributed histories and asynchronous systems

### Established contribution

Distributed-systems research establishes fundamental limits around ordering, liveness, agreement and knowledge under faults, partitions and asynchronous communication. Event-sourcing systems preserve application histories but ordinarily depend on origin application/runtime assumptions.

### ETS implication

ETS must not claim universal ordering, completeness or liveness in an asynchronous/adversarial environment. Any guarantee must state its assumptions.

### Candidate gap for investigation

Whether evidentiary continuity can remain independently verifiable through bounded offline capture, reordering, replication and later reconciliation without pretending that the evidence establishes a globally complete event history.

---

## 10. AI accountability and continuous auditing

### Relevant recent work

- Patrick Loic Foalem et al., **Logging Requirement for Continuous Auditing of Responsible Machine Learning-based Applications** (2025 preprint).
- Victor Ojewale, Harini Suresh, Suresh Venkatasubramanian, **Audit Trails for Accountability in Large Language Models** (2026 preprint).

### Established / emerging contribution

Recent work increasingly treats logging and audit trails as mechanisms for linking technical lifecycle events with governance records, approvals, model/data context, deployment and monitoring.

### ETS novelty exclusions

ETS must not claim novelty merely for maintaining AI audit trails, model metadata, governance events or append-only lifecycle records.

### Candidate gap for investigation

Whether evidence for a *specific consequential machine action* can be reconstructed independently across input/context, model/runtime identity, policy, authority, declared decision, tool/action execution and externally observed result—without requiring hidden chain-of-thought and without assuming that origin logs are complete.

---

## 11. Assured autonomy and learning-enabled cyber-physical systems

### Core sources

- DARPA, **Assured Autonomy**: <https://www.darpa.mil/research/programs/assured-autonomy>
- Ufuk Topcu et al., **Assured Autonomy: Path Toward Living With Autonomous Systems We Can Trust** (2020).
- Emerging work such as **CPS-Guard: Framework for Dependability Assurance of AI- and LLM-Based Cyber-Physical Systems** (2025 preprint).

### Established / emerging contribution

Assured-autonomy research addresses continuing assurance, monitoring, verification/validation and confidence in learning-enabled systems whose behavior can evolve in operation.

### ETS implication

ETS is not a replacement for safety assurance, formal verification, runtime monitoring or certification.

### Candidate gap for investigation

Evidence Architecture asks a complementary post-event question: what evidence permits an independent party to reconstruct which observation occurred, what inference/decision was made, what authority existed, what command was issued, whether an actuator executed and what resulting state was independently observed?

---

## 12. Assurance cases and dependability arguments

### Established contribution

Dependability and assurance-case disciplines structure claims, arguments and evidence used to justify confidence in safety/security properties.

### ETS implication

Evidence Architecture should not be presented as a replacement for an assurance case. ETS evidence may instead become evidence *used by* an assurance argument.

### Candidate gap for investigation

Whether machine-produced evidence can carry enough provenance and explicit trust boundaries to support later assurance arguments without forcing the analyst to trust a single origin system's account of events.

---

## 13. Evidence Architecture candidate synthesis

The literature map currently suggests that ETS novelty, if any, is likely to exist in the **composition and bounded semantics** of established mechanisms rather than in any primitive.

The strongest candidate synthesis is:

> A domain-neutral evidence architecture in which evidence objects and relationships remain separately attributable and independently inspectable; verifier output distinguishes verified, asserted, contradicted and unknown states; trust dependencies are explicit; authority/policy state is evidentiary context; and consequence custody distinguishes command from execution and independently observed resulting state.

This is a provisional research proposition, not a novelty finding.

## Search protocol for systematic phase

For each domain record:

- database/search engine;
- exact query string;
- search date;
- result count if available;
- inclusion/exclusion rule;
- included papers/specifications;
- backward citation chain;
- forward citation chain;
- nearest-work rationale;
- negative search notes.

Primary scholarly databases should include IEEE Xplore, ACM Digital Library, SpringerLink, Scopus or Web of Science where available, with Google Scholar used for citation chaining and arXiv used for discovery rather than automatic evidence of peer review.

## Immediate next expansion

The highest-risk novelty areas are:

1. formal relation-by-relation comparison against W3C PROV;
2. database/data provenance and provenance semirings;
3. secure/tamper-evident logging beyond Certificate Transparency;
4. remote attestation / RATS / TEE evidence;
5. digital chain-of-custody models;
6. knowledge/provenance graph trust and uncertainty;
7. AI accountability, ML observability and runtime provenance;
8. cyber-physical event provenance and forensic reconstruction;
9. assurance cases and evidence argumentation;
10. closest-work matrix for every `EA-C###` contribution.
