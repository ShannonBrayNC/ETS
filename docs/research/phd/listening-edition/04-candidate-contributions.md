# Part IV — Candidate Contributions: EA-C001 and EA-C002

The phrase “candidate contribution” has a precise purpose in this research program. It means the idea is coherent enough to define, compare, and test, but the evidence is not yet sufficient to promote it to an established contribution to knowledge.

The two candidates at the center of EXP-001 are EA-C001, the Evidence Object model, and EA-C002, the Evidence Graph model.

## EA-C001 — the Evidence Object model

### The problem

Many systems produce artifacts that can be checked in one dimension and then described too broadly. A signature validates, so the artifact is called verified. A log proves inclusion, so the event is treated as established. A producer identity is known, so its assertion is treated as authorized.

The Evidence Object candidate addresses this semantic inflation.

### Prior-art baseline

This candidate stands on substantial existing work. W3C PROV covers provenance. RATS covers evidence, attesters, verifiers, appraisal, and relying parties. in-toto covers signed workflow metadata and authorized functionaries. Transparency logs cover append-only cryptographic inclusion and consistency. Digital forensics covers chain of custody. Secure audit logs cover integrity properties.

Therefore EA-C001 cannot be “a signed provenance envelope” and still be a defensible novelty claim.

### Candidate distinction

The narrowed candidate is a domain-neutral object whose verification result is decomposed into bounded dimensions and whose nonclaims travel with the evidence.

The object is intended to keep integrity, identity, provenance, custody, freshness, standing, scoped completeness, epistemic status, and consequence linkage from collapsing into one generic verified state.

In the current version-two implementation, the object also has an explicit canonical identity boundary and typed bindings to separately versioned contracts. Proof material can evolve without necessarily redefining the canonical object identity.

That is implemented engineering. The doctoral question is whether the bounded semantic composition itself is distinct and useful.

### Falsifiable hypothesis

The corresponding hypothesis, H-C001-A, predicts that a verifier using a dimensional Evidence Object result will make fewer unsupported semantic inferences than a verifier given an otherwise equivalent binary verification result.

The hypothesis can fail. If evaluators do not make fewer unsupported inferences, then the proposed semantic discipline has not shown the expected benefit in that setting.

### What would strengthen EA-C001

Evidence that would strengthen the candidate includes deeper systematic prior-art qualification showing that the integrated semantics are not already standard; a clear minimum-sufficiency argument for the object; independent implementation or reproduction; and empirical evidence that bounded verification reduces specific interpretation errors while factual content is held constant.

It would also help to show that the benefit generalizes beyond one domain and is not merely the result of better prose, more facts, or more attractive formatting.

### What would weaken or eliminate EA-C001

The candidate should narrow or be retired if prior work already provides substantially equivalent integrated semantics.

It should also weaken if the benefit disappears when compared with a strong domain-extended provenance baseline. If users need so much extra training to understand the Evidence Object that the semantic benefit vanishes in realistic settings, that matters. If the object becomes a packaging convention without a measurable epistemic or verification advantage, it may remain useful engineering without being a doctoral contribution.

That is an acceptable outcome.

## EA-C002 — the Evidence Graph model

### The problem

Consequential events are relational. An observation informs an inference. An inference informs a decision. A decision may depend on a policy and delegated authority. A decision may generate a requested action. A system may accept it. An actuator or external service may respond. The external world may or may not change as intended. A later observation may support or contradict the intended result.

Traditional provenance graphs can represent much of this structure. The Evidence Graph candidate asks whether the relationships should be bounded as evidence claims rather than treated as semantically self-proving edges.

### Prior-art baseline

W3C PROV is the strongest baseline. It already provides typed relations and qualified influence. Database provenance already handles dependency. Scientific workflows already handle execution traces. Claim-evidence graphs already handle support and challenge. Authorization provenance already traces policy decisions. Cyber-physical systems already record control-message provenance.

Therefore EA-C002 cannot be defended as “a graph of evidence.”

### Candidate distinction

The narrowed distinction is a graph in which consequential edges may carry their own producer, provenance, verification status, epistemic state, and dependency information.

The graph should preserve contradiction rather than normalizing it away. It should preserve shared-source dependence so two derived outputs are not mistaken for two independent observations. It should preserve explicit noncausality: adjacency, temporal sequence, or a provenance relation should not be narrated as causal proof unless the evidence supports causality. It should preserve standing and consequence stages as separate propositions.

### Falsifiable hypotheses

Three hypotheses are especially important.

H-C002-A predicts that requiring independently attributable relationship evidence improves reconstruction precision compared with topology-only or unqualified provenance graphs.

H-C002-B predicts that explicit unknown, unavailable, indeterminate, and contradicted states reduce false positive and false negative conclusions compared with treating missing evidence as false or absent.

H-C002-C predicts that explicitly separating decision, requested action, accepted or executed action, and resulting-state observation reduces incorrect outcome attribution.

All three can fail.

### What would strengthen EA-C002

The candidate becomes stronger if a rigorous relation-by-relation mapping shows exactly which semantics are merely PROV expressions, which are domain specializations, and which require additional normative rules.

It becomes stronger if independent evaluators make fewer standing, completeness, contradiction, or action-result errors under matched factual conditions. It becomes stronger if the semantic rules can be implemented across administrative, AI, and cyber-physical domains without changing their meaning. External reproduction would matter substantially.

### What would weaken or eliminate EA-C002

If W3C PROV plus ordinary domain extensions yields the same reconstruction accuracy, the specific Evidence Architecture discipline may not be necessary.

If relationship metadata merely repeats information already obvious to evaluators, the contribution narrows. If explicit epistemic states add cognitive burden without reducing error, the design must be reconsidered. If deeper prior art already integrates relationship-level verification, standing, contradiction, and consequence separation in a substantially equivalent way, novelty must narrow regardless of how elegant the ETS implementation is.

## Why falsifiability is a strength

There is a product instinct to write claims that are difficult to disprove. Research should do the opposite.

A claim that survives a credible possibility of failure is more meaningful.

EXP-001 is valuable precisely because it contains a strong comparator: Condition B is allowed to use ordinary domain extensions and the same substantive facts as Evidence Architecture. Condition C is not permitted to win by receiving extra evidence.

If B performs as well as C, the doctoral program must take that seriously. The result would not make ETS worthless. It could show that the engineering implementation is useful while the proposed academic distinction is smaller than expected.

A doctoral contribution should be able to survive that separation.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/CONTRIBUTION_LEDGER.md`
- `docs/research/phd/WP1_EVIDENCE_OBJECT_GRAPH_PRIOR_ART.md`
- `docs/research/phd/WP1_PROV_RELATION_MAPPING_AND_DEEPER_PRIOR_ART.md`
- `docs/research/phd/WP1_DEEP_LITERATURE_QUALIFICATION.md`
- `ets/evidence_object/models_v2.py`
