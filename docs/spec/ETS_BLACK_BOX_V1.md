# ETS Black Box v1

Status: software reference implementation and physical-appliance qualification contract.

## Purpose

ETS Black Box is the specialized ETS incident recorder. It preserves evidence surrounding a
consequential failure, security event, crash, power event, watchdog reset, policy violation, or
operator-selected incident even when the monitored system later becomes unavailable, damaged, or
disputed.

It is deliberately different from ETS Vault. Vault is a long-term preservation and retention tier.
Black Box is an always-on recorder whose defining lifecycle is:

1. continuously maintain a bounded rolling pre-event record;
2. receive or detect a trigger;
3. freeze the relevant pre-event window so ring rotation cannot erase it;
4. continue a bounded post-trigger capture;
5. cryptographically seal the incident segment;
6. make the sealed segment independently verifiable and exportable to ETS Core and Vault.

## Research basis

The v1 requirements draw on several authoritative recorder/security patterns. These are design inputs,
not claims that ETS is certified to those unrelated regulated products.

- **49 CFR 563.9** locks qualifying vehicle EDR deployment-event memory against future overwrite while
  allowing defined handling of ordinary event buffers. ETS adopts the architectural principle that
  ordinary history may rotate but a qualifying triggered incident leaves the overwrite domain.
  Reference: https://www.law.cornell.edu/cfr/text/49/563.9
- **14 CFR 25.1459** provides useful flight-recorder principles around reliable recorder power,
  crash/fire placement, and erasure controls. ETS does not claim FAA/TSO compliance from this software.
  Reference: https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol1/pdf/CFR-2023-title14-vol1-sec25-1459.pdf
- **RFC 5848** targets origin authentication, message integrity, replay resistance, sequencing, and
  missing-message detection for signed logging. ETS uses its own canonical record format but adopts
  those security objectives. Reference: https://www.rfc-editor.org/rfc/rfc5848.html
- **NIST SP 800-92** treats logging as a lifecycle spanning generation, transmission, storage, access,
  and disposition. References: https://csrc.nist.gov/pubs/sp/800/92/final and
  https://csrc.nist.gov/pubs/sp/800/92/r1/ipd
- **NIST SP 800-193** establishes protect/detect/recover principles for platform firmware resiliency.
  Production Black Box therefore requires signed updates, measured boot, rollback controls, and secure
  recovery. Reference: https://csrc.nist.gov/pubs/sp/800/193/final
- **TCG TPM 2.0 Library Version 185 (March 2026)** supplies the current hardware-root model for device
  identity, attestation, sealed/non-exportable key use, and measured boot.
  Reference: https://trustedcomputinggroup.org/resource/tpm-library-specification/
- **NIST SP 800-57 Part 1 Rev. 5** supplies current final general key-management guidance.
  Reference: https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final
- **FIPS 140-3** defines requirements for cryptographic modules. The reference software does not itself
  claim FIPS validation. Reference: https://csrc.nist.gov/pubs/fips/140-3/final
- **RFC 3161** provides external proof-of-existence time stamping. ETS does not require a TSA per frame,
  but high-assurance deployments may timestamp or transparency-anchor sealed segment hashes.
  Reference: https://www.rfc-editor.org/rfc/rfc3161.html
- **NIST SP 800-88 Rev. 2 (September 2025)** provides the media-sanitization program model for device
  replacement and decommissioning. Reference: https://csrc.nist.gov/pubs/sp/800/88/r2/final

## Claims and non-claims

Black Box v1 software supports bounded claims that:

- accepted observations are digest-first and bounded rather than unrestricted raw payloads;
- every frame is chained to its predecessor and signed;
- a trigger freezes an explicit pre-trigger sequence boundary;
- post-trigger capture is bounded and explicitly represented;
- sealed segments bind the trigger, sequence range, ordered frame hashes, predecessor, chain head,
  seal reason, and signing-key identifier;
