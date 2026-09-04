# Ranger R0.1 Motion-Authority Lifecycle Evidence

**Status:** executable research contract; not a physical safety certification

**Profile:** `ets.ranger.lifecycle-event.v1`

**Tracks:** #605

## Objective

Make motion authority itself reconstructable. Mobility events already show whether an individual command was allowed or denied, but a verifier also needs first-class evidence of how Ranger entered or left states in which motion could be authorized.

The lifecycle layer therefore records software authority transitions separately from command authorization and separately from actuator or physical outcome claims.

## Transition chain

The reference lifecycle controller records:

`disarmed -> armed -> command timeout -> explicit re-arm`

and

`armed -> E-stop latched -> E-stop reset -> disarmed -> explicit re-arm`

Disarm is also a first-class transition. Hardware E-stop assertion discovered while processing a command or watchdog evaluation is linked to the corresponding `ets.ranger.mobility-event.v1` by canonical ETS digest.

## Evidence semantics

Each `ets.ranger.lifecycle-event.v1` binds:

- Ranger vehicle, mission, controller, controller-session, and boot identities;
- lifecycle sequence;
- lifecycle transition kind;
- mode before and mode after;
- local monotonic transition time and UTC evidence time;
- local clock quality;
- hardware E-stop input when relevant;
- reason code when relevant;
- source mobility-event identity and canonical digest when a safety evaluation caused the transition;
- whether an explicit operator re-arm is required.

The record explicitly states that it does **not** prove physical E-stop state, physical actuator state, or physical motion outcome.

## Fail-closed recovery rules

- A watchdog timeout transitions the controller to `command_timeout` and requires explicit re-arm.
- Re-arm after timeout is recorded distinctly as `timeout_recovery_rearm`, not as an ordinary arm event.
- E-stop assertion latches `estop_latched`.
- E-stop release alone cannot restore authority.
- Reset while the hardware E-stop input remains asserted is rejected.
- A successful E-stop reset returns only to `disarmed`; a separate explicit arm is still required.
- Lifecycle timestamps use the controller's trusted local monotonic ordering rules.

## Replay consequence

A verifier can now distinguish:

1. a command denied because Ranger never acquired motion authority;
2. a command denied because authority was revoked by E-stop or timeout;
3. the exact recovery transition that restored software authority; and
4. subsequent command authorization under that restored standing.

This closes an important epistemic gap: command evidence no longer has to imply the provenance of the authority state that governed it.

## Current boundary

These records are unsigned R0.1 source evidence. R0.2 must add device signing, durable append order, crash recovery, ETS Edge/Black Box projection, and independent verification of the resulting chain. Physical E-stop qualification remains a separate hardware obligation.
