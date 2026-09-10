# EXP-001 Fact-Equivalence Certification

**Status:** required pre-execution gate  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Purpose

Prevent the primary comparison from being confounded by one representation condition containing more substantive evidence than another.

Each of the 12 scenarios requires a completed certification before evaluator exposure.

## Certification unit

One certification covers one scenario across all three frozen representations.

Record:

- scenario ID;
- Condition A artifact path/hash;
- Condition B artifact path/hash;
- Condition C artifact path/hash;
- frozen fact-inventory path/hash;
- reviewer identity or reviewer code;
- review date;
- result: PASS / FAIL / PASS-WITH-DOCUMENTED-NONMATERIAL-DIFFERENCE.

## Mandatory checks

The reviewer SHALL verify:

1. every reconstruction-material fact ID appears in all three conditions;
2. no condition adds a reconstruction-material fact absent from the fact inventory;
3. no condition silently resolves an unknown, unavailable, indeterminate, or contradictory fact;
4. no condition converts a local/claimed timestamp into independently trusted time;
5. no condition converts identity into authority or authority into current standing;
6. no condition converts a requested command or acknowledgment into execution;
7. no condition converts execution into consequence or result observation without explicit evidence;
8. source dependence is factually preserved;
9. contradictions are preserved;
10. evidence absence is not converted into underlying event absence unless expectation/coverage evidence exists;
11. wording differences do not add causal or truth claims;
12. evaluator-facing formatting does not materially privilege one condition.

## Materiality test

A difference is material if a reasonable evaluator could reach a reconstruction conclusion from that difference that could not be reached from the other conditions.

Differences in syntax, relationship vocabulary, grouping, labels, or explicit semantic boundaries are expected experimental differences and are not automatically material factual differences.

## Failure rule

A FAIL blocks that scenario from confirmatory use.

Correction is allowed only before evaluator exposure. After any evaluator has seen the scenario, substantive correction requires an amendment and the affected data become exploratory unless a new prospective run is established.

## Independence target

The scenario author SHOULD NOT be the sole equivalence reviewer. Prefer at least one reviewer who did not author the scenario packet.

If no independent reviewer is available before an internal dry run, mark the certification `AUTHOR-ONLY / NOT CONFIRMATORY READY`.

## Certification template

```text
Scenario:
Fact inventory hash:
Condition A hash:
Condition B hash:
Condition C hash:
Reviewer:
Date:
Result:

Checks 1-12:
1. PASS/FAIL — notes
2. PASS/FAIL — notes
...
12. PASS/FAIL — notes

Material non-factual differences:
Unresolved concerns:
Corrective action required:
Signature/attestation method:
```

## Current state

No scenario is yet certified by an independent reviewer. Therefore EXP-001 remains NOT READY FOR CONFIRMATORY EXECUTION.
