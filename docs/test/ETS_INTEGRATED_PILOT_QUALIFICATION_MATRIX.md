# ETS Integrated Pilot Qualification Matrix

Parent milestone: #317  
SignalForge governance: Lantern-Protocol/SignalForge#60  
Frozen qualification baseline: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Purpose

This matrix defines the first integrated pilot qualification pass for the merged ETS software platform. It converts already-merged Core, Edge, Gateway, connector, enterprise-adapter, extensibility, Console, and Microsoft-boundary work into one reproducible evidence program.

A passing matrix qualifies only the exact frozen software baseline and the rows explicitly marked PASS. It does not establish source truth, complete observation, hardware attestation, legal admissibility, regulatory compliance, high availability, or production GA.

## Status vocabulary

- `NOT_RUN` — required scenario has not executed on the frozen baseline.
- `PASS` — expected result reproduced with retained evidence tied to the frozen SHA.
- `FAIL` — required result did not hold; a defect link is required.
- `EXCLUDED` — capability is intentionally outside this baseline's qualification claim; rationale required.
- `BLOCKED` — scenario cannot execute because a declared prerequisite is unavailable.

Every completed row must record environment/profile, command or automation, expected result, actual result, artifact/run reference, reviewer and execution date.

## IPQ-A — Core / Verifier / Persistence (#318)

| ID | Component | Scenario | Required result | Status | Evidence |
|---|---|---|---|---|---|
| IPQ-A01 | Core canonicalization | Canonicalize deterministic `EvidenceEvent` v1 fixture | Repeated canonical bytes/hash are identical | NOT_RUN | — |
| IPQ-A02 | Append-only log | Append deterministic event | Event is committed once with stable index/hash | NOT_RUN | — |
| IPQ-A03 | Merkle inclusion | Generate and verify inclusion proof | Offline/API verification returns valid | NOT_RUN | — |
| IPQ-A04 | Merkle consistency | Verify consistency between two tree sizes | Valid extension accepted without rewriting earlier history | NOT_RUN | — |
| IPQ-A05 | Proof bundle | Export portable proof bundle | Bundle verifies offline with no hosted dependency | NOT_RUN | — |
| IPQ-A06 | Certificates | Generate JSON, Markdown and HTML certificate outputs | Outputs identify verification scope/nonclaims and are reproducible | NOT_RUN | — |
| IPQ-A07 | Tamper negative | Modify event/proof/root/bundle inputs | Verification fails explicitly with stable diagnostics | NOT_RUN | — |
| IPQ-A08 | SQLite artifact registry | Register artifact, restart API, read/prove/verify | Artifact metadata and verification survive restart | NOT_RUN | — |
| IPQ-A09 | Artifact duplicate | Re-register same artifact after restart | Duplicate behavior is deterministic and safe | NOT_RUN | — |
| IPQ-A10 | Corrupt artifact metadata | Corrupt durable metadata fixture | Read/verification fails closed | NOT_RUN | — |
| IPQ-A11 | Raw-content boundary | Scan durable metadata/export surfaces for raw marker | Raw artifact bytes/marker absent under default profile | NOT_RUN | — |

## IPQ-B — ETS Edge Virtual (#319)

| ID | Component | Scenario | Required result | Status | Evidence |
|---|---|---|---|---|---|
| IPQ-B01 | Edge boot | Clean first boot | Durable SQLite state, software Ed25519 identity and local API key created | NOT_RUN | — |
| IPQ-B02 | Device continuity | Restart Edge Virtual | Device ID/public identity/API-key behavior remain stable | NOT_RUN | — |
| IPQ-B03 | Webhook capture | Send authenticated JSON webhook | Exact received bytes are SHA-256 committed; proof verifies | NOT_RUN | — |
| IPQ-B04 | Webhook mutation | Change one payload byte | Content digest changes and prior proof does not verify new bytes | NOT_RUN | — |
| IPQ-B05 | UDP syslog | Send RFC 5424 datagram | Exact datagram digest and proof verify | NOT_RUN | — |
| IPQ-B06 | UDP syslog negative | Send malformed RFC 5424 input | Diagnostic rejection; listener remains available | NOT_RUN | — |
| IPQ-B07 | Offline operation | Stop upstream and capture new evidence | Local commit/proof continues; queue becomes retryable/offline | NOT_RUN | — |
| IPQ-B08 | Restart recovery | Restart Edge while work is queued | Pending/retryable work recovers without evidence loss | NOT_RUN | — |
| IPQ-B09 | Reconnect sync | Restore upstream and synchronize | Qualified records synchronize once | NOT_RUN | — |
| IPQ-B10 | Idempotent replay | Run synchronization again | No duplicate upstream record is created | NOT_RUN | — |
| IPQ-B11 | Queue pressure | Fill queue to configured bound | Pre-capture backpressure prevents silent overrun/loss | NOT_RUN | — |
| IPQ-B12 | Raw-content boundary | Scan event/sync/upstream stores for webhook/syslog marker | Marker absent under default profile | NOT_RUN | — |

