# First fully live Agent 365 -> SharePoint -> Gateway -> Ranger R0 mission

This is the P0 execution gate after the controlled-tenant Agent 365 OTLP profile is frozen and marked `qualified`.

The objective is deliberately narrow: execute one bounded R0 motion from one live Microsoft mission while keeping identity, authority, runtime/tool telemetry, SharePoint state, controller acknowledgement, physical observation, and resulting state as separate evidence propositions tied together by the same `mission_id`.

## Non-negotiable entry conditions

Do not dispatch motion unless all of the following are true:

1. The Agent 365 profile qualification packet state is exactly `qualified` and contains a controlled-tenant live attestation.
2. The qualification packet digest reproduces from the supplied packet.
3. The live SharePoint observation has already retained exact Microsoft source bytes before parsing.
4. The SharePoint tenant, item ID, authorization-material commitment, source-payload commitment, and `mission_id` exactly match the qualified Agent 365 packet.
5. The sanitized Agent 365 correlation bundle has the same mission, tenant, SharePoint anchor, observation IDs, correlation bases, and retained source-envelope commitments as the qualified packet.
6. The robot is in the frozen R0 bench configuration, the hardware E-stop is available, the path is physically clear except for the deliberate stopping target/obstacle, and an independent physical-result observer is operating.

`ready_for_live_qualification` is not sufficient. A synthetic fixture or successful CI run may prove the software gate is ready, but it does not authorize physical motion.

## Frozen live path

The single live path is:

`Agent 365 identity -> runtime/invocation -> tool execution -> retained SharePoint mission state -> Gateway authorization -> robot receipt -> motion command -> controller acknowledgement -> independent motion observation -> independent stop-condition observation -> stop decision -> stop command -> controller acknowledgement -> independent stopped-state observation -> Evidence Object v1/v2 -> durable reconstruction`

The same `mission_id` must survive the entire path.

## Operator procedure

### 1. Freeze Microsoft-side evidence

Use the previously qualified controlled-tenant profile without changing any key mapping. Retain the selected Agent 365 catalog/identity source and OTLP exports before projection. Retain the live SharePoint item response before parsing.

Rebuild the sanitized Agent 365 correlation bundle and confirm that it is byte-semantically consistent with the qualified packet: same observation IDs, same retained source-envelope commitments, same correlation bases, same tenant, same SharePoint item, same authorization-material commitment, and same SharePoint source-payload commitment.

If any value differs, stop. Do not dispatch.

### 2. Confirm physical safety boundary

Before invoking the live orchestrator:

- confirm the R0 hardware E-stop works and is reachable;
- confirm the robot is on the bounded test surface;
- confirm no person, animal, or unplanned object is in the motion path;
- confirm maximum speed/distance/duration/stop-distance remain inside the frozen `r0-forward-stop-policy.v1` profile;
- confirm the independent motion/stop/result sensors are active and are not simply proxies for the motor-controller acknowledgement;
- record the actuator ID and independent result-observer ID in the hardware-run attestation.

Any asserted E-stop, sensor failure, controller rejection, observation-budget exhaustion, or evidence mismatch aborts the run. The physical adapter is responsible for the local fail-safe stop path after motion has been attempted.

### 3. Execute exactly one mission

Call `run_agent365_r0_live_mission(...)` with:

- the `Agent365ProfileQualificationResultV1` whose packet state is `qualified`;
- the exact `SharePointMissionLiveObservationV1` used as the live resource-state witness;
- the exact `Agent365R0CorrelationBundleV1` bound to that qualification;
- the real R0 actuator implementation;
- independent physical sensor implementations;
- `RangerR0HardwareRunAttestationV1` for this run;
- the production/system clock or a hardware-qualified clock implementation.

Do not reuse the `mission_id` for another physical mission. The Gateway and robot receipt ledgers enforce execution-once semantics.

### 4. Verify the retained result

A successful live run must produce and retain:

- the qualified Agent 365 profile packet and digest;
- the live SharePoint source commitment;
- Gateway ingress, authorization decision, egress, and robot-command commitments;
- robot receive evidence;
- motion and stop controller acknowledgements as separate retained source artifacts;
- the hardware-run attestation;
- independent motion, stop-condition, and result observations;
- verified Evidence Object v1/v2 material;
- a durable physical mission bundle;
- a durable sanitized Agent 365 correlation bundle;
- a sanitized live-mission report.

The process must then close and reopen both durable stores. The physical mission must reconstruct by `mission_id` with the independent stopped result still supported, and the reopened Agent 365 correlation bundle must exactly equal the qualified correlation input.

The authenticated mission API may then expose the sanitized Microsoft correlation section alongside the physical verifier status. It must not return raw OTLP or SharePoint source bodies through this endpoint.

## What a successful run proves

A successful run supports the bounded proposition that the retained Microsoft observations, the independently read SharePoint authorization state, the Gateway authorization/dispatch, the R0 execution records, the separately retained controller acknowledgements, and the independent stopped-state observation all correlate to one mission and survive durable verification/reconstruction.

It does **not** prove that an Agent 365 tool-success event alone proves SharePoint state. It does not make a motor-controller acknowledgement proof that the chassis moved or stopped. It does not make the Agent 365 observer proof of the physical result. It does not establish unbounded physical truth.

## Immediate contradiction matrix

After the first successful mission, keep the same scenario and execute the negative cases before any broader feature work:

- profile is only `ready_for_live_qualification`;
- live SharePoint source digest differs from the qualified packet;
- authorization-material commitment differs;
- Agent 365 runtime/tool observation belongs to another `mission_id`;
- retained Agent 365 source-envelope set changes after qualification;
- duplicate mission delivery without explicit retry linkage;
- expired/unauthorized SharePoint mission;
- Gateway dispatch succeeds but controller rejects motion;
- controller acknowledges motion but independent motion sensor does not observe movement;
- stop command is acknowledged but independent result sensor does not observe the stopped state;
- network interruption occurs after SharePoint state is observed but before or during Gateway/robot execution.

Each contradiction must fail closed or remain explicitly represented as a distinct evidentiary disagreement. Do not collapse different observers into one boolean success state.

## Soak gate

Start the integrated multi-hour run only after the first live mission and contradiction matrix are green. Start the 72-hour integrated soak only after there are no release-blocking evidence-schema or interface changes remaining. During soak, continue to retain evidence for restarts, disconnect/reconnect behavior, duplicate delivery attempts, clock behavior, controller/sensor failures, and independent verification from another system.
