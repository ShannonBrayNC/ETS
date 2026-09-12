# Post-RATS Thesis Narrowing

**Status:** provisional research-position update  
**Date:** 2026-09-12  
**Trigger:** W3C PROV qualification, EXP-002 strongest-RATS internal red-team, and 2026 emerging RATS/action-evidence prior art

## Purpose

This document records a deliberate narrowing of the doctoral thesis surface before confirmatory experimentation. It is not a declaration that the remaining claims are original or supported. It exists to prevent the application and publication program from continuing to repeat contribution language that the current prior-art record has already placed under material pressure.

## What has changed

The early Evidence Architecture framing placed substantial emphasis on the Evidence Object, dimensional verification, machine-action provenance and a typed Evidence Graph as candidate contributions.

The current prior-art and adversarial record requires a narrower position.

W3C PROV already supplies rich provenance relations and qualified provenance. RFC 9334 RATS already supplies Evidence, Attesters, Verifiers, appraisal policy, Attestation Results, freshness, trust assumptions and independent Relying Party policy. Rich application profiles can add domain-specific Claims, historical timestamps, source identifiers, authority information, uncertainty states and action/result fields. Current 2026 RATS work further explores behavioral evidence, action/authority/outcome composition and attested inference receipts.

The internal EXP-002 red-team therefore attempted to give RATS every reasonable advantage. Its provisional adverse result was that all frozen S01-S20 scenarios could be represented through direct RATS semantics or an ordinary application profile. No internal scenario presently requires an ETS-only primitive.

That result is not independent and may be overturned or further strengthened by external review. It is nevertheless sufficient to narrow the working thesis now.

## Claims that should no longer carry the doctorate by themselves

The doctoral program should not depend on originality claims of the form:

- ETS has an evidence object;
- ETS signs or hashes evidence;
- ETS has a verifier;
- ETS separates Attester-like and Relying-Party-like roles;
- ETS records provenance in a graph;
- ETS supports rich claims or uncertainty fields;
- ETS records model identity, inputs, outputs, telemetry, authority, action or outcome;
- ETS records command and result as separate fields;
- ETS has a tamper-evident log or chain of custody;
- ETS can encode the S01-S20 scenario facts while RATS cannot.

These may remain valuable engineering properties. They are not presently defensible as the core contribution to knowledge.

## Revised central thesis candidate

The strongest working thesis is now:

> Consequential machine-action evidence can be made more reliable for independent verification by applying a formal, substrate-independent non-collapse semantics that preserves separately supported propositions and prevents unsupported promotion across integrity, identity, authority, standing, provenance, execution, observation and consequence boundaries.

This thesis is intentionally substrate-independent. ETS is the principal implementation and research platform, but a successful RATS+ implementation of the same rules would not refute the thesis. It would instead show that the contribution is the rule system and its demonstrated value rather than a proprietary or ETS-specific evidence container.

## Non-collapse boundaries under test

The current rule families are:

1. **Integrity is not truth.** A valid signature, digest, schema or inclusion proof supports integrity/attribution claims, not the semantic truth of the signed assertion.
2. **Identity is not authority.** Authentication of an actor does not establish permission for a particular action.
3. **Current authority is not historical standing.** Authorization must be evaluated against the policy and delegation state applicable at the event time.
4. **Freshness dimensions are independent.** Fresh evidence can rely on stale policy or reference values; fresh transport does not refresh stale source state.
5. **Request is not execution.** A command or tool call supports requested action, not completed action.
6. **Execution is not resulting state.** Device or service execution evidence does not establish an independently observed external result.
7. **Result observation is not automatically causality.** A post-action state can be observed without proving that the preceding action caused it.
8. **Agreement is not independence.** Multiple claims derived from one upstream source do not constitute independent corroboration.
9. **Absence of evidence is not evidence of absence without an expectation model.** Bounded omission findings require coverage, sequence or expectation evidence.
10. **Unknown, unavailable, not observed, contradicted and false are distinct states.** Missing information must not silently become a negative fact.
11. **Verifier trust is independent of source integrity.** Valid source Evidence does not make an untrusted or stale-policy verifier result trustworthy.
12. **Provenance is not causal proof.** A derivation, temporal or graph relationship does not by itself establish causation.

