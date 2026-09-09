# ETS Public Works Manifest

This manifest inventories candidate works that may support future doctoral consideration. Inclusion here does not imply that a university will accept the item as a qualifying public work or publication.

## Record schema

```text
ID: PW-###
Title:
Type: publication | report | specification | software | formal model | dataset | experimental corpus | artefact | other
Public URL:
Persistent identifier/DOI:
Release/publication date:
Version/ref:
Authors/contributors:
Candidate contribution percentage:
Contribution roles:
Research questions:
Contribution IDs:
Methodology:
Supporting experiments:
Peer-review status:
External review status:
Independent reproduction status:
Impact evidence:
University-route notes:
```

## Initial candidate works

### PW-001 — ETS research corpus

- **Type:** scholarly/technical reports and research documentation
- **Public location:** `docs/research/`
- **Questions:** RQ0–RQ7 as applicable
- **Peer-review status:** not established
- **Route note:** useful supporting corpus; individual universities may not treat repository documentation as qualifying published work.

### PW-002 — Formal model and traceability corpus

- **Type:** formal models, claims, theorems, traceability artifacts
- **Public location:** formal ETS research artifacts including `FORMAL_TRACEABILITY_MATRIX.md`, `FORMAL_MODEL_CLAIMS.md`, `FORMAL_THEOREMS.md`, TLA+/Alloy models
- **Questions:** RQ1–RQ4, RQ7
- **Peer-review status:** not established
- **Route note:** potentially strong evidence of rigor and methodology, but requires external scholarly validation and publication packaging.

### PW-003 — ETS reference implementation

- **Type:** research software / engineering artefact
- **Public location:** repository source tree
- **Questions:** supports multiple questions but does not independently establish originality or contribution to knowledge
- **Peer-review status:** not applicable / not established
- **Route note:** potentially relevant to routes accepting engineering designs or artefacts; must be contextualized academically.

### PW-004 — Reproducibility and verification corpus

- **Type:** reproducibility documentation, tests, vectors, CI evidence
- **Public location:** repository research docs, tests, scripts, workflow outputs where durable
- **Questions:** RQ1, RQ3, RQ4, RQ7
- **Independent reproduction:** partial/internal unless externally reproduced
- **Route note:** supporting evidence rather than presumed qualifying publication.

### PW-005 — AI Witness / machine-action provenance research

- **Type:** architecture, research notes, case studies, software artifacts as available
- **Questions:** RQ5, RQ7
- **Peer-review status:** not established
- **Route note:** candidate source material for a dedicated paper.

### PW-006 — Ranger cyber-physical provenance research program

- **Type:** research platform, specifications, experiments, software/formal artifacts
- **Public location:** `docs/research/ranger/` and associated implementation/tests
- **Questions:** RQ6, RQ8
- **Peer-review status:** not established
- **Route note:** strongest future applied/experimental artefact once physical experiment results and independent observation evidence exist.

### PW-007 — ETS Adversarial Qualification research program

- **Type:** methodology/research program
- **Public location:** ETS security research documentation
- **Questions:** RQ7
- **Peer-review status:** not established
- **Route note:** candidate basis for security-methodology publication after bounded experiments are executed.

## Planned publication wave

The following are publication targets, not completed works.

| ID | Working title | Primary questions | Intended contribution |
|---|---|---|---|
| PUB-001 | Evidence Architecture: A Formal Framework for Independently Verifiable Digital Evidence | RQ0, RQ1, RQ3 | Foundations and trust boundary |
| PUB-002 | Evidence Objects and Evidence Graphs | RQ1, RQ2 | Representation and relationship semantics |
| PUB-003 | Independent Verification Without Origin-System Trust | RQ0, RQ3, RQ7 | Verification/trust decomposition |
| PUB-004 | Machine-Action Provenance for Nondeterministic AI Systems | RQ5, RQ7 | AI Witness experimental framework |
| PUB-005 | Evidence Continuity Under Offline and Asynchronous Operation | RQ4 | Distributed/offline provenance |
| PUB-006 | Cyber-Physical Decision Provenance with ETS Ranger | RQ6, RQ8 | Observation-to-consequence validation |
| PUB-007 | Adversarial Qualification of Evidence-Producing Systems | RQ7 | Security/failure-boundary methodology |

## Priority data to add

For each existing candidate work, capture next:

1. exact public URL and immutable ref/version;
2. first-public date;
3. full authorship and candidate contribution percentage;
4. related research questions and contribution IDs;
5. peer-review/publication status;
6. external reviews, citations, adoption, reproductions, or challenges;
7. restrictions on public data or artifacts;
8. closest scholarly publication target.