- removal, reordering, alteration, or key substitution causes verification failure;
- an active trigger can survive a supported software restart and continue capture;
- boot-counter rollback and boot-ID substitution without counter advance fail closed;
- Core receives a bounded manifest projection rather than the captured frame attributes;
- production mode rejects storage backends that do not meet the physical capability floor.

The recorder does not prove that a source told the truth, that every possible source signal was captured,
or that the software can survive physical destruction. It does not claim FIPS validation, FAA recorder
certification, automotive EDR compliance, or deployment-domain environmental qualification.

## Logical model

```text
source -> digest-only observation -> signed frame -> rolling pre-trigger ring
                                           |
                                        trigger
                                           |
                              freeze pre-event sequence window
                                           |
                                  bounded post-event capture
                                           |
                                  signed sealed segment
                                           |
                           +---------------+---------------+
                           |                               |
                           v                               v
                    ETS Core manifest                 ETS Vault
                    transparency event             full segment/artifact
```

Normal ring rotation is allowed only for frames not needed by an active incident. Once an incident is
sealed, the segment is outside ordinary ring rotation.

## Observation contract

`BlackBoxObservation` contains:

- `device_id` in the `ets-black-box:` namespace;
- boot ID and observation ID;
- source-system and event-type identifiers;
- optional subject/correlation references;
- UTC observation time;
- per-boot monotonic nanosecond value;
- clock-quality class and optional error bound;
- SHA-256 content digest and optional byte length;
- bounded JSON-native attributes;
- fixed `capture_mode=digest_only`.

There is no raw-payload field. Attributes are capped at 64 properties and 16 KiB canonical JSON. The
complete observation is also checked against the configured canonical-size limit before signing.

Large/sensitive artifacts should be stored through an authorized encrypted artifact/Vault path, with only
cryptographic digest/reference information in the Black Box frame.

## Frame contract

Every `SignedBlackBoxFrame` contains:

- global sequence number;
- boot counter;
- strict observation;
- previous frame SHA-256;
- current frame SHA-256;
- signing algorithm (`ed25519` for v1);
- signing-key identifier;
- Ed25519 signature.

The signing-key identifier is inside the signed payload. Substitution therefore changes both digest and
signature validation.

The first recorder frame uses an all-zero predecessor. A later retained rolling window keeps the real
predecessor hash on its first retained frame so a sealed segment remains linked to the omitted history.

## Boot and ordering semantics

Sequence numbers are global across boots for one recorder state. Within one boot, `monotonic_ns` must
strictly increase. UTC time can degrade without losing deterministic local order.

Persisted recorder state contains boot ID, monotonic boot counter, last sequence, chain head, last local
monotonic value, and active incident state.

- lower boot counter -> rejected as rollback;
- same boot counter with a different boot ID -> rejected;
- higher boot counter -> new boot accepted and per-boot monotonic state resets;
- global frame sequence/hash chain continues across boots.

The physical product should root the boot counter/anti-rollback state in TPM or equivalent qualified
hardware rather than an operator-editable file.

## Trigger and capture semantics

Supported trigger classes are `manual`, `fault`, `security`, `policy`, `power_loss`, `crash`, and
`watchdog`.

A trigger binds trigger ID, kind, bounded reason, UTC time, sequence-at-trigger, and optional actor
reference into the sealed segment. The v1 reference service permits one active incident at a time.

`pre_trigger_frames` controls the maximum retained frames ending at trigger sequence `T`.
`post_trigger_frames` controls how many frames are captured after `T` before automatic seal. A policy may
set post-trigger count to zero for immediate sealing.

Production profiles should convert counts into source-specific time/data-rate budgets and prove storage,
CPU, and power margins at worst-case configuration.

## Forced sealing

An active incident can be sealed before the desired post-window finishes only with an explicit forced
seal reason: `power_loss_imminent`, `operator`, or `recovery`.

This preserves partial evidence instead of discarding the incident. The manifest clearly records why the
post-window ended early.

A physical unit should wire brownout/UPS/supercapacitor indication to the power-loss-imminent path and
qualify the measured worst-case time from signal through durable seal.

