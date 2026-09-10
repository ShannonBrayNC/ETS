# EXP-001 Independent Reviewer Handoff

**Status:** reviewer-ready; no certification completed  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Purpose

Provide an independent reviewer with a self-contained procedure for determining whether each EXP-001 scenario preserves the same reconstruction-material facts across the three frozen representation conditions.

This review is a pre-execution validity gate. It is not participant evaluation, outcome scoring, peer review of the scientific contribution, or approval of the experiment as a whole.

## Independence requirement

The reviewer should not be the sole author of the scenario corpus or rendered packet set. A reviewer may know the study purpose, but should evaluate fact equivalence against the frozen inventory rather than judging which condition is preferable.

If only the author performs the review, the result must remain `AUTHOR-ONLY / NOT CONFIRMATORY READY` and does not satisfy the independent-review gate.

## Materials to review

For each scenario S01-S12, review:

- the frozen fact inventory in `EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`;
- Format M rendered packet;
- Format R rendered packet;
- Format K rendered packet;
- the authoritative packet SHA-256 manifest;
- the corresponding blank certification form under `exp001-equivalence/forms/`.

The evaluator-facing M/R/K labels are intentionally opaque. The reviewer need not infer or report which format corresponds to which internal condition in the completed form.

## Review objective

Determine whether a reasonable evaluator could obtain any reconstruction-material fact from one representation that is unavailable in another, excluding the representation semantics that constitute the experimental manipulation.

Expected experimental differences may include syntax, relationship vocabulary, grouping, domain labels, explicit verification boundaries, and epistemic treatment. Those differences are not automatically factual inequivalence.

## Mandatory checks

For every scenario, verify all 12 checks defined in `EXP-001_EQUIVALENCE_CERTIFICATION.md`:

1. every reconstruction-material fact appears in all three formats;
2. no format adds a material fact absent from the frozen inventory;
3. unknown, unavailable, indeterminate, or contradictory facts are not silently resolved;
4. timestamps are not upgraded to independently trusted time;
5. identity is not converted into authority and authority is not converted into standing;
6. request or acknowledgment is not converted into execution;
7. execution is not converted into consequence/result observation without evidence;
8. source dependence is preserved;
9. contradictions are preserved;
10. evidence absence is not converted into event absence without coverage evidence;
11. wording does not add causal or truth claims;
12. formatting does not materially privilege a condition beyond the intended semantic manipulation.

## Materiality rule

Treat a difference as material when it could reasonably change the substantive reconstruction conclusion because one format contains a fact, certainty level, temporal claim, causal implication, authority claim, result claim, or source-independence claim not supported by the other formats.

Do not mark a difference material merely because one format makes a boundary more explicit; explicit boundary semantics are part of the experimental variable.

## Allowed certification results

Use exactly one result per scenario:

- `PASS`
- `FAIL`
- `PASS-WITH-DOCUMENTED-NONMATERIAL-DIFFERENCE`

A `FAIL` blocks confirmatory use of that scenario until corrected prospectively. If correction changes a frozen packet, the packet manifest must be regenerated and the change documented before evaluator exposure.

## Review workflow

For each scenario:

1. verify the three packet filenames and hashes against the authoritative manifest;
2. read the frozen fact inventory for that scenario;
3. compare Format M to the inventory;
4. compare Format R to the inventory;
5. compare Format K to the inventory;
6. compare the three formats directly for added/omitted material facts;
7. complete all 12 checks;
8. record material non-factual differences separately;
9. record unresolved concerns;
10. select and attest the final result.

Do not edit the rendered packets during review.

## Reviewer record

Each completed form should contain:

- reviewer identity or stable reviewer code;
- independence basis;
- review date;
- result;
- notes for every failed or qualified check;
- corrective action required, if any;
- signature or attestation method.

The repository may retain a reviewer code instead of a public real name if the governing institution requires or prefers identity minimization, provided the investigator can demonstrate reviewer independence when required.

## Handling disagreement

If two reviewers disagree, preserve both original reviews. Do not erase a dissenting review. Resolve disagreement prospectively through documented adjudication or an additional independent review before confirmatory exposure.

The adjudication record should distinguish:

- factual-equivalence disagreement;
- interpretation of materiality;
- intended semantic manipulation;
- packet-formatting concern;
- possible scoring-key ambiguity.

## Security and integrity

Reviewers should use the committed repository artifacts or a cryptographically verified export. Any local copy used for review should be traceable to the authoritative packet manifest and repository commit.

Do not substitute manually edited packet copies for the frozen artifacts.

## Completion gate

The independent-review gate is complete only when all 12 scenario forms have an acceptable independent result and no unresolved `FAIL` remains.

Completion of this gate does **not** authorize evaluator recruitment by itself. The institutional human-subjects gate must also be satisfied.

## Handoff checklist

- [ ] Reviewer independence established.
- [ ] Authoritative packet manifest verified.
- [ ] S01 reviewed and form completed.
- [ ] S02 reviewed and form completed.
- [ ] S03 reviewed and form completed.
- [ ] S04 reviewed and form completed.
- [ ] S05 reviewed and form completed.
- [ ] S06 reviewed and form completed.
- [ ] S07 reviewed and form completed.
- [ ] S08 reviewed and form completed.
- [ ] S09 reviewed and form completed.
- [ ] S10 reviewed and form completed.
- [ ] S11 reviewed and form completed.
- [ ] S12 reviewed and form completed.
- [ ] Any disagreements/adjudications preserved.
- [ ] No unresolved FAIL remains.

**This handoff document does not itself certify any scenario.**
