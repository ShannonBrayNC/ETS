# EXP-003 Non-Collapse Calculus v0

**Status:** DESIGN INPUT — NOT FROZEN FOR EXECUTION  
**Date:** 2026-09-12

This document defines the first machine-oriented semantics for EXP-003. It is intentionally conservative. The purpose is not to maximize what the verifier can conclude; the purpose is to make every cross-boundary conclusion explicit, attributable to a rule, and falsifiable.

## 1. Core proposition classes

The calculus begins with separately typed proposition classes:

- `STRUCTURAL_VALID(P)`
- `INTEGRITY_VALID(P)`
- `PRODUCER_IDENTIFIED(P, A)`
- `SOURCE_PROVENANCE(P, S)`
- `FRESH_AT(P, T)`
- `AUTHORITY_VALID(A, X, T)`
- `STANDING_VALID(A, X, T)`
- `REQUESTED(X, T)`
- `EXECUTED(X, T)`
- `RESULT_OBSERVED(R, T, O)`
- `CONSEQUENCE_SUPPORTED(X, R, T)`
- `EXPECTATION(E, T)`
- `OMISSION_SUPPORTED(E, T)`
- `INDEPENDENT_SOURCE(S1, S2)`
- `VERIFIER_TRUSTED(V, T)`
- `POLICY_APPLICABLE(POL, T)`
- `DERIVED_FROM(P1, P2)`
- `CONTRADICTS(P1, P2)`

`X` is an action/operation, `A` an actor/principal, `R` a resulting state, `O` an observer, `S` a source/provenance root, `POL` a policy and `T` an event-relevant time.

The exact machine representation may change before freeze, but semantic types must remain separable.

## 2. Epistemic states

A proposition may be represented with one of the following states:

- `SUPPORTED`
- `ASSERTED`
- `UNKNOWN`
- `NOT_AVAILABLE`
- `NOT_OBSERVED`
- `INDETERMINATE`
- `CONTRADICTED`
- `NOT_APPLICABLE`

A proposition that is absent from a package is not automatically `FALSE`.

A future machine-readable version may add an explicit `FALSE` only when falsity is itself supported by evidence or a closed-world rule that is declared in advance.

## 3. Primitive support rule

A direct evidence item may support only the proposition types explicitly declared by its frozen evidence interpretation.

For example, a valid signature over a claim may support:

- `INTEGRITY_VALID(claim)`;
- `PRODUCER_IDENTIFIED(claim, signer)` under the declared trust model;

but does not by itself support the semantic truth of the signed claim.

Every primitive support mapping must be visible in the rule/adapter manifest.

## 4. Non-collapse prohibitions

The following are **invalid inference forms** unless a separate positive rule supplies the missing premises.

### NC-01 — Integrity -> truth

Invalid:

`INTEGRITY_VALID(P) => P is semantically true`

Integrity supports integrity and attribution only.

### NC-02 — Identity -> authority

Invalid:

`PRODUCER_IDENTIFIED(P, A) => AUTHORITY_VALID(A, X, T)`

Identity does not imply permission.

### NC-03 — Current authority -> historical standing

Invalid:

`AUTHORITY_VALID(A, X, now) => STANDING_VALID(A, X, Tpast)`

Historical standing requires event-time policy/delegation premises.

### NC-04 — Fresh message -> fresh policy/source state

Invalid:

`FRESH_AT(evidence, T) => POLICY_APPLICABLE(policy, T)`

Invalid:

`FRESH_AT(attestation, T) => reference values/current source state are fresh`

Freshness is typed by object and basis.

### NC-05 — Request -> execution

Invalid:

`REQUESTED(X, T) => EXECUTED(X, T)`

### NC-06 — Execution -> result observation

Invalid:

`EXECUTED(X, T1) => RESULT_OBSERVED(R, T2, O)`

### NC-07 — Result observation -> consequence

Invalid:

`RESULT_OBSERVED(R, T2, O) => CONSEQUENCE_SUPPORTED(X, R, T2)`

### NC-08 — Agreement -> independence

Invalid:

`P1 agrees with P2 => INDEPENDENT_SOURCE(S1, S2)`

Independence requires provenance-root evidence.

### NC-09 — Missing evidence -> event absence

Invalid:

`no record for E => E did not occur`

A bounded omission conclusion requires an expectation/coverage premise.

### NC-10 — Unknown-state collapse

Invalid conversions without evidence:

- `UNKNOWN => FALSE`
- `NOT_AVAILABLE => FALSE`
- `NOT_OBSERVED => FALSE`
- `INDETERMINATE => FALSE`
- `CONTRADICTED => arbitrary selected truth`

### NC-11 — Source validity -> verifier trust

Invalid:

`source evidence valid => VERIFIER_TRUSTED(V, T)`

### NC-12 — Provenance/sequence -> causality

Invalid:

`DERIVED_FROM/preceded_by/adjacent_to => caused_by`