## Segment sealing and verification

A `BlackBoxSegmentManifest` binds:

- device identity and trigger;
- first/last sequence and frame count;
- first/last observation time;
- seal time/reason;
- predecessor frame hash and final chain-head hash;
- ordered list of every frame hash in the signed segment payload;
- signing-key ID.

`segment_hash = SHA256(canonical_json(segment_payload))`

The segment ID is `bbxseg:<segment_hash>`, and the same payload is signed with Ed25519. Independent
verification checks every frame signature, sequence, predecessor link, final chain head, segment hash,
segment ID, and manifest signature.

## Storage contract

A Black Box store supports:

- exactly-once recorder-state initialization;
- atomic frame + resulting-state commit;
- durable trigger/boot-state update;
- pruning only the ordinary rolling window;
- insert-once sealed segment;
- atomic sealed-segment insertion + active-capture clearing.

### In-memory reference

`InMemoryBlackBoxStore` is deterministic and test-only. It is not durable and is never production-ready.

### SQLite reference

`SQLiteBlackBoxStore` uses WAL, `PRAGMA synchronous=FULL`, transactional frame/state commits, unique frame
sequence, and insert-only sealed-segment API. It is suitable for restart/recovery qualification.

It is still **software grade**: a privileged database/OS administrator can alter storage, normal hardware
may lose writes on power failure, and SQLite does not provide TPM custody, media encryption, measured
boot, or physical tamper resistance. It intentionally fails production qualification.

## Production capability floor

`BlackBoxBackendCapabilities.production_ready()` requires:

- atomic frame/state commit;
- crash consistency;
- durable writes;
- write-once sealed-segment enforcement;
- encryption at rest;
- qualified power-loss protection;
- hardware-backed keys;
- measured boot;
- tamper detection;
- `enforcement_boundary=hardware`.

`BlackBoxPolicy(require_production_backend=True)` refuses initialization when any capability is absent.
A future production adapter must back every claimed capability with qualification evidence; setting flags
alone is not sufficient product evidence.

## Device enrollment

ETS Device Enrollment v1 already reserves `product_type=black_box` and the `ets-black-box:` device ID
namespace. The physical product should use the shared ETS pending/enrolled/quarantined/revoked/
decommissioned lifecycle rather than inventing a separate identity plane.

Production enrollment should use X.509 with hardware custody or TPM attestation according to the shared
profile, with tenant/workspace scope remaining server-authoritative.

## Core and Vault integration

`BlackBoxRecorder.to_evidence_event()` emits a Core event with:

- `event_type=black_box.segment.sealed`;
- `source_system=ets-black-box`;
- `content_hash=<segment_hash>`;
- correlation ID equal to trigger ID;
- structural manifest metadata only;
- Core-supported `redaction_profile=none` because the projection is already minimized.

The Core projection intentionally omits frame attributes, trigger free-text reason, and actor reference.
The full sealed segment may be preserved in ETS Vault. Core then proves the segment identity while Vault
preserves the larger forensic object.

## Physical appliance requirements

### Platform

Recommended physical pilot floor:

- industrial x86-64 or ARM platform with Secure Boot/measured-boot capability;
- discrete TPM 2.0 or equivalent secure element;
- ECC RAM where supported;
- separate OS and recorder-media failure domains;
- independent-enough watchdog for application/OS stalls;
- protected hardware anti-rollback/boot state.

### Recorder media

Production recorder media should use enterprise SSD/NVMe with documented power-loss protection, high
endurance, ECC/data-path protection, health telemetry, verified flush/FUA behavior, and redundancy
appropriate to availability goals. Mirroring improves availability but is not evidence immutability.

### Power

The appliance should include hold-up power (UPS/supercapacitor/battery-backed equivalent), a brownout or
power-loss-imminent signal, measured reserve margin for durable seal under worst media latency, and
power-state telemetry. The margin must be destructively tested, not assumed.

### Tamper/physical controls

