# Epistemic Provenance and Evidentiary Reconstruction

Status: research architecture extension

## 1. Thesis

ETS must distinguish provenance from epistemic warrant.

> Provenance establishes where an artifact, observation, assertion, or interpretation came from. It does not establish that the represented proposition is true.

A cryptographically intact record may faithfully preserve error, deception, bias, incomplete observation, or an incorrect inference. ETS therefore treats provenance as necessary for evidentiary reconstruction but insufficient for truth.

This boundary can be summarized as:

```text
provenance != truth
integrity != correctness
authentication != authority
repetition != independent corroboration
precedence != causation
institutional acceptance != certainty
```

Informally: **provenance is not providence**. ETS can establish and preserve evidence about the history of a claim; it cannot cryptographically manufacture objective reality.

## 2. Epistemic pipeline

A real-world claim may traverse multiple transformations:

```text
reality
  -> observation
  -> recording/assertion
  -> preservation
  -> selection
  -> transformation
  -> corroboration
  -> interpretation
  -> narrative compression
  -> repetition
  -> institutional acceptance
```

Each transition may introduce uncertainty, information loss, dependence, distortion, or new assumptions. ETS SHOULD preserve these transitions rather than collapse them into a single evidence-to-truth edge.

## 3. Typed epistemic relations

Evidence Graph implementations SHOULD distinguish at least:

- `OBSERVED`: a source encountered a state or signal;
- `ASSERTED`: an actor expressed a proposition;
- `REPORTED`: a source relayed another assertion;
- `DERIVED_FROM`: an artifact was transformed from another artifact;
- `CORROBORATES`: evidence independently supports a proposition under declared criteria;
- `CONTRADICTS`: evidence conflicts with a proposition or observation;
- `INFERRED`: a conclusion was produced from declared inputs and assumptions;
- `INTERPRETED`: an analyst or model assigned meaning to evidence;
- `PRECEDES`: one event temporally precedes another;
- `CONTRIBUTES_TO`: evidence supports a bounded causal contribution claim;
- `CAUSES`: a causal claim is asserted under an explicit causal model;
- `NECESSITATES`: a stronger counterfactual/necessity claim is asserted.

These relations MUST NOT be treated as interchangeable.

## 4. Epistemic distance

**Epistemic distance** is the structured distance between a claimed event/state and the evidence currently used to justify a conclusion about it.

Distance is multidimensional rather than a single universal scalar. Relevant dimensions include:

- temporal distance between event, observation, recording, and evaluation;
- transformation depth;
- number of intermediary reporters;
- loss of original context;
- source dependence;
- model/analyst inference depth;
- uncertainty introduced at each transition.

ETS SHOULD preserve the vector of these factors. A scalar score MAY be computed by a declared policy, but the underlying dimensions MUST remain inspectable.

## 5. Contemporaneity

Evidence created near an event and retrospective recollection are epistemically different even when both artifacts are authentic.

ETS SHOULD record, when available:

- event time or interval;
- observation time;
- recording time;
- ingestion/commitment time;
- evaluation time;
- uncertainty on each time value.

Temporal proximity is not truth, but it is relevant evidentiary context.

## 6. Source independence and common-source collapse

Apparent corroboration can be illusory. Ten downstream reports copied from one originating source constitute many artifacts but not ten independent observations.

ETS SHOULD construct evidence ancestry sufficient to identify shared upstream dependencies. Corroboration policies SHOULD discount or collapse dependent branches when computing support.

This is especially important for AI systems trained on, retrieved from, or summarizing mutually derivative Internet sources.

## 7. Observability boundary and survival bias

Evidence can exist only for what a system was capable of observing, recording, retaining, and retrieving.

An **observability boundary** declares those limits. It may include:

- sensor field of view and resolution;
- collection scope;
- retention policy;
- archive survival;
- access restrictions;
- sampling behavior;
- known gaps or outages;
- transformation losses.

Absence outside or near an observability boundary MUST NOT be promoted to evidence of absence without an explicit expectation model.

## 8. Interpretation provenance

Interpretations are themselves evidence-producing events.

An interpretation record SHOULD bind:

```text
input evidence
+ method/model/version
+ assumptions
+ analyst/agent identity
+ parameters/policy
+ time/context
-> conclusion
```

This makes a human historical interpretation, AI Witness conclusion, classifier result, or forensic assessment independently reconstructable without representing the interpretation as objective fact.

## 9. Claim genealogy

A **claim genealogy** is the provenance graph of a proposition across time.

ETS SHOULD support reconstruction of:

- earliest known assertion;
- later repetitions;
- paraphrases and semantic strengthening/weakening;
- independent vs dependent attestations;
- corrections and retractions;
- contradictions;
- transitions from tentative claim to accepted narrative.

Repeated publication MUST NOT automatically increase independent evidentiary weight.

## 10. Causal and counterfactual discipline

Temporal order alone does not establish causation. ETS SHOULD preserve distinct semantics for:

```text
PRECEDES != CONTRIBUTES_TO != CAUSES != NECESSITATES
```

Causal claims SHOULD identify their causal model, assumptions, alternatives considered, and supporting evidence. Counterfactual or inevitability claims require stronger declared assumptions than ordinary temporal association.

## 11. Narrative compression

A narrative statement often compresses a large Evidence Graph into a small claim.

ETS defines **narrative compression** as a transformation from an evidentiary subgraph to a reduced representation intended for human or machine consumption.

A compressed narrative SHOULD preserve links to:

- the source subgraph;
- selection criteria;
- omitted material categories where known;
- contradictions and unresolved uncertainty;
- transformation method;
- author/model identity;
- version.

Compression is not neutral. It changes what is visible to the consumer and therefore belongs in provenance.

## 12. Epistemic warrant

ETS distinguishes three questions:

1. **Provenance:** Where did this artifact, assertion, or conclusion come from?
2. **Epistemic warrant:** What does the available evidence justify concluding under explicit assumptions and visibility limits?
3. **Objective reality:** What actually occurred independent of the evidence system?

ETS can make strong bounded claims about (1), can provide disciplined and computationally testable machinery for (2), and MUST NOT claim omniscient access to (3).

## 13. Cyber-physical application: Ranger

For Ranger, the distinction becomes concrete:

- a signed camera frame establishes what the sensor pipeline produced, not necessarily what existed in the physical world;
- a verified classifier output establishes what that model concluded from declared inputs, not that the classification was correct;
- a reconstructed decision chain establishes why Ranger selected an action under its recorded state and policy, not that the action was objectively optimal;
- resulting-state evidence establishes what downstream sensors subsequently reported, subject to their own observability boundaries.

A defensible Ranger evidence package therefore preserves:

```text
physical state (not directly knowable)
 -> sensor observation
 -> transformation
 -> classification/interpretation
 -> policy evaluation
 -> action authorization
 -> physical action
 -> resulting-state observation
```

Each edge requires provenance and each epistemic transition retains its uncertainty.

## 14. AI Witness application

AI Witness MUST distinguish source evidence from model-generated interpretation. Its output SHOULD include input ancestry, model/version, relevant policy and parameters, confidence semantics, contradictions encountered, visibility limits, and the exact conclusion produced.

AI Witness attestation proves the provenance and integrity of the inference event under stated assumptions. It does not prove the inference true.

## 15. Formal research implications

Future formalization SHOULD investigate invariants including:

- `AssertionDoesNotImplyObservation`;
- `IntegrityDoesNotImplyTruth`;
- `DependentReportsDoNotIncreaseIndependentWitnessCount`;
- `AbsenceRequiresExpectationModel`;
- `CausalClaimRequiresDeclaredCausalBasis`;
- `InterpretationRetainsInputAncestry`;
- `NarrativeRetainsSourceSubgraphReference`;
- `EpistemicTransformationIsTraceable`.

Candidate quantitative research includes a multidimensional epistemic-distance function and independence-aware corroboration models. Any scalar confidence derived from them must expose assumptions and MUST NOT be represented as universal probability of truth.

## 16. Architectural boundary

ETS is not a truth oracle.

Its stronger scientific claim is that it can preserve enough structure to make the path from observation to assertion to interpretation independently inspectable, while refusing to erase uncertainty introduced along that path.

That is the role of epistemic provenance in Evidence Architecture.