## 5. Positive rules — initial form

The calculus must contain positive rules so it does not win by refusing inference.

### R-AUTH-01 — Event-time standing

A bounded standing conclusion may be supported when all required premises are present:

1. actor identity is supported;
2. the relevant authority/delegation artifact is supported;
3. the applicable policy is identified;
4. the policy/delegation is effective at event time;
5. the requested action is within scope;
6. no higher-priority contradiction/revocation premise invalidates the authorization.

Output:

`STANDING_VALID(A, X, T)`

### R-EXEC-01 — Execution

Execution may be supported when an execution-specific evidence source asserts execution and that evidence passes the declared integrity/identity/trust checks required by the profile.

A command receipt alone is insufficient unless the profile explicitly defines that receipt as execution evidence and the experiment oracle agrees that this is a valid execution source.

Output:

`EXECUTED(X, T)`

### R-RESULT-01 — Result observation

A resulting state may be supported when an observation-specific evidence item reports the state and satisfies the declared integrity/identity/time/observer requirements.

Output:

`RESULT_OBSERVED(R, T, O)`

This rule does not produce `CONSEQUENCE_SUPPORTED`.

### R-OMISSION-01 — Bounded omission

A bounded omission conclusion may be supported when:

1. an explicit expectation/coverage rule requires evidence/event E;
2. the expectation applies to the relevant scope/time;
3. the observed sequence/coverage evidence proves a missing required slot or artifact;
4. the conclusion is limited to the expected evidence/event scope.

Output:

`OMISSION_SUPPORTED(E, T)`

### R-INDEP-01 — Independent corroboration

Two claims may be treated as independently corroborating only when their provenance roots are shown to be independent under the frozen independence model.

Common ingestion through a later shared collector does not necessarily destroy source independence, while two different reports derived from one upstream sensor do not create independence.

### R-CONSEQ-01 — Bounded consequence support

A consequence claim is the most restrictive positive rule in v0.

At minimum it requires:

1. `EXECUTED(X, T1)`;
2. `RESULT_OBSERVED(R, T2, O)` where `T2` is within the declared consequence window;
3. provenance/custody for the result observation sufficient to distinguish it from the action-originating self-report where the scenario requires independence;
4. no unresolved contradiction that defeats the result proposition;
5. no declared alternative-explanation condition that makes causal attribution indeterminate under the scenario model;
6. an explicit scenario/domain rule specifying that these premises are sufficient for the bounded causal/consequence conclusion being tested.

Output:

`CONSEQUENCE_SUPPORTED(X, R, T2)`

This rule deliberately does not claim universal causal inference. The sufficiency rule is scenario/domain bounded and is itself part of the evidence model.

## 6. Contradiction handling

If two independently supported propositions are materially incompatible and no frozen precedence/adjudication rule resolves them, the affected proposition state becomes `CONTRADICTED` or `INDETERMINATE`.

The verifier must preserve both support traces.

A signature, trust level, source count, or recency difference may resolve the conflict only when a frozen rule explicitly makes that property decisive.

## 7. Support-trace requirement

Every nonprimitive `SUPPORTED` conclusion must emit a support trace containing:

- conclusion proposition/type;
- rule ID;
- premise IDs;
- source/provenance roots;
- applicable policy IDs;
- event-time basis;
- trust assumptions;
- unresolved nonclaims/limitations.

A conclusion without a valid support trace is classified as an unsupported promotion in EXP-003.

## 8. Monotonicity goal and exceptions

Where practical, adding valid supporting evidence should not invalidate an unrelated supported proposition.

However, newly introduced contradiction, revocation, stale-policy evidence or source-dependence evidence may legitimately downgrade a prior conclusion. These are not monotonic additions in the epistemic sense because they change the support state.

The final formal model must distinguish ordinary support addition from defeaters.

## 9. Substrate-independence requirement

The rule system must be implementable without requiring the ETS Evidence Object schema.

Condition C of EXP-003 will deliberately encode the same semantics through a RATS+ profile.

If the RATS+ implementation cannot match Condition B, the reason must be documented at the exact rule/premise level rather than attributed to terminology.

## 10. What v0 does not establish

This design does not establish:

- originality;
- universal causal semantics;
- truth of source observations;
- legal evidentiary sufficiency;
- that independent observation is always required in every domain;
- that one evidence source cannot be sufficient when the threat model permits it;
- that all useful inference is monotonic;
- that the listed epistemic states are minimal or complete.

These remain research questions.

## 11. Freeze work remaining

Before EXP-003 confirmatory execution, convert v0 into machine-readable rules and freeze:

- proposition type schema;
- epistemic state schema;
- primitive evidence adapters;
- positive and prohibited inference rules;
- defeater/conflict semantics;
- independence model;
- consequence-window/causal-sufficiency model;
- support-trace schema;
- rule-version identifier and artifact hashes.
