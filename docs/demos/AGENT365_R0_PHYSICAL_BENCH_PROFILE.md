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

The Developer Preview uses one canonical 40-pin Raspberry Pi BCM map. Do not substitute pins during qualification without creating a new retained hardware-config artifact.

| Function | BCM | Physical pin | Connection |
| --- | ---: | ---: | --- |
| I2C SDA | 2 | 3 | both VL53L0X SDA |
| I2C SCL | 3 | 5 | both VL53L0X SCL |
| DRV8833 left IN1 | 12 | 32 | left motor channel input 1 |
| DRV8833 left IN2 | 16 | 36 | left motor channel input 2 |
| DRV8833 right IN1 | 13 | 33 | right motor channel input 1 |
| DRV8833 right IN2 | 19 | 35 | right motor channel input 2 |
| E-stop input | 17 | 11 | normally-closed switch to ground |
| front VL53L0X XSHUT | 22 | 15 | front sensor shutdown/address control |
| rear VL53L0X XSHUT | 27 | 13 | rear sensor shutdown/address control |
| 3.3 V | — | 1 | VL53L0X logic/sensor supply |
| Ground | — | 6 | Pi/sensor/DRV8833 common reference |

DRV8833 motor outputs connect to the two DC motors: channel A to the left motor and channel B to the right motor. The motor supply connects only to the DRV8833 motor-power input. The Raspberry Pi remains on its own USB power supply. The Pi ground and DRV8833 ground must share a common reference, but the motor supply must never be connected to the Pi 5 V or 3.3 V rail.

If the specific DRV8833 breakout exposes a board-specific sleep/enable input, follow that breakout's documentation before Phase A; the ETS canonical interface controls only IN1/IN2 for each motor channel.

The normally-closed E-stop is fail-closed: a healthy circuit pulls BCM17 low through the closed switch. Pressing/opening the E-stop, disconnecting the wire, or losing the ground return leaves the internal pull-up high and motion must be denied.

Before energizing the motor supply, use the multimeter to confirm:

1. no continuity exists between motor-supply positive and Pi 5 V/3.3 V;
2. Pi ground, DRV8833 ground, and sensor ground share continuity;
3. the E-stop reads closed to ground when healthy and open when pressed;
4. motor outputs are not shorted to ground or logic rails;
5. the two VL53L0X sensors are on the Pi 3.3 V/I2C domain.

The canonical retained file is:

`config/ranger/r0-bench-pi-drv8833-dual-vl53l0x.v1.json`

## Retained Phase A/B campaign

Create one qualification directory before touching the hardware:

```bash
export ETS_R0_CAMPAIGN="$HOME/ets-r0-qualification"
export ETS_CODE_SHA="$(git rev-parse HEAD)"

python scripts/ranger/r0_qualification_campaign.py init \
  --root "$ETS_R0_CAMPAIGN" \
  --campaign-id "agent365-r0-physical-001" \
  --code-sha "$ETS_CODE_SHA"

cp config/ranger/r0-bench-pi-drv8833-dual-vl53l0x.v1.json \
  "$ETS_R0_CAMPAIGN/hardware-config.json"
```

All Phase A/B JSON artifacts and the exact hardware configuration must be retained under that directory. The recorder hashes them into
`campaign.json` and updates `campaign.sha256`. Phase records are append-only.

## Gate 0 — no-motion preflight

Run this **before installing wheels on the floor**:

```bash
python scripts/ranger/r0_bench_preflight.py \
  --hardware-config "$ETS_R0_CAMPAIGN/hardware-config.json" \
  --output-json "$ETS_R0_CAMPAIGN/phase-a/preflight.json"
```

Retain Phase A only after the command succeeds:

```bash
python scripts/ranger/r0_qualification_campaign.py record-phase \
  --root "$ETS_R0_CAMPAIGN" \
  --phase A_preflight \
  --state pass \
  --artifact "$ETS_R0_CAMPAIGN/hardware-config.json" \
  --artifact "$ETS_R0_CAMPAIGN/phase-a/preflight.json"
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

Run the bounded supported-chassis pulse only after placing the chassis securely so wheel
rotation cannot propel the robot:

```bash
python scripts/ranger/r0_wheels_off_ground.py \
  --execute-wheels-off-ground \
  --hardware-config "$ETS_R0_CAMPAIGN/hardware-config.json" \
  --output-json "$ETS_R0_CAMPAIGN/phase-b/wheels-off-ground.json"
```

The automated result can prove that the E-stop stayed healthy, the stop command completed, and
the rear range witness did not observe chassis translation beyond the frozen limit. It cannot
infer wheel direction. After visually confirming that both wheels rotated forward, retain Phase B:

```bash
python scripts/ranger/r0_qualification_campaign.py record-phase \
  --root "$ETS_R0_CAMPAIGN" \
  --phase B_wheels_off_ground \
  --state pass \
  --artifact "$ETS_R0_CAMPAIGN/phase-b/wheels-off-ground.json" \
  --operator-observation both_wheels_forward

python scripts/ranger/r0_qualification_campaign.py status \
  --root "$ETS_R0_CAMPAIGN"
```

The status must report `ready_for_phase_c_live_mission: true` before proceeding.

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
