# ETS Doctoral Readiness Matrix

This matrix tracks whether the ETS research corpus can support credible application to research-degree routes. It is intentionally conservative and should be updated only from documented evidence.

## Program-neutral doctoral gates

| Gate | Current status | Evidence / gap |
|---|---|---|
| Coherent research theme | satisfied | ETS has a consistent focus on independently verifiable evidence/provenance across digital, AI, distributed, and cyber-physical systems. |
| Canonical research questions | satisfied | `RESEARCH_QUESTIONS.md` now defines RQ0–RQ8. |
| Candidate original contributions | partial | `CONTRIBUTION_LEDGER.md` identifies candidates; originality still requires systematic prior-art review. |
| Explicit methodology | partial | engineering/formal methods exist; publication-grade methods must be linked per contribution/experiment. |
| Formal evidence | partial | TLA+/Alloy/formal traceability exists for several bounded properties; refinement and broader formal coverage remain incomplete. |
| Experimental evidence | partial | extensive tests/simulations exist; doctoral experiment records and prospective protocols are only now being formalized. |
| Reproducibility | partial | reproducibility guidance and tests exist; independent reproduction is not yet broadly established. |
| Negative-result record | partial | conservative claim boundaries exist; systematic negative-result/counterexample ledger must be populated. |
| Literature review | missing | systematic scholarly literature map and bibliography still required. |
| Novelty/gap analysis | missing | each major contribution requires closest-prior-work comparison. |
| Public works inventory | partial | initial manifest exists; immutable refs, authorship, dates, impact, and public URLs must be populated. |
| Peer-reviewed publications | blocked | foundational ETS work has not yet been qualified here as peer-reviewed publication. |
| External scholarly validation | blocked | independent academic review/reproduction/citation must be developed. |
| Impact evidence | partial | public engineering activity exists; scholarly/field impact must be documented separately and conservatively. |
| Authorship contribution records | missing | must be populated per public work; collaborative works need contribution evidence. |
| Academic CV | missing | create research-focused CV distinct from engineering résumé. |
| Academic referees | blocked | identify/develop 2–3 suitable referees with direct knowledge of the research. |
| Doctoral proposal/synthesis | partial | research theme/questions exist; university-neutral proposal should follow literature/contribution inventory. |

## Target-route matrix

Requirements below are based on current public university guidance and should be revalidated before application.

### 1. Middlesex University — PhD by Public Works

Current public requirements include: a body of public work with demonstrated impact; admission-stage assessment against QAA Level 8 criteria for contribution to knowledge, significance, methodology, and originality; a motivation/coherence/originality proposal with full public-work links; contribution statements for joint works; normally a Master's degree plus normal university eligibility; interview; and ultimately a contextual statement up to 30,000 words.

| Requirement | Status | ETS action |
|---|---|---|
| Body of public work | partial | Populate manifest with stable public URLs/versions and identify which outputs plausibly qualify by discipline. |
| Demonstrated impact | missing/partial | Create impact ledger with citations, independent use, external review, reproduction, standards/industry uptake. |
| Level 8 originality/significance | partial | Complete literature and novelty map per candidate contribution. |
| Methodology | partial | Convert existing formal/experimental methods into explicit research methodology records. |
| Coherence | partial | Build synthesis showing how selected works answer RQ0 and subordinate RQs. |
| Joint-work contribution statements | missing | Add signed/traceable contribution records where applicable. |
| Proposal with public links | partial | Can be assembled after manifest is populated. |
| Interview readiness | partial | Build concise defense of novelty, method, limitations, and contribution. |

**Current route status: strongest immediate target, but impact and novelty evidence are critical gaps.**

### 2. University of Westminster — PhD by Published Work

Current guidance accepts a coherent body of work equivalent in quality, rigour, and volume to a standard PhD, including refereed papers and other public outputs such as engineering designs; applicants from outside Westminster are accepted; works generally must be no more than ten years old; the application includes a portfolio and proposal up to 2,000 words showing coherence and intended contribution; collaborative contribution evidence is required; successful candidates later prepare a commentary up to 15,000 words.

| Requirement | Status | ETS action |
|---|---|---|
| Coherent body of work | partial | Select a bounded portfolio rather than the entire repository. |
| Appropriate public outputs | partial | Determine which software/design/specification outputs the School would accept. |
| Original contribution to knowledge | partial | Complete prior-art and contribution qualification. |
| 2,000-word proposal | partial | Generate only after portfolio selection and novelty review. |
| Publication/work metadata | missing/partial | Add dates, full citations, URLs, versions, authorship. |
| Candidate contribution percentage | missing | Record per collaborative work. |
| Suitable internal expertise | blocked | Identify and contact matching Computer Science/Engineering academics. |
| Works within ten-year window | satisfied for ETS | Current ETS corpus is recent. |

**Current route status: very strong target if engineering/research artefacts are accepted as sufficient published work by the relevant College.**

