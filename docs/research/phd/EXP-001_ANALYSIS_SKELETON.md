# EXP-001 Analysis Skeleton

**Status:** frozen before data collection  
**Experiment:** EXP-001  
**Execution status:** NOT EXECUTED

This file defines the analysis structure before any evaluator response is observed. It contains no outcome data.

## Required input tables

### evaluator_assignments

- evaluator_id
- evaluator_stratum
- scenario_id
- condition_code
- presentation_order
- randomization_seed_ref

### evaluator_responses

- evaluator_id
- scenario_id
- condition_code
- question_id
- response_text
- confidence_1_to_5
- elapsed_seconds

### claim_scores

- evaluator_id
- scenario_id
- condition_code
- question_id
- claim_id
- claim_text
- primary_label: SUPPORTED | UNSUPPORTED | CONTRADICTED | INDETERMINATE | NOT_APPLICABLE
- error_UI
- error_SC
- error_CR
- error_FC
- error_MC
- error_EO
- error_SD
- error_IO
- error_ST
- error_TQ
- scorer_id
- adjudication_status

## Data-quality gates

Before analysis:

1. verify all evaluator-condition assignments against frozen randomization artifacts;
2. verify every evaluator answered all six fixed questions for each assigned scenario or mark missing responses explicitly;
3. verify scenario packages against fact-equivalence certification;
4. exclude no response because its result is inconvenient;
5. document technical failures and protocol deviations;
6. preserve raw text separately from scored claims.

## Primary condition summaries

For Conditions A, B, and C report:

- evaluator count;
- scenario exposures;
- substantive assertion count;
- SUPPORTED count;
- UNSUPPORTED count;
- CONTRADICTED count;
- INDETERMINATE count;
- unsupported-inference rate;
- standing-collapse rate;
- command-result-collapse rate;
- false-completeness rate;
- missed-contradiction rate;
- epistemic-overstatement rate;
- supported-claim precision;
- mean reconstruction time;
- median reconstruction time;
- confidence distribution.

Always report raw numerators and denominators beside rates.

## Primary confirmatory comparison

Evaluate the preregistered success rule exactly:

Condition C must show a lower aggregate rate than both A and B on at least three of:

1. unsupported inference;
2. standing collapse;
3. command/result collapse;
4. false completeness;

and must not materially worsen supported-claim precision.

Do not reinterpret this threshold after observing data.

## Secondary comparisons

Report without converting them into undeclared primary endpoints:

- source-dependence recognition;
- inference/observation recognition;
- stale/current distinction;
- time-quality recognition;
- contradiction recognition;
- confidence calibration;
- results by evaluator stratum.

## Inter-rater analysis

For the independently double-scored subset:

- preserve each scorer's original labels;
- calculate raw agreement;
- calculate an appropriate chance-corrected agreement statistic if sample size permits;
- report adjudicated and pre-adjudication agreement separately;
- inspect categories causing systematic disagreement.

Poor agreement is itself a result and may indicate ambiguous semantics or scoring criteria.

## Inferential statistics boundary

Descriptive results are mandatory. Inferential tests are optional and contingent on sample size and distribution.

Before interpreting inferential tests:

1. document the selected model/test and why it matches the repeated/matched assignment structure;
2. document multiplicity treatment;
3. report effect sizes and uncertainty intervals;
4. do not use p-values as substitutes for effect magnitude or evidentiary relevance.

No test may be selected solely because it yields a favorable result.

## Null-result handling

Explicitly report if:

- A, B, and C perform similarly;
- B performs as well as C;
- C lowers some errors but increases others materially;
- C substantially increases reconstruction time;
- effects exist only in one evaluator stratum;
- PROV representations already communicate particular boundaries adequately;
- scoring ambiguity undermines a metric.

These outcomes may narrow or refute EA-C001 and EA-C002.

## Interpretation template

For each major finding record:

- observed result;
- relevant hypothesis/contribution;
- effect magnitude;
- uncertainty;
- alternative explanations;
- representation verbosity/familiarity concerns;
- whether result supports, narrows, refutes, or leaves candidate claim unresolved;
- whether independent reproduction is required before stronger language.

## Artifact provenance

Final analysis must record:

- frozen corpus commit SHA;
- representation package commit SHA;
- scoring-key commit SHA;
- assignment/randomization artifact hash;
- analysis code/notebook commit SHA;
- raw response artifact hashes;
- scoring artifact hashes;
- any amendments or protocol deviations.

**No data has been analyzed in this skeleton.**
