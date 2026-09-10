# Part III — Prior Art: What Evidence Architecture Does Not Get to Claim

A doctoral contribution does not begin by asking, “What did we build?” It begins by asking, “What was already known?”

The prior-art review has materially narrowed the Evidence Architecture novelty surface. That is a positive development. A narrower claim that survives comparison is stronger than a broad claim that ignores established work.

## W3C PROV

The most important baseline for the Evidence Graph is the World Wide Web Consortium PROV family, usually spoken as “W three C Prov.”

PROV is a domain-neutral provenance model. It already represents entities, activities, and agents, along with generation, usage, derivation, attribution, association, delegation, revision, specialization, invalidation, primary sources, collections, and temporal relationships.

This has a major implication. Evidence Architecture cannot claim novelty for typed provenance graphs, connecting artifacts to activities or agents, derivation, revision, delegation, provenance of provenance, or domain-specific specialization of a provenance ontology.

Many ETS relationships map directly to PROV. Artifact production maps to generation. Consumption maps to usage. Artifact derivation maps to derivation. Source attribution maps to primary-source relations. Revision maps to revision. Actor responsibility maps to attribution or association. Delegation maps to “acted on behalf of.” Versioned state can be modeled using specialization.

Some Evidence Architecture relationships are also expressible through PROV specialization or qualified relations. An observation can be a generated entity with sensor metadata. An inference can be an activity using source observations. A policy can be represented as an entity used by a decision process. A decision-to-action chain can be encoded as activities and entities.

Therefore the candidate distinction is not graph encodability. It is whether additional normative semantics—standing separation, explicit epistemic states, relationship-level claims, dimensional verification, and consequence-stage non-collapse—produce independent reconstruction benefit.

## Database provenance and provenance semirings

Database provenance research predates ETS by decades. Why-provenance, where-provenance, lineage, and provenance semirings establish sophisticated accounts of how outputs depend on inputs. The semiring framework shows that provenance annotations can be composed algebraically through query evaluation.

Evidence Architecture therefore cannot claim that tracing which inputs influenced an output is new. It cannot claim source-dependency graphs as new. It cannot claim compositional provenance as new.

This matters directly to the shared-source analytical-score scenario. Detecting that two model outputs share the same upstream record is useful, but source-dependency analysis itself is not a novel contribution. The researchable question is whether dependency information combined with explicit epistemic semantics and evidence boundaries reduces false claims of independent corroboration.

## Scientific workflow provenance

Scientific workflows already capture execution traces for reproducibility and comparison. Research such as PDIFF compares provenance traces across executions and identifies where reproduced runs diverge.

Evidence Architecture cannot claim novelty for workflow traces, run reconstruction, version-aware workflow comparison, or provenance-based reproducibility.

A reproducible workflow tells us something important about computational history. It does not necessarily establish whether a consequential decision had valid standing, whether a requested action was actually carried out, or whether the intended external consequence occurred.

## Authorization provenance

Authorization provenance is established research. Prior work records the inputs and policy context used in access-control or authorization decisions. Systems such as ACCESSPROV use provenance to diagnose flaws in access-control decisions.

ETS therefore cannot claim novelty for recording authorization-decision provenance, tracing policy inputs, or recording delegation.

The candidate distinction is the insistence that standing is a separate verification boundary. Identity does not become standing. A signed decision does not become standing. A historically valid delegation does not remain current merely because its historical record is intact.

Whether this boundary is sufficiently distinct from authorization logic, trust management, capability systems, reference monitors, and policy provenance still requires continued scholarly comparison.

## Claim and evidence graphs

Claim-evidence graphs and structured argumentation are mature areas. Scientific-evidence models and Micropublications represent claims, evidence, support, challenge, attribution, and provenance.

Evidence Architecture cannot claim novelty for putting claims in a graph or linking evidence to claims.

The narrower candidate concerns operational relationships themselves. For a consequential relationship, Evidence Architecture investigates whether the relationship should carry attributable evidence, verification status, epistemic state, dependency history, and explicit nonclaims.

The graph should be able to preserve that a relationship is asserted by a particular source, supported to a bounded degree, contradicted elsewhere, or insufficient to establish causality beyond the stated evidence.

## Remote attestation