## IPQ-C — Gateway Native Ingress (#320)

| ID | Component | Scenario | Required result | Status | Evidence |
|---|---|---|---|---|---|
| IPQ-C01 | HTTPS ingress | Authorized webhook through deployed TLS host | Server scope is authoritative; local commit + durable sync state returned truthfully | NOT_RUN | — |
| IPQ-C02 | HTTPS authorization | Unauthorized source / tenant-workspace override attempt | Fails before authoritative commit | NOT_RUN | — |
| IPQ-C03 | HTTPS bounds | Exact and +1 request/header/concurrency/duration limits | Exact bound accepted where valid; +1 fails closed | NOT_RUN | — |
| IPQ-C04 | HTTPS replay | Identical retry and conflicting retry | Identical retry reconciles; conflicting immutable reuse fails | NOT_RUN | — |
| IPQ-C05 | HTTPS partial failure | Backpressure and append-before-enqueue failure | No silent loss; retry repairs allowed partial state idempotently | NOT_RUN | — |
| IPQ-C06 | Syslog TLS | mTLS URI-SAN authorized RFC 5425 message | Peer identity remains separate from message HOSTNAME; event commits | NOT_RUN | — |
| IPQ-C07 | Syslog framing | Fragmented and multiple octet-counted frames | Boundaries preserved; each complete frame processed once | NOT_RUN | — |
| IPQ-C08 | Syslog negative | Malformed/oversize/incomplete frame | No partial evidence committed | NOT_RUN | — |
| IPQ-C09 | Syslog shutdown | Drain admitted complete work while refusing new connections | Drain is bounded and no fabricated evidence appears | NOT_RUN | — |
| IPQ-C10 | File streamed hash | Empty/small/exact-bound files across chunk sizes | Digest independent of read segmentation | NOT_RUN | — |
| IPQ-C11 | File safety | Traversal/absolute/symlink/reparse escape | Fails closed before commitment | NOT_RUN | — |
| IPQ-C12 | File stability | Replace/truncate/change file during read | Instability detected/classified; unstable object not silently committed | NOT_RUN | — |
| IPQ-C13 | File commitment | Stable file through shared Gateway path | Digest+bounded metadata commit; raw object not retained by default | NOT_RUN | — |
| IPQ-C14 | OTLP HTTP | Logs/metrics/traces over protobuf HTTP | Accepted observations traverse shared commit path | NOT_RUN | — |
| IPQ-C15 | OTLP gRPC | Logs/metrics/traces over mTLS gRPC | Authorized observations traverse same shared commit path | NOT_RUN | — |
| IPQ-C16 | OTLP bounds | Malformed/oversize/gzip/decompression/partial-success cases | Bounded fail-closed/partial-success behavior is explicit | NOT_RUN | — |
| IPQ-C17 | OTLP retry | Retry/conflict/backpressure/partial-commit cases | Deterministic retry behavior; no silent checkpoint/event loss | NOT_RUN | — |
| IPQ-C18 | OTLP equivalence | Semantically equivalent HTTP and gRPC observation | Expected normalized representation/content hash equivalence holds | NOT_RUN | — |

## IPQ-D — Connector Platform / Dark Pro Console (#321)

