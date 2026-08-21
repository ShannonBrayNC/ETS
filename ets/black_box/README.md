# ETS Black Box

`ets.black_box` is the software reference implementation for the ETS Black Box incident-recorder
contract.

The Black Box is intentionally different from ETS Vault. Vault is the long-term preservation tier.
Black Box continuously maintains a bounded rolling observation window, freezes that window when an
incident trigger occurs, records a bounded post-trigger interval, and seals the resulting incident
segment so it can be independently verified and exported into ETS.

## Reference flow

```text
source observations
      |
      v
bounded digest-only frame
      |
      v
Ed25519 signed hash chain
      |
      +---- normal operation ----> rolling pre-trigger buffer
      |
      +---- trigger -------------> freeze pre-window
                                      |
                                      v
                              post-trigger capture
                                      |
                                      v
                              signed sealed segment
                                      |
                          +-----------+-----------+
                          |                       |
                          v                       v
                    ETS Core manifest        ETS Vault/artifact
                    transparency record      preservation
```

## Implemented software contract

- strict digest-first observations with bounded metadata;
- global monotonic frame sequence and per-boot monotonic clock ordering;
- explicit boot ID and monotonic boot counter;
- SHA-256 hash chaining and Ed25519 signatures for every frame;
- configurable rolling pre-trigger buffer;
- fault, security, policy, power, crash, watchdog, and manual triggers;
- bounded post-trigger capture;
- forced sealing for power-loss-imminent and controlled operator/recovery cases;
- signed segment manifests that bind every ordered frame hash;
- independent frame and segment verification;
- crash-consistent SQLite reference storage using WAL and `synchronous=FULL`;
- active-trigger recovery across process/device restart;
- manifest-only projection into the stable ETS Core `EvidenceEvent` contract;
- explicit production-backend capability qualification.

## Non-claims

The in-memory backend is test-only. The SQLite backend is a software recovery reference. Neither is
a production crash-survivable recorder boundary and both intentionally fail
`require_production_backend=True`.

A production ETS Black Box requires hardware-qualified power-loss protection, encrypted recorder
media, hardware-backed non-exportable device/signing keys, measured boot, tamper detection, and an
independently enforced sealed-segment storage boundary. Aviation, automotive, rail, maritime, or
industrial certification is deployment-specific and is not claimed by this software module.

See:

- `docs/spec/ETS_BLACK_BOX_V1.md`
- `docs/architecture/ETS_BLACK_BOX_ARCHITECTURE.md`
- `docs/security/ETS_BLACK_BOX_THREAT_MODEL.md`
- `docs/test/ETS_BLACK_BOX_TEST_PLAN.md`
