# ETS Python Testing Lab

The ETS Python Testing Lab is a local FastAPI UI for demonstrating the Evidence Transparency System alpha pipeline. It is designed for protocol walkthroughs, investor/customer demos, engineering tests, and public-safe education.

## Purpose

The lab breaks ETS into the same functional stages shown in the filing diagrams:

- source systems and event intake;
- EvidenceEvent validation;
- canonicalization and SHA-256 hashing;
- append-only log indexing;
- Merkle inclusion proof generation;
- tree-head progression and consistency checks;
- verification certificate generation;
- policy-gated routing;
- audit replay and claim boundaries.

The filing drawing package frames ETS as source systems feeding an ETS core made of API, canonicalization, EvidenceEvent validation, append-only log, Merkle tree, proof generator, verifier, certificate generator, policy gate, audit replay, and Explorer UI, with outputs such as proof bundles, verification certificates, human review, automation approval, quarantine/reject, and archive/restrict-release actions.

## Run the lab

Install the project with development dependencies first:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Start the lab UI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.lab.app:app --reload --port 8100
```

Then open:

```text
http://localhost:8100/lab
```

## Lab endpoints

The UI is backed by deterministic in-process Python endpoints:

- `GET /lab` - browser UI.
- `GET /lab/api/meta` - version and claim-boundary text.
- `GET /lab/api/components` - component cards mapped to figures and capabilities.
- `GET /lab/api/scenarios` - runnable scenario metadata.
- `POST /lab/api/run/{scenario_id}` - run a named scenario.
- `POST /lab/api/tree-head-progression` - run a compact consistency proof demonstration.

## Included scenarios

| Scenario | Demonstrates |
|---|---|
| `full-pipeline` | receive, validate, canonicalize, hash, append, prove, verify, certify, and route |
| `canonical-hash` | deterministic canonical JSON hashing |
| `inclusion-proof` | Merkle inclusion proof generation and verification |
| `tamper-detection` | proof mutation and root mismatch rejection |
| `policy-routing` | routing evidence states to automation, human review, quarantine, reject, archive, or restricted release |
| `civic-boundary` | civic/election-adjacent non-claim labeling |

## Public-safe demo boundary

The lab uses fictional, local-only, non-PII sample events. It does not use production evidence, official election data, customer data, private keys, USPTO filing records, claim charts, prior-art matrices, or attorney-review material.

ETS verifies submitted-event metadata, hashes, inclusion proofs, tree-head material, verification certificates, and policy-routing records. The lab does not prove real-world truth, legal sufficiency, election correctness, raw evidence authenticity, or completeness without an external expected-event policy and observation process.
