# Physical qualification execution packages

This directory contains operator-facing preparation material for named physical HQP executions and bounded pre-hardware simulation.

## Current Edge package

- `EDGE_RT0_PHYSICAL_EXECUTION_RUNBOOK_V1.md` — first physical ETS Edge execution runbook for #796.
- `edge-rt0-dut-readiness.template.json` — deliberately unpopulated preflight manifest for binding the first exact Edge DUT and lab environment.
- `EDGEW_RT0_DUT_SPEC_V1.md` — procurement/build specification for the preferred first physical Edge DUT while preserving `EDGE-RT0` as the qualification target class.
- `EDGEW_RT0_SHOPPING_LIST_V1.md` — current reference shopping/procurement list and reuse guidance.
- `EDGEW_RT0_VIRTUAL_TWIN_V1.md` — `EDGEW-RT0-VT0` pre-hardware KVM/QEMU virtual-twin plan with explicit simulated-vs-physical claim boundaries.
- `LEGACY_ROUTER_LAB_INVENTORY_TEMPLATE.md` — characterization worksheet for existing Linksys/D-Link equipment used as hybrid network-fault infrastructure and possible bounded legacy-source candidates.

## Boundary

These files are preparation artifacts. They are **not** qualification evidence and do not change the qualification state of any hardware.

A virtual-twin run remains `simulated` even if every executable test passes. It cannot establish physical power-loss durability, storage endurance, thermal behavior, discrete TPM custody, physical Secure Boot posture, or physical network reliability.

A physical claim begins only with a named DUT, immutable build/configuration, retained HQP-1 execution package, resulting-state evidence, and an eligible HQP-2 independent-verifier result. Publication then follows the HQP-5 qualification-index governance process.

Never commit a populated manifest containing reusable credentials, bootstrap secrets, private signing keys, or other secret material.
