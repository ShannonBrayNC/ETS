# Part V — EXP-001: The Experimental Design

EXP-001 is the Bounded Evidence Graph Reconstruction Comparison. It exists to test a narrow question.

When the underlying facts are held constant, does an Evidence Architecture representation with explicit bounded verification semantics reduce unsupported reconstruction conclusions compared with established provenance representations?

That is the experiment.

It does not ask whether Evidence Architecture contains more information. It does not ask whether ETS proves real-world truth. It does not ask whether Evidence Architecture is legally admissible. It does not test universal superiority over W3C PROV. It does not establish cryptographic novelty. And, at the current repository state, it has not been executed.

## The three conditions

Each of twelve factual scenarios is represented three ways.

For explanation in this listening edition, they are Conditions A, B, and C. Evaluators will not be shown those research labels. Their packets use opaque format labels so the names do not suggest which condition is expected to perform better.

Condition A is a baseline provenance representation. It uses ordinary W3C PROV-compatible concepts such as entities, activities, agents, generation, usage, derivation, attribution, association, delegation, revision, and time.

Condition A is not intentionally weakened by hiding facts. If a factual item does not map naturally to a first-class PROV relation, it can still appear as an attribute or associated entity. A weak baseline would prove very little.

Condition B is provenance plus ordinary domain extensions. It can explicitly represent authorization state, policy version, sensor availability, model output, action acceptance, physical observation, source dependence, contradiction, revocation, and quality metadata.

Condition B is deliberately strong. What it does not include is the Evidence Architecture normative discipline: no prescribed dimensional verification vector, no EA-specific epistemic vocabulary as a required semantic rule, no Standing Boundary rule, and no mandatory action-result non-collapse semantics.

Condition B therefore tests the most dangerous alternative explanation for a positive result: maybe the benefit comes simply from modeling the domain better.

Condition C is the Evidence Architecture representation. It contains the same substantive facts but makes relevant boundaries explicit: observation versus inference, integrity versus identity versus standing, historical standing versus current standing, evidence absence versus evidence of absence, source dependence, requested action versus accepted or executed action, consequence versus result observation, contradiction, time quality, and explicit nonclaims.

Condition C must not receive additional substantive evidence. If it does, that scenario is not valid for the primary confirmatory comparison.

## The factual-equivalence control

This is one of the most important controls in the study.

Imagine that Condition C performed better because its packet simply disclosed a sensor outage while another condition omitted that fact. That would not demonstrate a benefit from Evidence Architecture semantics. It would demonstrate a benefit from having more information.

To prevent that confound, every scenario has a frozen fact inventory. All three condition packages must preserve the reconstruction-material facts.

The independent equivalence reviewer is not asked which format is best. The reviewer asks whether a reasonable evaluator can obtain a material fact from one representation that is unavailable in another, excluding the semantic presentation differences that are the experimental variable.

That review is still pending. The author cannot satisfy the independent gate simply by certifying his own packets.

## Evaluator task

Each evaluator sees all twelve factual scenarios but only one representation condition for each scenario.

For every scenario, the evaluator answers the same six questions.

What events or states are directly supported?

What conclusions are inferred rather than directly observed?

Which actor or action had valid standing at the relevant time, if established?

What action was requested, what was executed, and what consequence or result was actually observed?

What material facts remain unknown, unavailable, contradictory, stale, or unverified?

And what is the strongest defensible overall conclusion without exceeding the evidence?

The evaluator also supplies a confidence rating from one to five, and response time may be recorded. The instructions explicitly permit “unknown,” “not established,” and “indeterminate.” That is part of the epistemic measurement.

## Randomization and balance

The preregistered target is at least twelve evaluators if feasible, with at least a technical or security stratum and a non-specialist but analytically competent stratum.

The assignment design uses twelve prospective evaluator slots. Each slot receives four scenarios in each of the three conditions. Across all twelve slots, each scenario appears four times in each format.

The base assignment is cyclic. In mathematical form, if e is the zero-based evaluator index and s is the zero-based scenario index, the condition index is e plus s, modulo three.

Spoken naturally: add the evaluator number to the scenario number and take the remainder after division by three.

A pseudorandom seed was frozen before outcome data existed. It determines scenario-order permutations and the opaque mapping between internal condition labels and evaluator-facing format labels. The exact seed and mapping are reference artifacts and do not need to be spoken aloud for comprehension.

The critical point is that assignments may not be adaptively changed after seeing performance. A replacement evaluator uses the next or corresponding pre-generated slot rather than a newly optimized assignment.

## Why the packets were frozen

The experiment has twelve scenarios and three representations per scenario, for thirty-six evaluator packets.

Those packets have now been deterministically materialized and frozen at the byte level.

This matters because pre-execution freezing prevents a researcher from quietly improving the preferred condition after seeing how evaluators respond.

The freeze is not evidence that the experiment worked. It is evidence that the inputs are controlled.

## The packet-hash discrepancy

The freeze process produced an important research-integrity event.

An early expected SHA-256 manifest did not match a regeneration of the committed packet source and renderer. In plain language, the repository had one set of expected digital fingerprints, but regenerating the packets from the committed source and generator produced different fingerprints.

The easy but unacceptable response would have been to overwrite the old expected hashes and move on.

Instead, the discrepancy was preserved as a historical record.

Because no evaluator had been exposed and no outcome data existed, a prospective correction remained possible.

The reconciliation procedure regenerated all thirty-six packets in a clean process, then regenerated them a second time. Both passes produced thirty-six packets. The two SHA-256 sets were identical.

That passed the deterministic-render gate.

A new authoritative hash manifest was created. The failed expected manifest remains in the repository as evidence of the unsuccessful first freeze.

This is the kind of behavior the research-integrity framework requires: preserve the failure, explain the correction, and avoid rewriting history.

## What the authoritative freeze does and does not mean

The authoritative packet freeze establishes byte reproducibility. It means the same frozen source and renderer reproduced the same packet bytes in two passes.

It does not establish fact equivalence across the three conditions. It does not certify scientific validity. It does not constitute independent review. It does not authorize human recruitment. It does not execute EXP-001.

The current artifact manifest therefore describes the internal deterministic work as substantially complete while keeping confirmatory evaluator exposure blocked on external gates.

Those external gates are the next major stage of the program.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/EXP-001_PREREGISTRATION.md`
- `docs/research/phd/EXP-001_CONDITION_PACKAGES.md`
- `docs/research/phd/EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`
- `docs/research/phd/EXP-001_EVALUATOR_INSTRUCTIONS.md`
- `docs/research/phd/EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md`
- `docs/research/phd/EXP-001_ASSIGNMENT_FREEZE.md`
- `docs/research/phd/EXP-001_ASSIGNMENT_MATRIX.md`
- `docs/research/phd/WP2_PACKET_FREEZE_RECONCILIATION.md`
- `docs/research/phd/exp001-packets/PACKET_FREEZE_DISCREPANCY.md`
- `docs/research/phd/EXP-001_PACKET_FREEZE_RESOLUTION.md`
- `docs/research/phd/EXP-001_ARTIFACT_MANIFEST.md`

The exact seed, hashes, blob identifiers, and format mapping are intentionally left to reference notes rather than narration.