### 3. City St George's, University of London — Computer Science prior/prospective publication path

Current Computer Science guidance lists a PhD by prior publication route with a 1–2 year duration and aligns research with areas including Software Reliability. Route-specific regulations and supervisory fit require direct confirmation.

| Requirement | Status | ETS action |
|---|---|---|
| Computer Science research fit | partial/satisfied | Frame ETS around software reliability, distributed evidence, trustworthy AI, and cyber-physical provenance. |
| Prior-publication eligibility | blocked | Request formal route assessment once public-work/publication inventory is complete. |
| Prospective-publication possibility | blocked | Confirm current rules directly with School/doctoral administration; do not assume equivalence from older guidance. |
| Supervisor fit | blocked | Identify academics after canonical dossier exists. |
| Research corpus | partial | Strong engineering/formal base; publication status still weak. |

**Current route status: high-priority inquiry, especially if the School offers a path that permits completing publications during registration.**

### 4. University of Portsmouth — PhD by Publication

Current guidance requires research already undertaken and published before registration, excluding self-publishing; eligible works may include peer-reviewed academic papers, books/chapters, or equivalent accepted materials; submission follows 6–12 months after registration; applicants need a relevant degree held for at least five years, a CV, two referees, proposed title, publication list, and a statement up to 1,000 words on significance.

| Requirement | Status | ETS action |
|---|---|---|
| Research published before registration | missing/blocked | Execute peer-reviewed publication pipeline. Repository/self-published material should not be assumed to qualify. |
| Coherent publication set | missing | Target 3–7 strong related publications. |
| 1,000-word significance statement | blocked | Build after publications exist. |
| CV | missing | Create academic CV. |
| Two referees | blocked | Develop academic referees through publication/research engagement. |
| Degree held >=5 years | verify | Capture qualification dates in application data store. |

**Current route status: excellent future target after peer-reviewed publication, not the first admission route to attack.**

### 5. Newcastle University — PhD by Prior Publication (Computing eligible)

Current guidance states that the route allows prior research undertaken and published as a lead author to form a summative body of work at standard PhD level. Computing is an eligible Academic Unit. The 2026/27 pre-application checklist opens 21 September 2026.

| Requirement | Status | ETS action |
|---|---|---|
| Published prior research | missing/blocked | Build peer-reviewed publication record. |
| Lead authorship | missing/partial | Preserve authorship/contribution evidence and ensure foundational papers have clear candidate lead authorship where accurate. |
| Summative doctoral-level body | partial | Coherence framework exists; scholarly publication evidence is missing. |
| Pre-approval checklist | scheduled externally | Revalidate and complete when available. |
| Computing fit | satisfied in principle | Route explicitly includes Computing; exact supervisory fit remains to be established. |

**Current route status: strong secondary target once publications mature.**

## Work packages in attack order

### WP1 — Literature and prior-art qualification

Deliverables:

- `literature/BIBLIOGRAPHY.bib`
- `literature/LITERATURE_MAP.md`
- `literature/GAP_ANALYSIS.md`
- closest-work table per `EA-C###`

Priority domains: W3C PROV, transparency/append-only logs, tamper-evident logging, digital forensics/chain of custody, event sourcing, supply-chain provenance, attestation/TEE, distributed systems, AI provenance/accountability, autonomous-system assurance, cyber-physical evidence, formal verification.

### WP2 — Existing-work inventory

For every major ETS artifact, capture:

- stable URL/ref;
- first publication date;
- authorship/contribution percentage;
- research-question mapping;
- contribution mapping;
- method/experiment mapping;
- peer-review status;
- external impact/reproduction evidence.

### WP3 — Research experiment conversion

Select the strongest existing test/model families and create explicit experiment records. Label all historical conversions `retrospective`. Future Ranger/AI/EAQ experiments should be `prospective` whenever practical.

### WP4 — Publication pipeline

Initial sequence:

1. Evidence Architecture foundations.
2. Evidence Objects / Evidence Graphs.
3. Independent verification without origin-system trust.
4. AI Witness / machine-action provenance.
5. Offline/asynchronous evidence continuity.
6. Ranger cyber-physical provenance.
7. Adversarial qualification.

### WP5 — External validation and impact

Seek independent review, reproduction, challenge, citation, use, or collaboration. Record evidence rather than promotional claims.

### WP6 — Application dossier

Once WP1–WP3 are materially complete, assemble:

- academic CV;
- public-works/publications portfolio;
- 1–2 page contribution summary;
- university-neutral doctoral proposal;
- route-specific wrappers;
- referee list;
- transcripts/qualification metadata;
- authorship declarations.

## Readiness rule

Do not mark a university route `ready` until every mandatory admission artifact is either `satisfied` or supported by a documented external decision from the university. A strong repository is not a substitute for publication, impact, supervisory fit, or route-specific eligibility where those are required.