| ID | Component | Scenario | Required result | Status | Evidence |
|---|---|---|---|---|---|
| IPQ-D01 | G2A schemas | Validate native and enterprise definitions/instances | One strict versioned contract validates both families | NOT_RUN | — |
| IPQ-D02 | Compatibility | Unsupported SDK/Gateway/capture/adapter combination | Activation/registration fails closed with actionable state | NOT_RUN | — |
| IPQ-D03 | Credential broker | Create/resolve/rotate/revoke credential reference | Reusable bytes are never returned by management surfaces | NOT_RUN | — |
| IPQ-D04 | Credential failure | Missing/expired/revoked/unavailable reference | Explicit health failure; source checkpoint does not advance | NOT_RUN | — |
| IPQ-D05 | G2C CRUD | Create/read/update/enable/disable connector instance | Versioned management operations succeed under server authorization | NOT_RUN | — |
| IPQ-D06 | G2C restart | Restart with runtime state | Checkpoint/retry/health/gap state survives separately from ETS Merkle state | NOT_RUN | — |
| IPQ-D07 | G2C conflicts | Stale revision/checkpoint compare-and-set | Conflict is deterministic and does not overwrite newer state | NOT_RUN | — |
| IPQ-D08 | Native catalog | Inspect Webhook/Syslog/File/OTLP definitions | All four are manageable and route to existing G1 ownership | NOT_RUN | — |
| IPQ-D09 | Console auth | Load Dark Pro production entrypoint | Identity/scope/capabilities come from server auth context | NOT_RUN | — |
| IPQ-D10 | Console workflow | Connection -> Scope -> Policy -> Collection -> Test -> Activate | Operator completes bounded configuration without raw file editing | NOT_RUN | — |
| IPQ-D11 | Console preview | Preview source -> policy -> normalization -> candidate | Preview is pre-commit and explicitly not verification | NOT_RUN | — |
| IPQ-D12 | Console health semantics | Exercise healthy/degraded/gap/verification states | Source health/gap remains distinct from ETS cryptographic verification | NOT_RUN | — |
| IPQ-D13 | Console UX smoke | Dark default, light mode, keyboard focus, non-color statuses | Merged connector path meets smoke-level accessibility expectations | NOT_RUN | — |

## IPQ-E — Enterprise / Generic REST (#322)

| ID | Component | Scenario | Required result | Status | Evidence |
|---|---|---|---|---|---|
| IPQ-E01 | GitHub Audit | Controlled org audit collection | Bounded page collects/minimizes/commits and releases checkpoint after durable sync enqueue | NOT_RUN | — |
| IPQ-E02 | GitHub restart/gap | Restart/resume + over-retention checkpoint | Resume deterministic; over-age state becomes explicit gap | NOT_RUN | — |
| IPQ-E03 | AWS CloudTrail | Controlled Event History collection | Bounded collection/minimization/shared Gateway commit succeeds | NOT_RUN | — |
| IPQ-E04 | AWS retry/gap | Throttle/retry/retention/backpressure/partial failure | State remains explicit; checkpoint advances only after qualified page | NOT_RUN | — |
| IPQ-E05 | Okta System Log | Controlled System Log collection | Origin/path-safe next-link collection/minimization/shared state succeeds | NOT_RUN | — |
| IPQ-E06 | Okta retry/gap | Auth/throttle/retention/restart cases | Explicit failure/gap behavior; no silent checkpoint advancement | NOT_RUN | — |
| IPQ-E07 | Generic REST transport | Deterministic HTTPS fixture + trusted host policy | Redirect/destination/timeout/size policy fails closed as specified | NOT_RUN | — |
| IPQ-E08 | Generic REST extraction | Declarative record ID/time/field mapping | Only allow-listed evidence fields become candidates | NOT_RUN | — |
| IPQ-E09 | Generic REST resume | Cursor and overlapping time-window modes | Restart behavior deterministic; continuity uncertainty remains explicit | NOT_RUN | — |
| IPQ-E10 | Generic REST commit | End-to-end collect -> normalize -> Gateway commit -> checkpoint release | Checkpoint releases only after local append + durable sync enqueue | NOT_RUN | — |
| IPQ-E11 | Generic REST failure | Backpressure and append-before-enqueue partial failure | Source progress withheld; retry recovers idempotently | NOT_RUN | — |
| IPQ-E12 | Enterprise scope | Attempt tenant/workspace injection from source payload/settings | Server-authorized scope remains authoritative | NOT_RUN | — |
| IPQ-E13 | Enterprise secret boundary | Scan candidates/evidence/sync/diagnostics for reusable credential markers | Reusable material absent | NOT_RUN | — |

## IPQ-F — Third-party Packaging / Microsoft Boundary (#323)

