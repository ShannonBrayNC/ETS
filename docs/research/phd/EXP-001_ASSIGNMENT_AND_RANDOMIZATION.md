# EXP-001 Assignment and Randomization Procedure

**Status:** frozen pre-execution design artifact  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Goal

Balance exposure to Conditions A/B/C across scenarios and evaluators while preventing condition identity from being obvious to participants.

## Design

Each evaluator receives all 12 scenarios and exactly one representation condition per scenario.

For each evaluator:

- 4 scenarios SHALL use Condition A;
- 4 scenarios SHALL use Condition B;
- 4 scenarios SHALL use Condition C.

Across the evaluator pool, each scenario SHOULD receive approximately equal observations under A, B, and C.

## Blocking

The 12 scenarios are grouped by domain:

- digital/administrative: D1-D4;
- AI/automated: A1-A4;
- cyber-physical: C1-C4.

Within each evaluator packet, assignments SHOULD avoid concentrating one representation condition in only one domain. Each condition SHOULD appear in each domain whenever the balancing design permits.

## Deterministic generation

Before evaluator recruitment, freeze:

1. a pseudorandom seed;
2. the assignment-generation script or exact manual Latin-square table;
3. the resulting evaluator-by-scenario condition matrix;
4. the scenario-order permutations;
5. the opaque mapping from internal condition labels A/B/C to evaluator-facing labels.

The seed MUST be generated before outcome data exist and recorded in the artifact manifest.

## Preferred assignment method

For evaluator index `e` and scenario index `s`, use a balanced cyclic base assignment:

`condition_index = (e + s) mod 3`

Then apply a frozen seed-based permutation independently to:

- scenario order per evaluator;
- the mapping of numeric condition index to evaluator-facing format label.

For evaluator counts not divisible by 3, retain the cyclic assignment and report the resulting small imbalance rather than modifying assignments based on observed results.

## Neutral labels

Evaluator-facing labels MUST NOT imply quality or chronology. Recommended labels:

- Format K;
- Format M;
- Format R.

The A/B/C -> K/M/R mapping SHALL be randomly permuted and frozen before evaluator exposure.

## Seed handling

The seed is not itself sensitive, but it SHOULD be withheld from evaluator materials until data collection is complete to avoid revealing assignment structure.

The manifest SHALL contain:

- algorithm name;
- seed value;
- software/runtime version if a script is used;
- hash of generated assignment matrix;
- hash of generated scenario-order table.

## No adaptive reassignment

Do not alter assignments because an evaluator is performing unusually well or poorly, because a condition appears advantageous, or because early responses suggest an effect.

Replacement participants, if any, receive the next pre-generated evaluator slot rather than a newly optimized assignment.

## Dry-run rule

A non-data-bearing dry run may validate packet mechanics, broken links, unreadable rendering, or timing instrumentation. Dry-run participants must not contribute confirmatory outcome data unless they were prospectively designated as evaluators before exposure.

## Current state

The procedure is frozen, but no seed, assignment matrix, or participant slots have been instantiated. EXP-001 remains NOT EXECUTED.
