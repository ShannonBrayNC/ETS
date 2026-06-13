# Model Checking Command Log

## Purpose

This document records the formal verification commands associated with Sprint
4. It separates commands available in CI from commands executed locally during
this sprint.

## Local Sprint 4 Execution

Local formal-tool execution was not performed in this environment.

Observed local tool availability:

| Tool | Local Status | Consequence |
| --- | --- | --- |
| `java` | Not found on shell path. | TLC cannot be executed locally here. |
| `tlc2.TLC` | Not found as a command. | Use CI workflow or install TLA+ tools. |
| `apalache-mc` | Not found on shell path. | Use CI workflow or install Apalache locally. |
| `lake` / Lean | Not found on shell path. | Use CI workflow or install Lean via elan. |

Sprint 4 therefore claims local document/test verification only, not local TLC,
Apalache, or Lean execution.

## GitHub Actions: TLC

Workflow: `.github/workflows/tla.yml`

The workflow installs Java 21, downloads `tla2tools.jar`, and runs:

```text
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSLog.tla -config ETSLog.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSVerifierFederation.tla -config ETSVerifierFederation.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSTemporalByzantineFederation.tla -config ETSTemporalByzantineFederation.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSProbabilisticTrust.tla -config ETSProbabilisticTrust.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSLivenessFederation.tla -config ETSLivenessFederation.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSAsyncTransport.tla -config ETSAsyncTransport.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSTemporalLivenessTheorems.tla -config ETSTemporalLivenessTheorems.cfg -deadlock
java -cp ../../tools/tla2tools.jar tlc2.TLC ETSUniversalTemporalLiveness.tla -config ETSTemporalLivenessTheorems.cfg -deadlock
```

Interpretation:

- This is bounded TLC model checking.
- This is bounded explicit-state model checking.
- It is CI evidence when the workflow runs successfully.
- It is not a universal proof, cryptographic proof, refinement proof, or
  arbitrary-network liveness proof.

## GitHub Actions: Apalache

Workflow: `.github/workflows/apalache.yml`

The workflow installs Java, downloads Apalache v0.40.7, validates
`formal/apalache/model-targets.json`, and runs symbolic-safe bounded checks:

```text
apalache-mc check --init=Init --next=Next --inv=TypeOK formal/apalache/models/ETSLogSymbolic.tla
apalache-mc check --init=Init --next=Next --inv=AcceptedRequiresQuorum formal/apalache/models/ETSVerifierFederationSymbolic.tla
apalache-mc check --init=Init --next=Next --inv=ReplayRequiresDelivery formal/apalache/models/ETSAsyncTransportSymbolic.tla
apalache-mc check --cinit=Init --next=Next --inv=BoundedProgress formal/apalache/models/ETSLivenessProgressSymbolic.tla
```

Interpretation:

- This is bounded symbolic checking over reduced/symbolic-safe models.
- It is not a complete symbolic verification suite.
- It is not proof of universal liveness.

## GitHub Actions: Lean

Workflow: `.github/workflows/lean-proofs.yml`

The workflow installs Lean via elan and runs:

```text
lean src/ETSProofs/TemporalLiveness.lean
lean src/ETSProofs/Fairness.lean
lean src/ETSProofs/ByzantineTemporal.lean
```

Interpretation:

- These are mechanized theorem checks for bounded ETS proof snippets.
- They support bounded temporal, fairness, timeout, and Byzantine
  classification semantics.
- They do not prove arbitrary Byzantine consensus or universal asynchronous
  liveness.

## Sprint 4 Follow-Up

For committee readiness, capture retained outputs:

1. GitHub Actions run URLs for TLC, Apalache, and Lean.
2. CI summaries and uploaded proof artifacts.
3. Tool versions: TLA+ tools, Apalache, Java, Lean.
4. Exact commit SHA.
5. Any counterexamples or excluded properties.
