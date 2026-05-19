# Evidence Transparency System: IEEE Draft Notes

## Abstract

ETS is a transparency-log design for evidence metadata and content hashes. It
combines deterministic canonicalization, append-only logs, Merkle proofs,
tree-head signatures, and offline verification.

## RC5 Contributions

- Executable protocol lab.
- Synthetic non-PII experiment generation.
- Fork and omission experiments.
- Benchmark JSON and Markdown output.
- Local Docker federation topology.

## Limitations

ETS does not prove real-world completeness. Omission detection depends on an
external expected event set. RC5 consistency proofs are linear rather than
compact.
