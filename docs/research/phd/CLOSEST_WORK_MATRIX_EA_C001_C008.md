# Closest-Work Matrix — EA-C001 through EA-C008

**Status:** doctoral prior-art qualification / candidate-contribution narrowing  
**Date:** 2026-09-12  
**Research integrity rule:** This matrix does not establish originality. Its purpose is to identify the strongest adjacent work that could invalidate, narrow, or absorb an ETS candidate contribution.

## Method

For each candidate contribution, identify the nearest established work family, state the material overlap, define the residual ETS hypothesis as narrowly as possible, and state a falsification condition. Where a prior system can represent the same facts but lacks a specific ETS rule, the possible contribution is the rule or verification discipline, not the underlying graph, signature, log, provenance record, or attestation primitive.

Primary baselines for this pass include W3C PROV/PROV-CONSTRAINTS, RFC 9334 RATS, ACCESSPROV, Schneier/Kelsey secure audit logging, provenance-semiring/database provenance, ML provenance frameworks, industrial-control provenance verification, runtime assurance, and assurance-case research.

---

## EA-C001 — Evidence Object model

### Closest work

- W3C PROV and qualified provenance descriptions.
- RFC 9334 Remote ATtestation procedureS (RATS): Attester, Evidence, Verifier, Appraisal Policy, Attestation Result, Relying Party.
- C2PA Content Credentials.
- in-toto / SLSA attestations and supply-chain provenance.
- secure audit records and signed forensic evidence containers.

### Material overlap

Established systems already support signed/attested claims, provenance metadata, producer identity under a trust model, policy-based appraisal, freshness concepts, lineage, and verifier-produced results. RATS in particular already makes clear that Evidence is a set of Claims requiring appraisal, not automatic truth.

### Residual ETS hypothesis

The remaining candidate contribution is not a novel evidence envelope. It is a **domain-general dimensional verification result** that keeps integrity, identity, provenance, custody, freshness, standing, scoped completeness, epistemic state, and consequence linkage independently inspectable and refuses to promote any one verified dimension into semantic truth.

### Falsification condition

Narrow or retire EA-C001 if prior work already provides materially equivalent cross-domain, machine-verifiable decomposition with explicit unsupported-assumption retention and comparable evaluator behavior.

### Research risk

**High.** Many primitives and architectures already exist; only integrated bounded semantics remain plausibly differentiating.

---

## EA-C002 — Evidence Graph model

### Closest work

- W3C PROV-DM / PROV-O / PROV-CONSTRAINTS.
- database provenance and provenance semirings.
- scientific-workflow provenance and run differencing.
- claim/evidence and argumentation graphs.

### Material overlap

Typed provenance graphs, derivation, generation, usage, attribution, delegation, revision, specialization, provenance-of-provenance, and graph reasoning are mature prior art. W3C PROV also permits domain-specific specialization.

### Residual ETS hypothesis

The candidate contribution is an **edge-as-claim verification discipline** in which consequential relationships themselves carry producer/provenance, epistemic status, verification state, dependency information, contradiction/noncausality semantics, and explicit consequence-stage separation.

### Falsification condition

Narrow or retire EA-C002 if existing provenance/argumentation systems already provide substantially equivalent relation-level verification semantics and prevent unsupported certainty propagation across observation → inference → authority → action → consequence.

### Research risk

**High.** The graph itself is plainly not novel; only the verification semantics may survive.

---

## EA-C003 — Explicit trust and claim-boundary decomposition

### Closest work

- RFC 9334 RATS appraisal architecture and trust assumptions.
- authorization-provenance research, including ACCESSPROV.
- assurance-case / dependability argumentation.
- trust-management and policy-evaluation systems.

### Material overlap

RATS already distinguishes Evidence from Attestation Results and gives Verifiers and Relying Parties separate appraisal policies. ACCESSPROV traces inputs to access-control decisions. Assurance cases explicitly separate claims, arguments, and evidence.

### Residual ETS hypothesis

ETS may contribute a **non-collapse verification rule**: integrity, identity, provenance, authority, standing, completeness, consequence, and semantic truth remain separately reportable even when several are supported by the same evidence package.

### Falsification condition

Narrow or retire EA-C003 if comparable systems already enforce equivalent machine-readable claim-boundary separation and show that it prevents trust-category errors without requiring an ETS-specific model.

### Research risk

**Medium-high.** The conceptual distinction is defensible, but evidence is needed that the decomposition changes verifier/evaluator outcomes.

---

## EA-C004 — Offline/asynchronous evidence continuity

### Closest work

