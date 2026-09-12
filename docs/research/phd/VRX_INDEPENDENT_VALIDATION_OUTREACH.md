# VectorRail/VRX Independent University Validation Outreach

**Status:** outreach-ready; no independent result claimed  
**Tracks:** #731  
**Release bundle:** `validation/releases/vectorrail-vrx/v0.1.0/`  
**Release-bundle merge commit:** `0a49a9cd9202a6e4251c993ec8b60dd92e071a96`  
**Frozen validation subject:** `a50720ab5ba451c6c97008da63b401fcaf28b34f`  
**Canonical package digest:** `sha256:ae2e40b9a272f077cbe139930d353e7610212b2b1877f51e9fb1a87691b312c0`

## Purpose

Obtain a durable independent university validation result for the frozen VectorRail/VRX consequence-custody experiment without changing the frozen bundle, coaching the reviewer toward a positive answer, or treating interest as validation.

The desired result is not an endorsement of ETS. The reviewer is explicitly invited to reject the result, classify it indeterminate, identify ambiguity, or show that the published contract is insufficient.

## What is frozen

The reviewer must evaluate the already-published bundle exactly as distributed. The following are part of the frozen handoff:

- canonical baseline portable package;
- source trial and acceptance fixtures;
- normative schemas;
- clean-room verifier contract;
- replay manifest;
- seven-case adversarial challenge manifest;
- external validation protocol;
- blank machine-readable independent-validation report;
- `SHA256SUMS` inventory.

Clarifications may be supplied only as separately attributable correspondence. They must not silently alter the normative contract or be folded into the bundle under the same release identifier.

## Reviewer qualification

A suitable reviewer should have credible expertise in at least one of:

- accountable or trustworthy autonomous systems;
- cyber-physical systems;
- formal methods, verification or validation;
- safety-critical software/system assurance;
- machine-action provenance, evidence or accountability.

The reviewer must not be an implementation author. The independence disclosure in the validation protocol remains authoritative.

## Outreach order

### 1. Man-Ki Yoon — NC State Computer Science

**Why first:** His published research profile centers on trustworthy and accountable computing for autonomous systems and cyber-physical systems. That is unusually close to the question this experiment asks: whether evidence about a consequential machine action can be independently reconstructed and challenged.

Public profile: `https://csc.ncsu.edu/people/myoon2/`

### 2. John Baugh — NC State

**Why second:** His work includes formal methods for safe and trustworthy software, verification and validation, and cyber-physical systems. This makes him a strong reviewer for the clean-room contract and the experiment's reproducibility boundary.

Public profile: `https://ccee.ncsu.edu/people/jwb/`

### 3. Radu Calinescu / Centre for Assuring Autonomy — University of York

**Why third:** York's assurance programme focuses directly on evidence-based assurance of AI-enabled autonomous systems. Professor Calinescu's work includes formal verification of autonomous and AI systems, making this a strong independent academic challenge path if the first two contacts do not progress.

Public centre page: `https://www.york.ac.uk/assuring-autonomy/about/our-team/`

## Initial invitation

**Subject:** Independent validation request — reproducible cyber-physical evidence experiment

Professor [Name],

I am developing a research programme on independently verifiable evidence for consequential machine actions. I have frozen a small external-validation experiment around a cyber-physical reference case, VectorRail/VRX, and I am looking for an academic reviewer willing to try to reproduce or defeat the result from the public contract alone.

The experiment is intentionally bounded. It asks whether an independent party can reconstruct the same consequence-custody conclusion from a frozen package containing the source records, Evidence Object projections, dependency graph, hashes, verifier contract and adversarial challenge cases. The expected baseline is `VERIFIED_REPLAYABLE` / `VERIFIED_CONSISTENT`, but a `REJECT` or `INDETERMINATE` result is equally valuable if the contract, evidence or reasoning does not hold.

The frozen release is in the public ETS repository at:

`validation/releases/vectorrail-vrx/v0.1.0/`

Release-bundle commit:
`0a49a9cd9202a6e4251c993ec8b60dd92e071a96`

Frozen validation subject:
`a50720ab5ba451c6c97008da63b401fcaf28b34f`

Canonical package digest:
`sha256:ae2e40b9a272f077cbe139930d353e7610212b2b1877f51e9fb1a87691b312c0`

The bundle includes a reviewer README, SHA-256 inventory, language-neutral verifier contract, canonical baseline, seven adversarial challenges and a blank machine-readable validation report. It is designed so the review does not require access to Lantern infrastructure or private implementation guidance.

I am specifically not asking for an endorsement of ETS or for acceptance of broader claims. A useful review can identify ambiguity, fail a challenge, reject the conclusion, or show that the result is reproducible only under narrower assumptions. The published claim boundary explicitly does not assert sensor correctness, objective physical truth, legal sufficiency, regulatory approval or production safety.

If this falls within your research interests and you would be willing to review it, I would be grateful for an independent result or even a short assessment of where the validation contract is insufficient. I will preserve negative findings and disagreements as part of the research record.

Thank you,
Shannon Bray

## Reviewer task summary

The reviewer should be able to work from the frozen bundle without private guidance and should:

1. verify the SHA-256 inventory and frozen identifiers;
2. implement or independently exercise the clean-room verifier contract;
3. reproduce the canonical baseline or record the exact mismatch;
4. execute every required adversarial challenge;
5. preserve platform/runtime details and ambiguity findings;
6. complete the machine-readable validation report;
7. return `APPROVE`, `REJECT`, or `INDETERMINATE` under the published claim boundary.

## Contact policy

- Send the same frozen references to every reviewer.
- Do not change the release bundle between reviewers.
- Do not lead with a request for endorsement, citation, supervision, funding or adoption.
- A follow-up may ask whether the reviewer had an opportunity to consider the request, but must not pressure for a positive conclusion.
- If a reviewer declines, preserve the decline as outreach history without treating it as a negative technical result.
- If a reviewer identifies ambiguity, preserve the original finding before issuing any later corrected release.

## Result handling

### APPROVE

Record the completed report, reviewer independence basis, verifier/archive reference, environment, baseline result, challenge results, ambiguities and residual limitations. Promote only the bounded claim that was actually validated.

### REJECT

Preserve the report and reproduce the failure internally. Do not edit the frozen release in place. Open a new research issue and, if warranted, produce a new versioned release that documents the correction and why the earlier release failed.

### INDETERMINATE

Preserve the unresolved ambiguity or missing premise. Treat the result as evidence that the current public contract is insufficient for independent validation until the issue is resolved prospectively.

## Completion rule

Issue #731 is complete only when a durable independent report has been preserved or the outreach campaign has been explicitly closed with its outcomes recorded. Silence, an email acknowledgment, an invitation to discuss, or general praise does not satisfy the independent-validation gate.

## Claim boundary

Successful independent replay would support a claim that the frozen experiment is reproducible and that the published validation contract is sufficiently precise for an independent implementation to reach the same bounded result.

It would not establish sensor correctness, objective physical truth, arbitrary-use device safety, legal admissibility, regulatory approval, causal truth beyond the represented evidence, or correctness of ETS outside the frozen experimental scope.
