# Evidence Standing and Consequence Custody

Status: normative architecture boundary for ETS Evidence Architecture.

Refs: #547

## 1. Purpose

ETS distinguishes evidence reconstruction from standing and from consequence custody.
These are related but materially different guarantees and MUST NOT be collapsed into a
single meaning of replay, verification, or trust.

The architecture is computational-regime neutral. It applies to probabilistic,
deterministic, formally constrained, human-operated, and hybrid systems.

## 2. Canonical boundaries

### 2.1 Reconstruction Boundary

The Reconstruction Boundary asks:

> Can the system establish what happened, under what conditions, and what remains
> unknown?

Reconstruction concerns evidence sufficient to evaluate claims about prior events,
actions, artifacts, states, transitions, and outcomes. Reconstruction does not by
itself establish that an action or consequence was authorized when it occurred.

### 2.2 Standing Boundary

The Standing Boundary asks:

> Did the material predicates authorizing an action, decision, transition, or
> consequence hold at the relevant time?

Standing can depend on authority, identity, policy, consent, entitlement, scope,
validity windows, revocation, jurisdiction, external conditions, contradictory
evidence, and other predicates.

A historically valid decision can lose standing without its original evidence
becoming false. Conversely, a well-preserved event can be reconstructed even when
it never possessed valid standing.

Standing evaluation MUST therefore remain distinct from event integrity, Merkle
inclusion, log continuity, replay, and reconstruction.

### 2.3 Consequence Custody Boundary

The Consequence Custody Boundary asks:

> Was the transition from a standing-qualified state into consequence itself governed,
> and can that governance be evidenced?

Consequence custody is a stronger execution guarantee than retrospective evidence
alone. A consequence-custodial implementation MUST evaluate all required standing
predicates before bind and MUST fail closed when required standing is absent,
expired, revoked, contradictory, unverifiable, or otherwise invalid.

The canonical fail-closed rule is:

> **NO STANDING -> NO BIND**

This rule is normative only for implementations that claim consequence custody. ETS
components that merely capture, preserve, transport, or verify evidence MUST NOT be
represented as providing consequence custody unless they actually enforce the rule at
the bind boundary.

## 3. Evidence classes

ETS uses the following implementation-neutral evidence classes.

### 3.1 Evidence of State

Evidence describing the relevant state of a subject, system, policy, identity,
resource, authority, or environment at a point or interval in time.

Examples include configuration state, policy version, identity assignment, authority
scope, model/version identity, consent state, entitlement, resource state, and
external-condition observations.

### 3.2 Evidence of Standing

Evidence sufficient to evaluate whether the predicates authorizing a proposed or
completed action, decision, transition, or consequence held at the relevant time.

Evidence of Standing MUST identify the predicates evaluated and SHOULD preserve the
policy, authority, identity, temporal, and external-state references used in the
evaluation.

### 3.3 Evidence of Transition

Evidence describing an attempted or completed state transition, including its source
state, target state, triggering action or decision, relevant standing evaluation, and
transition result.

Where consequence custody is claimed, Evidence of Transition MUST bind the transition
to the standing evaluation that authorized or denied it.

### 3.4 Evidence of Consequence

Evidence describing the consequence that actually formed, including its relationship
to the transition that produced it and, where applicable, the standing evaluation
under which that transition was permitted to bind.

Evidence that a consequence exists is not equivalent to evidence that the consequence
had lawful or policy-valid standing to form.

## 4. Architectural progression

ETS recognizes three progressively stronger architectural guarantee classes.

### 4.1 Evidence Architecture

Evidence Architecture captures, preserves, correlates, and makes evidence independently
verifiable so claims can be evaluated. It can establish evidence about standing but
does not necessarily enforce standing before consequence.

### 4.2 Standing-aware architecture

A standing-aware architecture evaluates standing as an explicit architectural object
before or during a consequential transition. It can produce Evidence of Standing and
bind that evaluation to the transition record.

A standing-aware architecture MAY still permit consequence despite failed standing if
its policy allows override, advisory-only evaluation, or deferred enforcement. It
therefore MUST NOT automatically be described as consequence-custodial.

### 4.3 Consequence-custodial architecture

A consequence-custodial architecture makes valid standing a prerequisite to binding
consequence.

It MUST:

1. identify the standing predicates required for bind;
2. evaluate those predicates at the relevant transition time;
3. fail closed when required standing is absent or invalid;
4. bind the standing evaluation to the attempted transition;
5. distinguish denied transitions from successfully bound consequences;
6. preserve sufficient evidence to reconstruct the evaluation and transition; and
7. expose the boundary and its guarantees without requiring trust in an undocumented
   internal assertion.

## 5. Replay semantics

Replay MUST be qualified by the guarantee it provides.

Possible replay semantics include:

- **event replay** — re-presenting a prior recorded event;
- **evidence replay** — reproducing the evidence and verification path for a claim;
- **state replay** — reconstructing relevant system state;
- **decision replay** — re-evaluating a decision under defined inputs and rules;
- **standing replay** — evaluating whether standing held under the state and conditions
  that existed at the relevant time;
- **transition replay** — reconstructing or re-evaluating whether a transition was
  permitted to bind.

For nondeterministic systems, regenerating an identical model output is neither
required nor generally sufficient for evidence replay. For deterministic or formally
constrained systems, stronger reproducibility guarantees MAY exist and SHOULD be
stated explicitly.

No ETS document may use `replay` without enough context to identify which guarantee is
being claimed.

## 6. Verifier boundary

`standing_status=current_log` in ETS Verifier v1 means only that the evidence remains
included in the current append-only log view and that continuity from the verified
checkpoint has been established.

It does **not** mean that:

- an authorization remains valid;
- consent remains active;
- an entitlement still exists;
- an identity retains authority;
- a policy remains unchanged;
- a decision still has standing; or
- a consequence was permitted to bind.

Those are separate claims requiring standing evidence and, when consequence custody
is claimed, enforcement evidence from the consequence-custody boundary.

## 7. Claim discipline

ETS documentation, APIs, user interfaces, and qualification evidence MUST state the
strongest guarantee actually established and MUST NOT silently widen a weaker claim.

In particular:

- integrity MUST NOT be described as standing;
- inclusion MUST NOT be described as authorization;
- continuity MUST NOT be described as current entitlement;
- reconstruction MUST NOT be described as consequence custody;
- Evidence of Consequence MUST NOT be described as Evidence of Standing; and
- standing-aware behavior MUST NOT be described as `NO STANDING -> NO BIND` unless
  bind is actually prevented when required standing fails.

## 8. Qualification requirements

Any ETS component that claims consequence custody MUST be qualified with at least:

1. a valid-standing positive control that binds consequence;
2. a missing-standing negative control that does not bind consequence;
3. an expired or revoked-standing negative control that does not bind consequence;
4. a contradictory or failed predicate control that does not bind consequence;
5. retained Evidence of Standing and Evidence of Transition for both permitted and
   denied attempts; and
6. restart/recovery evidence showing that a previously denied transition cannot bind
   merely because runtime state was lost or restarted.

Where a component does not claim consequence custody, its qualification MUST state the
boundary explicitly rather than implying enforcement it does not provide.

## 9. Architectural invariant

The system of record for ETS architectural meaning is:

**Reconstruction establishes what can be evidenced about what happened. Standing
establishes whether the material predicates for an action or consequence held.
Consequence custody governs whether a standing-qualified transition is permitted to
bind into consequence.**

These guarantees are cumulative only when the implementation and qualification prove
each layer independently.
