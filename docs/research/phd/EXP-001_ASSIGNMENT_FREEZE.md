# EXP-001 Assignment Freeze

**Status:** frozen pre-execution assignment artifact  
**Execution state:** NOT EXECUTED  
**Seed:** `a5c57f031335d92aa42b64affd657334`

## Opaque format mapping

- internal Condition A -> evaluator-facing **Format M**
- internal Condition B -> evaluator-facing **Format R**
- internal Condition C -> evaluator-facing **Format K**

This mapping was generated before any evaluator outcome data existed and must not be changed based on later observations.

## Balanced 12-slot condition matrix

| Evaluator slot | S01 | S02 | S03 | S04 | S05 | S06 | S07 | S08 | S09 | S10 | S11 | S12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E01 | M | R | K | M | R | K | M | R | K | M | R | K |
| E02 | R | K | M | R | K | M | R | K | M | R | K | M |
| E03 | K | M | R | K | M | R | K | M | R | K | M | R |
| E04 | M | R | K | M | R | K | M | R | K | M | R | K |
| E05 | R | K | M | R | K | M | R | K | M | R | K | M |
| E06 | K | M | R | K | M | R | K | M | R | K | M | R |
| E07 | M | R | K | M | R | K | M | R | K | M | R | K |
| E08 | R | K | M | R | K | M | R | K | M | R | K | M |
| E09 | K | M | R | K | M | R | K | M | R | K | M | R |
| E10 | M | R | K | M | R | K | M | R | K | M | R | K |
| E11 | R | K | M | R | K | M | R | K | M | R | K | M |
| E12 | K | M | R | K | M | R | K | M | R | K | M | R |

Each slot contains four M, four R, and four K exposures. Every scenario receives four observations in each format if all 12 slots are filled.

## Frozen scenario-order permutations

- E01: S01, S07, S12, S11, S10, S03, S02, S09, S06, S05, S04, S08
- E02: S04, S12, S09, S03, S10, S11, S02, S07, S06, S01, S08, S05
- E03: S05, S02, S09, S01, S08, S11, S04, S10, S07, S12, S03, S06
- E04-E12: generate deterministically from the same seed using the procedure in `EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md`; exact permutations must be materialized and hashed before recruitment.

## Replacement rule

A replacement participant receives the next unused pre-generated evaluator slot. Do not optimize or adapt assignments based on observed performance.

## Boundary

This artifact freezes assignment logic and the A/B/C-to-format mapping. It is not participant data and does not execute EXP-001.
