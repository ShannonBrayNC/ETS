# Ranger Epistemic Identity and Bounded Observability

**Status:** Research requirement  
**Program:** ETS Ranger R0  
**Purpose:** Define how Ranger represents person recognition, identity claims, uncertainty, contradiction, and absence of knowledge without overstating what its sensors or credentials establish.

## Principle

Ranger SHALL NOT elevate the epistemic strength of an evidence claim beyond the capability of the mechanism that produced it.

A credential can establish possession or use of a credential. A face matcher can establish similarity to an enrolled biometric template. GNSS can establish a location observation subject to its measurement and trust limits. Ranging can establish a proximity observation. None of these observations, alone, proves the complete human narrative.

ETS therefore preserves the provenance of claims and observations rather than silently converting observations into stronger facts.

`Observed != Authenticated != Inferred != Proven`

## Identity is a claim graph

Ranger should separate at least these propositions:

`Detection -> Continuity -> Recognition -> Identity Claim -> Identity Verification`

- **Detection:** a sensor reports a human or other subject.
- **Continuity:** observations are assessed as belonging to the same subject across time or sensors.
- **Recognition:** an observation matches an enrolled representation within an explicit threshold.
- **Identity claim:** a name, principal, credential, account, or external source associates the subject with an identity.
- **Identity verification:** one or more mechanisms support the identity claim under an explicit policy and assurance level.

These states MUST NOT be collapsed into a single unqualified `identity = person` assertion.

## Enrolled recognition

Ranger R0 may maintain a deliberately small local enrollment set. This permits recognition against registered principals without requiring identification against a large population database.

A successful face-template comparison should be represented as evidence that the observed face matched a particular enrolled template under a specified algorithm, model/version, threshold, quality state, and confidence or score. The enrollment record may associate that template with a named principal, but the template match and the human identity claim remain separately attributable propositions.

Example conceptual chain:

`camera observation -> face representation -> enrolled-template match -> registered-principal claim -> policy evaluation`

The evidence package should retain the source observation identity, matcher/version, enrollment-record identity, threshold, score, relevant quality metadata, and policy that interpreted the result.

## Unknown is first-class evidence

Failure to establish identity is not merely missing data. The reason Ranger did not know something can materially affect whether a later decision was justified.

ETS SHALL distinguish at least:

- **NOT_OBSERVED** — the proposition was not observed or no determination was attempted.
- **NOT_AVAILABLE** — evidence required to evaluate the proposition was unavailable.
- **UNKNOWN** — evaluation occurred but no qualifying identity/evidence was established.
- **INDETERMINATE** — evidence existed but was insufficient to cross the applicable decision threshold.
- **CONTRADICTED** — credible evidence supported incompatible propositions.

These states are semantically distinct and SHOULD be represented explicitly in decision evidence.

The architecture therefore preserves:

`what was known + what was not known + why it was not known`

## Persistent unknown subjects

An unknown person may still require continuity without receiving a human identity. Ranger may assign an event- or mission-scoped pseudonymous subject identifier such as `SUBJECT-7F31` so observations can be correlated without asserting a real-world name.

Such identifiers MUST be distinguishable from registered principals and MUST NOT be interpreted as verified human identities.

## External identity claims

Public or third-party information can supply identity claims but does not automatically supply authoritative identity.

For example, a public profile associating an image with the name `Brian` establishes that the source made that association. It does not by itself establish that the observed person is Brian.

ETS SHOULD preserve:

- source identity and retrieval time;
- the exact claim being relied upon;
- source authority/assurance classification;
- integrity and custody information where available;
- matching method and confidence;
- dependencies between apparently independent sources;
- contradictory identity claims; and
- whether the claim was used in a consequential policy decision.

Repeated claims derived from a common upstream source MUST NOT automatically be treated as independent corroboration.

## Multi-factor physical context

Ranger may combine independent observations such as:

- device or credential identity;
- hardware-backed signatures or attestations;
- enrolled biometric recognition;
- Ranger and subject/device location observations;
- UWB or other ranging/proximity observations;
- trusted or bounded time evidence;
- explicit operator interaction or authorization;
- mission context and policy state.

Combination increases available evidence but does not justify erasing the provenance, uncertainty, or limitations of the individual factors.

## Consequential-action requirement

For any consequential autonomous decision involving a person, the Ranger Decision Event SHOULD preserve the identity-related state that existed at decision time, including unknown and contradictory states.

A verifier should be able to answer:

1. Was a person detected?
2. Was the subject correlated with prior observations?
3. Was identity evaluation attempted?
4. Which evidence sources participated?
5. Did any enrolled principal match?
6. What thresholds and policies were active?
7. What identity state resulted?
8. What uncertainty or contradictions existed?
9. Which identity propositions actually participated in authorization or action selection?
10. What relevant information was unavailable or not observed?

## Example

A defensible event should communicate the semantic equivalent of:

```text
subject: SUBJECT-7F31
observation.class: human
observation.confidence: 0.998
continuity.same_subject: 0.974
enrollment_match.principal: RANGER-USER-001
enrollment_match.score: 0.992
identity_claim.name: <registered principal name>
identity_claim.source: ETS enrollment record
identity_state: REGISTERED_PRINCIPAL_MATCH
external_claims: [unverified claim(s)]
contradictions: [claim conflicts, if any]
```

For an unidentified subject:

```text
subject: SUBJECT-A921
observation.class: human
enrollment_match: NONE
identity_state: UNKNOWN
```

The second record is not deficient merely because it lacks a name. `UNKNOWN` is part of the evidence state available to the decision.

## Policy implication

Autonomy policy SHOULD consume epistemic state rather than treating absence as falsehood or silently substituting a guessed identity. For example, a policy may distinguish a registered principal, an unknown subject, an indeterminate recognition result, and contradictory identity evidence and prescribe different bounded behavior for each.

The exact behavior belongs to mission and safety policy; the evidence architecture's responsibility is to preserve the state and its provenance faithfully.

## ETS research implications

This requirement generalizes beyond facial recognition and Ranger. Evidence Architecture should model epistemic absence wherever consequential systems operate with incomplete information.

Candidate general ETS requirements:

> **Bounded-claim requirement:** ETS SHALL NOT elevate the epistemic strength of an evidence claim beyond the capability of the mechanism that produced it.

> **Epistemic-absence requirement:** ETS SHALL represent epistemic absence as first-class evidence, distinguishing facts that were unknown, unobserved, unavailable, indeterminate, and contradicted at the time of consequence.

These requirements should inform the Ranger Decision Event schema, Evidence Object Model, Evidence Graph Model, inference-provenance research, verifier semantics, and future ETS Black Box reconstruction work.
