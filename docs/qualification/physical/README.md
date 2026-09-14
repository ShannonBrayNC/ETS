# Physical qualification execution packages

This directory contains operator-facing preparation material for named physical HQP executions.

## Current package

- `EDGE_RT0_PHYSICAL_EXECUTION_RUNBOOK_V1.md` — first physical ETS Edge execution runbook for #796.
- `edge-rt0-dut-readiness.template.json` — deliberately unpopulated preflight manifest for binding the first exact Edge DUT and lab environment.

## Boundary

These files are preparation artifacts. They are **not** qualification evidence and do not change the qualification state of any hardware.

A physical claim begins only with a named DUT, immutable build/configuration, retained HQP-1 execution package, resulting-state evidence, and an eligible HQP-2 independent-verifier result. Publication then follows the HQP-5 qualification-index governance process.

Never commit a populated manifest containing reusable credentials, bootstrap secrets, private signing keys, or other secret material.
