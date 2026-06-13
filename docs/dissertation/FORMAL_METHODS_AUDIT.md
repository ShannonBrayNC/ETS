# Sprint 4 Formal Methods Audit

## Purpose

This Sprint 4 audit converts ETS formal-methods artifacts into
dissertation-safe review language. It distinguishes:

- bounded TLC model checking;
- Apalache symbolic-safe bounded checking;
- Lean mechanized proof snippets;
- traceability documents;
- pending refinement and theorem-proof work;
- explicit non-claims.

The audit is designed for advisor review before any committee-facing formal
methods chapter is finalized.

## Current Formal Asset Summary

| Asset Family | Representative Artifacts | Current Status | Dissertation-Safe Claim |
| --- | --- | --- | --- |
| TLA+ explicit-state models | `formal/tla/*.tla`, `formal/tla/*.cfg`, `.github/workflows/tla.yml` | CI executes bounded TLC checks on push to `main` and pull requests. | ETS includes executable bounded TLA+ models for selected safety and fairness-scoped properties. |
| Apalache symbolic-safe models | `formal/apalache/models/*.tla`, `.github/workflows/apalache.yml` | PR/manual workflow executes symbolic-safe bounded checks and uploads proof artifacts. | ETS has a symbolic-checking workflow for reduced models; it is not a complete symbolic proof suite. |
| Lean mechanized proofs | `formal/lean/src/ETSProofs/*.lean`, `.github/workflows/lean-proofs.yml` | CI executes Lean files on push to `main` and pull requests. | ETS mechanizes bounded temporal, fairness, and Byzantine-classification lemmas. |
| Theorem registry | `docs/dissertation/THEOREM_REGISTRY.md` | Documents invariants, validation coverage, and limitations. | ETS maintains a theorem/invariant registry for claim discipline. |
| Formal proof index | `docs/dissertation/FORMAL_PROOF_INDEX.md` | Separates modeled, validated, symbolic, refinement, and proof categories. | ETS tracks formal proof maturity explicitly. |
| Research theorem appendix | `docs/research/FORMAL_THEOREMS.md` | Maps theorem statements to code, tests, and limitations. | ETS states theorem obligations and non-theorems in restrained terms. |
| Traceability matrix | `docs/research/FORMAL_TRACEABILITY_MATRIX.md` | Maps claims to TLA+, Alloy, code, tests, and status. | ETS has traceability evidence, not a full refinement proof. |

## Formal Claim Boundaries

ETS may claim:

- bounded append-only safety modeling;
- bounded verifier federation and conflict-visibility modeling;
- bounded transport, delay, loss, and replay-order modeling;
- fairness-scoped liveness under explicit assumptions;
- bounded symbolic-safe checks for selected reduced models;
- mechanized Lean lemmas for bounded temporal progress and classification;
- traceability from claims to artifacts.

ETS must not claim:

- universal correctness;
- full implementation-to-model refinement proof;
- cryptographic theorem proof of SHA-256, Ed25519, or Merkle soundness;
- arbitrary-network liveness;
- asynchronous Byzantine consensus;
- stochastic convergence proof;
- complete symbolic verification coverage;
- legal sufficiency.

## Local Verification Note

Local formal-tool execution was not performed in this environment. The local
shell does not currently expose `java`, `tlc2.TLC`, `apalache-mc`, or `lake` on
the shell path. Therefore Sprint 4 does not claim that TLC, Apalache, or Lean
were executed locally during this pass.

The repository does contain GitHub Actions workflows for:

- TLA+ TLC execution: `.github/workflows/tla.yml`;
- Apalache symbolic-safe checking: `.github/workflows/apalache.yml`;
- Lean proof execution: `.github/workflows/lean-proofs.yml`.

The local Sprint 4 verification is therefore document/test verification plus
workflow/path audit, not local formal-model execution.

## Advisor Review Questions

1. Are the current bounded TLC and Lean assets sufficient for a formal-methods
   dissertation contribution when framed conservatively?
2. Should Apalache outputs be required before committee review?
3. Which Lean lemmas are central dissertation evidence rather than appendix
   support?
4. Does the committee expect an implementation refinement proof, or is
   traceability plus executable tests sufficient?
5. Which formal claims need published artifact outputs before defense?
