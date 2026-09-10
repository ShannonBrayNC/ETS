# EXP-001 Analysis Implementation

**Execution state:** NOT EXECUTED  
**Data state:** no participant responses or scores are committed here

`exp001_analysis.py` implements the preregistered descriptive analysis structure from
`../EXP-001_ANALYSIS_SKELETON.md` without selecting or running an inferential model.

## Required inputs

The script requires three CSV files whose schemas match the frozen analysis skeleton:

- `evaluator_assignments.csv`;
- `evaluator_responses.csv`;
- `claim_scores.csv`.

It validates required columns, assignment/response consistency, confidence bounds, elapsed-time
non-negativity, and allowed primary claim labels before producing any summary.

## Produced summaries

For each condition present in the supplied assignments, the implementation reports evaluator count,
scenario exposures, assertion counts, primary-label counts, the preregistered error rates with raw
numerators and denominators, supported-claim precision, mean/median reconstruction time, and the
confidence distribution.

## Boundary

This implementation contains no outcome data and does not itself establish the preregistered success
criterion. Inferential statistics remain optional and must be selected prospectively according to the
frozen analysis skeleton rather than because a particular model produces a favorable result.

The code may be mechanically tested with synthetic data, but synthetic fixtures must be labeled as
non-experimental and must never be mixed with EXP-001 participant data.
