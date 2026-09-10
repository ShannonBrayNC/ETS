# Part VI — Measurement and Analysis

A good experiment does not merely state that one representation felt clearer. EXP-001 preregisters specific reconstruction errors. The analysis must preserve raw numerators and denominators, effect magnitude, uncertainty, and null results rather than reducing the study to a favorable p-value.

## Unsupported inference

In plain English, unsupported inference asks: how often did an evaluator state something stronger than the evidence justified?

Technically, the frozen scoring key labels substantive claims and identifies unsupported-inference errors. The preregistered rate is based on unsupported assertions relative to substantive assertions.

Examples include declaring that an underlying condition definitely occurred because two models produced elevated scores, or declaring that a device signature proves scene truth.

This metric is central because it measures the broad epistemic problem the architecture is intended to constrain.

## Standing collapse

Standing collapse happens when a verifier treats identity, signature, integrity, or inclusion as if it were sufficient authorization.

The expired-delegation scenario is the canonical example. The reviewer identity is valid. The record is signed. The high-value delegation is expired. If the evaluator concludes that the reviewer therefore had valid approval authority merely because identity and signature checked out, standing has collapsed into integrity.

Technically, the frozen scoring key defines the standing-collapse rate over scenarios containing a standing trap.

## Command-result collapse

This measures whether an evaluator treats intention, request, acknowledgment, or internal controller state as proof of later execution or consequence.

The accepted account-change request and the Ranger motion request are examples. Technically, the scoring key defines this rate over scenarios containing an action-stage trap.

The distinction matters because many APIs and controllers use success statuses for local operations that are not equivalent to real-world completion.

## False completeness

False completeness occurs when missing evidence is converted into proof that the underlying event or state did not exist.

The missing Finance approval scenario shows the risk. If capture was degraded, absence from the package cannot establish nonoccurrence. The unavailable east-enclosure sensor makes the same point in a different domain.

Technically, the scoring key defines the false-completeness rate over scenarios with missingness or observation-capability traps.

## Missed contradiction

A contradiction is valuable evidence when two material observations cannot both support the same simple interpretation.

If an account-change request is accepted but a later event shows the old access state still functioning, the later event challenges the assumption of completed execution. If a controller reports an expected state but an independent physical measurement remains inconsistent with that state, the physical observation contradicts the simple completion claim.

Missed-contradiction rate asks how often evaluators fail to identify such conflicts when they are present.

The key research principle is that contradictions should be preserved, not normalized away because one source appears more authoritative.

## Epistemic overstatement

Epistemic overstatement occurs when unknown, unavailable, or indeterminate evidence is converted into a positive or negative fact.

“No evidence of Finance approval” becomes “Finance did not approve.”

“Sensor C unavailable” becomes “no hazard existed.”

“Clock order uncertain” becomes “the valve definitely changed state first.”

The scoring key defines this rate relative to substantive assertions about unknown or unavailable states. This metric is closely related to unsupported inference, but it focuses on the treatment of uncertainty itself.

## Supported-claim precision

Supported-claim precision asks what proportion of the evaluator's asserted conclusions are actually supported under the frozen scoring rules.

Conceptually, this is a counterweight to a strategy of saying very little. A representation should not reduce errors merely by making evaluators unwilling to state anything. The study is interested in accurate bounded reconstruction, not maximal skepticism.

Condition C must therefore reduce core boundary errors without materially worsening supported-claim precision.

## Reconstruction time

Reconstruction time measures how long an evaluator takes to work through a scenario.

This is not cosmetic. A representation could reduce errors but impose extreme cognitive cost. Or it could be faster while encouraging overclaiming. The study records mean and median reconstruction time, while interpretation must consider the tradeoff between accuracy and effort.

## Secondary measures

The experiment also tracks source-dependence recognition. Did evaluators notice when two analytical outputs share one upstream source?

It tracks inference-versus-observation recognition. Did evaluators distinguish a model score from a directly observed fact?

It tracks stale-versus-current distinction. Did evaluators recognize that authentic historical policy or authority state can be stale?

It tracks time-quality recognition. Did evaluators recognize that precise signed timestamps do not automatically establish event ordering?

It tracks evaluator confidence. Confidence should ideally track evidentiary quality rather than familiarity with the domain.

And where responses are independently double-scored, the study evaluates inter-rater agreement. Poor scorer agreement is itself a research result. It may indicate ambiguous scenarios, ambiguous semantics, or an unstable scoring rubric.

## The confirmatory success criterion

The primary hypothesis is considered supported only if Condition C shows a lower aggregate rate than both A and B on at least three of four core boundary errors:

unsupported inference;

standing collapse;

action-result collapse;

and false completeness;

while not materially worsening supported-claim precision.

This threshold is intentionally stronger than Condition C beating the simplest baseline.

If C improves only over A but not B, ordinary domain extension may explain the effect. That would weaken the claim that Evidence Architecture's specific semantic discipline produced the benefit.

## What a null result means

A null result is not a failed research process.

If A, B, and C perform similarly, the data would not support the current claim that the EA-specific representation improves these reconstruction outcomes. The candidate contributions would need to narrow, change, or remain unresolved.

If B performs as well as C, the most direct interpretation is that ordinary domain-extended provenance may deliver the same practical reconstruction benefit in this experiment.

If C reduces errors but substantially increases reconstruction time, the tradeoff must be reported.

If benefits appear only in one evaluator stratum, generalization must be limited.

If some scenarios are already adequately represented by ordinary PROV, that negative finding should remain in the record.

If inter-rater agreement is poor, the scoring system itself may need reconsideration.

These outcomes are scientifically useful because they locate the boundary of the claim.

## A current pre-execution implementation-alignment item

The current repository contains both a frozen scoring key and an executable descriptive-analysis implementation.

The scoring key specifies trap-specific denominators for several rates. For example, standing collapse is defined over scenarios with a standing trap, and command-result collapse is defined over scenarios with an action-stage trap.

The current Python implementation, however, appears to calculate the denominator for each listed error metric using all substantive scored assertions.

That is a source-level implementation-alignment issue, not an experimental result.

No participant data have been collected. Therefore the discrepancy can still be reconciled prospectively before execution, with the correction documented and the frozen analysis intent preserved.

The important research-integrity rule is that the repository should not silently pretend the formulas and implementation are already identical if they are not.

Before EXP-001 executes, the analysis code and frozen metric definitions need a documented alignment decision so the implementation operationalizes the preregistered measures rather than redefining them after outcomes exist.

## Inferential statistics

Descriptive results are mandatory.

Inferential tests are optional and depend on sample size, matched structure, and observed data distribution. If inferential statistics are used, the analysis must state why the chosen test fits the repeated or matched design, how multiplicity is handled, and what effect size and uncertainty interval accompany the result.

A p-value below zero point zero five is not a substitute for evidentiary significance.

The experiment should be interpreted as a bounded evaluator study. It does not become a universal theorem about provenance or human reasoning.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/EXP-001_PREREGISTRATION.md`
- `docs/research/phd/EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`
- `docs/research/phd/EXP-001_ANALYSIS_SKELETON.md`
- `docs/research/phd/exp001-analysis/README.md`
- `docs/research/phd/exp001-analysis/exp001_analysis.py`

Pre-execution alignment note:
- The frozen scoring key uses trap-specific or proposition-specific denominators for SC, CR, FC, MC, and EO.
- The current `summarize_condition` implementation uses all non-`NOT_APPLICABLE` scored claims as the denominator for every error metric in `ERROR_FIELDS`.
- This listening edition records that discrepancy but does not modify canonical analysis files.
