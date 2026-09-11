# Evidence Architecture Technical Manual — 2026-09-11 Synchronization Addendum

**Status:** manual synchronization addendum  
**Source baseline:** `main` at `f4e576e4fdecf032f94a69cdc67f461ea99c2272`  
**Purpose:** bring the manual-facing Evidence Architecture narrative into alignment with the current canonical ETS research and Ranger evidence contracts after the September 2026 research merges.

This addendum is not a replacement for the full manual. It is the normative delta that must be incorporated into the next integrated edition. Where older manual wording conflicts with this document or with the cited canonical research artifacts, the newer bounded formulation governs.

## 1. The central epistemic boundary

Evidence Architecture must distinguish provenance, epistemic warrant, and objective reality.

A useful shorthand is:

```text
provenance != truth
integrity != correctness
authentication != authority
repetition != independent corroboration
precedence != causation
institutional acceptance != certainty
```

A cryptographically intact artifact can faithfully preserve an error, deception, incomplete observation, biased sample, or incorrect inference. Cryptography can establish bounded propositions about identity, integrity, sequence, lineage, and signatures. It cannot manufacture objective truth.

The strongest defensible claim is therefore not "the system proves reality." It is that the system preserves enough structure for an independent verifier to determine what the supplied evidence supports, what it contradicts, what remains unknown, and which assumptions are still external.

Canonical sources: `docs/dissertation/EPISTEMIC_PROVENANCE.md`, `docs/dissertation/EVIDENCE_THEORY.md`.

## 2. Typed epistemic relations

Evidence Graphs should not collapse materially different relationships into one generic edge. The architecture now distinguishes relations such as:

- `OBSERVED` — a source encountered a state or signal;
- `ASSERTED` — an actor expressed a proposition;
- `REPORTED` — a source relayed another assertion;
- `DERIVED_FROM` — an artifact was transformed from another artifact;
- `CORROBORATES` — evidence independently supports a proposition under declared criteria;
- `CONTRADICTS` — evidence conflicts with a proposition or observation;
- `INFERRED` — a conclusion was produced from declared inputs and assumptions;
- `INTERPRETED` — a human or model assigned meaning to evidence;
- `PRECEDES` — one event temporally precedes another;
- `CONTRIBUTES_TO`, `CAUSES`, and `NECESSITATES` — progressively stronger causal claims that require explicit supporting assumptions.

These relations are not interchangeable. In particular:

```text
ASSERTED != OBSERVED
PRECEDES != CAUSES
AUTHENTICATED != AUTHORIZED
COMMAND_ACCEPTED != PHYSICAL_RESULT
```

## 3. Epistemic distance and observability boundaries

Evidence Architecture now treats epistemic distance as multidimensional. Relevant dimensions can include:

- time between event, observation, recording, and evaluation;
- transformation depth;
- number of intermediary reporters;
- loss of original context;
- dependence on shared upstream sources;
- model or analyst inference depth;
- uncertainty introduced at each transition.

No universal scalar confidence score is required. If a policy computes one, the underlying factors must remain inspectable.

Every evidence system also has an observability boundary: the set of conditions it was capable of observing, recording, retaining, and retrieving. Absence outside that boundary must not be promoted to evidence of absence without an explicit expectation model.

## 4. Source independence and common-source collapse

Artifact count is not witness count. Ten reports copied from one originating source may be ten artifacts but only one independent evidentiary branch.

Evidence Graph implementations should preserve ancestry sufficient to identify common upstream dependencies. Corroboration logic should discount or collapse dependent branches when it would otherwise overstate independent support.

This is especially important for AI-assisted analysis, retrieval systems, and Internet-scale reporting where multiple outputs can inherit one source silently.

## 5. Interpretation provenance and claim genealogy

Interpretations are themselves evidence-producing events. A human analysis, AI Witness conclusion, classifier result, forensic reconstruction, or narrative summary should retain provenance to:

```text
input evidence
+ method/model/version
+ assumptions
+ analyst/agent identity
+ parameters/policy
+ time/context
-> conclusion
```

Evidence Architecture should also support claim genealogy: the history of a proposition across initial assertion, repetition, paraphrase, strengthening or weakening, independent corroboration, contradiction, correction, and retraction.

Repeated publication does not automatically increase independent evidentiary weight.

## 6. Prior-art and novelty boundary

The current prior-art qualification materially narrows what ETS should claim as original.

The following broad ideas are not novel and must not be presented as ETS inventions:

- provenance graphs;
- signed provenance objects;
- append-only Merkle transparency logs;
- chain-of-custody practice;
- software supply-chain attestations;
- content provenance manifests;
- cryptographic signing of process metadata.

The current candidate research gap is narrower: typed evidentiary claim and edge semantics, explicit verification-state boundaries, and preservation of unsupported assumptions across heterogeneous digital, AI, distributed, and cyber-physical evidence chains.

EA-C001 and EA-C002 remain candidate contributions until broader scholarly review and independent evaluation justify stronger language.

Canonical source: `docs/research/phd/LITERATURE_PRIOR_ART_EA_C001_C002.md` and the current WP1 literature artifacts.

## 7. Independent machine-action provenance

The 2026 autonomous-agent case study sharpens a general architecture rule:

