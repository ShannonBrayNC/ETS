# Hardware Qualification Execution Order

**Locked:** 2026-09-18  
**Primary trackers:** #868, #814, #812

This file records the current execution order for ETS physical and hardware
qualification. The order is intentional and must not drift silently.

## Priority rule

When the Ranger R0 bench is physically available, **#868 is the highest operator
execution priority**.

When that bench is unavailable, implementation work continues in parallel on the
Edge Compact R0 qualification corpus under #814. Android Beta 0 under #812 remains
an independent lane.

## Locked sequence

### Lane P0 — Agent 365 → Ranger R0

1. #868 Phase A — no-motion preflight.
2. Retain Phase A PASS.
3. #868 Phase B — wheels-off-ground actuation.
4. Retain Phase B PASS.
5. Phase C — first fully live Agent 365 → SharePoint → Gateway → physical R0 mission.
6. Phase D — contradiction matrix.
7. Phase E — integrated soak.
8. Phase F — 72-hour gate.

No parallel software work may be interpreted as superseding this physical priority.

### Lane E — Edge Compact R0

The qualification order is:

1. R0.1 provisioning/build identity.
2. R0.2 identity persistence.
3. R0.3 sustained capture and independent proof.
4. R0.4 upstream loss/offline capture/reconnect.
5. R0.5 idle hard-power recovery.
6. R0.6 active-capture hard-power recovery.
7. R0.7 synchronization hard-power recovery.
8. R0.8 disk pressure/exhaustion.
9. R0.9 queue saturation/backpressure.
10. R0.10 network instability.
11. R0.11 clock displacement.
12. R0.12 valid upgrade.
13. R0.13 failed upgrade/rollback.
14. R0.14 recovery media.
15. R0.15 endurance/soak.
16. R0.16 source-to-proof operator workflow.
17. R0.17 independent HQP-2 verification.

Implementation completion and physical qualification are separate facts. Closing an
implementation issue means the execution/evaluation machinery exists. It does not
mean a physical DUT passed that phase.

### Lane A — Android Beta 0

#812 proceeds independently and does not serialize routine Edge or Ranger work.
Only shared-contract defects in HQP, Evidence Object, custody, Gateway,
synchronization or Verify may become cross-lane blockers.

### Legacy hardware

The Linksys BEFSR41 current-scope characterization is complete. D-Link and other
legacy devices are follow-on work unless they expose a shared-contract defect or
become necessary as fault-injection infrastructure.

## Destructive-action boundary

ETS qualification tooling may record, validate and evaluate destructive stimuli but
must not silently execute them.

Explicit operator control and independent observation remain mandatory for:

- hard power removal;
- destructive storage pressure or exhaustion;
- recovery-media execution;
- firmware/security-state changes;
- any action that could erase the sole retained evidence copy.

## Change control

Reordering this sequence requires a documented blocker, dependency or safety reason
on the relevant parent issue. The replacement order must be recorded before work
proceeds under the new priority.
