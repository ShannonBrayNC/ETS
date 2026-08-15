# IPQ-F Frozen Package and Microsoft Result

Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`  
Qualification sprint: #347  
Harness PR: #348  
Initial evidence run: `31859009394`

## Result summary

The detached IPQ-F harness executed the third-party package verifier and the Microsoft/Entra source-boundary suites against the immutable frozen SUT. No frozen product file was patched or rewritten.

| Area | Result | Reproduced evidence |
|---|---|---|
| Strict `ets.connector.package.v1` package model/integrity | **PASS** | Frozen package suite passed 10/10: strict manifest/schema, declared inventory, per-file/aggregate digests, tamper, undeclared-file, symlink, traversal/unknown-field, compatibility and deterministic digest behavior. |
| Missing declared package file | **PASS** | Detached probe removed a declared file and the frozen verifier failed closed on exact inventory mismatch. |
| Declared-path special/FIFO file | **PASS** | Detached probe replaced a declared module with a FIFO and the frozen verifier rejected special files without reading/executing the path. |
| Publisher / qualification distinction | **PASS** | Detached validation accepted Lantern built-in qualified, Lantern-qualified third-party qualified, and community unqualified states; community/unqualified self-asserting `qualified` was rejected. |
| Package verification without importing/executing package code | **PASS** | Frozen verifier/test boundary statically parses and hashes package content; package conformance is kept distinct from ETS evidence verification. |
| Microsoft cloud / consent / credential readiness | **PASS** | 15/15 frozen common-profile tests passed: qualified global/national-cloud roots, arbitrary endpoint-override rejection, explicit consent states, credential metadata states, and sanitized provider failures. |
| Graph validation / bounded notification parsing | **PASS (source boundary)** | Frozen Graph source/subscription group passed 22/22: validation token handling, bounded resource/lifecycle parsing, clientState/tenant/subscription rejection, deterministic/minimized resource observations, malformed/oversize bounds and lifecycle possible-gap state. |
| Synthetic Graph subscription lifecycle | **PASS (source boundary)** | Create/renew/reauthorize/delete, qualified cloud roots, auth/authorization/throttle classification, response binding checks and token zeroization are reproduced under deterministic clients. |
| End-to-end Graph Gateway commitment | **EXCLUDED / NOT CLAIMED** | Frozen qualification intentionally stops at the merged source-side boundary. #305 remains open and this result does not imply accepted Graph notifications were committed through the complete Gateway evidence path. |
| Entra users/groups delta / cursor boundary | **PASS** | 29/29 frozen Entra tests passed across connector/delta/HTTP/resync suites: initial/multipage users/groups observations, exact nextLink/deltaLink handling, same-cloud/same-collection validation, changed/deleted removal markers, repeated entity identity, minimized metadata, bounded HTTP behavior and resync/gap state present in the frozen baseline. |
| Live Microsoft production connectivity / real tenant consent | **EXCLUDED** | Deterministic synthetic clients, tenant IDs, application IDs and credential providers are used. No live Microsoft tenant/service availability or production-consent readiness is claimed. |
| Source truth / completeness | **EXCLUDED** | Accepted source observations and delta/lifecycle state are not proof that Microsoft or another upstream source is truthful or complete. |

## Retained evidence

### Third-party package

- job: `94948840482`
- frozen tests: `10 passed in 0.19s`
- detached probes: `missing_declared_file=PASS`, `declared_path_fifo=PASS`, `publisher_classes=PASS`, `community_cannot_claim_qualified=PASS`
- artifact: `ipq-f-package-frozen`
- artifact ID: `9239924438`
- artifact ZIP SHA-256: `0b791fc6062755b638ef84971603411c7c9dde160e19e5b9e1d79c4d026fb77a`

### Microsoft common readiness

- job: `94948840508`
- tests: `15 passed in 0.25s`
- artifact: `ipq-f-microsoft-common-frozen`
- artifact ID: `9239924469`
- artifact ZIP SHA-256: `c9b7e3afc8cff54c39d5ac1a7adfce737041b7b29635ac1f497aa3eedf59419d`

### Graph notification/subscription source boundary

- job: `94948840465`
- tests: `22 passed in 0.55s`
- artifact: `ipq-f-graph-source-frozen`
- artifact ID: `9239924025`
- artifact ZIP SHA-256: `5c7f24be78a47619ec56db52e7c9a1897ce42aec873a12d1ee6d7149ab479c41`

### Entra delta/resync boundary

- job: `94948840427`
- tests: `29 passed in 0.68s`
- artifact: `ipq-f-entra-delta-frozen`
- artifact ID: `9239924611`
- artifact ZIP SHA-256: `1b9ba085eeac5ec55ea2f169d70a07a05e55774c85b6868ebdc734f13fab86a9`

## Interpretation

The frozen baseline satisfies the mandatory IPQ-F package-integrity/provenance and merged Microsoft/Entra **source-boundary** scenarios under controlled fixtures. The Graph result is intentionally narrower than an end-to-end connector qualification: it proves accepted source-side notification/subscription behavior at the level merged into `75927c5...`, not complete Gateway commitment.

Package verification establishes integrity, compatibility and provenance-policy inputs for package activation; it does not convert package code or package-emitted claims into verified ETS evidence.

## Final exact-head qualification

Adding this result record moves the harness head. Earlier repository CI/security/formal results therefore become stale for merge purposes. The final #348 head must rerun the detached IPQ-F collector plus CI, Security Audit, CodeQL, Formal Specs, Benchmarks, Apalache and Lean, then receive fresh independent review before merge.

## Nonclaims

This result does not close #305 and does not establish live Microsoft production connectivity, production credentials, source truth/completeness, legal admissibility, regulatory compliance, high availability, production GA, hardware attestation, or end-to-end evidence verification for an accepted Graph notification or third-party package.
