# ETS Doctoral Literature Map

Status: seed map for systematic expansion.

This map organizes adjacent work by the ETS research property it constrains. It is not a systematic literature review and must not be used alone to claim novelty.

| Domain | Canonical/seed work | What it establishes | ETS question constrained |
|---|---|---|---|
| General provenance | W3C PROV | interoperable entity/activity/agent provenance and relationships | RQ2, RQ3 |
| Public append-only auditability | Certificate Transparency, RFC 6962 | Merkle inclusion/consistency, signed tree heads, detectable conflicting views | RQ1, RQ3, RQ4 |
| Software supply-chain integrity | in-toto | signed authorized-step metadata, materials/products, expected layouts | RQ1, RQ2, RQ3 |
| Software artifact provenance | SLSA Provenance | verifiable where/when/how build/source artifacts were produced | RQ1, RQ2, RQ3 |
| Media provenance/authenticity | C2PA Content Credentials | signed manifests/assertions, content binding, provenance history under trust model | RQ1, RQ2, RQ3, RQ5 |
| Digital forensics / evidence management | NIST digital-forensics and evidence-management guidance | integrity, custody, validated methods, repeatability, reporting | RQ1, RQ3, RQ7 |
| Tamper-evident audit logs | expansion required | secure logging beyond CT, forward integrity, deletion/truncation/fork detection | RQ3, RQ4, RQ7 |
| Database/data provenance | expansion required | lineage semantics, semirings, query-result provenance | RQ2, RQ3 |
| Remote attestation / TEEs | expansion required | measurement, platform identity, trust roots, attested execution state | RQ3, RQ5, RQ6 |
| Knowledge/provenance graph verification | expansion required | graph semantics, uncertainty/trust/claim propagation | RQ2, RQ3 |
| AI accountability/provenance | expansion required | model/data/runtime lineage, decision logging, accountability boundaries | RQ5, RQ7 |
| Cyber-physical/robotics assurance | expansion required | sensing, decision, command, actuator and resulting-state assurance | RQ6, RQ7, RQ8 |
| Formal verification | existing ETS TLA+/Alloy plus expansion required | safety/liveness/model-bound correctness and refinement | RQ3, RQ4, RQ7 |

## Seed primary sources

- W3C PROV Model Primer: <https://www.w3.org/TR/prov-primer/>
- RFC 6962 Certificate Transparency: <https://www.rfc-editor.org/rfc/rfc6962.html>
- in-toto specifications: <https://in-toto.io/docs/specs/>
- in-toto model/getting started: <https://in-toto.io/docs/getting-started/>
- SLSA Provenance v1.2: <https://slsa.dev/spec/v1.2/provenance>
- C2PA Content Credentials 2.4: <https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html>
- NIST Digital Forensics glossary: <https://csrc.nist.gov/glossary/term/digital_forensics>
- NIST Evidence Management: <https://www.nist.gov/forensic-science/interdisciplinary-topics/evidence-management>

## Search protocol required for systematic phase

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

Primary scholarly databases should include IEEE Xplore, ACM Digital Library, SpringerLink, Scopus or Web of Science where available, with Google Scholar used for citation chaining and arXiv used for discovery rather than as automatic evidence of peer review.

## Immediate next expansion

The next highest-risk novelty areas for `EA-C001`/`EA-C002` are:

1. database/data provenance and provenance semirings;
2. secure/tamper-evident logging beyond Certificate Transparency;
3. remote attestation and TEE evidence;
4. digital chain-of-custody models;
5. provenance/knowledge graph trust and uncertainty;
6. cyber-physical event provenance.
