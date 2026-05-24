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
- temporal event guarantees
