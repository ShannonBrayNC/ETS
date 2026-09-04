# ADR 0001: Use one fail-closed motion authorization boundary

- **Status:** Accepted for R0 simulation
- **Date:** 2026-09-04
- **Gate:** R0.1 Mobility
- **Tracks:** #605

## Context

Ranger will receive motion requests from teleoperation first and bounded autonomy later.
Separate safety logic in each command source would create inconsistent enforcement and
fragment the evidence needed to reconstruct why physical motion was permitted.

## Decision

All motion sources and all simulator or hardware drive adapters must cross one deterministic
authorization contract. A request receives non-zero output only while the vehicle is armed,
the hardware E-stop input is clear, controller/vehicle/mission/session identities match, the
command is fresh and ordered, the teleoperator deadman is asserted, and the requested motion
satisfies the active policy.

Denial produces an explicit zero-motion actuator command and a typed decision record. E-stop
and command-timeout conditions latch until their documented recovery transition occurs.
Queue age and watchdog logic use a trusted local monotonic clock; remote wall time is retained
only as evidence.

The contract records authorization but does not claim actuator response or physical outcome.

## Consequences

- Simulation and physical adapters can share the same testable safety/evidence semantics.
- Later autonomy cannot bypass safety policy by using a different command path.
- Policy and command provenance can be cryptographically bound in R0.2 without redesigning
  the motion interface.
- The controller becomes safety-sensitive software and must be independently complemented by
  a de-energizing hardware E-stop and physical qualification.
- Availability may be reduced by conservative latching, which is acceptable for R0.

## Alternatives rejected

- **Clamp invalid commands:** rejected because it obscures the distinction between requested
  and authorized action.
- **Implement safety separately in teleoperation and autonomy:** rejected because enforcement
  and evidence would diverge.
- **Use remote command timestamps for the watchdog:** rejected because cross-device clock
  error or manipulation could create false freshness.
- **Put Gateway in the real-time control loop:** rejected because network or cloud failure
  must not create or become the sole arbiter of physical safety.
