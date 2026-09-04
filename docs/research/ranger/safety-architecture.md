# Ranger R0.1 Safety Architecture

**Status:** reference safety contract for simulation; not a physical safety certification

**Profile:** `ets.ranger.mobility-safety.v1`

**Tracks:** #605

## Objective

Place one deterministic, fail-closed authorization boundary between every R0 motion
request and every simulator or motor-controller adapter. The boundary must stop motion
when required safety standing is absent and must produce a typed record explaining the
observed inputs, derived values, policy result, and actuator command.

This is the first Ranger consequence-custody boundary:

> No valid motion standing -> no non-zero actuator command.

It does not claim that a motor obeyed the command or that the vehicle physically moved.
Those facts require separate actuator-response and result observations in later gates.

## Scope

The R0.1 reference implementation covers:

- disarmed startup;
- explicit arming;
- a hardware E-stop input that dominates software motion;
- latched E-stop behavior requiring physical release, reset, and re-arm;
- teleoperator deadman state;
- vehicle, mission, controller, and controller-session binding;
- monotonic command ordering and local queue-age checks;
- policy-bounded linear speed, yaw rate, and reverse motion;
- a local monotonic watchdog with a latched command-timeout state;
- zero-motion output for every denied request; and
- typed, deterministic authorization records for simulation and later evidence capture.

Geofencing, obstacle response, waypoint navigation, autonomous command sources,
cryptographic signing, physical actuator feedback, and physical E-stop qualification are
deliberately outside this increment.

## Trust and control boundary

The simulator and future hardware adapter are downstream of the safety controller.
Neither may bypass it for motion commands. The ETS Gateway remains out-of-band and is
never placed in the vehicle's real-time safety loop. Loss of an upstream ETS service
therefore cannot create motion authority.

A production vehicle must implement the emergency stop as an independent, normally
closed, de-energizing hardware path. Software can observe and record that circuit state,
but this Python reference cannot implement or qualify the physical interruption.

## State model

| State | Non-zero motion permitted | Exit requirement |
|---|---:|---|
| `disarmed` | No | Explicit arm with hardware E-stop clear |
| `armed` | Only after a valid command evaluation | Disarm, E-stop, or watchdog timeout |
| `estop_latched` | No | Hardware release, explicit reset, then explicit arm |
| `command_timeout` | No | Explicit arm with hardware E-stop clear |

Every denied authorization selects exactly zero linear speed and zero yaw rate. An
out-of-policy command is rejected, not silently clamped, because silent rewriting would
obscure what was requested and which action was actually authorized.

## Safety-time semantics

Remote wall-clock time is evidence, not the R0.1 safety clock. Queue age and watchdog
decisions use the Ranger controller's local monotonic clock. This prevents a remote clock
offset from manufacturing fresh standing for a delayed command. Wall-clock timestamps and
their quality remain in the record for later timeline reconstruction.

A local monotonic-order violation fails closed. R0.2 must preserve boot identity and boot
counter evidence so monotonic domains cannot be confused across restarts.

## Evidence classifications

`ets.ranger.mobility-event.v1` distinguishes the following fields rather than flattening
them into an untyped log message:

| Record field | Evidence class | Meaning |
|---|---|---|
| `operator_command` | Operator command | What the bound teleoperator session requested |
| `observed_facts` | Observed fact | What the safety boundary observed at its interfaces |
| `derived_values` | Derived value | Queue age, watchdog elapsed time, and absolute rates |
| `policy_evaluation` | Policy evaluation / machine decision | Reasons and allowed/denied result under an identified policy digest |
| `actuator_command` | Actuator command | The exact motion vector released downstream; zero on denial |
| `observed_result` | Observed result | Always absent in R0.1 because this boundary cannot observe physical outcome |

The record carries the fixed claim boundary
`authorization_only_no_actuator_or_physical_outcome`. Consumers must not describe a valid
record as proof that the vehicle obeyed or achieved the command.

## ETS component mapping

- **ETS Edge:** will durably ingest the typed mobility record and keep local operation
  authoritative during disconnection.
- **ETS Black Box:** will retain bounded pre/post safety-event windows and seal signed
  segments. R0.1 emits source records only and does not claim Black Box durability.
- **ETS Gateway:** may transport locally committed records upstream, but it remains outside
  the safety-control path.
- **ETS Verifier:** will verify the later hash/signature/inclusion package. Verification will
  establish integrity, not the semantic truth of a sensor or physical outcome.
- **ETS AI Witness:** is not invoked by this deterministic teleoperation slice. If an AI
  component later proposes motion, its model/request/response lineage must be bound as
  separate evidence and still pass this safety boundary.

The R0.2 integration must wrap or bind these source records without redefining ETS Core
canonicalization, hash, signature, or verification semantics.

## Qualification tests

The automated R0.1 suite establishes:

1. disarmed startup denies motion;
2. a fresh, identity-bound, deadman-held, in-policy command is allowed;
3. excessive speed or yaw is denied rather than clamped;
4. deadman release produces zero motion;
5. E-stop assertion latches and cannot be cleared while hardware remains asserted;
6. release alone does not restore motion;
7. stale, replayed, out-of-order, or identity-mismatched commands are denied;
8. watchdog expiry stops motion and requires re-arm;
9. invalid monotonic ordering fails closed;
10. identical initial state and inputs produce an identical decision record; and
11. the strict schema rejects invented physical-result fields.

These tests are simulation evidence only. A later physical gate must test contactor state,
stopping distance, E-stop channel faults, motor-controller failure behavior, runaway power,
braking on grade, towing/recovery, and safe power sequencing on the selected chassis.

## Known limitations and risks

- Events are typed but unsigned and not yet hash-linked; R0.2 owns device identity,
  signatures, durable storage, and tamper-evident linkage.
- Arm, disarm, and E-stop-reset lifecycle transitions are not yet projected as evidence
  events; this increment records their effect on command authorization and safety stops.
- A process failure cannot substitute for an independent hardware E-stop.
- A compromised host below or around the controller could bypass software output; physical
  architecture must enforce the command path and de-energize independently.
- The policy limits are research values, not validated stopping-distance limits.
- Receipt monotonic time must be assigned at the trusted local ingress boundary; accepting a
  sender-supplied value would allow stale-command manipulation.
- Teleoperator authentication is represented by bound identifiers but not cryptographically
  proven in this gate.

## Cost impact

This simulation-first increment requires no hardware or operating expenditure. It reduces
procurement risk by defining the command and evidence interface that candidate motor
controllers must support before a chassis is selected.