| ID | Component | Scenario | Required result | Status | Evidence |
|---|---|---|---|---|---|
| IPQ-F01 | Connector package | Validate sample `ets.connector.package.v1` | Manifest/file inventory/digests/compatibility validate without executing package code | NOT_RUN | — |
| IPQ-F02 | Package tamper | One-byte package content mutation | Integrity verification fails | NOT_RUN | — |
| IPQ-F03 | Package inventory | Add undeclared/missing/traversal/symlink/special file | Verification fails closed | NOT_RUN | — |
| IPQ-F04 | Package qualification | Compare built-in/qualified-third-party/community states | Publisher and qualification state remain explicit and separate from evidence verification | NOT_RUN | — |
| IPQ-F05 | Microsoft cloud profile | Synthetic Global/US Gov/China profile validation | Only server-approved cloud roots/identities accepted | NOT_RUN | — |
| IPQ-F06 | Microsoft readiness | Consent and credential-readiness state matrix | Pending/partial/revoked/failure states remain explicit and sanitized | NOT_RUN | — |
| IPQ-F07 | Graph endpoint validation | Validation-token flow | Exact bounded validation behavior reproduced | NOT_RUN | — |
| IPQ-F08 | Graph notifications | Valid/invalid clientState, foreign tenant, unknown subscription, oversize body | Invalid cases fail closed; valid source-side receipt is bounded | NOT_RUN | — |
| IPQ-F09 | Graph lifecycle | Create/renew/reauthorize/delete + missed/removed state | Operational state/gap behavior remains explicit | NOT_RUN | — |
| IPQ-F10 | Graph commitment claim boundary | Inspect frozen baseline Graph resource receipt status | Must not overclaim end-to-end commitment while #305 remains open | NOT_RUN | — |
| IPQ-F11 | Entra delta links | Initial/multipage nextLink/deltaLink fixtures | Same-cloud/same-collection state accepted and preserved exactly | NOT_RUN | — |
| IPQ-F12 | Entra delta negative | Cross-cloud/cross-collection cursor | Rejected before credential-bearing reuse | NOT_RUN | — |
| IPQ-F13 | Entra lifecycle | Add/update/remove/restore/repeated entity fixtures | Occurrences preserved/minimized without global-order or uniqueness claims | NOT_RUN | — |

## IPQ-G — Security / Evidence Pack / Go-No-Go (#324)

| ID | Gate | Required result | Status | Evidence |
|---|---|---|---|---|
| IPQ-G01 | Exact-head CI | Required Python/release/frontend checks green for the qualified candidate | NOT_RUN | — |
| IPQ-G02 | Security Audit | Dependency audit, npm audit where applicable, gitleaks and security workflow evidence acceptable | NOT_RUN | — |
| IPQ-G03 | CodeQL | Security-extended CodeQL result or explicitly recorded unavailable state | NOT_RUN | — |
| IPQ-G04 | Formal Specs | Required formal-spec workflow green | NOT_RUN | — |
| IPQ-G05 | Apalache | Required symbolic-verification workflow green | NOT_RUN | — |
| IPQ-G06 | Lean | Required mechanized-proof workflow green | NOT_RUN | — |
| IPQ-G07 | Benchmarks | Required benchmark workflow completes with no qualification-blocking regression | NOT_RUN | — |
| IPQ-G08 | Evidence completeness | Every PASS row has exact SHA/environment/run/artifact/reviewer/date | NOT_RUN | — |
| IPQ-G09 | Defect reconciliation | Every FAIL/BLOCKED/EXCLUDED row has defect/rationale and claim treatment | NOT_RUN | — |
| IPQ-G10 | Secret/raw-content review | Retained qualification artifacts contain no reusable credentials or prohibited raw markers | NOT_RUN | — |
| IPQ-G11 | Independent review | Independent reviewer approves bounded qualification report | NOT_RUN | — |
| IPQ-G12 | Go/no-go | Final report states qualified/conditional/excluded/open capabilities and decision | NOT_RUN | — |

## Explicit baseline exclusions

The following do not become qualified merely because related code exists elsewhere:

- Microsoft Graph end-to-end commitment beyond the behavior present in this frozen baseline while #305 remains open.
- Kubernetes enterprise adapter until #291 closes and the implementation is merged into a specifically qualified baseline.
- Full production Console/P1 acceptance while #209 and #255 remain open.
- TPM/HSM-backed Edge attestation or non-exportable hardware custody.
- Production HA, universal source completeness, source truth, compliance certification, legal admissibility or general availability.

## Execution strategy

IPQ-A through IPQ-F may execute in parallel because each is pinned to the same immutable baseline. IPQ-G is the integration gate and must not declare a go decision until A-F evidence is reconciled.

If a defect requires a code change, open a bounded issue and fix it on a separate branch. A repaired build becomes a **new qualification SHA**; do not silently replace the SHA recorded above. The final report must state exactly which SHA actually earned the qualification decision.
