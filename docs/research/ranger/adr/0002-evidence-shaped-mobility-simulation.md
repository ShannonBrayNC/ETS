# ADR 0002: Require evidence-shaped deterministic mobility simulation

- **Status:** Accepted for R0 simulation
- **Date:** 2026-09-04
- **Gate:** R0.1 Mobility
- **Tracks:** #605

## Context

Ranger needs hardware-independent tests before chassis procurement. A simulator that accepts
bare motion vectors or returns only pose values would create a second command path and would
not test the provenance boundaries intended for the physical platform.

## Decision

The reference simulator accepts only a complete `ets.ranger.mobility-event.v1` emitted by the
single fail-closed motion boundary. It applies the event's selected actuator command, enforces
identity and contiguous ordering, and emits separately typed actuator-response and simulated-
result records linked by canonical ETS digests.

Simulated pose is classified as a deterministic derived value. Fixed environment and claim-
boundary fields prohibit representing it as a physical actuator response, sensor observation,
or external-world outcome.

## Consequences

- Simulation exercises the same safety-to-adapter boundary intended for chassis integration.
- Deterministic replay can verify command, response, model/configuration, and result linkage.
- Denied commands test the zero-motion consequence without recovering rejected intent.
- R0.2 can sign and durably chain these records without redesigning their semantic separation.
- The simple planar model cannot validate vehicle dynamics or physical safety.

## Alternatives rejected

- **Accept bare motion vectors:** rejected because callers could bypass the safety decision and
  its evidence.
- **Embed simulated result in the mobility authorization event:** rejected because authorization,
  actuator response, and result are different claims made at different boundaries.
- **Label calculated pose as an observed fact:** rejected because no physical sensor observed it.
- **Add a high-fidelity physics engine now:** rejected because deterministic evidence linkage,
  not dynamics fidelity, is the current gate and the simpler experiment has zero hardware cost.
