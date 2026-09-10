# Part VI — Research Integrity as Part of the Evidence

Evidence Architecture is a research program about preserving boundaries in evidence. The doctoral work has to apply the same discipline to itself.

That begins with the difference between prospective and retrospective records.

A prospective hypothesis is documented before the relevant outcomes are observed. A retrospective reconstruction is created after earlier engineering work and uses dated or immutable evidence to explain what was done.

Retrospective work is legitimate. It becomes misleading only when it is presented as if it were preregistered.

EA-C001 and EA-C002 are explicitly recorded as retrospective candidate contributions. EXP-001 is a prospective experiment registered before evaluator data.

## Negative results are first-class research records

The methodology requires preservation of failed experiments, failed hypotheses, counterexamples, anomalies, null results, inconclusive results, and unsupported cases.

A result that narrows a contribution can improve the research.

This is especially important for a project that also has a product identity. Product development tends to reward success stories. Doctoral research has to preserve disconfirming evidence.

The experiment preregistration therefore lists negative outcomes in advance. No meaningful difference among A, B, and C must be reported. Condition B performing as well as C must be reported. C increasing confusion or time cost must be reported. Benefits restricted to one evaluator group must be reported. Poor scoring agreement must be reported.

Those outcomes are not defects to hide. They are possible answers to the research question.

## The failed packet manifest as a worked example

The packet-freeze discrepancy is a useful example of the integrity standard.

An initial expected hash manifest failed to reproduce the bytes generated from the committed source and renderer. The repository preserved the failed manifest and the discrepancy record.

Later, before evaluator exposure, the source and renderer were regenerated twice. Both passes produced thirty-six packets with identical hash sets. The new authoritative manifest superseded the earlier one for operational packet use. The old one was not deleted.

This creates a transparent history of the correction and prevents the research narrative from pretending that the first freeze succeeded when it did not.

The correction was prospective because no evaluator data existed. If the same change had been made after outcome data were observed, the confirmatory status could be affected under the preregistration amendment rule.

## Claims must remain typed by evidence class

The repository distinguishes engineering verification, formal evidence, research experiments, and external reproduction.

A unit test can demonstrate implementation behavior. A model checker can establish a bounded property under stated assumptions. A participant experiment can evaluate a hypothesis. An independent reproduction can test whether another party obtains the result.

These are different evidence classes.

The formal ETS materials include implemented or bounded claims about canonical event hash determinism, append-only behavior, omission relative to expectation, fork suspicion, asynchronous-network classification, and fairness-scoped liveness.

Those properties should be narrated at their actual scope. Fairness-scoped liveness depends on weak fairness and eventual removal of partition or adversarial pressure. It is not Internet-scale adversarial liveness. Omission detection depends on an external expected-event set. It is not proof of global completeness. A Bayesian verifier-reliability model is statistical, not an adversarial correctness proof.

No formal artifact proves real-world truth, legal sufficiency, private-key uncompromisability, Byzantine consensus, or election correctness.

## Reproducibility has levels

The research framework distinguishes levels from undocumented work through repeatable internal work, packaged work, independent reproduction, and independent challenge.

A repository that its own author can rerun is not the same as a result reproduced by another researcher. Independent reproduction is also not the same as independent challenge of failure boundaries.

The strongest research program therefore needs outsiders who can reproduce, criticize, and attack the assumptions.

## The self-referential standard

There is a useful way to state the integrity rule:

The doctoral program should be able to produce evidence about its own claims with the same refusal to overstate that it asks operational systems to follow.

If a gate is pending, preserve pending.

If approval does not exist, do not say approved.

If a hash freeze failed first, preserve the failure.

If code does not yet match a frozen metric definition, record the discrepancy before execution.

If a candidate contribution is weakened by prior art, narrow the claim.

Research integrity is not administrative overhead around Evidence Architecture. It is Evidence Architecture applied to the research process itself.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/METHODOLOGY_AND_RESEARCH_INTEGRITY.md`
- `docs/research/phd/EXPERIMENT_LEDGER.md`
- `docs/research/phd/EXP-001_PREREGISTRATION.md`
- `docs/research/phd/exp001-packets/PACKET_FREEZE_DISCREPANCY.md`
- `docs/research/phd/EXP-001_PACKET_FREEZE_RESOLUTION.md`
- `docs/research/FORMAL_MODEL_CLAIMS.md`
- `docs/research/FORMAL_TRACEABILITY_MATRIX.md`
- `docs/research/FORMAL_THEOREMS.md`
- `docs/research/REPRODUCIBILITY_APPENDIX.md`
