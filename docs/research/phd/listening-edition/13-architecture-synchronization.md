# Part X — The Architecture Has Become More Precise

In this update, I want to tighten the language around what Evidence Architecture can establish and, just as importantly, what it cannot.

The project has matured beyond a simple contrast between trust and proof. The more useful distinction is now between provenance, epistemic warrant, and objective reality.

Provenance tells me where an artifact, assertion, observation, or interpretation came from.

Epistemic warrant asks what the available evidence justifies me in concluding under explicit assumptions and visibility limits.

Objective reality is whatever actually occurred independent of the evidence system.

Evidence Architecture can make increasingly strong bounded claims about provenance. It can provide disciplined machinery for evaluating epistemic warrant. It cannot turn cryptography into omniscience.

That is why I now use a shorthand that has become central to the research:

Provenance is not providence.

Integrity is not correctness.

Authentication is not authority.

Repetition is not independent corroboration.

Precedence is not causation.

And a valid signature is not the same thing as current authorization.

## Evidence relationships are not interchangeable

The Evidence Graph also becomes more precise when I stop treating every connection as a generic edge.

An observation is different from an assertion.

A report is different from an independent observation.

An inference is different from a measurement.

A temporal relationship is different from a causal relationship.

A decision is different from a command.

A command is different from execution.

And execution is different from independently observed consequence.

These distinctions matter because every time a system collapses two different propositions into one, it creates an opportunity to overclaim.

For example, if a robot controller reports that it issued a movement command, I have evidence about the controller. I do not yet have proof that the vehicle physically moved as intended. I need resulting-state evidence for that.

If an AI model says that a person appears to match an identity, I have evidence of what the model concluded from its inputs. I do not automatically have proof of that person's objective identity.

If ten articles repeat the same originating report, I have ten artifacts. I may still have only one independent source.

## Epistemic distance

Another concept that has become important is epistemic distance.

The distance between an event and a conclusion is not one number. It has several dimensions.

How much time passed between the event and the observation?

How many transformations occurred?

How many people or systems relayed the claim?

How much original context was lost?

How dependent are the sources on one another?

How much interpretation was introduced by a human or model?

What uncertainty was added at each step?

A policy can compress those factors into a score if it needs to, but the underlying factors should remain inspectable. I do not want a confidence number to hide the path that produced it.

## The observability boundary

Every evidence system also has a boundary around what it could observe.

A camera has a field of view.

A microphone has a range.

A log collector has a configured scope.

A retention system has a survival window.

A sensor may be unavailable.

A network may be partitioned.

So when evidence is missing, I have to ask whether the system was actually capable of observing and preserving the thing I am looking for.

No observation is not automatically a negative observation.

Absence outside the observability boundary is not proof of absence.

## Interpretation has provenance too

This becomes especially important when AI is used to analyze evidence.

An AI Witness conclusion should not replace the source evidence. It should become another evidence-producing event.

I want to preserve the inputs, the model and version, the assumptions, the policy and parameters, the time and context, and the exact conclusion that was produced.

That means a later analyst can challenge the interpretation without changing the underlying evidence.

The same principle applies to human forensic analysis.

Interpretation is not outside the evidence system. Interpretation has provenance.

## Prior art has narrowed the research claim

The prior-art work has also made the doctoral claim more disciplined.

I cannot reasonably claim novelty for provenance graphs. W3C PROV is direct prior art.

I cannot claim novelty for append-only transparency logs. Certificate Transparency and related research already establish that space.

I cannot claim novelty for signed software-supply-chain attestations. in-toto and SLSA are strong precedents.

I cannot claim novelty for signed content provenance. C2PA is a major adjacent system.

And chain of custody, integrity preservation, and forensic evidence management have deep existing bodies of practice.

That is useful, not discouraging.

It forces the candidate contribution to become narrower and more defensible.

The current research question is whether typed evidentiary claims and edges, explicit verification-state boundaries, and preservation of unsupported assumptions across heterogeneous digital, AI, distributed, and cyber-physical systems form a materially useful contribution beyond those existing systems.

That remains a candidate contribution, not an established originality claim.

## The autonomous-agent incident changes the practical framing

