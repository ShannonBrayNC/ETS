# ETS Apalache Symbolic Verification

## Purpose

This directory contains the symbolic verification scaffold for ETS.

TLC currently provides bounded explicit-state exploration. Apalache adds
SMT-backed symbolic checking for selected TLA+ specifications over supported
TLA+ fragments.

ETS includes an Apalache GitHub Actions workflow for pull requests and manual
dispatches: `.github/workflows/apalache.yml`.

## Scientific Boundary

Apalache integration does not mean ETS is universally proven correct.

It provides another validation mode:

- TLC: bounded explicit-state exploration.
- Apalache: bounded symbolic analysis over supported TLA+ fragments.
- Refinement proof and theorem proving: future work.

The workflow pins Apalache v0.40.7 and executes symbolic-safe reduced models.
Until retained outputs are attached to a specific commit and mapped into the
proof index, ETS should describe Apalache as bounded symbolic-safe validation,
not complete symbolic verification.

## Initial Target Models

The first symbolic targets should be small, safety-oriented models:

1. `formal/tla/ETSLog.tla`
2. `formal/tla/ETSAsyncNetwork.tla`
3. `formal/tla/ETSLiveness.tla`, only for properties that fit the selected
   Apalache fragment.

Liveness-heavy models may require refactoring or separate Apalache-oriented
specifications. Candidate future targets from the sprint roadmap include
`ETSVerifierFederation.tla` and `ETSAsyncTransport.tla` when those files exist.

## Run Locally

Install Apalache using the official release instructions, then run a supported
target such as:

```bash
apalache-mc check formal/tla/ETSLog.tla
```

## Required Future Work

- Add Apalache-compatible type annotations where needed.
- Add CI installation and version pinning.
- Add symbolic checks for safety invariants.
- Add refinement mappings from implementation traces to TLA+ states.
- Publish symbolic validation artifacts.
- Map Apalache results into the proof index and traceability matrix.
- Document properties that remain outside Apalache scope.

## Current Status

This is a symbolic-safe verification workflow for reduced ETS models. It
establishes a repeatable validation path while documenting limitations. It is
not evidence of complete symbolic model checking coverage or implementation
refinement.
