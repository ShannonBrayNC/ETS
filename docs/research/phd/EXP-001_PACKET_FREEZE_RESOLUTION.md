# EXP-001 Authoritative Packet Freeze Resolution

**Status:** prospective pre-execution reconciliation complete for deterministic rendering  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED  
**Baseline commit:** `ace12315203396de4b961cd50234d9c248d6f961`

## Result

The candidate authoritative packet source and renderer defined by WP2 were regenerated twice
without modifying scenario facts, condition mapping, seed, or rendering semantics.

- Packet source blob: `47984a13eb484e3f3737ac6afcfc2633415ff033`
- Generator blob: `488a449685229c605eb0c76755443a5309a8e678`
- Seed: `a5c57f031335d92aa42b64affd657334`
- Opaque mapping: A→M, B→R, C→K
- Pass 1 packet count: 36
- Pass 2 packet count: 36
- Pass 1 / Pass 2 SHA-256 sets identical: **YES**
- Deterministic-render gate: **PASS**

## Supersession

`rendered_sha256.expected.json` is retained as historical evidence of the failed first freeze and
is not rewritten or deleted. It is superseded **for authoritative packet use only** by
`rendered_sha256.authoritative.json`.

This correction is prospective: no evaluator has been exposed to the packets and no evaluator
outcome data existed when the corrected freeze was established.

## Materialized packet set

The repository now contains 36 rendered Markdown packets under `exp001-packets/rendered/`.
Their byte-level SHA-256 values are recorded in the authoritative manifest.

The rendering freeze establishes byte reproducibility only. It does **not** by itself establish
fact equivalence across A/B/C. Independent fact-equivalence certification remains required for
all 12 scenario triplets.

## Remaining gates

1. Independent fact-equivalence certification for S01–S12.
2. Final artifact-manifest update including rendered and assignment artifacts.
3. Governing institutional human-subjects determination before evaluator recruitment.
4. No evaluator exposure until all required pre-execution gates are satisfied.

EA-C001 and EA-C002 remain candidate claims. No result, effect size, or scientific conclusion is
created by this packet-freeze resolution.
