# Wave 1 R0.11 — Clock displacement, rollback and time-quality handling

**Tracking:** #895  
**Parent:** #814  
**Claim boundary:** `r0_11_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.11 proves that ETS Edge does not treat wall-clock time as the sole ordering
authority.

The test deliberately moves wall time forward and backward, creates an
unsynchronized/untrusted interval, and restores synchronization while requiring:

- monotonic/process-relative ordering to remain forward-moving;
- event/log/checkpoint ordering to remain non-regressing;
- explicit time quality to follow the observed clock state;
- prior evidence to remain immutable;
- independent external time observation;
- prior R0.8/R0.9/R0.10 boundaries to remain healthy.

## Ordering model

R0.11 retains distinct evidence for:

```text
wall-clock observation
monotonic/relative ordering
clock synchronization state
external independent UTC observation
event/log/checkpoint ordering
```

A wall-clock rollback is allowed. An evidence-order rollback is not.

## Time-quality states

The retained profile uses explicit classifications:

- `trusted_synchronized`
- `externally_bounded_unsynchronized`
- `device_relative_untrusted`
- `unknown`

Restoring synchronization does not retroactively upgrade the quality of evidence
captured while time was untrusted.

## Safety boundary

The evaluator never sets system time.

Clock manipulation remains an operator/controller action on the W1-1 qualification
clock boundary and must be independently observed.

The run must retain before execution:

- exact forward offset;
- exact rollback offset;
- unsynchronized interval when used;
- restore step;
- per-step tolerance and duration;
- controller implementation/digest;
- external observer identity;
- operator stop condition.

Do not alter firmware/RTC state unless that action is explicitly part of the approved
qualification profile.

## Baseline

The `EdgeR0ClockBaseline` binds the exact R0.10 PASS and retains:

- DUT wall-clock UTC;
- monotonic reference;
- external UTC;
- synchronization state;
- time quality;
- boot identity;
- local checkpoint and log head;
- queue/storage/network health;
- representative proof material.

R0.11 begins synchronized with trusted time.

## Fault profile

The `EdgeR0ClockFaultProfile` is ordered and immutable.

At minimum it contains:

1. a positive forward jump;
2. a negative rollback;
3. a restore step.

An explicit unsynchronized interval may also be retained.

The final profile step must restore trusted synchronized time.

## Transition observations

For each profile step, retain:

- controller command time;
- independent observation time;
- DUT wall-clock UTC;
- DUT monotonic value;
- external UTC;
- observed synchronization state;
- observed time quality;
- queue/storage/network guardrail state;
- controller, external-observer and DUT observation digests.

The observed DUT-vs-external offset must match the requested profile within the
declared tolerance.

## Evidence generated across clock faults

Each `EdgeR0TimedEvidenceEvent` retains:

- stable event identity;
- explicit sequence number;
- profile-step binding;
- wall-clock UTC;
- monotonic ordering value;
- external UTC;
- synchronization state;
- time quality;
- content/proof commitment;
- local checkpoint;
- log head.

The evaluator requires monotonic values to continue increasing even when wall-clock
time moves backward.

Checkpoint ordering may remain equal or increase, but must not regress.

## Immutability

The complete fault-window event set is committed canonically.

Restoration must carry the same event commitment. A mismatch is treated as evidence
rewrite.

The pre-fault log-head digest must also still be observable after restoration.

## Prior-phase guardrails

R0.11 is invalid if clock testing silently broadens into another fault domain.

Throughout the clock profile:

- queue state must remain inside the R0.9 bounds;
- storage must remain below the R0.8 high watermark;
- network connectivity must remain healthy under the R0.10 boundary.

A violation fails the phase instead of redefining the clock test.

## Independent verification

The bound off-DUT verifier must verify:

1. representative pre-fault proof material; and
2. every timed event retained during the clock-fault window.

Verification failure, proof-digest mismatch, non-independent execution, or verifier
host mismatch fails R0.11.

## Restoration

A valid restoration requires:

- synchronized clock state;
- `trusted_synchronized` time quality;
- DUT wall time within the declared tolerance of independent external UTC;
- increasing monotonic value;
- preserved event commitment;
- preserved pre-fault log head;
- non-regressing checkpoint;
- healthy queue/storage/network state.

## Evaluator

```bash
python3 -m ets.physical_edge_phase10 evaluate-r0-11 \
  --manifest /path/to/bench-manifest.json \
  --phase9-evaluation /path/to/r0-10-evaluation.json \
  --baseline /path/to/clock-baseline.json \
  --fault-profile /path/to/clock-fault-profile.json \
  --window /path/to/clock-fault-window.json \
  --restoration /path/to/clock-restoration.json \
  --proof-receipt /path/to/pre-fault-proof.json \
  --proof-receipt /path/to/fault-event-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-11-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_11_passed=true
```

It is not a secure hardware-time claim, universal timestamp-truth claim, production
clock-resilience claim, or HQP-5 physical qualification result.

## Failure conditions

R0.11 fails on, among other cases:

- profile/transition mismatch;
- requested wall-clock offset not independently observed;
- monotonic transition or event regression;
- event/checkpoint regression;
- duplicate event identity;
- event time quality inconsistent with the active clock state;
- restoration retroactively rewriting prior event commitments;
- changed pre-fault log head;
- prior queue/storage/network boundary crossing;
- missing or failed independent proof verification;
- restoration outside the declared clock tolerance;
- untrusted post-recovery canary.

Failed runs remain retained as evidence.

## Next gate

After physical R0.11 is green, proceed to **R0.12 valid software upgrade**.
