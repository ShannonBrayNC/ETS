# EXP-001 Neutral Condition Packages

**Status:** frozen pre-execution design artifact  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Purpose

Define the neutral representation contract used to render each of the 12 frozen EXP-001 scenarios under three conditions while holding substantive facts constant.

The condition labels shown to evaluators MUST be neutral. The implementation may use internal labels A/B/C, but evaluator-facing materials MUST use opaque labels such as `Format X`, `Format Y`, and `Format Z`, with the mapping randomized and preserved outside the evaluator packet.

## Common source rule

For every scenario, all three condition packages MUST be generated from the same frozen fact inventory. No condition may introduce a reconstruction-material fact absent from another condition.

A representation difference is permitted only when it concerns semantic treatment, structure, relationship typing, verification vocabulary, or explicit boundary labeling already implied by the same underlying facts.

If a condition adds materially new factual content, that scenario is disqualified from confirmatory analysis until corrected before evaluator exposure.

## Condition A — Baseline provenance representation

Render the scenario using ordinary W3C PROV-compatible concepts and relations where applicable:

- entities;
- activities;
- agents;
- generation;
- usage;
- derivation;
- attribution;
- association;
- delegation;
- revision;
- time annotations;
- collections/bundles where useful.

Condition A MUST NOT intentionally hide facts that are present in the frozen fact inventory. When a fact lacks a natural first-class PROV relation, it may be represented as an ordinary attribute or associated entity so information equivalence is preserved.

Condition A MUST NOT add Evidence Architecture-specific interpretation rules, verification claim vectors, epistemic-state vocabulary, standing-boundary labels, or command/result non-collapse instructions.

## Condition B — Provenance plus ordinary domain extensions

Render exactly the same underlying facts as Condition A and C, but allow explicit domain-specific nodes, edge types, and attributes.

Condition B MAY represent concepts such as:

- authorization state;
- policy version;
- expected event;
- sensor availability;
- model output;
- command acceptance;
- actuator acknowledgment;
- physical observation;
- source dependency;
- contradiction;
- revocation;
- confidence or quality metadata.

Condition B MUST NOT use Evidence Architecture's normative boundary rules or pre-classified verification dimensions. It is deliberately the strongest non-EA comparator and tests whether ordinary domain modeling alone explains any observed benefit.

## Condition C — Evidence Architecture bounded semantics

Render the same frozen facts while making the following semantics explicit where the scenario supports them:

- observation versus inference;
- direct source versus derived claim;
- evidence integrity versus identity versus authority/standing;
- historical standing versus current standing;
- missing evidence versus evidence of absence;
- epistemic states such as unknown, unavailable, indeterminate, or contradicted;
- source-dependence and non-independent corroboration;
- requested action versus accepted command versus execution;
- execution versus consequence versus result observation;
- time quality/freshness where material;
- verification claim dimensions and explicit nonclaims;
- relationship/edge provenance when material.

Condition C MUST NOT state semantic truth, legal correctness, causality, completeness, currentness, or physical outcome unless the frozen facts support that exact proposition.

## Fixed evaluator-facing package template

Each scenario packet SHALL contain only:

1. an opaque scenario ID;
2. an opaque format label;
3. the rendered evidence representation;
4. the fixed six reconstruction questions from `EXP-001_EVALUATOR_INSTRUCTIONS.md`.

It SHALL NOT disclose:

- which format is Evidence Architecture;
- expected hypotheses;
- scoring categories;
- which traps the scenario was designed to test;
- the answer key;
- the researcher's preferred interpretation.

## Scenario rendering requirements

Each scenario SHALL preserve all fact IDs from `EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`.

Before use, the renderer/reviewer must certify for each condition:

- all material facts represented;
- no extra material facts added;
- contradictions preserved;
- unknown/unavailable facts not silently resolved;
- timestamps copied without upgrading time quality;
- authority records copied without upgrading standing;
- command/ack/result stages preserved as separate facts when present;
- shared-source dependencies preserved;
- wording does not reveal condition identity.

## Neutrality rule

Presentation quality MUST be approximately comparable across conditions. Condition C cannot receive substantially better typography, explanation, organization, or visual emphasis merely because it is the experimental representation.

Where possible, use matched density, font size, node count, edge visibility, ordering, and explanatory text length.

Any unavoidable presentation asymmetry must be recorded before evaluator exposure.

## Freeze rule

This document defines the rendering contract. Individual rendered scenario packets may be generated after this commit, but once the 36 packets (12 scenarios x 3 conditions) are frozen and hashed, no packet may be substantively changed without an amendment recorded before evaluator data are viewed.
