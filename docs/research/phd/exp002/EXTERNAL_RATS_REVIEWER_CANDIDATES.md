# EXP-002 — External RATS Reviewer Candidates

**Status:** outreach preparation  
**Date:** 2026-09-12  
**Goal:** obtain an independent technical challenge from a person with current RATS/attestation expertise before EXP-002 is permitted to support any doctoral contribution claim.

## Selection criteria

The preferred reviewer should:

- be independent of ETS/Lantern Protocol;
- have demonstrated technical depth in RFC 9334/RATS, EAT, attestation results, endorsements, multi-verifier composition or adjacent work;
- be willing to challenge the strongest-RATS baseline rather than validate ETS;
- be able to distinguish ordinary RATS profiling from genuinely additional normative rules;
- disclose relevant conflicts or prior collaboration;
- permit the review outcome, including adverse findings, to be retained in the research record.

## Ranked candidates

### 1. Ned Smith — primary recommendation

**Why:** current co-chair of the IETF RATS Working Group; co-author of RFC 9334; active in current RATS work including CoRIM and multi-verifier material. Current IETF metadata lists him as independent and provides a public standards contact address.

**Public contact:** `ned.smith.ietf@outlook.com`

**Why first:** combines architectural authority, active standards involvement and independence from ETS. A challenge from a current RATS chair would carry substantial methodological weight.

**Risk:** availability/time constraints due to WG leadership.

### 2. Henk Birkholz — primary alternate

**Why:** co-author of RFC 9334 and active author/editor across current RATS interaction models, endorsements, CoRIM and related work; Fraunhofer SIT.

**Public contact:** `henk.birkholz@sit.fraunhofer.de` (also appears in IETF metadata under `henk.birkholz@ietf.contact` for some documents).

**Why strong:** exceptionally broad architectural and implementation context across the RATS ecosystem.

**Risk:** similarly high standards workload.

### 3. Anton Sokolov — direct-overlap specialist

**Why:** author of the August 2026 Internet-Draft *Composing Application-Layer Action Evidence with Remote Attestation Procedures*. That draft is unusually close to ETS machine-action evidence because it binds action, authority and outcome records to RATS while explicitly preserving the self-report/independent-observation boundary.

**Public contact:** `anton.sokolov@tyche.institute`

**Why strong:** likely the most direct adversarial reviewer for EA-C005 / machine-action evidence and consequence-boundary claims.

**Risk:** the AEP draft is an individual Internet-Draft and not an adopted WG standard; review is highly relevant but should not be treated as IETF consensus.

### 4. Dave Thaler — architecture/endorsement specialist

**Why:** co-author of RFC 9334 and active author of current RATS Endorsements work.

**Public contact:** `dave.thaler.ietf@gmail.com`

**Why strong:** deep architectural and standards expertise; especially useful for distinguishing profile semantics from architecture-level contribution.

### 5. Michael Richardson — architecture/composite-attester specialist

**Why:** co-author of RFC 9334 and continuing contributor to composite-attester and RATS-related work.

**Public contact:** `mcr+ietf@sandelman.ca`

**Why strong:** useful second-line reviewer for composition, trust-boundary and deployment questions.

## Outreach strategy

Use a staged approach rather than sending a bulk request.

1. Contact **Ned Smith** first with the frozen reviewer brief and a concise explanation that the requested role is explicitly adversarial.
2. If unavailable or no response after a reasonable interval, contact **Henk Birkholz**.
3. Independently consider **Anton Sokolov** for a second, narrower review of machine-action/action-evidence overlap even if Ned or Henk accepts the general review.
4. Preserve all review correspondence and resulting classifications as research provenance.

## Requested review scope

The reviewer should receive:

- `EXP-002_RATS_EQUIVALENCE_PREREGISTRATION.md`;
- `SCENARIO_CORPUS.json` (S01–S20);
- `RATS_STRONG_BASELINE_PROFILE.md`;
- `INTERNAL_RATS_REDTEAM_FINDINGS.md`;
- `EQUIVALENCE_RUBRIC.md`;
- `EXTERNAL_RATS_REVIEWER_BRIEF.md`;
- `WP1_RATS_2026_EMERGING_PRIOR_ART.md`.

The reviewer is asked to find stronger RATS encodings, identify any scenario misclassified as requiring profile/extra-rule behavior, and explicitly attempt to eliminate ETS differentiation.

## Acceptance rule

A reviewer agreeing with ETS is not the objective. A high-quality review may conclude that the internal red-team baseline already collapses the alleged distinctions. Such a result must be retained and may require narrowing or retiring EA-C001/EA-C003/EA-C005 novelty claims.
