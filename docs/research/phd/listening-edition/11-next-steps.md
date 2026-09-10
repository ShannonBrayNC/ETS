# Part VIII — What Happens Next

The next steps should occur in a controlled order because some gates depend on others.

## Gate One — independent fact-equivalence review

An independent reviewer should compare all twelve A, B, and C scenario triplets against the frozen fact inventory. Every scenario needs an acceptable result with no unresolved failure.

If a material inequivalence is found, the affected packets must be corrected prospectively before evaluator exposure. Any changed packet must be re-frozen and its authoritative hash history updated without deleting the earlier record.

The author can support the review, but cannot self-attest the independent gate.

## Gate Two — institutional human-subjects determination

The governing doctoral institution or research-oversight authority needs to provide a written determination for the planned evaluator study.

The repository already contains a submission packet, cover memo, and participant-information draft. Those are inputs to the determination. They are not substitutes for it.

The outcome may require consent language, participant information, training, privacy controls, retention rules, recruitment constraints, compensation rules, or another review pathway. Whatever the institution requires must be completed before recruitment.

## Gate Three — correct pre-execution control discrepancies

Any open control mismatch should be resolved before outcome data exist.

One current example is the analysis implementation's metric denominators versus the frozen scoring-key formulas.

The goal is not to choose whichever formula later produces a better result. The goal is to reconcile the executable analysis with the preregistered metric definitions prospectively, document the decision, and freeze the corrected implementation before participant data.

Independent equivalence review may reveal additional packet issues. Those also belong in this gate.

## Gate Four — final pre-execution repository freeze

Once independent equivalence and institutional requirements are satisfied, the repository should record the final pre-execution commit and all authoritative artifact references. The experiment ledger should then point to that exact frozen state.

From that point forward, substantive changes need amendment handling under the preregistration rules.

## Gate Five — evaluator recruitment

Only after the external gates are complete should evaluators be recruited.

The intended design uses adults and a balanced pool spanning technical or security participants and non-specialist but analytically competent participants.

Each participant receives a pre-generated slot. Assignments should not be optimized in response to early performance.

## Gate Six — execute EXP-001

Execution means collecting actual evaluator responses under the frozen protocol. Until this happens, there are no empirical results.

During collection, preserve incomplete sessions and protocol deviations rather than silently dropping inconvenient data. Raw response text should remain separate from later scoring.

## Gate Seven — scoring

Evaluator responses are decomposed into substantive claims and scored using the frozen labels and error taxonomy.

The independently double-scored subset should preserve both original scorer judgments. Disagreement should be adjudicated transparently rather than overwritten. Poor agreement should be reported.

## Gate Eight — analysis

Run the preregistered descriptive analysis first. Report raw numerators and denominators. Report reconstruction time and supported-claim precision. Evaluate the confirmatory success rule exactly as frozen.

If inferential statistics are justified, document the selected method, matched design, multiplicity treatment, effect size, and uncertainty. Do not select a test because it produces a favorable p-value.

## Gate Nine — publication

Publish the method and the result together. That includes negative findings, deviations, limitations, artifact provenance, and the effect of the strongest comparator.

A foundational Evidence Architecture paper should not describe candidate claims as established beyond what the data and prior art support.

## Gate Ten — replication and challenge

Package the study so another researcher can reproduce it. Then seek independent replication.

Eventually, stronger evidence comes from independent challenge: someone testing the failure boundaries, not merely repeating the happy path.

## Gate Eleven — evaluate EA-C001 and EA-C002

Only after prior art, empirical results, and external validation are available should the candidate contribution ledger be reconsidered.

A contribution may become supported. It may remain candidate. It may be revised. It may be refuted or retired.

The decision should follow the evidence.

The order matters because Evidence Architecture is not just a theory about operational records. The research program itself should preserve a verifiable lineage from question, to hypothesis, to method, to frozen artifact, to observation, to analysis, to claim.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/EXP-001_ARTIFACT_MANIFEST.md`
- `docs/research/phd/EXP-001_EQUIVALENCE_CERTIFICATION.md`
- `docs/research/phd/EXP-001_INDEPENDENT_REVIEWER_HANDOFF.md`
- `docs/research/phd/EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md`
- `docs/research/phd/EXP-001_INSTITUTIONAL_REVIEW_PACKET.md`
- `docs/research/phd/EXP-001_PREREGISTRATION.md`
- `docs/research/phd/EXP-001_ANALYSIS_SKELETON.md`
- `docs/research/phd/METHODOLOGY_AND_RESEARCH_INTEGRITY.md`
