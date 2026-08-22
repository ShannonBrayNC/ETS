# ETS Fleet Presence Runtime v1

Status: Implementation profile  
Date: 2026-08-21  
Parent: #513 / FLEET-B1  
Depends on: FLEET-A enrollment runtime and physical qualification foundation

## 1. Purpose

FLEET-B1 defines the provider-neutral operational presence runtime for ETS devices.

The runtime maintains two independent observations:

1. **transport presence** from a bounded provider event such as Azure IoT Hub Event Grid;
2. **ETS signed heartbeat posture** from a message bound to an authorized Fleet credential.

These signals are deliberately separate.

**Presence is not health.** A transport event can show that a provider observed a connection
transition, but it cannot prove that the device is uncompromised, that a source is complete, or
that evidence is semantically true.

**Heartbeat is not evidence verification.** A valid heartbeat proves only the bounded operational
claims carried by the signed heartbeat under the accepted device identity and policy. It does not
make unrelated ETS evidence valid.

Cryptographic ETS evidence and independent verification remain separate protocol concerns.

## 2. Azure transport source

The initial provider adapter is Azure IoT Hub Event Grid.

Current Microsoft documentation recommends Event Grid for most device connection-state monitoring
and exposes:

- `Microsoft.Devices.DeviceConnected`;
- `Microsoft.Devices.DeviceDisconnected`;
- IoT Hub resource source/topic;
- `devices/<device-id>` subject;
- `data.deviceId`;
- `data.hubName`;
- `data.deviceConnectionStateEventInfo.sequenceNumber`.

The connection sequence is a fixed-width 256-bit value. Microsoft documents that it is strictly
increasing and can be compared as a string.

Event Grid is still an observation with known limitations. IoT Hub samples connection-state
changes on a bounded interval, events can be delayed, and intermediate connect/disconnect churn can
be omitted. The Fleet runtime therefore never interprets a missing event as complete historical
knowledge.

## 3. Prohibited connection-state shortcut

The Fleet runtime MUST NOT query or rely on the IoT Hub device-twin `connectionState` field as
production truth.

Microsoft documents that the field is intermittent, protocol-dependent, and may lag by several
minutes. It is suitable for development/debugging but not a runtime authorization or presence
decision boundary.

FLEET-B1 consumes ordered Event Grid lifecycle events instead and keeps signed heartbeat freshness
as an independent signal.

## 4. Provider-neutral state

Each device has a bounded `PresenceState` containing:

- canonical ETS device ID;
- current authoritative enrollment ID and lifecycle posture;
- transport state: `unknown`, `online`, or `offline`;
- last accepted transport event ID;
- last accepted transport sequence;
- provider event time;
- trusted service receipt time;
- heartbeat posture: `missing`, `current`, or `stale`;
- last boot/session ID;
- last accepted heartbeat sequence;
- device observation time;
- trusted service receipt time;
- signer fingerprint;
- software version;
- profile version.

No private key, certificate private material, SAS value, bearer token, Azure token, connection
string, raw customer payload, or evidence content is retained in this state.

## 5. Transport ingestion

Transport ingestion fails closed unless all of the following hold:

1. the event is a supported connected/disconnected lifecycle type;
2. source/topic matches the configured IoT Hub resource exactly, case-insensitively;
3. `hubName` matches the configured hub;
4. the event is for a device rather than a module;
5. `subject == devices/<data.deviceId>`;
6. the device exists in the authoritative ETS enrollment registry;
7. the sequence is a fixed-width 256-bit hexadecimal value.

Event IDs are deduplicated.

If a new event has a sequence less than or equal to the last accepted sequence, it is retained only
as a processed event ID and cannot roll operational state backward.

A transport event for a known revoked or quarantined device may still be recorded as an operational
observation. Recording the observation does not authorize the device.

## 6. Signed heartbeat profile

The heartbeat payload schema is:

`ets.fleet.heartbeat.v1`

It contains only bounded operational fields:

- canonical ETS device ID;
- enrollment ID;
- boot/session ID;
- monotonic sequence;
- UTC device observation time;
- software version;
- profile version;
- bounded non-secret metadata.

The envelope additionally carries:

- signer public-key fingerprint;
- detached Base64 signature.

The canonical bytes to sign are the UTF-8 JSON representation of the heartbeat payload with sorted
keys and compact separators.

The signature algorithm is deliberately behind a `HeartbeatSignatureVerifier` port. FLEET-B1 does
not force a specific cryptographic library or key provider and does not require export of a
hardware-backed private key.

## 7. Heartbeat authorization

Before accepting a heartbeat, the runtime:

1. resolves the authoritative current ETS enrollment;
2. calls the Fleet authorization boundary using server-owned tenant/workspace scope;
3. verifies that the authorized enrollment ID matches the heartbeat enrollment ID;
4. verifies the detached signature using the presented signer fingerprint;
5. checks bounded clock skew;
6. applies boot/session and sequence replay rules.

A credential mismatch, expired/superseded credential, pending device, quarantine, revocation, or
decommission state fails closed.

Credential rotation remains governed by the existing Fleet authorization service. FLEET-B1 does
not create a second rotation policy.

## 8. Boot/session replay rule

Within one boot/session ID, heartbeat sequence must strictly increase.

A newly observed boot/session ID MUST start at sequence `0`.

After a device advances to a newer accepted boot/session ID, a previously retained session ID
cannot become current again. This blocks simple replay of an earlier boot session.

The durable production store used in FLEET-B2 or later must persist seen boot/session identifiers
across service restarts. The in-memory implementation is a deterministic reference store only.

## 9. Freshness and clocks

Heartbeat freshness is calculated from **trusted service receipt time**.

Device-reported `observed_at_utc` is retained separately as context and is checked against the
configured clock-skew policy. It is not the sole freshness clock.

Default reference values are:

- heartbeat stale threshold: 5 minutes;
- maximum device/service clock skew: 2 minutes.

Deployment policy may change these values, but the distinction between observation time and receipt
time must remain.

## 10. Truth boundaries

The Fleet portal and notification pipeline must preserve these statements:

- online does not mean healthy;
- offline does not prove the device was continuously disconnected;
- current heartbeat does not prove evidence completeness;
- stale heartbeat does not prove compromise;
- a valid heartbeat does not validate unrelated evidence;
- an authorized enrollment does not make every device observation true;
- evidence verification remains independent of Fleet presence state.

This separation is required for the future Fleet Dark Pro UI.

## 11. FLEET-B2 handoff

FLEET-B2 should add Azure and notification adapters around this runtime:

`IoT Hub -> Event Grid -> authenticated internal event processor -> durable PresenceStore`

and:

`device D2C heartbeat -> authenticated intake -> FleetPresenceService`

The next slice should also add:

- durable Azure-backed or database-backed presence storage;
- Event Grid webhook authentication/source validation at the ingress boundary;
- signed heartbeat transport intake;
- debounce/correlation policy;
- notification decision engine;
- bounded first-online/reconnect/stale/disconnect/quarantine/revocation notifications;
- administrative ETS lifecycle evidence for material Fleet status changes.

The B2 adapter must not weaken the provider-neutral state semantics defined here.
