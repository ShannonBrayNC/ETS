# Wave 1 R0.5 — Idle hard-power interruption and recovery

R0.5 is the first Edge Compact R0 qualification phase that intentionally removes physical power. It is deliberately restricted to an **idle** DUT. It does not authorize power removal during active capture, synchronization, upgrade, recovery, or storage mutation.

## Preconditions

Do not begin R0.5 unless all of the following are true:

- the exact W1-1 bench manifest is `ready_for_qualification`;
- R0.1 through R0.4 phase evidence passed for the same DUT/build/configuration;
- the W1-1 `power` control is present and requires operator approval;
- local Edge health is good;
- capture activity is idle;
- synchronization activity is idle;
- queue depth and queue bytes are zero;
- `pending`, `in_flight`, `retryable_failure`, and `terminal_failure` are all zero;
- the external observer and verifier are available;
- at least one representative committed proof is retained for post-recovery verification.

If any precondition is false, **abort the physical cut**. Do not try to convert a busy-system test into R0.5; that belongs to the later active-capture or active-sync power-loss phases.

## Authority boundary

`python -m ets.physical_edge_phase4` records and evaluates evidence only. It does **not** control a PDU, smart outlet, relay, BMC, UPS, GPIO line, or host shutdown interface.

The operator performs the external hard-power interruption using the W1-1 power control. The observer must independently retain evidence of both loss and restoration.

## Procedure

### 1. Record the idle pre-cut state

Retain:

- canonical public Edge device identity;
- current Linux boot ID;
- `/edge/v1/sync/status` output;
- current retained log/tree head artifact;
- one or more representative committed inclusion-proof artifacts;
- external observer receipt showing the DUT was reachable and idle.

Create the bounded pre-cut artifact with `record-pre-cut`. The command rejects a non-idle synchronization queue.

### 2. Perform the external hard-power cut

After operator approval:

1. record the controller command/receipt;
2. remove power using the bound W1-1 power control;
3. independently observe loss of DUT reachability/power;
4. leave the DUT unpowered long enough to establish a real interruption rather than a process restart;
5. restore power through the same controlled path;
6. independently observe restoration.

Create the retained power-event artifact with `record-power-event`.

### 3. Capture the recovery state

After the operating system and Edge services return:

- capture the new Linux boot ID;
- capture the canonical public Edge identity again;
- retain post-boot queue status;
- retain the recovery journal excerpt/artifact;
- retain filesystem/database recovery-check evidence;
- confirm the pre-cut log/tree head remains addressable;
- retain an external recovery observer receipt.

Create the recovery artifact with `record-recovery`.

The new boot ID must differ from the pre-cut boot ID. R0.5 still expects `key_custody=software_volume` and `hardware_attested=false`; TPM/Secure Boot claims remain outside Edge Compact R0.

### 4. Re-verify pre-cut committed evidence

On the independent W1-1 verifier host, verify every representative proof retained in the pre-cut snapshot. Record one `record-preserved-proof` receipt for each proof.

A missing proof, changed proof digest, failed inclusion verification, verifier-host mismatch, or non-independent execution context fails R0.5.

### 5. Run the post-recovery canary

Submit one bounded canary capture after recovery using the normal Edge ingress path. Retain its authoritative receipt and inclusion proof, then verify that proof on the independent verifier host.

Record the result with `record-canary`.

The canary demonstrates that recovery was not merely a successful boot: Edge must still be capable of committing new evidence and producing independently verifiable proof.

### 6. Evaluate R0.5

Run `evaluate-r0-5` with the manifest, passing R0.4 evaluation, pre-cut snapshot, power observation, recovery snapshot, all preserved-proof receipts, and the canary receipt.

R0.5 passes only when:

`idle pre-cut → external power loss → distinct reboot → same Edge identity → same idle queue semantics → pre-cut evidence still verifies → new canary verifies`

## Failure conditions

R0.5 fails on any unexplained divergence, including:

- power removal was commanded before the retained idle snapshot;
- queue was not demonstrably idle;
- Linux boot ID did not change;
- device ID, signing public key, fingerprint, custody, or attestation posture changed;
- filesystem recovery was not clean;
- the pre-cut log/tree head is missing or digest-mismatched;
- synchronized-record count changes during an otherwise idle interruption;
- unresolved pending/retryable/terminal work appears after recovery;
- any representative pre-cut proof cannot be independently verified;
- the post-recovery canary cannot be independently verified.

Failures are retained as evidence. Do not rewrite earlier artifacts to make a later evaluation pass.

## Claim boundary

A passing R0.5 evaluation remains:

`disposition=phase_evidence_only`

`claim_boundary=r0_5_phase_evidence_not_a_physical_qualification_result`

It is an input to the later canonical HQP-1 package and does not itself create a `lab_tested`, `qualified`, or HQP-5 registry claim.

## Next gate

Only after R0.5 is clean should Wave 1 progress to **power loss during active capture**. Power loss during synchronization remains a separate, later gate because it exercises a different persistence and acknowledgement boundary.
