# ETS Apalache Symbolic Verification

## Purpose

This directory contains the symbolic verification scaffold for ETS.

TLC currently provides bounded explicit-state exploration. Apalache adds SMT-backed symbolic checking for selected TLA+ specifications.

## Scientific Boundary

Apalache integration does not mean ETS is universally proven correct.

It provides another validation mode:

- TLC: bounded explicit-state exploration
- Apalache: bounded symbolic analysis over supported TLA+ fragments
- Theorem proving: future work

## Initial Target Models

The first symbolic targets should be the smallest safety-oriented models:

1. `ETSLog.tla`
2. `ETSVerifierFederation.tla`
3. `ETSAsyncTransport.tla`

Liveness-heavy models may require refactoring or separate Apalache-oriented specifications.

## Run Locally

Install Apalache using the official release instructions, then run:

```bash
apalache-mc check --config formal/apalache/apalache.json formal/tla/ETSLog.tla
```

## Current Status

This is Sprint 12 scaffolding. It establishes a repeatable symbolic-verification path while documenting limitations.

Future work should:

- refactor unsupported TLA+ constructs;
- add symbolic-safe model variants;
- publish symbolic validation artifacts;
- map Apalache results into the proof index.
