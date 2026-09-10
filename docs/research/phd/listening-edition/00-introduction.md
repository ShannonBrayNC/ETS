# Part I — Introduction: How to Listen to This Research

This listening edition is a derivative narration of the doctoral research material in the ETS repository. It is designed for the author and principal researcher, Shannon W. Bray, to hear the research as a coherent argument before external review and before the first confirmatory evaluator study.

The most important fact to establish at the beginning is also the easiest fact to accidentally blur later: EXP-001 has not been executed. There are no participant responses, no experimental effect sizes, no confirmatory findings, and no statistical result from that study. The experiment has been preregistered and much of its pre-execution machinery has been frozen, but design is not outcome.

The two contributions at the center of EXP-001, EA-C001 and EA-C002, also remain candidate contributions. EA-C001 concerns the Evidence Object model. EA-C002 concerns the Evidence Graph model. Both have been narrowed through prior-art review. Neither should be narrated as established novelty simply because software exists, a schema is formalized, a test passes, or a repository contains substantial engineering work.

This distinction is central to the entire doctoral program.

There are several different kinds of things in the repository, and they have different evidentiary weight.

A proposed theory says what might be true and why it matters.

A formalized architecture states definitions, boundaries, invariants, or normative requirements.

An implemented engineering artifact shows that a particular design has been encoded in software or hardware.

A mathematical or formal result establishes a bounded property under stated assumptions.

A prior-art finding establishes that other researchers or standards already cover some idea, which may narrow the novelty claim.

A preregistered hypothesis states a prediction before outcome data are observed.

An unexecuted experiment describes a method that has not yet produced empirical evidence.

An empirical result exists only after the method is actually executed and the resulting data are analyzed.

These categories can support one another, but they are not interchangeable.

For example, ETS contains implementation and formal work around deterministic hashing, append-only behavior, omission detection relative to an external expectation set, bounded asynchronous behavior, and fairness-scoped liveness. Those are real engineering or formal artifacts. They do not, by themselves, prove that the Evidence Object or Evidence Graph is an original contribution to knowledge, and they do not answer the evaluator-comparison hypothesis in EXP-001.

The same discipline applies in the other direction. A future positive EXP-001 result would not make every ETS engineering claim true. EXP-001 is designed to test whether specific evidence-representation semantics reduce specific reconstruction errors when the underlying facts are held constant. It is not a proof of real-world truth, legal admissibility, universal superiority over W3C PROV, cryptographic novelty, or correctness of every ETS component.

Throughout this listening edition, the phrase “the evidence supports” is used intentionally. It is stronger than speculation and weaker than unrestricted truth.

That leads to the question organizing the research program:

When a system says something happened, what evidence allows an independent party to determine what was observed, inferred, authorized, decided, executed, consequential, preserved, and ultimately verifiable?

The rest of this edition develops that question in stages.

First, it explains why modern logs and provenance are often insufficient for high-consequence reconstruction.

Second, it explains the Evidence Architecture thesis: Evidence Objects, Evidence Graphs, epistemic states, standing, consequence-stage separation, and bounded verification.

Third, it confronts prior art and explicitly identifies what ETS cannot legitimately claim as new.

Fourth, it defines the remaining candidate contribution surface and the conditions under which those candidates should be strengthened, narrowed, or rejected.

Fifth, it walks through EXP-001 in enough detail to understand why its controls exist.

Sixth, it explains measurement, research integrity, independent equivalence review, and the unresolved human-subjects gate.

Finally, it explains what evidence is still missing before the work can be defended as a doctoral contribution rather than an ambitious software project.

One listening rule will help with everything that follows: whenever the word “verified” appears, ask, “Verified in what dimension, under what trust assumptions, at what time, and with what nonclaims?”

That question is the heart of Evidence Architecture.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/README.md`
- `docs/research/phd/RESEARCH_QUESTIONS.md`
- `docs/research/phd/CONTRIBUTION_LEDGER.md`
- `docs/research/phd/EXPERIMENT_LEDGER.md`
- `docs/research/phd/METHODOLOGY_AND_RESEARCH_INTEGRITY.md`
- `docs/research/FORMAL_MODEL_CLAIMS.md`
- `docs/research/FORMAL_TRACEABILITY_MATRIX.md`

Source baseline for this listening edition: `main` at commit `374c0ab32cd1ba0ffda1b75fa561fc075a60fd11`.
