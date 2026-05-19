# ETS RC3 Executable Research Plan

The executable research plan evaluates whether ETS can provide reproducible
evidence-hash verification, inclusion proof verification, tree-head comparison,
fork detection, and omission findings against synthetic non-PII datasets.

Experiments:

- Fork simulation: construct same-size divergent trees and detect root mismatch.
- Omission detection: compare expected synthetic event IDs with observed log
  entries.
- Benchmark harness: append synthetic events and generate inclusion proofs,
  writing JSON and Markdown outputs.

All experiments are deterministic and avoid real PII.
