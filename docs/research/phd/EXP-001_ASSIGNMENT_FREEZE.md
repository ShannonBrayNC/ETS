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

- E01: S01, S02, S12, S05, S11, S04, S06, S09, S10, S03, S08, S07
- E02: S08, S07, S10, S01, S05, S04, S06, S11, S02, S03, S12, S09
- E03: S06, S07, S02, S04, S03, S11, S10, S12, S01, S09, S08, S05
- E04: S08, S10, S02, S11, S06, S01, S12, S09, S03, S05, S07, S04
- E05: S12, S07, S02, S03, S09, S01, S08, S04, S05, S06, S10, S11
- E06: S01, S10, S02, S08, S03, S12, S04, S11, S06, S07, S05, S09
- E07: S05, S03, S12, S10, S02, S09, S04, S11, S06, S08, S01, S07
- E08: S04, S09, S01, S05, S12, S03, S10, S08, S06, S02, S11, S07
- E09: S01, S05, S12, S06, S08, S03, S11, S07, S09, S02, S10, S04
- E10: S02, S09, S08, S04, S10, S12, S01, S06, S11, S03, S05, S07
- E11: S01, S05, S07, S06, S08, S12, S10, S02, S09, S03, S11, S04
- E12: S03, S12, S07, S11, S01, S09, S05, S04, S02, S10, S08, S06

These exact permutations are frozen before evaluator recruitment and SHALL NOT be regenerated or adapted in response to observed outcomes.

## Replacement rule

A replacement participant receives the next unused pre-generated evaluator slot. Do not optimize or adapt assignments based on observed performance.

## Boundary

This artifact freezes assignment logic and the A/B/C-to-format mapping. It is not participant data and does not execute EXP-001.
