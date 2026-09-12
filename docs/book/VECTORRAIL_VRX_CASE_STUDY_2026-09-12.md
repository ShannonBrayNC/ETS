# Evidence Architecture Case Study — VectorRail/VRX

**Status:** Technical Manual integration case study  
**System:** ETS VectorRail (VRX), Captive Electromagnetic Actuation & Consequence-Custody Module

## Why VectorRail matters to Evidence Architecture

A digital log can say that a controller issued a command. That fact is useful, but it is not the same proposition as saying the physical world changed.

VectorRail/VRX is a deliberately constrained laboratory instrument for teaching and testing that distinction. It uses a low-energy electromagnetic actuator whose moving element remains mechanically captive. The value of the apparatus is not projectile performance. Its value is that a short physical event produces several independently observable domains at once: authority, software control, electrical response, mechanical motion, thermal change, and final safe state.

That makes VRX a compact consequence-custody laboratory.

## The evidence chain

The naive system model is:

`Command → Success`

Evidence Architecture requires a richer decomposition:

`Request → Authority → Safety policy → Issued/rejected command → Electrical observation → Mechanical observation → Thermal observation → Resulting-state observation → Integrity seal → Verification`

Every arrow represents a potential evidentiary discontinuity.

An authorized request may be rejected by an interlock. An issued command may produce no electrical event. An electrical event may occur while motion is mechanically blocked. A controller may report motion while an independent position sensor reports none. Two independent sensors may disagree. The apparatus may actuate successfully but fail to return to a verified safe state.

These are not edge cases to hide. They are precisely the states an evidence architecture must preserve.

## Consequence custody

Traditional provenance often asks where a record came from. Consequence custody extends the question into the physical world:

> Can the evidence establish the relationship between a machine's authority, its command, the physical system's response, and the state observed afterward?

VRX makes that relationship inspectable. Electrical current is not treated as proof of motion. Motion is not treated as proof of the controller's interpretation. A final safe state is not inferred merely because the command routine returned successfully.

Each proposition has its own evidence and epistemic standing.

## Epistemic conservation

Suppose the current sensor is unavailable. The correct evidence state is not "zero current." It is `NOT_AVAILABLE` or `UNKNOWN`, with the reason preserved.

Suppose two independent position sensors disagree outside their tolerance. Evidence Architecture does not choose whichever measurement best fits the controller's narrative. Both observations remain preserved, their source ancestry and independence remain visible, and the derived physical-consequence proposition may become `CONTRADICTED` or `INDETERMINATE`.

This is epistemic conservation: a transformation or projection must not create stronger knowledge than its inputs warrant.

## Fail-closed safety as evidence

VRX also demonstrates that safety state itself is evidence. An open enclosure interlock, unknown safety state, missing required safety telemetry, or controller fault prevents actuation. The rejection is then preserved as an evidentiary event.

The resulting record does not merely say "nothing happened." It can establish that an action was requested, policy evaluated the request, the safety boundary was unsatisfied, the command was rejected, and no downstream consequence was affirmatively inferred.

## Independent verification

The end-to-end VRX verifier recomputes canonical integrity and then evaluates semantic consistency. Integrity and truth remain separate concepts.

A valid digest establishes that the sealed evidence has not changed under the declared canonicalization profile. It does not establish that every sensor was accurate. Semantic consistency establishes that the evidence does not contradict the claimed bounded conclusion under the verifier rules. It does not establish objective physical truth beyond the observability boundary.

The strongest defensible statement is therefore bounded:

> The identified instrumentation, under the recorded configuration and stated observability limits, produced evidence consistent with the declared consequence chain.

## Generalization

VectorRail is intentionally simple, but the pattern generalizes.

For Ranger:

`Sensor → perception → decision → authority → actuator command → vehicle response → resulting state`

For an AI infrastructure agent:

`Observation → model/tool decision → authority → API/tool call → external system response → resulting state`

For industrial automation:

`Process state → controller decision → policy/interlock → actuator command → valve/motor response → process consequence`

The physical mechanisms differ. The evidence problem is the same.

## Manual takeaway

The VectorRail case demonstrates a core Evidence Architecture rule:

**Intent is not consequence. Command is not consequence. A controller's report of consequence is not independent evidence of consequence.**

Evidence Architecture therefore preserves the chain from authority through physical response and resulting state while retaining uncertainty, contradiction, source ancestry, integrity, and observability boundaries.
