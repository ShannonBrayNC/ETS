# Methodology and Research Integrity

This document establishes research-integrity controls for ETS work intended to support doctoral consideration or scholarly publication.

## Prospective versus retrospective records

Every research question, hypothesis, experiment, and claimed contribution must indicate whether it was documented:

- `prospective` — before the relevant experiment or evaluation began; or
- `retrospective` — reconstructed after work had already occurred using dated source evidence.

Retrospective reconstruction is legitimate when clearly identified. It must never be presented as preregistration or contemporaneous hypothesis formation.

## Source provenance

Retrospective records should cite immutable or dated sources where available:

- commit SHAs;
- pull requests and issues;
- tagged releases;
- CI/workflow artifacts;
- experiment output bundles;
- dated technical reports;
- externally archived publications;
- DOI/version identifiers.

## Methodological minimum

A research experiment intended to support a doctoral contribution should state:

1. research question and hypothesis;
2. system and trust boundary;
3. variables and controls/baselines where applicable;
4. threat, fault, or environmental assumptions;
5. procedure;
6. evidence captured;
7. analysis method;
8. result;
9. alternative explanations;
10. limitations and failure conditions;
11. reproducibility status.

## Claim discipline

ETS already maintains an intentionally conservative distinction between protocol properties and real-world truth. Doctoral materials must preserve that discipline.

In particular:

- integrity is not authenticity;
- authenticity is not semantic truth;
- command authorization is not actuator execution;
- actuator execution is not physical consequence;
- capture is not completeness;
- omission detection requires an expectation, witness, or equivalent external basis;
- model checking within bounded assumptions is not universal correctness;
- statistical evidence is not an adversarial proof;
- a successful demonstration is not external validation.

## Negative evidence

Research records must preserve:

- failed experiments;
- failed hypotheses;
- counterexamples;
- anomalous observations;
- null or inconclusive results;
- known unsupported cases.

A result may narrow a contribution and still increase the quality of the research.

## Authorship and contribution

Each public work intended for a doctoral portfolio should record contributor roles using a consistent taxonomy, preferably aligned with CRediT where practical.

Minimum record:

```text
Work ID:
Contributors:
Conceptualization:
Methodology:
Formal analysis:
Software:
Validation:
Investigation:
Data curation:
Visualization:
Writing — original draft:
Writing — review/editing:
Supervision/advisory:
Estimated candidate contribution percentage:
Evidence supporting attribution:
```

AI-assisted drafting, coding, analysis, or review should be disclosed according to the policy of the target venue or university. AI tools are not authors and must not be used to fabricate sources, results, peer review, experimental history, or human contribution.

## Literature and novelty control

No item in the Contribution Ledger should be promoted from `candidate` to `supported` until a systematic prior-art review has identified:

- the closest related work;
- what that work already solves;
- the remaining gap;
- how the ETS contribution differs;
- whether the distinction is theoretical, methodological, empirical, architectural, or merely engineering implementation.

Priority comparison domains include W3C PROV, cryptographic/transparency logs, digital forensics and chain of custody, event sourcing, software supply-chain provenance, trusted execution/attestation, distributed systems, AI accountability/provenance, autonomous-system assurance, cyber-physical systems, and formal verification.

## Reproducibility levels

Use these levels:

- `R0 undocumented` — insufficient material to repeat.
- `R1 repeatable-internal` — original team can repeat with preserved instructions.
- `R2 packaged` — code/data/configuration and procedure are packaged for third parties.
- `R3 independently-reproduced` — an independent party has reproduced the result.
- `R4 independently-challenged` — independent work has tested boundary/failure cases in addition to reproduction.

## Impact evidence

Maintain evidence of impact separately from popularity metrics. Stronger forms include independent citations, adoption, implementation, standards discussion, invited scholarly/technical review, external reproduction, or use of ETS-derived methods in other work.

GitHub stars, page views, social engagement, or self-authored media may be retained as context but should not be represented as scholarly impact without qualification.
