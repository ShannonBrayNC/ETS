# EXP-001 Institutional Review Packet

**Status:** submission-ready draft; institutional determination not yet obtained  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED  
**Participant recruitment:** BLOCKED pending governing institutional determination

## Purpose

This packet is intended to support a university, institutional review board, research ethics office, or equivalent governing body in determining the applicable human-subjects review pathway for EXP-001. It does not assert that the study is exempt, non-human-subject research, expedited, or otherwise approved.

## Study title

**Comparative reconstruction accuracy under provenance-only, domain-extended provenance, and bounded Evidence Architecture representations**

## Research question

Does a bounded evidence representation that explicitly separates provenance, authority, standing, epistemic state, source dependence, command execution, consequence, and resulting-state observation reduce reconstruction errors relative to ordinary provenance and provenance plus domain extensions when substantive facts are held constant?

## Study design

EXP-001 uses a prospective within-participant repeated-measures design. Each evaluator receives all 12 frozen scenarios, with exactly one of three representation conditions per scenario. Assignment is balanced and prospectively frozen.

The three internal conditions are:

- Condition A: ordinary provenance-oriented representation;
- Condition B: provenance plus domain-specific relationship types and state labels;
- Condition C: bounded Evidence Architecture representation with explicit verification boundaries.

Evaluator-facing labels are opaque: Format M, Format R, and Format K. The mapping and assignment matrix were frozen before any evaluator data existed.

## Participant population

The intended population is adults capable of reading technical or operational evidence scenarios and answering structured reconstruction questions. The confirmatory study should prefer adults aged 18 or older. Recruitment source, inclusion criteria, exclusion criteria, compensation, and target sample size must be approved or acknowledged under the governing institutional process before recruitment.

The preregistered target is at least 12 evaluators. If fewer than 12 usable evaluator records are obtained, the analysis is treated as exploratory rather than confirmatory.

## Participant procedures

Each evaluator will:

1. receive 12 frozen scenario packets in a prospectively assigned order;
2. review one representation format for each scenario;
3. answer the same six reconstruction questions for every scenario;
4. provide confidence on a 1–5 scale;
5. have elapsed response time recorded;
6. not be asked to search external sources;
7. be permitted to state that a conclusion is unknown or indeterminate.

The six fixed questions are already frozen in `EXP-001_EVALUATOR_INSTRUCTIONS.md` and the rendered packets.

## Data collected

The study is designed to minimize collection of personally identifying information. Expected study data include:

- evaluator study code;
- evaluator stratum, if prospectively approved;
- scenario identifier;
- assigned condition code;
- presentation order;
- free-text answers to the six fixed questions;
- confidence score from 1 to 5;
- elapsed response time;
- scorer labels and adjudication metadata.

The study does not require collection of Social Security numbers, government identifiers, precise location, medical records, financial account data, passwords, biometric identifiers, or other unnecessary sensitive identifiers.

If the governing institution requires demographic variables, each added field must be documented before recruitment and limited to what is necessary for the approved research purpose.

## Foreseeable risks

Expected risks are primarily those associated with ordinary technical-evaluation research:

- inconvenience or fatigue from reading multiple scenarios;
- mild frustration or performance anxiety;
- privacy risk if free-text responses are linked to real-world identity;
- possible reputational concern if individual performance were improperly disclosed.

No physical intervention, deception about material risk, clinical procedure, or high-consequence operational action is part of EXP-001.

## Risk minimization

Controls include:

- use of study codes rather than public participant identity in analytic datasets;
- separation of recruitment/contact records from response data where feasible;
- collection only of fields required by the approved protocol;
- no public reporting of named individual performance;
- aggregate reporting for confirmatory findings;
- retention of raw text separately from scored claims;
- fixed scoring rules and prospective analysis controls to reduce post hoc manipulation;
- explicit participant ability to state uncertainty rather than being forced into unsupported conclusions.

