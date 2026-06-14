# ETS Reproducibility Matrix

ETS is the **Evidence Transparency System**. This matrix maps every exported or verifier-facing artifact to the inputs needed for deterministic verification, expected output, verifier command, failure condition, and claim boundary.

## Reproducibility Rule

A verifier should be able to reproduce the same verification decision from exported proof material without querying the original ETS API, except where the row explicitly depends on local service state or environment-specific tooling.

## Artifact Matrix

| Artifact | Required Inputs | Deterministic Expected Output | Verifier Command | Failure Condition | Claim Boundary |
|---|---|---|---|---|---|
| EvidenceEvent JSON | EvidenceEvent v1 JSON using supported canonical JSON values | Stable SHA-256 event hash | `.\.venv\Scripts\ets-verify.exe event-hash .\path\to\event.json` | Invalid JSON, unsupported value, schema mismatch, or hash mismatch when `--expected` is supplied | Reproduces the submitted event hash only; does not prove raw evidence truth or completeness. |
| EvidenceEvent JSON with expected hash | EvidenceEvent JSON and expected event hash | `{"valid": true, ...}` when recomputed hash matches | `.\.venv\Scripts\ets-verify.exe event-hash .\path\to\event.json --expected <event-hash>` | Recomputed hash differs from expected hash | Proves hash agreement for the submitted event payload only. |
| InclusionProof JSON | InclusionProof JSON containing leaf hash, audit path, root hash, tree size, and leaf index | Valid/invalid inclusion result | `.\.venv\Scripts\ets-verify.exe inclusion-proof .\path\to\proof.json` | Tampered leaf hash, sibling hash, path direction, tree size, or root hash | Proves inclusion in the stated tree head only; does not prove the raw evidence is authentic. |
| Sprint 3 inclusion proof alias | Same as InclusionProof JSON | Same result as `inclusion-proof` | `.\.venv\Scripts\ets-verify.exe verify-proof .\path\to\proof.json` | Same as inclusion proof | Compatibility alias only; no broader claim. |
| ConsistencyProof JSON | Previous tree size/root, latest tree size/root, and supported consistency proof payload | Valid/invalid append-only extension result | `.\.venv\Scripts\ets-verify.exe consistency-proof .\path\to\consistency-proof.json` | Previous root cannot be recomputed, latest root cannot be recomputed, tree sizes regress, or supplied leaves do not support extension | RC validation of supported consistency profile; not a compact RFC 6962 proof unless explicitly implemented and documented. |
| EvidenceProofBundle JSON | EvidenceEvent, event hash, leaf hash, tree head, inclusion proof, and verification metadata | Valid/invalid bundle result | `.\.venv\Scripts\ets-verify.exe bundle .\path\to\bundle.json` | Event hash mismatch, malformed proof, root mismatch, schema mismatch, or invalid bundle fields | Reproduces protocol verification from bundle material; does not prove submitter authority or legal sufficiency. |
| Verification certificate JSON | EvidenceProofBundle JSON | JSON certificate with protocol fields, warnings, and claim-safe verification sections | `.\.venv\Scripts\ets-verify.exe certificate .\path\to\bundle.json --format json --out certificate.json` | Bundle cannot be parsed or validated | Certificate reports ETS verification result; it is not legal advice, official status, or a real-world truth claim. |
| Verification certificate Markdown | EvidenceProofBundle JSON | Markdown certificate with `What This Verifies` and `What This Does Not Verify` sections | `.\.venv\Scripts\ets-verify.exe certificate .\path\to\bundle.json --format markdown --out certificate.md` | Bundle cannot be parsed or validated | Human-readable claim-safe report only. |
| Verification certificate HTML | EvidenceProofBundle JSON | HTML certificate with `What This Verifies` and `What This Does Not Verify` sections | `.\.venv\Scripts\ets-verify.exe certificate .\path\to\bundle.json --format html --out certificate.html` | Bundle cannot be parsed or validated | Human-readable claim-safe report only. |
| Previous/latest tree heads | Previously trusted tree head JSON and latest tree head JSON | Valid/invalid tree-head transition result | `.\.venv\Scripts\ets-verify.exe tree-head .\path\to\previous-head.json .\path\to\latest-head.json` | Log ID changes, tree size regresses, timestamp regresses, equal-size root changes, or suspicious unchanged root at larger size | Detects local rollback/equivocation signals; does not replace external monitoring or anchoring. |
| Election proof bundle | Fictional ElectionInclusionProofBundle JSON | Valid/invalid election proof result | `.\.venv\Scripts\ets-verify.exe election-proof .\path\to\election-proof.json` | Packet/proof mismatch, schema mismatch, root mismatch, or tampered proof material | Demonstrates fictional evidence/audit verification only; not voting software, tabulation software, election correctness, or the vote of record. |
| Election RC root manifest | `artifacts/election-rc-demo/root-manifest.json` from RC walkthrough | Stable manifest fields for generated demo run | Verify through walkthrough and proof bundle commands | Missing fields, changed root, or inconsistent artifact references | Demo manifest for fictional packets only; does not prove all expected packets were submitted. |
| Election RC audit log | `artifacts/election-rc-demo/audit-log.json` from RC walkthrough | Deterministic audit event list for the sample demo | Inspect with JSON tooling and verify exported proof bundle | Missing expected sample packet IDs or inconsistent event ordering | Reproduces demo sequence only; does not prove real-world election activity. |
| Election RC tamper result | `artifacts/election-rc-demo/tamper-result.json` from RC walkthrough | Tampered proof rejection | Run `.\scripts\run-election-rc-demo.ps1` and inspect tamper result | Tampered artifact verifies as valid | Demonstrates tamper rejection for sample artifact only. |
| Benchmark JSON | `artifacts/benchmarks/benchmark-results.json` after benchmark run | Stable output shape and event counts; timings may vary | `.\.venv\Scripts\python.exe -m ets.benchmarks.run_benchmarks` | Missing output, invalid JSON, or unexpected shape | Reproduces reference benchmark structure; does not prove production throughput. |
| Benchmark Markdown | `artifacts/benchmarks/benchmark-results.md` after benchmark run | Human-readable benchmark report | `.\.venv\Scripts\python.exe -m ets.benchmarks.run_benchmarks` | Missing output or inconsistent benchmark summary | Human-readable benchmark artifact only; timings are machine-dependent. |
| Fork simulation output | Fork simulation module output | Conflicting roots are reported for deterministic scenario | `.\.venv\Scripts\python.exe -m ets.experiments.run_fork_simulation` | No conflict reported when fixed scenario expects divergence | Demonstrates disagreement detection; does not identify which node is honest. |
| Omission detection output | Omission experiment module output | Missing expected IDs are reported only when absent from observed IDs | `.\.venv\Scripts\python.exe -m ets.experiments.run_omission_detection` | Missing IDs reported without expectation or expected absences not reported | Omission suspicion requires external expected-event policy; does not prove real-world completeness. |
| TLA+ model files | `formal/tla/*.tla` and `.cfg` files | Model-checker result when TLC is installed and bounds are documented | Tooling-dependent; document TLC command, version, and bounds when run | Syntax errors, invariant failures, or undocumented bounds | Bounded formal model evidence only; not an implementation refinement proof unless separately completed. |
| Alloy model file | `formal/alloy/ETSCausalModel.als` | Alloy Analyzer check result when installed and bounds are documented | Tooling-dependent; document Analyzer command/version/bounds when run | Assertion counterexample or undocumented bounds | Structural/causal model evidence only; not cryptographic proof. |

## Required Reproduction Metadata

Every exported verification bundle or certificate should preserve, directly or by reference:

- ETS protocol version;
- EvidenceEvent schema version;
- canonicalization profile;
- hash algorithm;
- event hash;
- leaf hash;
- event index or leaf index;
- tree size;
- tree root;
- log ID;
- proof schema version;
- proof generation time, if present;
- signing algorithm and key ID, if present;
- verifier version;
- tenant/workspace scope metadata when exportable;
- redaction profile when applicable;
- warnings and claim boundaries.

## Claim Boundary

Reproducibility means the verification decision can be independently reproduced from the exported material. It does not mean the underlying real-world evidence is true, complete, legally sufficient, official, or independently observed.