# Formal Evidence Status Snapshot — 2026-06-24

## Purpose

This snapshot records the current formal evidence state after the GitHub Actions
startup/log-retention issue was resolved. It supports issues `#70` and `#67` by
separating command-level formal failures from infrastructure failures.

## Current infrastructure finding

The original no-step/no-log GitHub Actions failure is resolved. Current workflow
runs start runners, populate job steps, and expose command-level failures.

That matters because formal evidence can now be evaluated as engineering output
instead of being blocked by missing runner diagnostics.

## Current workflow state

| Workflow | Current interpretation |
| --- | --- |
| CI | Repository validation path passed after #76 remediation: Ruff, Mypy, Pytest, dependency audit, secret scan, and Explorer build. |
| Benchmarks | Completed successfully on the post-#76 PR run. |
| Formal Specs / TLC | Fails at the model execution command with populated steps. This is a formal-model evidence issue, not an Actions startup issue. |
| Lean Mechanized Proofs | Fails at the proof validation command with populated steps. This is a proof-target issue, not an Actions startup issue. |
| Apalache Symbolic Verification | Fails at the symbolic model command with populated steps. This is a symbolic-model issue, not an Actions startup issue. |

## Sprint changes in this branch

This branch adds evidence capture instead of weakening formal coverage:

- `scripts/run-tlc-models.sh` runs the configured TLC model set, records one log
  per model, writes `summary.md`, writes `results.json`, and fails at the end if
  a non-timeout failure occurs.
- `.github/workflows/tla.yml` now uploads `tlc-evidence-artifacts` even on
  failure.
- `.github/workflows/full-tlc-evidence.yml` adds a manual full TLC evidence gate
  outside the pull-request smoke gate.
- `scripts/run-lean-proofs.sh` records one log per Lean proof file and uploads a
  structured summary through the Lean workflow.
- `scripts/run-apalache-models.sh` records one log per symbolic target and
  uploads a structured summary through the Apalache workflow.
- `docs/research/FORMAL_EVIDENCE_CAPTURE_GATE.md` defines the claim-use policy
  for passed, failed, timed-out, deferred, and missing formal evidence.

## Evidence artifacts created by the new gate

| Artifact | Producer | Purpose |
| --- | --- | --- |
| `tlc-evidence-artifacts` | Formal Specs workflow | PR-gate TLC model logs and summary. |
| `full-tlc-evidence-artifacts` | Full TLC Evidence Capture workflow | Long-running TLC evidence package outside the PR gate. |
| `lean-proof-artifacts` | Lean Mechanized Proofs workflow | Per-proof Lean validation logs and summary. |
| `symbolic-proof-artifacts` | Apalache Symbolic Verification workflow | Per-target symbolic model logs and summary. |

## Claim boundaries

The project may claim that evidence was executed only when a workflow run, commit
SHA, and retained artifact exist for the claim.

The project may not claim:

- universal theorem proof;
- universal liveness;
- Byzantine consensus;
- Internet-scale adversarial correctness;
- production throughput;
- legal sufficiency;
- real-world evidence completeness.

Formal failures must be represented as pending remediation, not as passed
research evidence.

## Next execution requirement

After this branch is merged, run the manual `Full TLC Evidence Capture` workflow
from the default branch and record:

- workflow run ID;
- commit SHA;
- timeout policy;
- artifact name;
- pass/fail/timeout status for every TLC target.

That run is the concrete execution step for closing issue `#70`. Issue `#67`
can close when the retained evidence references are copied into the evidence
capture report and downstream publication/dissertation claims cite only retained
artifacts.
