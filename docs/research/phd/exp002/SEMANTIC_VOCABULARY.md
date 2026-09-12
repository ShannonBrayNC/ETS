# EXP-002 Frozen Semantic Vocabulary

**Experiment:** EXP-002 — RATS Equivalence / Dimensional Verification Falsification  
**Status:** FROZEN PRE-EXECUTION VOCABULARY  
**Freeze date:** 2026-09-12  
**Change rule:** any semantic change after merge requires a documented protocol amendment before execution.

## Purpose

This vocabulary fixes the semantic distinctions that EXP-002 will test. It does not assume that Evidence Architecture owns or uniquely expresses any term. The experiment asks whether a rich RFC 9334 RATS profile can preserve materially equivalent distinctions without importing additional normative rules equivalent to Evidence Architecture's non-collapse discipline.

## Canonical verification dimensions

Each dimension is independent unless an explicit rule states otherwise. Success in one dimension MUST NOT automatically promote another dimension.

| ID | Dimension | Canonical meaning | Explicit nonclaim |
|---|---|---|---|
| D01 | `STRUCTURAL_INTEGRITY` | The object/message satisfies the frozen schema/canonicalization rules applicable to the condition. | Does not establish semantic truth. |
| D02 | `CRYPTOGRAPHIC_INTEGRITY` | Required digest/signature/MAC checks succeed under the declared trust material. | Does not establish source correctness, authority, completeness, or consequence. |
| D03 | `PRODUCER_IDENTITY` | The producer/attester/signer is identified under the declared identity/trust model. | Identity does not imply authorization or truthfulness. |
| D04 | `PROVENANCE_DERIVATION` | Declared source/derivation relationships are preserved and traceable. | A traceable derivation may still begin from a false or uncertain observation. |
| D05 | `CUSTODY_CONTINUITY` | Required custody/transfer history is represented and satisfies the frozen custody rules. | Custody does not establish truth or action-time standing. |
| D06 | `FRESHNESS_CURRENTNESS` | Evidence/results satisfy the frozen temporal freshness/currentness requirement. | Fresh evidence may still be false, incomplete, or unauthorized. |
| D07 | `AUTHORITY_POLICY` | The action/decision is associated with relevant policy/authority material. | Association alone does not prove that authority was valid at the relevant time. |
| D08 | `HISTORICAL_STANDING` | The required authorization/policy predicates are supported as valid at the action/decision time. | Standing does not prove execution or consequence. |
| D09 | `SCOPED_COMPLETENESS` | Required evidence expected within the declared scope is present or omission is detectably bounded by expectation evidence. | Does not imply universal completeness outside the declared scope. |
| D10 | `REQUESTED_ACTION` | Evidence supports that an action/command was requested or issued. | Does not prove acceptance, execution, or result. |
| D11 | `EXECUTED_ACTION` | Evidence supports that the requested/accepted action was executed to the declared execution boundary. | Does not by itself prove external/physical consequence. |
| D12 | `RESULT_OBSERVATION` | Evidence supports an observation of the resulting external/digital/physical state. | Observation may be incorrect, incomplete, delayed, or sensor-dependent. |
| D13 | `CONSEQUENCE_LINKAGE` | The evidence package supports a bounded linkage from execution to an observed resulting state under declared assumptions. | Does not establish universal causality or semantic truth beyond the bounded claim. |
| D14 | `VERIFIER_TRUST` | The verifier and its policy/trust basis satisfy the frozen trust assumptions. | A trusted verifier does not make false input claims true. |
| D15 | `POLICY_FRESHNESS` | The appraisal/authorization policy used was the intended version effective for the evaluated event. | A current policy does not retroactively establish historical standing. |
| D16 | `NONCLAIM_DISCIPLINE` | Unsupported dimensions remain explicitly unsupported rather than being inferred from success elsewhere. | No implicit promotion from integrity, identity, provenance, or authorization to truth/consequence is permitted. |

## Canonical epistemic states

Every material conclusion must resolve to exactly one of the following states under the applicable condition:

- `SUPPORTED` — positive support exists under the frozen rules.
- `ASSERTED` — a claim is present but lacks sufficient independent support for `SUPPORTED`.
- `UNKNOWN` — available evidence is insufficient to decide.
- `NOT_AVAILABLE` — required evidence is known to be unavailable.
- `INDETERMINATE` — evidence exists but the frozen rules cannot resolve the claim.
- `CONTRADICTED` — materially conflicting evidence prevents an unqualified positive conclusion.
- `NOT_OBSERVED` — the relevant event/state was not observed by the declared observation process.
- `NOT_APPLICABLE` — the dimension does not apply to the scenario and this is explicitly justified.

`false`, `missing`, and `unknown` are not interchangeable.

## Action/consequence stage vocabulary

The experiment fixes the following stage order without asserting that every scenario contains every stage:

`Observation -> Inference -> Decision -> Authority/Standing -> Requested Action -> Accepted Action -> Executed Action -> Result Observation -> Consequence Claim`

### Non-collapse rules

1. `Decision` MUST NOT imply `Requested Action`.
2. `Requested Action` MUST NOT imply `Accepted Action`.
3. `Accepted Action` MUST NOT imply `Executed Action`.
4. `Executed Action` MUST NOT imply `Result Observation`.
5. `Result Observation` MUST NOT imply semantic correctness of the observation.
6. `Authority/Standing` MUST NOT imply execution or consequence.
7. `CRYPTOGRAPHIC_INTEGRITY` MUST NOT imply any later-stage state.
8. `PRODUCER_IDENTITY` MUST NOT imply `HISTORICAL_STANDING`.
9. `PROVENANCE_DERIVATION` MUST NOT imply independent corroboration where sources are shared.
10. Absence of evidence MUST NOT be promoted to evidence of absence unless an expectation model makes the omission detectable within declared scope.

## Claim trace requirements

Every final bounded conclusion must identify:

- conclusion identifier;
- epistemic state;
- semantic dimension(s);
- source evidence identifiers;
- policy/appraisal identifiers;
- trust assumptions;
- unsupported dependencies/nonclaims;
- scenario timestamp or relevant event-time interval when applicable.

## RATS neutrality rule

Condition R may encode these same factual distinctions using ordinary RATS Claims, Endorsements, Reference Values, Evidence, Attestation Results, Appraisal Policies, and application-specific namespaces. The comparison MUST NOT penalize RATS for different terminology.

A distinction counts as an Evidence Architecture-specific residual only when materially equivalent semantics cannot be achieved under the frozen RATS condition without adding an extra normative rule/profile classified by the equivalence rubric.

## Freeze boundary

The vocabulary is frozen for EXP-002 once merged. Clarifying examples may be added only if they do not change classification criteria. Any addition/removal/semantic redefinition of a dimension, epistemic state, or non-collapse rule requires a preregistration amendment committed before scenario execution begins.