Recommended controls include chassis-open/tamper input, tamper-evident seals, protected debug/JTAG/serial
interfaces, disabled/authenticated production maintenance ports, and tamper events as evidence/triggers.

Crash/fire/water/vibration/EMI claims require separate qualification of the actual enclosure, storage,
power, and mounting design for the target domain.

## Firmware/update requirements

Production updates should be signed, anti-rollback protected, and use an atomic A/B or equivalent update
with protected recovery. The unit should record software/image digest, firmware versions, Secure Boot
state, measured-boot identity, update outcome, recovery, and unexpected measurement drift as ETS evidence.

## Cryptographic requirements

- SHA-256 is the v1 observation/frame/segment digest.
- Ed25519 is the v1 software reference signing algorithm.
- Production device/recorder private keys should be non-exportable.
- Key identifiers are signed.
- Rotation must preserve historical verification material.
- Fleet trust policy must distinguish present revocation from historical validity/standing.
- regulated profiles use approved/validated cryptographic modules where required.

## Time requirements

Time is evidence with quality, not assumed truth. Each observation has UTC time, clock quality, optional
error bound, local monotonic value, and global recorder sequence.

Production deployments should use authenticated/qualified time appropriate to the use case (for example
NTS, PTP, or GNSS). Loss of trustworthy UTC degrades clock quality but does not stop local ordering.
High-assurance deployments may periodically anchor segment/chain heads into ETS or an RFC 3161 TSA.

## Network and management boundary

Default production posture:

- no direct inbound Internet management exposure;
- separate management/capture interfaces where practical;
- mutually authenticated device communication;
- least-privilege outbound paths to Gateway/Core/Vault/fleet;
- capture continues while upstream networking is unavailable;
- local maintenance disabled or physically controlled by default;
- no reusable credentials in CLI arguments/logs;
- MFA-backed human administration;
- strict rate/size bounds on external source input.

## Recovery behavior

On restart the recorder validates persisted identity, key ID, boot counter, live sequence/hash chain,
frame signatures, state head, and frozen incident-window availability before new writes. An active
incident remains active across restart. A higher boot counter/new boot may continue the remaining
post-window. If recovery sees a completed post budget, it seals with `seal_reason=recovery`.

## Privacy/minimization

A Black Box can become a high-value surveillance target if capture is unbounded. Every deployment source
profile should specify necessity, raw-content prohibition/exception, retention, access roles, export
destination, and legal restrictions.

Credentials, tokens, private keys, unrestricted packet payloads, full prompts, or documents must not be
captured merely because they are available. Sensitive artifacts use an encrypted artifact/Vault boundary
and Black Box records only digest/reference information.

## Failure modes that fail closed

The implementation rejects or detects invalid device namespace, malformed hashes, raw/unknown observation
fields, oversized observations, non-increasing per-boot monotonic values, boot rollback, boot-ID
substitution, signing-key-ID substitution, frame gaps, predecessor mismatch, invalid signatures, missing
frozen frames, segment digest/ID/signature mismatch, overlapping active trigger, and production startup on
an unqualified backend.

## Remaining physical qualification gates

Before marketing a physical unit as **production ETS Black Box**, complete at least:

1. TPM-backed non-exportable signing/enrollment adapter;
2. Secure Boot/measured-boot evidence and enforcement;
3. hardware anti-rollback boot counter;
4. encrypted recorder media;
5. enterprise PLP media with destructive power-cut testing;
6. protected write-once sealed-segment boundary;
7. brownout/hold-up timing qualification;
8. signed anti-rollback A/B update and protected recovery;
9. chassis-tamper trigger/evidence qualification;
10. sustained endurance/thermal/write-rate soak;
11. corruption/media-failure injection and recovery;
12. fleet enrollment/rotation/revocation/quarantine/decommission tests;
13. authenticated asynchronous Gateway/Core and optional Vault export;
14. historical verifier/trust-material packaging;
15. NIST SP 800-88 Rev. 2 sanitization procedure;
16. target-domain environmental/regulatory qualification where applicable.
