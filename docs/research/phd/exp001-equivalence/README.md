# EXP-001 Independent Fact-Equivalence Review Packet

**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED  
**Gate:** independent fact-equivalence certification required before evaluator exposure

This directory contains reviewer-facing certification scaffolding for the 12 frozen scenario triplets.
It does not certify any scenario and it does not execute EXP-001.

## Reviewer independence

The scenario author must not be the sole reviewer used to establish confirmatory readiness.
Author-only review may be used for internal quality control only and must be labeled:

`AUTHOR-ONLY / NOT CONFIRMATORY READY`

## Review unit

One completed form covers one scenario across the three frozen evaluator-facing packet formats:

- Format M — internal Condition A;
- Format R — internal Condition B;
- Format K — internal Condition C.

The reviewer should compare the three packets against the frozen fact inventory and verify that the
experimental representation differences do not introduce or remove reconstruction-material facts.

## Required result

Each scenario must receive one of:

- `PASS`;
- `FAIL`;
- `PASS-WITH-DOCUMENTED-NONMATERIAL-DIFFERENCE`.

A `FAIL` blocks that scenario from confirmatory use.

## Mandatory checks

The reviewer must evaluate all 12 checks from
`docs/research/phd/EXP-001_EQUIVALENCE_CERTIFICATION.md`, including preservation of unknowns,
source dependence, contradictions, authority/standing boundaries, command/execution/result separation,
time-quality limits, and absence semantics.

## Forms

Run `generate_certification_forms.py` to materialize blank reviewer forms for S01-S12. The generated
forms intentionally contain no reviewer identity, result, signature, or completed checkboxes.

Do not recruit evaluators until this gate and the governing institutional human-subjects determination
are complete.
