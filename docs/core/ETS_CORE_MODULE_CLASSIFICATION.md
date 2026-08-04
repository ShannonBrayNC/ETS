# ETS Core Module Classification

Status: Sprint C0 review draft

## Classification vocabulary

- **Normative core** — deterministic protocol behavior and supported public API.
- **Reference implementation** — one implementation of a core interface; useful but not normative.
- **Optional extension** — separately versioned capability that consumes core contracts.
- **Product adapter** — Edge, Cloud, hosted, transport, identity, or portal concern.
- **Research** — experimental or publication-oriented work not in the stable API.
- **Compatibility** — historical behavior retained only for explicit verification or migration.

## Current module disposition

| Current area | Classification | Target disposition |
|---|---|---|
| `ets/core/canonical_json.py` | Normative core | Retain; freeze canonicalization profile and rejection rules. |
| `ets/core/models.py` | Normative core / compatibility | Retain EvidenceEvent v1 as an explicitly versioned compatibility contract. |
| `ets/core/merkle.py` | Normative core | Retain; expose named Merkle profiles. |
| `ets/core/proofs.py` | Normative core | Retain pure generation/verification contracts. |
| `ets/core/tree_head.py` | Normative core | Retain payload and verification contracts; signer providers remain outside core. |
| `ets/core/bundle.py` | Normative core | Retain portable bundle contract and pure verification. |
| `ets/verifier` | Normative core interface | Package with core; CLI is a thin adapter over pure verification APIs. |
| `ets/core/log.py` | Reference implementation | Keep in a reference-log extra or implementation namespace. |
| `ets/core/storage.py` | Reference interface | Keep storage protocol outside normative hash semantics. |
| `ets/core/sqlite_store.py` | Reference implementation | Move to optional `storage-sqlite` extra or reference package. |
| `ets/core/artifacts.py` | Optional extension | Retain only generic digest/reference helpers; product registry behavior is separate. |
| `ets/core/artifact_registry.py` | Product/reference adapter | Move outside the minimal core import surface. |
| `ets/core/anchors.py` | Optional extension | Separate anchor profile; core must not require an external anchor. |
| `ets/core/federation.py` | Research/optional extension | Keep outside core v1 stable API until a federation profile is normative. |
| `ets/core/quorum.py` | Research/optional extension | Exclude from trust root and core v1 public API. |
| `ets/core/hash_chain.py` | Optional/legacy extension | Do not conflate with the normative Merkle transparency profile. |
| `ets/reports` | Presentation adapter | Consume verifier results; do not place report formatting in the trust root. |
| `ets/api` | Product adapter | Excluded from `ets-core`; imports core only. |
| `ets/sdk` | Consumer facade | Generated or maintained against the public core API; not normative itself. |
| `ets/evidence_object` | Pending normative core | Becomes core only after C2 schema/hash approval. |
| `formal/` | Verification evidence | Retain as release evidence; models do not define runtime behavior by themselves. |
| `schemas/` | Normative publication | Package approved schemas and preserve stable identifiers. |
| vectors/fixtures | Normative publication | Package approved golden/negative vectors and version them independently. |
| Explorer/portals | Product adapter | Excluded from core. |
| Azure/hosted signing | Product adapter | Signer-provider implementation outside core; canonical signed payload remains core. |

## Public import surface

The initial stable surface should be intentionally small:

- canonicalization and digest helpers;
- version/profile identifiers;
- EvidenceEvent and approved Evidence Object models;
- Merkle root/path helpers;
- inclusion and consistency proof data and verification;
- signed tree-head payload and verification;
- proof-bundle data and verification;
- deterministic result and error types.

Storage classes, FastAPI objects, registry singletons, environment configuration, hosted signers, and report rendering must not be re-exported from the minimal core facade.

## Migration rule

Extraction begins inside the monorepo. A separate repository is not required until package release, CI ownership, dependency boundaries, and consumer migration are demonstrated. Premature repository splitting would increase coordination risk while alpha and Edge baselines are still being reconciled.