## Benefits

Participants should not be promised direct personal benefit. The research may contribute to understanding whether evidence-representation semantics improve reconstruction accuracy in administrative, AI/automated, and cyber-physical decision contexts.

## Compensation

No compensation structure is frozen in the research design. If compensation is used, the amount, method, prorating rule, withdrawal treatment, and payment-data handling must be specified before recruitment and must not be coercive.

## Consent / participant information

No final consent claim is made in this repository. The governing institution should determine whether informed consent, an information sheet, waiver/alteration, or another approved mechanism applies.

A separate neutral participant-information draft may be prepared, but it must not be treated as institutionally approved until the governing institution confirms the applicable pathway.

## Withdrawal

Before recruitment, the approved protocol must state:

- whether participation is voluntary;
- how a participant may stop participation;
- whether already collected data can be withdrawn and until what point;
- how incomplete sessions are handled analytically;
- whether compensation, if any, is prorated.

No outcome-driven exclusion rule is permitted.

## Confidentiality and data security

At minimum, the operational plan should provide:

- unique evaluator study codes;
- access limited to authorized research personnel;
- separate storage of contact/recruitment information from response datasets when practical;
- encrypted storage and transport using institutionally approved services where required;
- explicit retention period and deletion/archive rule;
- no publication of raw identifying response records without separately authorized disclosure.

## Data retention

The final retention duration is intentionally not invented here. The governing institution, doctoral program, sponsor, publication venue, or applicable policy may impose retention requirements. The approved duration and disposition rule must be added before recruitment.

## Analysis plan

The analysis plan was frozen before participant data collection. Required descriptive metrics and the confirmatory success rule are defined in `EXP-001_ANALYSIS_SKELETON.md`, with a no-results executable implementation under `docs/research/phd/exp001-analysis/`.

No inferential test may be selected solely because it produces a favorable result. Null and negative results must be retained and reported.

## Research-integrity controls already completed

Before institutional submission:

- prior-art qualification completed without promoting the candidate claims;
- EXP-001 preregistration frozen;
- 12-scenario corpus frozen;
- scoring key frozen;
- evaluator instructions frozen;
- assignment seed and format mapping frozen;
- all 12 evaluator assignment slots and scenario orders frozen;
- all 36 evaluator packets deterministically materialized;
- two-pass packet regeneration produced identical SHA-256 sets;
- historical packet-hash discrepancy preserved rather than erased;
- no-results analysis implementation prepared;
- independent equivalence-review forms prepared.

## Remaining gates

The following must remain blocked until completed:

1. governing institutional human-subjects determination;
2. any required consent or participant-information approval;
3. independent fact-equivalence certification for all 12 scenario triplets;
4. final pre-execution artifact/commit freeze;
5. evaluator recruitment and exposure.

## Requested institutional determination

The investigator requests written guidance identifying the applicable review pathway for EXP-001 and any required submission, consent, data-handling, recruitment, training, or oversight obligations.

The repository must not convert silence, informal conversation, or self-assessment into an approval claim. The determination record should be retained with the research artifacts before recruitment.

## Primary supporting artifacts

- `EXP-001_PREREGISTRATION.md`
- `EXP-001_SCENARIO_CORPUS.md`
- `EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`
- `EXP-001_EVALUATOR_INSTRUCTIONS.md`
- `EXP-001_ANALYSIS_SKELETON.md`
- `EXP-001_CONDITION_PACKAGES.md`
- `EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md`
- `EXP-001_ASSIGNMENT_MATRIX.md`
- `EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md`
- `EXP-001_ARTIFACT_MANIFEST.md`
- `EXP-001_PACKET_FREEZE_RESOLUTION.md`
- `exp001-packets/rendered_sha256.authoritative.json`
- `exp001-equivalence/`
- `exp001-analysis/`

**This packet is preparation for institutional review, not evidence that review has occurred.**
