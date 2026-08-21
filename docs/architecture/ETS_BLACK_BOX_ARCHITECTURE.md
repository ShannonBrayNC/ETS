# ETS Black Box Architecture

## Role in the ETS device family

ETS Black Box is the incident-survivability capture tier. It complements rather than duplicates the
other ETS products:

- **Edge** captures evidence at a source boundary and supports offline operation.
- **Gateway** aggregates and relays multiple source/device streams.
- **AI Witness** specializes in AI/agentic workload observations.
- **Black Box** specializes in rolling pre-event and sealed post-event incident reconstruction.
- **Vault** preserves evidence/artifacts under long-term retention controls.
- **Verifier** independently validates signed evidence and ETS proofs.

## Component model

```text
+------------------------------------------------------------------+
|                     Physical ETS Black Box                       |
|                                                                  |
| source adapters -> observation normalization -> frame signer     |
|                                                / TPM in prod     |
|                                                      |           |
|                                           rolling pre-event ring |
|                                                      | trigger   |
|                                                      v           |
|                                               frozen window      |
|                                                      |           |
|                                               post capture       |
|                                                      |           |
|                                                      v           |
|                                               segment sealer     |
|                                                  /        \       |
|                                         sealed local     export  |
+--------------------------------------------------|---------|-------+
                                                   |         |
                                                   v         v
                                                Vault      Core
                                               segment    manifest
```

## Trust boundaries

### Source boundary

A source adapter can claim only what it directly observed. It cannot assert tenant/workspace authority or
hardware attestation. Source truth/authenticity remains separate from recorder integrity.

### Recorder boundary

The recorder owns ordering, hash chaining, signatures, trigger state, and local durability. A physical
profile extends this boundary to TPM/secure element, measured boot, PLP media, and power hold-up.

### Sealed-segment boundary

A sealed segment is no longer in ordinary ring rotation. Production storage must prevent or independently
detect overwrite outside the normal application process trust boundary.

### Export boundary

Export cannot reinterpret the segment. Core receives a minimized manifest tied to `segment_hash`; Vault
may receive the exact full segment. Network failure leaves local sealed evidence intact for retry.

## State machine

```text
BOOT / RECOVER
      |
      v
ROLLING_CAPTURE -- trigger --> INCIDENT_ACTIVE
      ^                            |
      |                            | post budget reaches zero
      |                            | or forced seal
      |                            v
      +----------------------- SEAL_SEGMENT
                                   |
                                   +--> insert sealed segment once
                                   +--> clear active incident atomically
```

Restart validation occurs before accepting new frames. An active incident is not silently canceled by a
process/device restart.

## Cryptographic construction

Frame payload:

```text
schema_version
sequence
boot_counter
observation
previous_frame_hash
signing_key_id
```

`frame_hash = SHA256(canonical_json(frame_payload))`

`frame_signature = Ed25519(frame_payload)`

Segment payload binds device, trigger, first/last sequence, count, first/last observation time, seal time
and reason, predecessor, chain head, ordered frame hashes, and signing-key ID.

`segment_hash = SHA256(canonical_json(segment_payload))`

`segment_id = "bbxseg:" + segment_hash`

The segment payload is independently Ed25519 signed.

## Storage model

The SQLite reference has three logical tables:

- singleton recorder state;
- live frames keyed by global sequence;
- sealed segments keyed by segment ID.

A new frame and resulting state head commit in one transaction. Segment insertion and active-state clear
commit in one transaction. WAL plus `synchronous=FULL` gives a useful crash-consistency reference, not a
physical PLP claim.

A production backend preserves the same logical atomicity while moving durability, encryption,
write-once enforcement, measured boot, and key custody into qualified hardware boundaries.

## Enrollment integration

Device Enrollment v1 already defines `product_type=black_box` and `ets-black-box:` IDs. Physical units
use the common ETS lifecycle and server-authoritative scope. Production enrollment should use the shared
X.509/TPM attestation contract, with non-exportable key custody and explicit key rotation/revocation.

## Deployment profiles

**Conformance/virtual:** software Ed25519 key, in-memory or SQLite store, no hardware-attestation claim.

**Physical pilot:** TPM/secure-element key, Secure Boot/measured boot, encrypted enterprise PLP media,
hold-up power/brownout trigger, tamper input, authenticated fleet enrollment, private management plane.

**Production:** physical pilot plus destructive power-cut evidence, anti-rollback update evidence,
storage/endurance/thermal/tamper/source-adapter qualification, complete key lifecycle, and target-domain
environmental/regulatory testing where relevant.