The 2026 autonomous-agent incident gives me a concrete digital example of the same problem Ranger exposes physically.

The principle is straightforward:

The subject of an investigation should not be the sole authority for the evidence used to establish its own consequential actions.

For an AI system, I want to distinguish the actor's own account from independently captured evidence at the tool or action boundary.

That means preserving execution identity, policy state, authority, the requested action, the actual invocation, the external effect, the resulting state, and the evidence custody around those steps.

I do not need private chain-of-thought to do that.

I need evidence at the externally meaningful boundary where the system affects something outside itself.

That same model applies to Ranger.

Sensor observation.

Perception.

Decision.

Authority.

Actuator command.

Physical action.

Resulting-state observation.

The physical consequence is different, but the evidence problem underneath it is remarkably similar.

## Adversarial qualification becomes part of the architecture

This is also why ETS Adversarial Qualification matters.

I do not want security qualification to be a final penetration test that produces a PDF and disappears into a folder.

I want the qualification itself to become reproducible evidence.

A meaningful EAQ run should bind the authorization, the scope, the exact system under test, the configuration, the hypothesis, the procedure, the observations, the result, any remediation, and the regression evidence.

The possible result should be explicit: pass, fail, inconclusive, or blocked.

And the observer of the qualification should not be the same component that is being challenged whenever independence is material to the claim.

EAQ begins as a research discipline. It does not mean every current ETS component has already earned a mature adversarial certification.

## Historical validity is not current authority

The newest Ranger publication-key work gives me another very concrete example of the architecture's epistemic discipline.

Suppose a publication receipt was correctly signed by a publisher key last month.

That key may later rotate.

Or it may be revoked after compromise.

The old signature can remain historically valid without the old key remaining currently authorized.

So the verifier now separates three questions.

Did this source signature validate?

Did the key have authority-relative standing in the exact lifecycle-history prefix named by the evidence?

And is that key still current relative to the fuller history I am evaluating now?

Those are three different propositions.

A later rotation can make the answer to the third question no while preserving yes for the first two.

That distinction is exactly the kind of thing Evidence Architecture is supposed to preserve.

It also exposes another boundary. The lifecycle record does not, by itself, prove when the source signature happened relative to the lifecycle event. That requires a separate trusted-time composition.

## Freshness is relative too

A cryptographically valid history can still be stale.

If I retain a prior trusted head, I can detect some forms of rollback or stale presentation relative to that retained state.

But that still does not give me universal knowledge of the globally latest history.

Fresh relative to my retained checkpoint is not the same as globally current.

That may sound like a small wording change, but it matters enormously in a system that is supposed to survive adversarial review.

## What I now consider the stronger thesis

The strongest form of Evidence Architecture is not a universal truth engine.

It is an architecture for preserving the distinctions that ordinary systems often erase.

What was observed.

What was asserted.

What was inferred.

What was authenticated.

What was authorized.

What was executed.

What was independently witnessed.

What consequence was actually observed.

What remains uncertain.

What is contradicted.

And what cannot be known from the evidence available now.

If I can preserve those distinctions across digital systems, AI systems, enterprise workflows, and cyber-physical systems, then I have a research program worth testing.

If established provenance systems with ordinary domain extensions produce the same practical result, then the claim must narrow.

That is not failure.

That is the research doing its job.

---

## Reference notes — do not narrate

Primary synchronization sources:
- `docs/dissertation/EPISTEMIC_PROVENANCE.md`
- `docs/dissertation/EVIDENCE_THEORY.md`
- `docs/research/phd/LITERATURE_PRIOR_ART_EA_C001_C002.md`
- `docs/security/ETS_ADVERSARIAL_QUALIFICATION_PROGRAM.md`
- `docs/security/EAQ_RESEARCH_ROADMAP.md`
- OpenAI/Hugging Face 2026 Evidence Architecture case study merged in PR #616
- `docs/research/ranger/publication-key-lifecycle.md`
- `docs/research/ranger/adr/0013-publication-custodian-key-lifecycle.md`
- `docs/dissertation/EPISTEMIC_PROVENANCE_MATHEMATICAL_APPENDIX.md`
