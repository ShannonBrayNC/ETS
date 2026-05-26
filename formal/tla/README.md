# ETS TLA+ Model

This directory contains executable TLA+ specifications for ETS.

## Goals

The initial model verifies:

- append-only semantics
- sequence monotonicity
- root disagreement detection
- non-mutation properties

## Files

- `ETSLog.tla` — protocol model
- `ETSLog.cfg` — TLC configuration
- `ETSAsyncNetwork.tla` — bounded asynchronous queue and loss model
- `ETSAsyncNetwork.cfg` — TLC configuration for the network model
- `ETSLiveness.tla` — fairness-scoped replay, witness, and recovery model
- `ETSLiveness.cfg` — TLC configuration for liveness properties

## Running TLC

1. Install the TLA+ Toolbox.
2. Open `ETSLog.tla`.
3. Load `ETSLog.cfg`.
4. Execute model checking.

## Current RC4 Scope

The RC4 model intentionally focuses on:

- append-only invariants
- federation fork signaling
- state consistency

Future versions should add:

- Merkle proof semantics
- omission suspicion states
- verifier federation quorum logic
- refinement proofs from implementation traces

## Async Network Scope

`ETSAsyncNetwork.tla` models message queues, delivery, and packet loss as
nondeterministic transitions. It is useful for checking bounded queue
invariants, but it is not a probabilistic model and does not prove BFT
convergence, partial-synchrony liveness, or Internet-scale adversarial
correctness.

## Liveness And Fairness Scope

`ETSLiveness.tla` states replay eventuality, partition healing, witness
propagation completion, stale-state recovery, and convergence after adversarial
pressure under explicit weak-fairness assumptions. These properties are
conditional: if partition healing or adversarial-pressure removal is not a fair
enabled behavior, ETS does not claim eventual convergence.