- secure/forward-integrity logging.
- distributed logs, replicated histories, event sourcing and eventual consistency.
- transparency-log consistency/inclusion mechanisms.
- workflow provenance under disconnected or distributed execution.

### Material overlap

Tamper-evident history, append-only logs, replay handling, partitioned replication, eventual synchronization, and distributed-ordering problems are mature fields.

### Residual ETS hypothesis

The remaining hypothesis is that **bounded evidentiary properties can survive asynchronous transport and later reconciliation while preserving uncertainty about ordering, freshness, completeness, custody and authority rather than reconstructing a falsely total history**.

### Falsification condition

Narrow or retire EA-C004 if existing replicated/provenance-log approaches already preserve the same bounded verification vector and uncertainty semantics under equivalent partition/fault models.

### Research risk

**Medium.** Strong prior art exists in distributed systems, but ETS may have a narrower evidence-semantics contribution.

---

## EA-C005 — AI Witness / machine-action provenance

### Closest work

- end-to-end ML pipeline provenance (e.g. MLflow2PROV).
- yProv4ML and related PROV-based ML lineage systems.
- Atlas and attestable ML lifecycle/supply-chain provenance.
- model lineage / model genealogy research.
- AI assurance and runtime monitoring.

### Material overlap

Training-data lineage, pipeline provenance, model identity, artifact authenticity, deployment lineage, genealogy, and attestable ML operations are active established research areas.

### Residual ETS hypothesis

The candidate contribution is not model lineage. It is **consequential machine-action evidence** that separates input observation, inference/output, policy/authority, decision, requested tool/action, accepted/executed action, consequence, and resulting observation without depending on hidden chain-of-thought or claiming semantic correctness of the model.

### Falsification condition

Narrow or retire EA-C005 if existing AI provenance/accountability systems already capture and independently verify the same action/consequence chain with equivalent uncertainty and authority semantics.

### Research risk

**Medium-high.** AI provenance is moving quickly; novelty must be continuously revalidated.

---

## EA-C006 — Cyber-physical decision provenance

### Closest work

- F2-Pro / Message Authentication and Provenance Verification for Industrial Control Systems.
- runtime assurance architectures for autonomous systems.
- dynamic/continuous assurance cases.
- cyber-physical logging and control-message provenance.

### Material overlap

Peer-reviewed ICS work already provides cryptographically verifiable message-source/path provenance and evidence that commands traversed required checks. Runtime-assurance research already separates advanced autonomous behavior from safety-monitor/controller mechanisms.

### Residual ETS hypothesis

The remaining candidate contribution is **cross-boundary evidence decomposition** from observation through inference, authority, command, actuator execution, and independently observed resulting physical state, with an explicit rule that authenticated command provenance does not establish actuator execution or physical consequence.

### Falsification condition

Narrow or retire EA-C006 if cyber-physical provenance/assurance literature already provides equivalent independently verifiable command→execution→result decomposition under comparable sensor/actuator fault models.

### Research risk

**Medium.** This is one of the stronger remaining empirical opportunities, but F2-Pro materially narrows message-provenance novelty.

---

## EA-C007 — Consequence custody

### Closest work

- digital-forensics chain of custody.
- safety/assurance cases linking claims to runtime evidence.
- runtime assurance and safety interlocks.
- transactional/audit approaches that verify committed state transitions.
- cyber-physical provenance and independent sensing.

### Material overlap

Custody, signed transfer histories, runtime assurance, safety evidence, and state-transition logging are established. The phrase "consequence custody" must therefore not be used to imply that custody itself is novel.

### Residual ETS hypothesis

The candidate contribution is a distinct **post-action evidentiary boundary** requiring separately attributable evidence for the resulting external/digital state and preserving custody/provenance of that consequence evidence rather than inferring outcome from intent, authorization, command, acknowledgment, or execution claim.

### Falsification condition

Narrow or retire EA-C007 if existing assurance/forensics/control literature already defines an equivalent generalized boundary and demonstrates independent result-state verification across digital and physical systems.

### Research risk

**Medium-high conceptually, potentially high-value empirically.** The terminology may be new while the substance may overlap existing safety/transaction/forensic concepts; experiments must establish useful distinction.

---

## EA-C008 — Evidence-aware adversarial qualification

### Closest work

- penetration/adversarial testing with reproducible test artifacts.
- formal security models and fault injection.
- secure logging and auditability of test systems.
- safety/assurance evidence management.
- reproducible systems-security experimentation.

### Material overlap

Adversarial qualification, fault injection, formal attacker models, negative-result reporting, reproducibility, and test-artifact provenance are not novel individually.

### Residual ETS hypothesis

