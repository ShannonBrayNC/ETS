# Dissertation Integration Sprint

## Purpose

This sprint converts ETS sprint artifacts into a committee-draft path. It does
not claim the dissertation is committee-ready. It creates the integration
structure required to turn artifacts into continuous prose, normalized
references, figures, tables, and Missouri S&T formatting.

## Integrated Dissertation Spine

The dissertation should be assembled as one argument:

> ETS defines a bounded evidence-transparency architecture for digital systems
> where claims must remain traceable to observed artifacts, explicit
> assumptions, and reproducible validation rather than informal trust.

This spine connects the current artifact set:

- Chapter 1 frames the research problem and bounded thesis.
- Chapter 2 positions ETS against transparency logs, formal methods,
  distributed systems, and computational trust.
- Chapter 3 defines evidence theory.
- Chapter 4 presents the ETS protocol architecture.
- Chapter 5 presents formal models and proof status.
- Chapter 6 explains the reference implementation.
- Chapter 7 presents reproducibility and experiments.
- Chapter 8 discusses governance and applied implications.
- Chapter 9 consolidates limitations.
- Chapter 10 states the final contribution.

## Continuous Prose Starter

Digital systems increasingly rely on artifacts that are distributed across
services, teams, tools, and institutions. A ticket, model output, approval,
audit log, dataset, or deployment record may become evidence in later
technical, governance, legal, or operational review. Yet most systems treat
the preservation of evidence, the observation of evidence, the interpretation
of evidence, and the truth of a claim as if they were the same concept. ETS
separates these concepts.

Evidence Transparency Systems are proposed here as a bounded architecture for
recording digital evidence events, preserving their integrity, exposing
verifiable proof material, and making uncertainty explicit. ETS does not claim
to prove that every real-world statement inside an artifact is true. Instead,
it asks a narrower and more defensible question: given an artifact, a set of
observed events, and a stated verification boundary, what can be proven about
the artifact's recorded existence, integrity, ordering, visibility, and
consent or approval chain?

This dissertation therefore treats ETS as a protocol research platform, not as
a production trust oracle. Its contribution is the disciplined separation of
evidence, observation, confidence, trust, disagreement, omission suspicion, and
completion. The implementation, formal models, and experiments are used to
demonstrate bounded claims under explicit assumptions.

## Citation Normalization Plan

| Citation Area | Required Action |
| --- | --- |
| Transparency logs | Normalize Certificate Transparency, Trillian, Sigsum, and Merkle-log citations. |
| Formal methods | Normalize TLA+, Apalache, Alloy, Lean, and refinement citations. |
| Distributed systems | Normalize Byzantine fault tolerance, consensus, gossip, and observability citations. |
| Computational trust | Normalize epistemic logic, trust propagation, and confidence semantics citations. |
| ETS artifacts | Use stable repo paths and commit references for implementation and experiment artifacts. |

All citations should be converted into the advisor-approved style before
committee circulation. Until then, citation lists are research scaffolding, not
final bibliography.

## Figure Plan

| Figure | Chapter | Purpose |
| --- | --- | --- |
| Figure 1: ETS layered architecture | Chapter 4 | Show evidence, integrity, log, federation, temporal, transport, and epistemic layers. |
| Figure 2: Evidence event lifecycle | Chapter 4 | Show artifact hashing, event creation, append, proof generation, and verification. |
| Figure 3: Verifier federation disagreement | Chapter 5 | Show root observations, quorum assessment, and fork/conflict visibility. |
| Figure 4: Evidence capture workflow | Chapter 7 | Show tests, formal runs, benchmarks, replay manifests, and artifacts. |
| Figure 5: Claim boundary map | Chapter 9 | Show what ETS proves, suspects, defers, and excludes. |

## Tables

| Table | Chapter | Purpose |
| --- | --- | --- |
| Contribution map | Chapter 1 | Map theory, formal, implementation, evaluation, and governance contributions. |
| Related work matrix | Chapter 2 | Compare ETS against transparency logs, consensus, SIEM, and trust systems. |
| Formal model coverage | Chapter 5 | Map model, property, tool, result, and limitation. |
| Implementation traceability | Chapter 6 | Map protocol requirement to code path and tests. |
| Evidence capture matrix | Chapter 7 | Map validation command or workflow to artifact and status. |
| Non-claim table | Chapter 9 | Preserve scientific and governance boundaries. |

## Missouri S&T Formatting Gate

Before committee circulation:

- title page, abstract, acknowledgments, table of contents, lists of figures,
  and lists of tables must follow the required order;
- headings must be normalized to the approved dissertation hierarchy;
- figures and tables must be numbered and captioned;
- appendices must contain formal artifacts, reproduction instructions, and
  proof-status material in a stable order;
- references must use the advisor-approved citation style;
- DOCX/PDF rendering must be reviewed manually.

## Integration Boundary

This sprint produces the integration path and starter prose. It does not
replace advisor review, final citation work, institutional formatting review,
or committee approval.
