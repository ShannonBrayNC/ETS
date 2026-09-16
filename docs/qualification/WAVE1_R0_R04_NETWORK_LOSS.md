# Wave 1 W1-4 — Edge Compact R0 R0.4 network-loss qualification

Tracking: #824, parent #814.

R0.4 is the first deliberate fault-injection phase for the physical Edge Compact R0 profile. It begins only after the same named DUT/build/configuration has passing R0.1-R0.3 phase evidence.

## Claim boundary

Passing R0.4 remains `phase_evidence_only` and uses:

`r0_4_phase_evidence_not_a_physical_qualification_result`

It does not publish `lab_tested`, `qualified`, production readiness, or a hardware-attestation claim.

## Purpose

Demonstrate that removing **upstream reachability** does not remove the Edge's local evidence function:

`external loss stimulus → loss independently observed → local capture continues → local proof continues → queue retains work → reconnect independently observed → sync resumes → outage event set accepted exactly once → independent verification`

The DUT itself must remain locally reachable throughout the outage. R0.4 is not a cable-pull-from-the-DUT test if that cable also removes the controller's ability to observe local Edge behavior. Prefer an isolated upstream path control, firewall/routing boundary, managed switch/VLAN control, or equivalent lab mechanism that leaves the Edge/controller local path intact.

## Authority and safety boundary

The W1-4 CLI **does not change networking**. The W1-1 manifest identifies the network control and requires explicit operator approval because the stimulus is disruptive.

R0.4 does not include:

- hard power removal;
- disk fill or queue-saturation testing;
- clock manipulation;
- firmware/BIOS changes;
- upgrade/rollback;
- recovery-media execution.

Those remain later R0 gates.

## Minimum R0.4 envelope

The baseline is intentionally semantic rather than a throughput benchmark:

- at least **30 seconds** of independently confirmed upstream loss;
- at least **10 authoritative local captures** during that confirmed outage;
- one retained local proof per capture;
- independent proof verification on the W1-1 verifier host;
- reconnect observation produced independently of the DUT;
- complete synchronization of the outage event set;
- no remaining pending, in-flight, retryable, or terminal queue state at the end of the controlled run;
- one upstream acceptance for every outage capture with no duplicate idempotency key.

A later endurance gate repeats offline/reconnect cycles for a much longer duration. R0.4 only establishes the first controlled physical fault semantic.

## Operator sequence

1. Confirm the exact W1-1 `ready_for_qualification` bench manifest.
2. Confirm the same DUT has passing R0.3 evidence.
3. Capture `/edge/v1/sync/status` while upstream is healthy.
4. Start the external network controller/observer journal.
5. Apply only the predeclared W1-1 network control after operator authorization.
6. Independently establish that upstream is unreachable while the local Edge endpoint remains reachable.
7. Record the loss observation with `python -m ets.physical_edge_phase3 record-network-loss`.
8. Capture at least ten deterministic source events over at least thirty seconds.
9. Retain each `WebhookCaptureReceipt`, source payload digest and local inclusion proof.
10. Capture queue/resource state while upstream is unavailable. `pending` and `retryable_failure` are valid outage states; a terminal failure is not.
11. Verify every local proof away from the DUT and retain the verifier output.
12. Restore the upstream path with the external controller and independently observe reconnect.
13. Run the existing Edge sync endpoint until the controlled outage backlog is drained.
14. Retain every sync-run response, final queue status and upstream acceptance artifact.
15. Generate per-event upstream acceptance receipts and the reconnect summary.
16. Run `python -m ets.physical_edge_phase3 evaluate-r0-4`.
17. Preserve the failed evaluation unchanged if any invariant fails. Do not repair retained evidence in place.

## Required invariants

R0.4 passes only when all of the following are established for the exact outage window:

- the fault observation binds to the W1-1 network control and external observer;
- capture starts only after upstream loss is independently confirmed;
- every attempted offline sequence has one unique local record/event/log index;
- request-byte SHA-256 equals Edge `content_hash`;
- every offline record retains a local proof;
- every local proof verifies independently on the bound verifier host;
- the upstream event set after reconnect equals the outage event set exactly;
- idempotency keys are unique across the outage event set;
- every outage record has exactly one retained upstream acceptance;
- the final controlled-run queue is drained and upstream is `online`;
- no terminal failure or unexplained evidence-chain discontinuity remains.

## Failure interpretation

A failure is useful qualification evidence. Examples include silent local loss, a missing proof, a duplicate idempotency key, a record accepted upstream before reconnect, an unresolved retryable item, terminal queue state, or a verifier-host mismatch. The phase evaluator records these conditions as a failed R0.4 result; it does not convert them into a successful claim.

## Next gate

After R0.4 is green on a named physical DUT, proceed to the next controlled physical-recovery gate. Hard-power interruption should remain separate so network semantics are proven before filesystem/process recovery variables are introduced.