> The subject of an investigation must not be the sole authority for the evidence used to establish its own consequential actions.

For consequential machine actions, the evidence model should separate:

```text
environment observation
-> execution identity
-> policy / authorization state
-> requested action
-> actor-side record
-> independent witness record
-> tool or actuator invocation
-> externally observed effect
-> resulting state
-> custody / integrity commitments
-> independent verification
```

The independent witness need not capture private chain-of-thought. The evidentiary requirement is at the externally meaningful decision/action boundary: identity, relevant inputs or commitments to them, policy state, authority, requested operation, invocation, result, state transition, order, and integrity.

Canonical source: the OpenAI/Hugging Face 2026 Evidence Architecture case study merged in PR #616.

## 8. ETS Adversarial Qualification

Evidence Architecture now includes ETS Adversarial Qualification, or EAQ, as a research program for deliberately challenging security and evidence invariants in authorized isolated environments.

EAQ principles include:

- authorization before testing;
- isolation by default;
- invariant-driven rather than tool-driven tests;
- independent observation of the qualification run;
- explicit PASS / FAIL / INCONCLUSIVE / BLOCKED semantics;
- remediation followed by retained regression evidence;
- qualification evidence that is itself reproducible and reviewable.

EAQ is additive. It does not mean that every current ETS component has passed a mature adversarial release gate. The program begins as research and can mature toward release qualification as the evidence warrants.

Canonical sources: `docs/security/ETS_ADVERSARIAL_QUALIFICATION_PROGRAM.md`, `docs/security/EAQ_RESEARCH_ROADMAP.md`.

## 9. Historical key standing is not current authority

Ranger R0.2 now provides an executable example of a key epistemic distinction.

A valid historical publisher or custodian signature does not imply that the key remains currently authorized after rotation or revocation. The publication key-lifecycle profile therefore separates:

1. source-signature validity;
2. authority-relative standing at an exact retained lifecycle-history prefix; and
3. current authorization relative to the larger history presented to the verifier.

This allows old evidence to remain historically verifiable while refusing to treat an old key as current authority.

The lifecycle model uses authority-signed append-only enrollment, dual-proof rotation, bounded revocation, predecessor and sequence checks, role separation, cross-role key-reuse rejection, and source-key-standing records bound to an exact history prefix.

Successful verification still does not establish source-signature time, trusted time, global currentness, operational authorization, physical WORM storage, organizational independence, complete capture, semantic truth, or physical outcome.

Canonical source: `docs/research/ranger/publication-key-lifecycle.md` and ADR 0013.

## 10. Freshness is verifier-relative unless independently anchored

A cryptographically valid history can still be stale. A verifier can strengthen freshness by retaining a prior trusted head or comparing against an independently retained checkpoint, but the claim remains relative to that retained view unless a stronger external latest-state authority is configured.

Therefore:

```text
valid history != globally current history
fresh relative to retained head != universal freshness
```

The manual should avoid language that converts successful verification into a global currentness claim.

## 11. Consequence custody remains a stronger claim

The existing Reconstruction, Standing, and Consequence Custody boundaries remain intact.

- Reconstruction asks what can be established about prior events from the evidence now available.
- Standing asks whether the material predicates authorizing an action or decision held under the applicable policy context.
- Consequence Custody asks whether the transition from standing-qualified state into consequence was itself governed and evidenced.

A component may support reconstruction or standing evaluation without enforcing consequence custody. Only an implementation that actually makes valid standing a prerequisite to binding the consequential transition may claim consequence custody.

## 12. Manual terminology corrections

Future integrated editions should prefer the following language:

| Avoid | Prefer |
|---|---|
| "proof that the event really happened" | "evidence supporting a bounded proposition about the event" |
| "verified truth" | "verified integrity / identity / provenance / standing under stated assumptions" |
| "the log proves the result" | "the log preserves a signed or committed record of the reported result" |
| "multiple reports corroborate" | "independent reports corroborate, subject to ancestry analysis" |
| "timestamp proves when it happened" | "timestamp records a time claim unless bound to trusted-time evidence" |
| "valid old signature means authorized" | "historical signature validity and current authorization are separate" |
| "no record means it did not happen" | "absence is bounded by the observability and retention model" |

## 13. Integration checklist for the next full manual edition

The next consolidated manual should incorporate this addendum into the primary prose rather than leave it as a detached appendix. At minimum:

- revise introductory epistemology so evidence does not become synonymous with objective truth;
- add typed epistemic relations and claim genealogy to the Evidence Graph chapter;
- add observability boundaries and source-independence treatment to evidence quality;
- add interpretation provenance to AI Witness and forensic-analysis sections;
- narrow novelty language using the current prior-art qualification;
- add the machine-action provenance case study;
- add EAQ as the adversarial qualification discipline;
- add historical-key-standing versus current-authority semantics;
- preserve trusted-time, global-currentness, completeness, and physical-outcome nonclaims;
- update the mathematical appendices with the formal deltas in `docs/dissertation/EPISTEMIC_PROVENANCE_MATHEMATICAL_APPENDIX.md`.

## 14. Nonclaim

This synchronization does not promote any candidate doctoral contribution to established novelty, does not create an empirical result for EXP-001, does not claim legal sufficiency, and does not convert any current software-reference profile into production certification.