## Consequence custody as the highest-value domain specialization

The most consequential specialization of the non-collapse thesis is **consequence custody**.

For a consequential action, the evidence chain should be able to represent separately:

`observation -> inference -> decision -> authority/standing -> requested action -> accepted/executed action -> resulting-state observation -> consequence attribution`

The final arrow is deliberately difficult. A verifier may have strong evidence that an action was requested and executed and strong evidence that a later state was observed, while still lacking a justified causal claim that the action produced that state.

The research question is therefore not whether ETS can store an `outcome`. The question is what evidence, independence, timing, custody and alternative-explanation conditions are sufficient to permit a bounded consequence conclusion.

Ranger and VRX are valuable because they make this boundary physical and measurable. AI Witness is valuable because it exposes the same boundary in software/tool-mediated action. The cross-domain claim survives only if the semantics remain stable across both.

## Revised falsification strategy

The narrowed thesis must be able to fail in at least four ways.

### F1 — Ordinary rich profiles already prevent the errors

If an equally informative ordinary RATS/PROV/domain profile, without the proposed non-collapse rule system, produces the same bounded conclusions and the same error rate, the rule contribution is weakened or refuted.

### F2 — The rule system blocks too much

If the non-collapse calculus reduces unsupported conclusions only by materially suppressing conclusions that are actually supported, it is not useful evidence semantics.

### F3 — The benefit is domain-specific

If the rules work only for administrative or synthetic examples but fail in AI or cyber-physical settings, the domain-neutral thesis must narrow.

### F4 — Existing prior art already contains materially equivalent normative rules

If external review identifies established provenance, attestation, assurance, digital-forensics or causal-evidence work with substantially equivalent rule semantics and scope, originality must narrow regardless of ETS implementation quality.

## Experimental consequence

EXP-001 remains useful because it measures human reconstruction error, but it depends on evaluator recruitment and institutional human-subjects determination.

EXP-002 remains useful because it tests whether the proposed distinctions are already ordinary RATS/profile semantics.

The next experiment, EXP-003, should therefore test the rule system itself without human-subject dependency. It will use machine-generated adversarial claim combinations, a frozen truth/support oracle, and three conditions:

- a rich-profile baseline with the same facts but no mandatory cross-dimensional non-collapse calculus;
- the formal non-collapse calculus;
- a RATS+ implementation of the same calculus.

The decisive outcomes will be unsupported semantic-promotion rate and supported-conclusion recall. If the RATS+ implementation matches the calculus, the correct interpretation is substrate independence, not ETS superiority.

## Application consequence

The doctoral application should present the existing ETS corpus as preliminary feasibility and a mature research platform, not as a completed proof of originality.

The strongest supervisor framing is now:

> The preliminary platform exposed a narrower research problem than the original engineering design suggested. Existing provenance and attestation standards can encode far more of the evidence surface than a weak comparison would imply. The proposed doctorate therefore asks whether a formal non-collapse semantics and consequence-custody discipline provides a measurable, cross-domain verification benefit beyond rich but unconstrained standards profiles, and under what conditions that benefit disappears.

That framing is stronger precisely because current negative evidence is part of the proposal rather than hidden from it.

## Current external gates

- Professor Ilir Gashi has been contacted regarding doctoral fit and supervision.
- Ned Smith has been asked to independently challenge the RATS equivalence analysis.
- Neither contact is treated as validation until an actual response is received and recorded.

## Rule for future updates

No future document should restore a broad EA-C001/EA-C003/EA-C005 novelty claim merely because an ETS implementation is more convenient, integrated or polished than a comparator.

A claim may broaden only if new prior-art review, external challenge or prospective evidence justifies that change.