The remaining candidate contribution is to treat **the evidence generated by the qualification itself as a first-class object subject to the same provenance, custody, trust-boundary, standing, contradiction and consequence rules as the system under test**, enabling independent verification of both the tested claim and the qualification chain.

### Falsification condition

Narrow or retire EA-C008 if prior assurance/security-test frameworks already provide materially equivalent evidence-of-evidence semantics and independent verification of the qualification process.

### Research risk

**Medium-high.** Likely valuable as a research methodology even if it does not survive as a standalone original contribution.

---

# Cross-contribution disposition

| ID | Candidate contribution | Broad novelty status | Residual thesis value | Current risk |
|---|---|---|---|---|
| EA-C001 | Evidence Object | broad claim rejected | dimensional bounded verification | High |
| EA-C002 | Evidence Graph | broad claim rejected | edge-as-claim / epistemic propagation rules | High |
| EA-C003 | Trust decomposition | overlapping prior art | non-collapse verification discipline | Medium-high |
| EA-C004 | Offline continuity | mature distributed/logging prior art | bounded evidence semantics under partition/reconciliation | Medium |
| EA-C005 | AI Witness | ML provenance/lineage overlap | external machine-action/consequence evidence | Medium-high |
| EA-C006 | CPS provenance | message provenance/runtime assurance overlap | command-execution-result decomposition | Medium |
| EA-C007 | Consequence custody | custody/assurance overlap | independent post-action result boundary | Medium-high |
| EA-C008 | Adversarial qualification | testing/reproducibility overlap | qualification evidence as first-class evidence | Medium-high |

# Strongest doctoral synthesis after this pass

The most defensible thesis is increasingly **architectural and compositional rather than primitive-level**:

> A consequential machine system should not emit a single undifferentiated "verified" history. It should preserve independently inspectable evidence for observation, inference, identity, integrity, authority/standing, decision, requested action, execution, consequence and resulting state; explicitly preserve unknown/unsupported/contradicted states; and allow an independent verifier to determine which transitions are supported without promoting cryptographic validity or provenance connectivity into semantic truth.

This remains a hypothesis, not an originality claim.

# Highest-priority falsification tests

1. **RATS equivalence test:** determine whether dimensional ETS verification is substantively stronger than rich RATS Attestation Results plus application-specific appraisal policy, or merely a vocabulary/profile difference.
2. **PROV-extension equivalence test:** determine whether ordinary W3C PROV plus domain extensions can reproduce all claimed ETS semantics without the EA rules providing measurable evaluator benefit.
3. **F2-Pro/CPS equivalence test:** determine whether command-path provenance plus runtime assurance already subsumes the claimed cyber-physical contribution.
4. **Assurance-case equivalence test:** determine whether dynamic assurance cases already provide the claimed standing/consequence separation in functionally equivalent form.
5. **AI provenance equivalence test:** re-run literature qualification before publication because AI provenance/agent accountability is rapidly evolving.

# Primary references for this matrix

- W3C, PROV-DM / PROV-CONSTRAINTS / PROV-O: https://www.w3.org/TR/prov-dm/ ; https://www.w3.org/TR/prov-constraints/ ; https://www.w3.org/TR/prov-o/
- Birkholz et al., RFC 9334, Remote ATtestation procedureS (RATS) Architecture: https://www.rfc-editor.org/rfc/rfc9334.html
- Capobianco, Skalka, Jaeger, ACCESSPROV: Tracking the Provenance of Access Control Decisions, TaPP 2017.
- Schneier and Kelsey, Secure Audit Logs to Support Computer Forensics, ACM TISSEC, 1999.
- Green, Karvounarakis, Tannen, Provenance Semirings, PODS 2007.
- Esiner et al., Message Authentication and Provenance Verification for Industrial Control Systems, ACM TCPS 7(4), 2023, DOI 10.1145/3607194.
- Schlegel and Sattler, Capturing end-to-end provenance for machine learning pipelines, Information Systems 132 (2025), article 102495.
- Padovani, Anantharaj, Fiore, yProv4ML: Effortless provenance tracking for machine learning systems, SoftwareX 31 (2025), 102298.
- Spoczynski, Melara, Szyller, Atlas: A Framework for ML Lifecycle Provenance & Transparency, EuroS&P Workshops 2025.
- Schierman et al., Runtime Assurance for Autonomous Aerospace Systems, Journal of Guidance, Control, and Dynamics.
- ACCESS: Assurance Case Centric Engineering of Safety-critical Systems, Journal of Systems and Software, 2024.

# Next gate

No candidate contribution should be promoted solely from this matrix. The next step is prospective testing of the highest-risk distinctions—first RATS/PROV equivalence and evaluator error reduction, then cyber-physical command/execution/result separation.