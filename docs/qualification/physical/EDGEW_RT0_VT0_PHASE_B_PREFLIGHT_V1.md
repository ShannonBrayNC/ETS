# EDGEW-RT0-VT0 HQP Phase B Preflight v1

Status: read-only simulated-lab preflight  
Depends on: passing VT0 Phase A evidence  
Cases prepared:

- `EDGE-HQP-DUR-001`
- `EDGE-HQP-BPR-001`
- `EDGE-HQP-OFF-001`
- `EDGE-HQP-CHK-001`
- `EDGE-HQP-OPS-001`

## Purpose

Phase B moves from identity/posture into durable behavior and bounded degradation. The preflight deliberately performs no fault or restart stimulus. It establishes that the current VT0 runtime, qualification storage, queue, exact DUT build, retained Phase A package, and external verifier environment are ready before execution.

Run from the T430 host:

```bash
bash scripts/qualification/edgew_vt0/preflight_vt0_phase_b.sh
```

The preflight is read-only. A ready result ends with:

```text
PHASE_B_PREFLIGHT_READY=true
```

## DUR-001 — controlled restart

Planned stimulus:

1. capture one synthetic webhook;
2. retain the authoritative receipt, committed event, inclusion proof, export bundle, and signed tree head;
3. restart only `edge-api`;
4. retrieve the same event and proof after readiness returns;
5. verify inclusion again.

The virtual result can establish restart persistence for the bounded software/runtime path. It cannot establish physical power-loss durability.

## BPR-001 — bounded backpressure

The execution harness will first drain pending synchronization state, then temporarily recreate only `edge-webhook` with:

```text
ETS_EDGE_SYNC_MAX_ITEMS=3
ETS_EDGE_SYNC_MAX_BYTES=1048576
```

With the demo upstream stopped, the first three synthetic captures must receive authoritative `201` receipts. The fourth must fail explicitly with `503` backpressure. After reconnect, the queue must drain and all previously accepted records must remain recoverable.

The base queue configuration is restored after the case. No volume deletion is permitted.

## OFF-001 — offline local evidence

Only the demo `edge-upstream` container is stopped. Local Edge capture remains reachable.

Required evidence includes:

- upstream-stop receipt/state;
- local capture receipt;
- committed event;
- inclusion proof and bundle;
- local proof verification while upstream is unavailable;
- retryable synchronization state;
- queue state after `edge-webhook` restart;
- reconnect/synchronization result.

This is a bounded virtual network dependency test, not physical NIC/router qualification.

## CHK-001 — proof continuity

The execution retains the DUR checkpoint and inclusion proof before later Phase B disruptions. After BPR/OFF activity it retrieves the later tree head, requests an ETS consistency proof, verifies that proof, and re-verifies the earlier DUR inclusion proof.

No log repair or history rewrite is allowed to force continuity.

## OPS-001 — source-to-proof export and host verifier

The selected OFF capture is exported as:

`receipt -> canonical event -> inclusion proof -> proof bundle -> tree head`.

Verification executes outside the guest on the T430 host using ETS Verifier. The lab trust file is constructed from the separately retained **public** VT0 device identity.

That separation proves independent verifier execution/reproduction. It does **not** prove independent trust-anchor issuance, production trust distribution, or third-party validation.

If the T430 host cannot import `ets.verifier.cli`, the preflight blocks Phase B rather than silently weakening OPS-001.

## Secret boundary

The guest's reusable API key is used only in a temporary guest-local curl configuration and must be deleted during cleanup. Private signing-key bytes are never exported. Host evidence may contain public device identity and public verification material only.

## Recovery boundary

Every executable Phase B run must:

- start `edge-upstream` during cleanup;
- restore the base `edge-webhook` Compose definition;
- retain Docker volumes;
- leave committed evidence history intact;
- retain failures rather than editing evidence until a case passes.

## Claim boundary

Every Phase B VT0 result remains `simulated`.

It does not establish physical:

- storage durability under actual power interruption;
- physical NIC/router reliability;
- TPM/HSM key custody;
- hardware performance envelope;
- truth/completeness of source observations;
- compliance, safety, production readiness, or GA.

The physical EDGE-RT0 campaign must execute the normative corpus again on the exact named physical DUT with independent observation and HQP-2 verification.
