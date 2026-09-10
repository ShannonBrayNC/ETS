# EXP-001 Frozen Assignment Matrix

**Status:** frozen pre-execution control  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED  
**Seed:** `a5c57f031335d92aa42b64affd657334`  
**Evaluator slots:** 12 prospective anonymous slots (`E01`–`E12`)

## Opaque format mapping

- internal Condition A -> evaluator-facing Format M
- internal Condition B -> evaluator-facing Format R
- internal Condition C -> evaluator-facing Format K

## Assignment rule

For zero-based evaluator index `e` and zero-based scenario index `s`, internal condition index is `(e + s) mod 3`, with A/B/C indexed 0/1/2. The opaque mapping above is then applied.

## Evaluator-by-scenario format matrix

| Slot | S01 | S02 | S03 | S04 | S05 | S06 | S07 | S08 | S09 | S10 | S11 | S12 |
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

## Frozen scenario order per slot

- **E01:** S01 -> S02 -> S12 -> S05 -> S11 -> S04 -> S06 -> S09 -> S10 -> S03 -> S08 -> S07
- **E02:** S08 -> S07 -> S10 -> S01 -> S05 -> S04 -> S06 -> S11 -> S02 -> S03 -> S12 -> S09
- **E03:** S06 -> S07 -> S02 -> S04 -> S03 -> S11 -> S10 -> S12 -> S01 -> S09 -> S08 -> S05
- **E04:** S08 -> S10 -> S02 -> S11 -> S06 -> S01 -> S12 -> S09 -> S03 -> S05 -> S07 -> S04
- **E05:** S12 -> S07 -> S02 -> S03 -> S09 -> S01 -> S08 -> S04 -> S05 -> S06 -> S10 -> S11
- **E06:** S01 -> S10 -> S02 -> S08 -> S03 -> S12 -> S04 -> S11 -> S06 -> S07 -> S05 -> S09
- **E07:** S05 -> S03 -> S12 -> S10 -> S02 -> S09 -> S04 -> S11 -> S06 -> S08 -> S01 -> S07
- **E08:** S04 -> S09 -> S01 -> S05 -> S12 -> S03 -> S10 -> S08 -> S06 -> S02 -> S11 -> S07
- **E09:** S01 -> S05 -> S12 -> S06 -> S08 -> S03 -> S11 -> S07 -> S09 -> S02 -> S10 -> S04
- **E10:** S02 -> S09 -> S08 -> S04 -> S10 -> S12 -> S01 -> S06 -> S11 -> S03 -> S05 -> S07
- **E11:** S01 -> S05 -> S07 -> S06 -> S08 -> S12 -> S10 -> S02 -> S09 -> S03 -> S11 -> S04
- **E12:** S03 -> S12 -> S07 -> S11 -> S01 -> S09 -> S05 -> S04 -> S02 -> S10 -> S08 -> S06

## Balance verification

Across 12 slots, every scenario appears exactly four times in Format K, four times in Format M, and four times in Format R. Each evaluator slot receives exactly four scenarios in each format.

## Replacement rule

If a recruited evaluator withdraws before usable data are collected, the replacement uses the same pre-generated slot. No reassignment may be optimized using observed responses.

## Research-integrity boundary

This file allocates representation formats and presentation order only. It contains no participant identities, responses, scores, outcomes, or experimental findings. It does not execute EXP-001.
