# Wave 1 R0.6 — Active-capture hard-power interruption and recovery

**Tracking:** #884  
**Parent:** #814  
**Claim boundary:** `r0_6_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.6 moves the physical Edge Compact R0 corpus from an idle power cut to a
power interruption during controlled active ingestion.

The key question is not whether every in-flight request survives. The required
property is narrower and stronger:

> No record that was authoritatively acknowledged/committed before the cut may
> silently disappear after recovery.

At the same time, an in-flight request that had no authoritative acknowledgement
before power loss must never be rewritten after the fact as though the client had
received one.

## Preconditions

Do not begin physical R0.6 unless:

- the exact W1-1 bench manifest is ready;
- R0.1 through R0.5 are retained as PASS for the same DUT/build/configuration;
- the W1-1 power control is operator-gated and independently observable;
- an isolated qualification source/workload is available;
- synchronization is intentionally idle for this phase;
- the DUT is recoverable and prior retained evidence exists away from the DUT;
- the operator explicitly authorizes the physical cut.

If any precondition is false, abort the physical cut.

## Required transaction boundary

The pre-cut workload must contain at least:

1. one request that has an authoritative Edge commit/acknowledgement and retained
   proof material before the cut; and
2. one request that is demonstrably in flight and unacknowledged when the cut is
   commanded.

The retained `EdgeR0ActiveCaptureWindow` therefore separates:

- `authoritatively_committed`;
- `in_flight_unacknowledged`;
- `client_attempt_only`.

Only the first class is allowed to carry pre-cut authoritative event, commit, and
proof fields.

## Physical stimulus

The qualification tooling does **not** actuate power.

The independent bench controller/operator:

1. starts the bounded capture workload;
2. confirms active ingestion;
3. records the cut boundary;
4. removes physical power using the W1-1 control;
5. independently observes loss of DUT power/reachability;
6. restores power;
7. independently observes restoration.

Controller and observer artifacts are retained separately and committed by SHA-256.

## Recovery classification

Every pre-cut attempt must receive exactly one recovery disposition:

- `committed_before_cut_preserved`;
- `not_authoritatively_acknowledged_but_commit_recovered`;
- `not_authoritatively_acknowledged_retryable`;
- `not_authoritatively_acknowledged_absent`;
- `rejected_with_explicit_receipt`.

The second case is important. Storage may contain a commit for which the client
never received a pre-cut acknowledgement. ETS may preserve that recovered commit,
but it must not relabel it as an acknowledgement that occurred before the cut.

## Pass/fail invariants

R0.6 fails if any of the following occurs:

- an acknowledged pre-cut commit is missing after recovery;
- a recovered event/proof does not match the acknowledged pre-cut commit;
- one logical attempt has more than one authoritative recovered commit;
- any attempt lacks an explicit recovery disposition;
- an unacknowledged attempt is retroactively classified as
  `committed_before_cut_preserved`;
- a recovered commit lacks independent proof verification;
- the independent verifier host does not match the W1-1 binding;
- the Linux boot ID does not change across the hard-power interruption;
- the declared R0 software-backed device identity changes unexpectedly;
- filesystem recovery is not clean;
- the post-recovery canary does not independently verify.

## Evaluator

The first implementation intentionally keeps destructive control outside the ETS
CLI. Physical/controller artifacts are assembled into the strict R0.6 models and
then evaluated with:

~~~bash
python3 -m ets.physical_edge_phase5 evaluate-r0-6 \
  --manifest /path/to/bench-manifest.json \
  --phase4-evaluation /path/to/r0-5-evaluation.json \
  --window /path/to/active-capture-window.json \
  --power-observation /path/to/power-observation.json \
  --recovery /path/to/recovery.json \
  --attempt-recovery /path/to/attempt-1-recovery.json \
  --attempt-recovery /path/to/attempt-2-recovery.json \
  --proof-receipt /path/to/recovered-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-6-evaluation.json
~~~

A passing output has:

~~~text
disposition=phase_evidence_only
r0_6_passed=true
~~~

That remains phase evidence. It is not an HQP-5 qualification claim.

## Independent verification rule

Every authoritative recovered commit must have an off-DUT verification receipt.
This includes:

- acknowledged pre-cut commits that survive; and
- unacknowledged commits discovered after recovery.

The latter proves only that a commit is recoverable and independently verifiable.
It does not prove that the client received an acknowledgement before the cut.

## Post-recovery canary

After recovery, issue one new bounded capture and independently verify its proof.

The canary establishes that the recovered Edge can continue operating without
modifying or repairing the pre-cut history.

## Failure handling

A failed physical run is retained as evidence.

Do not edit the package to make it pass. Seal the failed run, classify whether the
failure belongs to the DUT, harness, execution, or profile, fix the engineering
problem separately, and run a new package with explicit linkage.

## Next gate

After R0.6 is green on a named physical DUT, proceed to **R0.7 synchronization
hard-power interruption**. R0.7 deliberately introduces active synchronization and
must remain separate from the active-ingestion failure semantics proven here.
