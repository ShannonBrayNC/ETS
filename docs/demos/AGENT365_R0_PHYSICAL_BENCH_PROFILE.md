# Physical R0 bench profile — first live Agent 365 mission

This runbook binds the small Physical Agent R0 bench to the already-frozen ETS evidence path:

`Agent 365 -> SharePoint -> Gateway -> Ranger R0 -> independent physical observation -> Evidence Object v1/v2 -> durable reconstruction`.

The hardware profile is intentionally narrow. It exists to qualify one safe, bounded demonstration before any broader Ranger expansion.

## Reference hardware

- LAFVIN 2WD V2 chassis / two-motor platform
- Raspberry Pi-class 40-pin host
- DRV8833 dual H-bridge motor driver
- two VL53L0X-class time-of-flight sensors
  - **front** sensor: independent obstacle/stop-condition observation
  - **rear** sensor: independent forward-displacement and stopped-state witness
- normally-closed physical E-stop circuit wired to a dedicated GPIO input
- external webcam retained as an additional ETS witness

The webcam is an external witness only in this gate. It does not replace the front/rear range sensors and it does not turn a controller acknowledgement into proof of motion.

## Why two range sensors

The motor controller is not allowed to be its own historian.

For the frozen forward-only mission, the rear-facing range sensor observes increasing distance from a fixed rear reference as the robot moves forward. That provides an independent displacement signal for motion start, travelled distance, and final stationary-state checks.

The front-facing range sensor independently observes the stopping target/obstacle.

This gives us three distinct propositions:

1. **DRV8833/controller acknowledgement** — the command was accepted and applied.
2. **Front/rear physical sensors** — motion/stop conditions were physically observed.
3. **Webcam witness** — an additional externally visible record exists for later evidence comparison.

## Software profile

Install the project and the optional R0 hardware dependencies on the Pi:

```bash
python -m pip install -e ".[r0]"
```

The concrete adapters are in:

`ets/ranger/agent365_r0_bench_hardware.py`

They implement the existing `RangerR0PhysicalActuator` and `RangerR0PhysicalSensors` contracts without changing the Gateway, mission, Evidence Object, or verifier models.

## Wiring contract

Choose BCM GPIO pins appropriate for the actual Pi and record them in the retained run notes. Do not rely on an undocumented breadboard layout.

The required logical connections are:

| Function | R0 connection |
| --- | --- |
| DRV8833 left IN1 | Pi PWM-capable GPIO |
| DRV8833 left IN2 | Pi GPIO |
| DRV8833 right IN1 | Pi PWM-capable GPIO |
| DRV8833 right IN2 | Pi GPIO |
| front VL53L0X XSHUT | Pi GPIO |
| rear VL53L0X XSHUT | Pi GPIO |
| VL53L0X SDA/SCL | Pi I2C bus |
| E-stop input | Pi GPIO with pull-up |
| E-stop return | Ground through normally-closed switch |

The normally-closed E-stop is fail-closed: a healthy circuit pulls the configured input low. Pressing/opening the E-stop, disconnecting the wire, or losing the return path leaves the pull-up high and motion must be denied.

Do not energize the motors until motor power, Pi ground, DRV8833 ground, and logic ground have been checked with the multimeter.

## Gate 0 — no-motion preflight

Run this **before installing wheels on the floor**:

```bash
python scripts/ranger/r0_bench_preflight.py \
  --left-in1 <BCM> \
  --left-in2 <BCM> \
  --right-in1 <BCM> \
  --right-in2 <BCM> \
  --estop-pin <BCM> \
  --front-xshut <BCM> \
  --rear-xshut <BCM> \
  --calibrated-max-speed-mps 0.15 \
  --max-duty-cycle 0.55
```

This command must not authorize motion. It:

- forces the DRV8833 outputs stopped;
- verifies the normally-closed E-stop is healthy;
- assigns separate I2C addresses to the two VL53L0X sensors;
- captures three front/rear distance samples;
- prints the frozen calibration values;
- reports `motion_authorized: false`.

If the E-stop is open, either range sensor cannot be read, or GPIO/I2C initialization fails, the preflight fails and physical motion remains out of scope.

## Gate 1 — wheels-off-ground actuation

The first motor actuation is a bench test with the chassis supported so the wheels cannot propel the robot.

Use a deliberately low frozen calibration ceiling. Confirm:

1. left and right wheels rotate forward together;
2. a stop command removes drive from both channels;
3. opening the E-stop causes the live physical execution path to fail closed;
4. a controller acknowledgement is retained separately from range-sensor evidence;
5. the rear sensor does not falsely claim chassis translation while the wheels spin off-ground.

That fifth condition is important. Wheel rotation is not physical travel.

## Gate 2 — bounded floor motion

Only after Gate 0 and Gate 1 pass:

- place the R0 on a short, clear test lane;
- place a stable rear reference behind the rear VL53L0X;
- place the stopping target in front of the front VL53L0X;
- keep the hardware E-stop in hand/reach;
- keep people, animals, and unrelated objects out of the lane;
- run exactly one bounded mission;
- do not reuse its `mission_id`.

Use the frozen `r0-forward-stop-policy.v1` limits. The live orchestrator remains responsible for Gateway authorization, execution-once semantics, fail-safe stop, Evidence Object promotion, durable storage, and reconstruction.

## Required first live run

The first real qualification run must use:

`run_agent365_r0_live_mission(...)`

with:

- a controlled-tenant Agent 365 profile whose state is exactly `qualified`;
- the exact retained live SharePoint observation;
- the exact Agent 365 correlation bundle;
- `Drv8833R0Actuator`;
- `DualRangeR0PhysicalSensors`;
- a hardware-run attestation naming the DRV8833 actuator and dual-range observer;
- a unique `mission_id`.

The successful output must survive reopening both durable stores and reconstruct the same mission by `mission_id`.

## Immediate contradiction matrix

Do not add features after the first successful floor run. Execute the negative cases from `AGENT365_R0_FIRST_LIVE_MISSION.md` immediately, including:

- E-stop asserted before motion;
- E-stop opened during motion;
- controller accepts motion but rear sensor does not observe displacement;
- front sensor stops reporting;
- stop command is acknowledged but rear sensor still observes motion;
- changed SharePoint source commitment;
- changed Agent 365 observation set;
- duplicate mission delivery;
- network interruption during the Microsoft-to-physical path.

Every case must either fail closed or preserve the disagreement explicitly. A controller success flag must never overwrite contradictory physical evidence.

## Soak entry

Begin the multi-hour integrated run only after the positive mission and contradiction matrix pass.

Begin the 72-hour soak only after:

- the bench hardware profile is frozen;
- no release-blocking evidence schema/interface changes remain;
- restart/reload reconstruction is green;
- disconnect/reconnect behavior is green;
- independent verification from another system is green.

The goal of the soak is not to make the robot impressive. It is to demonstrate that the **same mission evidence semantics remain defensible over time, faults, restarts, and repeated observation**.
