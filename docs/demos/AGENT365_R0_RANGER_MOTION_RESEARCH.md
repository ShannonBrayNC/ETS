# P0 Ranger R0 motion-boundary research notes

Date reviewed: 2026-09-17

These notes record the external engineering conventions used to constrain the P0 reference
implementation. They are research inputs, not certification claims.

## Emergency-stop boundary

ISO 13850:2015 is the currently published ISO emergency-stop design standard. Its scope is the
functional requirements and design principles for an emergency-stop function, independent of
energy type, and it points to IEC 60204-1 for electrical/electronic realization.

For P0 this supports two conservative software rules:

- an asserted hardware E-stop denies local motion even after upstream authorization; and
- an E-stop observation during the run is a stop trigger, not permission to perform some other
  maneuver.

The reference implementation does not claim that its Python state machine is a safety-rated
emergency-stop implementation. The physical E-stop circuit and motor power architecture require
separate hardware risk assessment and qualification.

## Stop command versus achieved stop

Industry documentation summarizing IEC 60204-1 distinguishes several stop sequences, including
immediate power removal and controlled deceleration. The physically appropriate stop mechanism
therefore depends on hardware and risk assessment; software cannot infer the achieved physical
state merely because a stop request was issued or acknowledged.

P0 consequently records these as separate stages:

```text
STOP decision -> stop actuation acknowledgement -> later resulting-state observation
```

The resulting-state observation must come from an observer distinct from the actuator identity.

## Managed hardware lifecycle

ROS 2 managed-node design explicitly distinguishes inactive and active lifecycle states, while
`ros2_control` hardware guidance separates readable hardware state from movement-capable command
interfaces. Ranger R0 does not require ROS 2 in this phase, but the lifecycle pattern reinforces
the local interlock used here: receiving a network command does not itself activate motion.

## Sources

1. ISO 13850:2015, *Safety of machinery — Emergency stop function — Principles for design*.
   https://www.iso.org/standard/59970.html
2. ROS 2 Design, *Managed nodes*.
   https://design.ros2.org/articles/node_lifecycle.html
3. Rockwell Automation, *Kinetix Faults and Countermeasures*; stop-category discussion based on
   IEC 60204-1.
   https://literature.rockwellautomation.com/idc/groups/literature/documents/wp/motion-wp010_-en-p.pdf

## Research-derived implementation rules

- Preserve `mission_id` from Gateway through every robot and sensor record.
- Bind the first Ranger receipt to the exact Gateway egress digest.
- Require local readiness after upstream authorization.
- Give E-stop precedence over ordinary motion authorization.
- Enforce forward-only P0 actuation and the Gateway-authorized speed ceiling.
- Require an observed stop condition before the STOP decision.
- Keep stop acknowledgement and stopped-state observation epistemically separate.
- Treat retry delivery as transport recovery, never as authority to execute the mission twice.
- Do not label this boundary ISO/IEC compliant without the required physical safety engineering,
  risk analysis, component selection, validation, and certification work.