The IETF Remote ATtestation procedureS architecture, or RATS, is strong prior art against any generic “evidence plus verifier” novelty claim.

RATS already separates an Attester, Evidence, Verifier, Attestation Result, Relying Party, Reference Values, Endorsements, and appraisal policy. It already treats evidence as claims to be appraised rather than automatic truth.

EA-C001 therefore cannot be defended merely by saying that an evidence producer gives evidence to an independent verifier. The candidate Evidence Object must be distinguished by its broader claim-boundary semantics, if those semantics are genuinely distinct and useful.

## Software supply-chain provenance

Software supply-chain systems such as in-toto are strong prior art for signed step metadata, authorized functionaries, commands, materials, products, and verification against expected layouts.

Evidence Architecture cannot claim novelty for signed workflow-step records, authorized functionaries, digested artifacts, or declared workflow expectations. Nor can domain generality alone save the novelty claim. Applying an established pattern to another domain is not automatically a contribution to knowledge.

## Transparency logs and secure audit logs

Certificate Transparency and related authenticated-log systems provide Merkle-based inclusion and consistency proofs, signed tree information, append-only monitoring, and mechanisms for detecting certain log misbehavior. Secure and forward-integrity audit-log literature also predates ETS.

ETS cannot claim novelty for Merkle inclusion, append-only history, signed log roots, or tamper-evident logging in general. These can be foundations for Evidence Architecture; they are not the novelty.

Cryptographic strength at the storage layer also does not remove epistemic limits at the observation layer. A perfectly protected record can preserve an incorrect observation. A perfectly protected stale checkpoint is still stale. A perfectly protected action record does not prove external consequence.

## AI and machine-learning provenance

AI provenance is an active research area. Existing work covers training-data lineage, model genealogy, pipeline provenance, deployment history, attestable model artifacts, and machine-readable model records.

Evidence Architecture cannot claim that recording model versions and inputs is a novel AI accountability framework.

The remaining question is more operational: can a machine-action evidence chain distinguish input observation, inference, policy and authority, decision, tool or action request, accepted or executed action, consequence, and result observation, without claiming access to hidden model reasoning?

For nondeterministic models, reproducing the identical model output may be impossible or irrelevant. Evidence replay can instead ask whether externally inspectable inputs, runtime identity, authority, tools, declared outputs, and consequences can be reconstructed.

## Cyber-physical provenance, runtime assurance, and assurance cases

Cyber-physical research already includes control-message provenance, provenance-aware policy enforcement, runtime assurance, safety controllers, safety interlocks, and structured safety or assurance cases.

Evidence Architecture cannot claim runtime assurance itself, safety cases, or preservation of control-message history as novel.

The candidate distinction is narrower: consequence custody and a non-collapse rule in which evidence of a requested or accepted action is not automatically evidence of execution, and execution is not automatically evidence of resulting physical state. Even that candidate still requires deeper comparison with reference monitors, transactional systems, safety enforcement, industrial event logging, and assurance-case literature.

## What remains after prior art

After these exclusions, the candidate research surface is substantially smaller:

Dimensional verification claim vectors instead of a universal “verified” state.

First-class epistemic states and explicit nonclaims.

Standing as a separate verification boundary.

Decision-to-action-to-consequence non-collapse.

Consequence custody as a separately qualified boundary.

Edges or relationships treated as separately attributable evidentiary claims.

Shared-source dependence used to prevent false corroboration.

None of these is currently established as an original contribution merely because the repository names them.

If deeper prior art already integrates substantially equivalent semantics, the contribution must narrow or be retired. If ordinary W3C PROV with well-designed domain extensions performs as well as Evidence Architecture, the claim of EA-specific semantic benefit weakens. If Evidence Architecture introduces complexity without reducing errors, that is evidence against the current framing.

Prior art is therefore not an obstacle to the research. It is a filter that turns a broad product idea into a falsifiable scientific question.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/WP1_EVIDENCE_OBJECT_GRAPH_PRIOR_ART.md`
- `docs/research/phd/WP1_PROV_RELATION_MAPPING_AND_DEEPER_PRIOR_ART.md`
- `docs/research/phd/WP1_DEEP_LITERATURE_QUALIFICATION.md`
- `docs/research/phd/CONTRIBUTION_LEDGER.md`
