# Part II — The Evidence Architecture Thesis

Evidence Architecture is not built around the proposition that one cryptographic mechanism can turn a system record into truth. It is built around a stricter proposition: claims should remain bounded by the evidence and mechanisms that support them.

A useful spoken sequence is:

Observed is not the same as authenticated.

Authenticated is not the same as authorized.

Authorized is not the same as executed.

Executed is not necessarily the same as consequential.

And a recorded consequence is not automatically independently verified truth.

Every transition between those statements is a place where a system can accidentally overclaim.

## Evidence Objects

EA-C001 is the candidate Evidence Object contribution. It is not a claim that a record plus a hash is novel. The intended model is a portable evidentiary envelope with an explicit identity boundary and typed bindings to evidence contracts. The implemented version-two model separates canonical identity-bearing material from proof material that may evolve independently, with bindings for events, claims, provenance, context, relationships, policy, privacy, and verification.

That is implemented engineering. The doctoral question is narrower: does a domain-neutral object that preserves bounded verification dimensions provide a materially distinct and useful contribution?

Instead of one universal green light labeled verified, the verifier should be able to ask separate questions. Did the bytes canonicalize as expected? Does the digest match? Does a signature validate under the stated key and trust model? What source identity does that support? What custody is evidenced? What policy or standing context applies? How fresh is the retained state? What is known about completeness? What consequence is supported? What is explicitly not claimed?

Intuitively, imagine several gauges rather than one light. A valid signature may support integrity. It should not automatically establish authority, completeness, freshness, standing, or physical outcome.

## Evidence Graphs

Evidence rarely exists as one isolated object. An observation may inform an inference. A decision may depend on policy and delegated authority. A decision may produce a requested action. A later observation may support or contradict the intended result.

EA-C002 is the candidate Evidence Graph contribution. The graph itself is not novel; W3C PROV and decades of provenance research already provide rich graph models. The candidate distinction is that consequential relationships may themselves need to be treated as evidentiary claims whose source, provenance, verification status, epistemic status, dependencies, and nonclaims remain inspectable.

A line connecting decision to result is not self-proving. A graph should preserve whether that relationship is directly evidenced, inferred, contradicted, unavailable, or dependent on a shared source.

This matters when two analytical outputs appear to corroborate each other but both ultimately depend on the same upstream observation. Two outputs can exist without constituting two independent sources.

## Epistemic states

Evidence Architecture treats uncertainty as information rather than something to erase.

Useful states include unknown, not observed, not available, indeterminate, and contradicted. These are not synonyms.

Not observed can mean an observation process ran and did not detect the event. Not available can mean the observation mechanism could not provide evidence. Unknown means the package does not establish the proposition. Indeterminate means the evidence cannot distinguish competing possibilities. Contradicted means material evidence conflicts with the proposition or with another item.

If two sensors report no hazard while the only sensor covering a third region is unavailable, the supported conclusion is coverage-bounded. No hazard was detected where observation existed; the unobserved region remains unknown. Failure to observe is not automatically a negative observation.

## The epistemic ceiling

The Ranger cyber-physical research states an important rule: a derived or asserted claim must not exceed the evidentiary strength supported by the mechanisms and evidence available at consequence time.

That is the epistemic ceiling.

A signed media artifact can support capture provenance under a stated device trust model without proving the semantic truth of the scene. A model score can support an inference without proving the underlying real-world condition. Motor telemetry can support controller output without necessarily proving physical displacement.

The evidence sets the maximum height of the claim.

## Reconstruction Boundary

The Reconstruction Boundary asks: can the system establish what happened, under what conditions, and what remains unknown?

Reconstruction concerns prior events, artifacts, states, transitions, and outcomes. A well-preserved record can be reconstructable even when the associated action did not possess valid standing.

## Standing Boundary

The Standing Boundary asks: did the material predicates authorizing an action, decision, transition, or consequence hold at the relevant time?

Standing may depend on identity, delegated authority, policy version, consent, entitlement, scope, revocation, jurisdiction, validity windows, external state, and contradictory evidence.

An authentic record may remain historically valid while its authority context becomes stale. Identity evidence and record integrity therefore do not automatically establish current standing.

A verifier should also avoid overcorrection. If the supplied package does not establish valid authority, that does not prove that no lawful authority existed elsewhere. The strongest defensible conclusion must remain bounded by the supplied evidence.

## Consequence Custody Boundary

The architecture defines a third, stronger boundary: Consequence Custody. It asks whether the transition from a standing-qualified state into consequence was itself governed and whether that governance can be evidenced.

For implementations that truly claim consequence custody, the normative rule is: no standing, no bind.

This is not a blanket ETS claim. A component that captures, preserves, transports, or verifies evidence may help evaluate standing without enforcing it. A standing-aware architecture may evaluate standing but permit policy-defined override. Only an implementation that actually makes valid standing a prerequisite to binding the consequential transition may claim consequence custody.

## No command-result collapse

Cyber-physical systems make stage separation especially clear. The research distinguishes decision, requested action, accepted action, controller response, physical response, and observed result.

These stages can occur close together and still be different propositions. An internal status can be evidence about the controller while an independent physical measurement provides different evidence about the external world. If they conflict, the contradiction should be preserved rather than normalized away.

## Verification without truth inflation

The deepest thesis is not that ETS proves what happened. Evidence Architecture attempts to make it harder for a system to claim more than the available evidence can support.

Integrity is useful. Identity is useful. Provenance is useful. Custody is useful. Standing is useful. Consequence observation is useful. None should silently inherit the semantics of another.

If this discipline proves useful under independent evaluation, it may form part of a contribution. If ordinary provenance with domain extensions provides the same benefit, the candidate contribution must narrow. That willingness to lose the larger claim is a strength of the research design.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/CONTRIBUTION_LEDGER.md`
- `docs/research/phd/WP1_PROV_RELATION_MAPPING_AND_DEEPER_PRIOR_ART.md`
- `docs/research/phd/WP1_DEEP_LITERATURE_QUALIFICATION.md`
- `docs/architecture/EVIDENCE_STANDING_CONSEQUENCE_CUSTODY.md`
- `docs/research/ranger/cyber-physical-observability.md`
- `ets/evidence_object/models_v2.py`
