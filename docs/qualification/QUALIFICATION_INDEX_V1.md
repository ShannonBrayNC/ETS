# ETS Qualification Index v1

**Tracking:** #798  
**Schema:** `schemas/qualification/v1/qualification-index.schema.json`  
**Registry:** `docs/qualification/qualification-index-v1.json`

## Purpose

The ETS Qualification Index is the authoritative registry for bounded physical qualification claims. It connects a public or internal statement such as "this Edge target is qualified" to the exact device under test, hardware revision, firmware/security-element posture, immutable software/configuration identity, HQP profile version, retained evidence package, independent verifier result, limitations, validity window, and supersession state.

The index does not replace the roadmap. It prevents roadmap maturity language from being mistaken for qualification evidence.

`capability maturity != qualification state != production readiness`

## Claim boundary

A qualification claim applies only to the exact combination recorded in the index:

`product + qualification class + profile/version + DUT/revision + firmware/signer posture + software/configuration build + environment-bound HQP run + retained evidence + independent verifier result`

A passing result for one device, revision, image, signer posture, or profile version does not silently qualify another.

## Publication rule

A claim may be published as `qualified` or `qualified_with_deviation` only when all of the following are true:

1. the HQP run package is complete and retained;
2. required artifacts and Evidence Object bindings are present;
3. the independent HQP verifier marks the claimed disposition as eligible;
4. the exact DUT/revision/build/profile combination is recorded;
5. limitations and deviations are explicit;
6. the claim has not expired or been superseded.

`lab_tested` and `qualification_in_progress` may be published as factual execution states, but they must not be phrased as qualification.

`failed`, `expired`, and `superseded` results remain historically traceable and must not be deleted merely because a later run passes.

## Qualification states

The index uses the common HQP state vocabulary:

- `not_tested`
- `simulated`
- `lab_tested`
- `qualification_in_progress`
- `qualified`
- `qualified_with_deviation`
- `failed`
- `expired`
- `superseded`

The state represents evidence-backed qualification status only. Product roadmap labels such as research, prototype, alpha, beta, pilot, release candidate, or production are separate capability-maturity statements.

## Required claim bindings

Every index entry must identify:

- product and qualification class;
- capability maturity at the time of the claim;
- HQP profile identifier and version;
- DUT manufacturer, model, hardware revision, asset identifier, firmware map, and signer profile;
- immutable source/build revision, artifact digest, and configuration digest;
- HQP run package and deterministic qualification report;
- artifact-manifest digest and referenced Evidence Object identifiers;
- independent verifier identity, result location, result digest, and disposition eligibility;
- limitations;
- effective/expiry timestamps;
- supersession links.

## Requalification triggers

A published physical qualification claim requires requalification when a claim-critical dimension changes. At minimum, triggers include:

- DUT model or hardware revision;
- boot firmware or claim-critical device firmware;
- storage device/firmware where durability or recovery is in scope;
- TPM, secure element, signer, or key-custody profile;
- Secure Boot or storage-protection posture when part of the profile claim;
- immutable Edge software artifact or source revision;
- claim-critical configuration digest;
- HQP profile version or required corpus semantics;
- a claim-critical environment assumption;
- verifier contract/version changes that invalidate prior eligibility;
- newly discovered evidence showing the prior claim was incomplete or incorrect.

A change may be handled by a formally defined equivalence profile only when the product-specific profile explicitly permits it. Edge currently defaults to no cross-revision qualification by implication.

## Expiration

Profiles may define time-based expiration or event-based expiration. Even without a calendar expiry, a claim becomes invalid for current use when a requalification trigger occurs.

The historical entry remains retained and transitions to `expired` or `superseded`; it is not rewritten as though the prior qualification never existed.

## Supersession

When a new claim replaces an earlier claim:

1. the new entry records `supersedes=<old claim id>`;
2. the old entry records `superseded_by=<new claim id>`;
3. the old entry transitions to `superseded` once the new claim is authoritative;
4. both evidence packages remain independently retrievable.

A failed replacement attempt does not automatically supersede a previously valid claim unless a separate requalification trigger already invalidated that earlier claim.

## Failure and invalidity

A test failure and an invalid run are different:

- **failed** — the test was validly executed and the DUT did not satisfy the required criterion;
- **invalid** — required evidence, provenance, identity binding, or execution integrity was insufficient to support a qualification disposition.

The v1 index does not publish `invalid` as a qualification state because an invalid execution does not create a qualification claim. Invalid runs remain retained in the underlying HQP execution corpus and may be referenced in engineering records.

## Roadmap governance

The public roadmap may summarize qualification only by reference to the index. It may say a named profile is qualified only when an active index entry supports that statement.

The roadmap must not infer qualification from:

- a merged PR;
- green CI;
- an implemented feature;
- a simulated test;
- a historical issue checkbox;
- an unverified producer-side report;
- qualification of a different hardware revision;
- qualification of a related product.

## Initial registry state

The v1 registry is intentionally initialized with zero published physical qualification claims.

That is a positive governance property: HQP-0 through HQP-4 provide contracts, tooling, corpora, and reuse bindings, but no physical Edge Compact R0 claim should appear until Wave 1 executes on a named DUT and passes independent verification.

## Wave 1 integration

Wave 1 tracker #814 is the first intended producer of an Edge Compact R0 index entry.

The R0 entry must preserve the deliberately weaker initial trust posture:

```text
identity_profile: software_volume
hardware_attested: false
secure_boot_verified: false
hardware_key_protection: false
qualification_class: EDGE_COMPACT_R0
```

A successful R0 entry therefore supports a bounded claim about physical Edge evidence semantics and recovery behavior. It does not imply hardware-attested identity. Edge Enterprise R1 will establish that stronger boundary in a later qualification profile.
