# EXP-002 Rich-RATS Baseline Adversarial Review

**Status:** PRE-EXECUTION REVIEW GATE  
**Purpose:** prevent EXP-002 from winning by comparing Evidence Architecture against an artificially weak RFC 9334 RATS implementation.

## Reviewer mission

Assume the role of a technically sophisticated RATS/attestation implementer whose goal is to **collapse every alleged ETS distinction into ordinary RATS architecture or a reasonable application profile**.

The reviewer should not attempt to validate ETS. The reviewer should try to falsify its differentiation.

## Required challenges

For every frozen semantic dimension and every scenario family, attempt to show that Condition R can achieve materially equivalent semantics using:

- rich Evidence Claims;
- Endorsements;
- Reference Values;
- freshness/recentness mechanisms;
- multiple Attesters where warranted;
- multiple Verifiers where warranted;
- rich Attestation Results rather than booleans;
- Appraisal Policy for Evidence;
- Appraisal Policy for Attestation Results;
- application-specific claim namespaces;
- event timestamps and policy-effective intervals;
- source/derivation identifiers;
- explicit uncertainty or availability claims;
- relying-party authorization logic.

## Prohibited weakening of Condition R

Do not:

- reduce RATS output to PASS/FAIL if richer Attestation Results are reasonable;
- prohibit application-specific Claims;
- prohibit historical timestamps or policy versioning;
- prohibit multiple evidence sources;
- assume one Attester or one Verifier when multiple roles are justified;
- prevent the Relying Party from applying its own policy;
- treat RFC 9334 terminology differences as inability to represent a concept;
- deny RATS ordinary extensibility merely because a claim is not named by the base architecture.

## Extra-rule boundary

The reviewer must identify when a proposed RATS solution stops being an ordinary application profile and begins to add a normative rule specifically needed to reproduce the frozen non-collapse semantics.

Each such rule must be written explicitly in the review record and classified against the equivalence rubric.

Examples of potentially extra rules include mandatory prohibitions such as:

- integrity success MUST NOT support historical standing;
- command issuance MUST NOT satisfy execution;
- execution MUST NOT satisfy resulting-state observation;
- missing evidence MUST be distinguished from false, not-observed, and known-unavailable states;
- two claims sharing one upstream source MUST NOT count as independent corroboration.

The existence of such a rule is not automatically favorable to ETS; the reviewer should search for equivalent established RATS/profile/attestation practice first.

## Scenario review checklist

For each of S01–S20 record:

1. Can Condition R represent all source facts?
2. Can it preserve all decision-relevant epistemic states?
3. Can it preserve historical event time and policy-effective time?
4. Can it distinguish identity from authority/standing?
5. Can it distinguish request, acceptance, execution, and result observation?
6. Can it represent contradictions without arbitrary promotion?
7. Can it represent shared-source dependence?
8. Can it distinguish undetectable omission from bounded detectable omission?
9. Can it preserve verifier trust and policy freshness as separate concerns?
10. Does it need an extra normative rule to reach the same bounded conclusion as Condition E?

## Deliverable

The adversarial review must produce a table with:

- scenario ID;
- challenged dimension;
- proposed strongest RATS encoding;
- relevant RFC/profile/standard basis if known;
- extra rule required (`NONE` if none);
- provisional equivalence class;
- unresolved issue;
- reviewer identity/date.

## Pass condition for execution gate

EXP-002 may proceed to semantic comparison only after:

- every scenario has a documented strongest-RATS construction or unresolved challenge;
- obvious artificial limitations on Condition R have been removed;
- any R+ extra rules are explicit;
- the reviewer confirms that the comparison is not knowingly using a straw-man RATS profile.

This gate does not require the reviewer to agree with Evidence Architecture or its research claims.
