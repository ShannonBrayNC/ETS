# ETS Integrated Pilot Qualification Report

Qualification milestone: #317  
Final evidence-pack gate: #324 / #365  
Frozen software baseline: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Executive summary

ETS has reproduced substantial controlled pilot behavior on the immutable frozen baseline across Core/Verify, durable persistence, Edge capture and offline synchronization, Gateway native ingress, connector management, enterprise collection, package integrity, and the merged Microsoft/Entra source boundary.

The final frozen-baseline decision is **NO-GO for declaring the complete frozen baseline pilot-qualified without exclusions**.

The blocking reason is not an unexplained proof divergence or event-loss failure. It is an explicit frozen security defect: the Edge baseline persists a reusable local API key itself in plaintext at rest, even though the file is restricted to mode `0600`. IPQ-G #324 lists credential disclosure as a no-go condition. The result therefore cannot be converted into an all-up PASS merely because later PR #334 repaired the storage design.

A second material frozen limitation is IPQ-D13: the Dark Pro browser path fails deterministic modal focus/return and narrow responsive visibility of the server-authorized state. PR #342 repairs those behaviors after the frozen baseline, but does not rewrite the frozen result.

This report therefore distinguishes two decisions:

1. **Complete frozen baseline:** **NO-GO** for an unqualified integrated-pilot PASS.
2. **Bounded reproduced capability subsets:** **QUALIFIED WITH EXPLICIT EXCLUSIONS** as listed below.

The appropriate next qualification target is a separately named repaired candidate that includes the post-baseline security/accessibility repairs and is tested as its own exact SHA. The frozen baseline remains immutable evidence of what was and was not true at `75927c5...`.

## Qualification method

All child qualification harnesses are post-baseline test machinery. The system under test is checked out separately at the exact frozen SHA and is not patched, rebased, regenerated or silently substituted with later product code.

Every child result must preserve the distinction between:

- `sut_sha`: the immutable product revision under qualification;
- `harness_sha`: the later qualification machinery;
- post-baseline repairs: evidence about a later candidate only.

Repository CI/security/formal checks on a qualification branch validate that exact harness/report head. They do not prove that a later product revision was part of the frozen SUT.

## Capability matrix

| Area | Frozen disposition | Bounded qualified claim | Important exclusions / failures |
| --- | --- | --- | --- |
| IPQ-A — Core / Verify / persistence | **PASS for reproduced scope** | Canonical append, Merkle/inclusion evidence, valid/tampered verification, offline proof bundle, Markdown certificate, ETS-v1 linear consistency verification, SQLite event/artifact restart recovery, duplicate behavior, tested corrupt-state fail-closed, tested raw-artifact-byte non-retention. | Compact RFC 6962 consistency conformance is excluded and remains #194. No source-truth, legal, compliance, HA or GA claim. |
| IPQ-B — Edge Virtual | **MIXED: functional lifecycle PASS; credential-at-rest FAIL** | Stable software-volume identity, exact-byte webhook/syslog behavior in selected tests, proof facade, durable queue/backpressure, outage capture, restart recovery, reconnect/drain, duplicate-safe replay, tested raw sync-payload exclusion. | Frozen reusable local API key is plaintext at rest. `hardware_attested=false`. #334 is post-baseline repair only. No hardware/source-truth/HA/GA claim. |
| IPQ-C — Gateway native ingress | **PASS for reproduced scope** | HTTPS, RFC 5425 Syslog/TLS, File/Drop and OTLP HTTP/gRPC selected frozen paths reproduce their bounded ingress, representation, limit/negative and lifecycle semantics. | No universal network availability, source truth/completeness, hardware attestation, HA/GA, legal or compliance claim. |
| IPQ-D — connector platform / Dark Pro | **MIXED: major paths PASS; D13 FAIL** | Selected connector platform tests, locked production build, guided Connection → Scope → Evidence Policy → Collection → Test → Activate path, text/symbol status semantics, visible focus styling, dark default and light switching. | D13 fails modal focus/return and narrow responsive server-authorization visibility. #342 is post-baseline repair only. Broader Console P1 #209 remains open. |
| IPQ-E — enterprise / Generic REST | **PASS for controlled reproduced scope** | GitHub Audit, AWS CloudTrail, Okta System Log and Generic REST controlled adapters reproduce server-authoritative scope, local-append + durable-enqueue checkpoint ordering, backpressure, retry/partial-commit recovery and bounded source-side behavior. | Live production-service connectivity and source truth/completeness are excluded. |
| IPQ-F — package / Microsoft boundary | **PASS for controlled reproduced scope** | Package manifest/inventory/digest/tamper/conformance checks; Microsoft cloud/readiness; Graph notification/subscription source boundary; Entra users/groups delta/resync boundary. | Full Graph Gateway commitment is excluded under #305. Live Microsoft tenant/service consent/connectivity and source truth/completeness are excluded. Package integrity is not ETS evidence verification. |

## Child evidence index

### IPQ-A — Core / Verify / persistence

Retained run: `31860458736`

- Core/Verify: `65 passed`
  - artifact ID `9240401305`
  - ZIP SHA-256 `2a1fad7343cd1f02f5463a26c0b02c8b808c22c27f0885da330556304e4c451d`
- Persistence/artifacts: `43 passed`
  - artifact ID `9240400741`
  - ZIP SHA-256 `04f49a6c8563e2fca362aa54e91d78e5c1655f67773ee48b570aa1bff6d252e4`

Result record: `docs/test/IPQ_A_FROZEN_RESULT.md` on qualification PR #353 until final synchronization/merge.

### IPQ-B — Edge Virtual

Retained run: `31866484647`

- Frozen Edge-native selected suite: `41 passed`
  - artifact ID `9242163652`
  - ZIP SHA-256 `0c3062aa16c9d006cb24bfece4cc440f2438ce67488ca94832aac8c47b09701d`
- Detached restart/reconnect/secret-boundary probe: harness PASS with mixed product disposition
  - artifact ID `9242163833`
  - ZIP SHA-256 `a9a7582fe41293d4bbd9b635f71c50c9c32ee616168cd4cad7dc8007df63ac0c`

The lifecycle probe reproduces:

- offline durable queue capture;
- reconstruction after restart;
- reconnect and drain;
- duplicate-safe upstream replay;
- absence of raw payload bytes from the exercised sync payload;
- `credential_at_rest=FAIL_PLAINTEXT_REUSABLE_API_KEY`;
- `hardware_attested=FALSE`.

Result record: `docs/test/IPQ_B_FROZEN_RESULT.md` on qualification PR #363 until final synchronization/merge.

### IPQ-C — Gateway native ingress

Retained run: `31860502073`

| Family | Tests | Artifact ID | ZIP SHA-256 |
| --- | ---: | ---: | --- |
| HTTPS | 41 | `9240413827` | `a3993c53d356b90fc38d35aaa80395553a7c2091e9bd2462106b3d1653ba6d54` |
| RFC 5425 Syslog/TLS | 44 | `9240410479` | `77973c2a777d65605f8b68f4ce39af43ca4769fe1d1cc1ee99a0357553c56031` |
| File/Drop | 67 | `9240412414` | `e506acc1794f48d4b898c16ad69ed404a9c95985544f850cda904c371f6fe648` |
| OTLP HTTP/gRPC | 57 | `9240411506` | `6cf06a233ba31d02f9784a1229ef13bb9e3dc487bfdd34ea6b55ab1afb6572b1` |
| **Total** | **209** |  |  |

Result record: `docs/test/IPQ_C_FROZEN_RESULT.md` on qualification PR #354 until final synchronization/merge.

### IPQ-D — connector platform / Dark Pro

Result record merged on main: `docs/test/IPQ_D_FROZEN_RESULT.md`.

- selected frozen connector/Console Python suite: `56/56 PASS` after correcting a harness working-directory defect;
- frozen production build/static boundary: PASS;
- D10 guided browser flow: PASS;
- D13 theme/status subtest: PASS;
- D13 modal focus/return: **FAIL**;
- D13 narrow responsive server-authorization visibility: **FAIL**;
- retained browser run `31858256730`;
- browser artifact ID `9239723989`;
- ZIP SHA-256 `2ad0bd815b38a7844860a22da8746e4a5d8c3fb88d0877257cf27bdb3e1925fe`.

### IPQ-E — enterprise / Generic REST

Retained run: `31858741473`

- GitHub Audit: `11/11 PASS`
  - artifact ID `9239846763`
  - SHA-256 `099fa172a17e25ba6770eb255d65fc059ffe83d428fccd1c472207b9393d25ea`
- AWS CloudTrail: `11/11 PASS`
  - artifact ID `9239847187`
  - SHA-256 `203a933987b63797fabd9a5eb46c0f39942c10da055459dda818a4f6ead4dfb7`
- Okta System Log: `12/12 PASS`
  - artifact ID `9239844981`
  - SHA-256 `da00e59526310f6e70487d1d26c31c083e670cb3c5f39bffaf24d90854445dbc`
- Generic REST: `29/29 PASS`
  - artifact ID `9239846106`
  - SHA-256 `34fbe093fad7eefa4ee5faf83f346dc516c808cf983791ac159313a7e85a3e53`

Result record merged on main: `docs/test/IPQ_E_FROZEN_RESULT.md`.

### IPQ-F — package / Microsoft boundary

Retained run: `31859009394`

- third-party package: `10/10 PASS` plus detached negative probes
  - artifact ID `9239924438`
  - SHA-256 `0b791fc6062755b638ef84971603411c7c9dde160e19e5b9e1d79c4d026fb77a`
- Microsoft common readiness: `15/15 PASS`
  - artifact ID `9239924469`
  - SHA-256 `c9b7e3afc8cff54c39d5ac1a7adfce737041b7b29635ac1f497aa3eedf59419d`
- Graph source boundary: `22/22 PASS`
  - artifact ID `9239924025`
  - SHA-256 `5c7f24be78a47619ec56db52e7c9a1897ce42aec873a12d1ee6d7149ab479c41`
- Entra delta/resync: `29/29 PASS`
  - artifact ID `9239924611`
  - SHA-256 `1b9ba085eeac5ec55ea2f169d70a07a05e55774c85b6868ebdc734f13fab86a9`

Result record merged on main: `docs/test/IPQ_F_FROZEN_RESULT.md`.

## Environment / profile matrix

| Evidence family | Controlled environment/profile |
| --- | --- |
| A | Detached frozen source tree; GitHub-hosted Linux/Python test harness; local SQLite persistence fixtures; no production source connectivity. |
| B | Detached frozen source tree; Linux/Python; temporary local SQLite queue/upstream files; frozen software-volume identity; synthetic tenant/workspace/event metadata. |
| C | Detached frozen source tree; Linux/Python; controlled HTTPS, TLS, filesystem and OTLP fixtures/hosts. |
| D | Detached frozen source tree plus controlled Node production build and Chromium/browser fixture harness for the frozen Console. |
| E | Detached frozen source tree; deterministic synthetic enterprise clients/credential providers; no live GitHub/AWS/Okta production credential claim. |
| F | Detached frozen source tree; deterministic package and Microsoft/Entra clients/profiles; no live Microsoft tenant or production-consent claim. |
| G | Current evidence-pack harness downloads retained A–F artifacts, inventories extracted files and performs a high-risk secret-shape audit. G validates the evidence pack/report head, not a different frozen product revision. |

## Evidence disclosure audit

IPQ-G workflow `.github/workflows/ipq-g-evidence-pack.yml` downloads the retained A–F artifacts from the run IDs above and:

1. hashes every extracted evidence file;
2. scans text evidence for high-risk secret-shaped material such as private-key PEM blocks, bearer-token shapes, AWS access-key IDs, Azure Storage account keys and client-secret assignments;
3. records only the file and pattern class when a match occurs, never the matched value;
4. counts explicit raw-payload/real-PII fixture markers separately so synthetic negative fixtures are not silently confused with production credentials;
5. fails the evidence-pack gate if a high-risk secret shape is detected.

This audit is distinct from the IPQ-B product finding. A clean evidence artifact does not make plaintext credential storage inside the frozen Edge product acceptable.

The final report head must not merge until this automated audit reports PASS.

## Defect / exclusion register

| ID / boundary | Treatment in frozen decision | Later or open work |
| --- | --- | --- |
| IPQ-B reusable local API key plaintext at rest | **NO-GO trigger for complete frozen-baseline PASS.** Mode `0600` limits filesystem access but does not encrypt or one-way protect the reusable credential. | #334 is post-baseline repaired-candidate evidence only. |
| IPQ-D13 modal focus/return | **FAIL / excluded from frozen passing claim.** | #342 post-baseline repair evidence. |
| IPQ-D13 narrow responsive server-authorization visibility | **FAIL / excluded from frozen passing claim.** | #342 post-baseline repair evidence. |
| Compact RFC 6962 consistency proof | **EXCLUDED.** Frozen ETS-v1 linear/full-leaf-list consistency is not compact RFC 6962 conformance. | #194 remains the dedicated target. |
| Full Microsoft Graph Gateway commitment | **EXCLUDED.** Frozen F stops at the Graph source boundary. | #305 remains open. |
| Live GitHub/AWS/Okta/REST/Microsoft production connectivity | **EXCLUDED.** Deterministic controlled clients do not prove live service availability or tenant consent. | Separate live qualifications where commercially required. |
| Kubernetes audit adapter | **NOT PART OF FROZEN SUT.** The adapter has since completed post-baseline, but that later completion is not imported into `75927c5...`. | Qualify separately on a later candidate if claimed. |
| Broader production Console lifecycle | **EXCLUDED beyond reproduced D scope.** | P1 #209 remains open. |
| Hardware-backed Edge identity / TPM / HSM custody | **EXCLUDED.** Frozen Edge explicitly reports software-volume custody and `hardware_attested=false`. | Separate hardware product qualification. |
| HA / cross-region DR / production GA | **EXCLUDED.** | Separate reliability qualification. |
| Source truth / source completeness | **EXCLUDED by architecture.** | ETS proves bounded evidence integrity/verification, not universal truth or complete observation. |
| Legal admissibility / regulatory compliance / certification | **EXCLUDED.** | Requires jurisdiction/policy-specific assessment and evidence. |

## Claim boundaries

### Cryptographic verification is not source truth

A valid ETS proof establishes that the qualified event/evidence representation is consistent with the claimed cryptographic evidence path under the exercised protocol boundary. It does not prove that an upstream person, sensor, SaaS API, AI model or external system told the truth.

### Observation is not completeness

Successful collection proves that the qualified path observed and processed the exercised records. It does not prove that every relevant real-world event existed in, or was emitted by, the source.

### Source health is not ETS verification

Connector/API availability, checkpoint state and collection health are operational states. They remain distinct from cryptographic verification of committed ETS evidence.

### Software identity is not hardware attestation

The frozen Edge identity is software-held. Stability across restart does not convert it into TPM/HSM custody, measured boot or hardware attestation.

### Package integrity is not evidence verification

A connector package can have a valid manifest, inventory and digest while code executed later can still emit incorrect claims. Package conformance is an activation/provenance input, not proof of downstream evidence truth.

### Pilot qualification is not GA/certification

Even a repaired-candidate PASS would not by itself establish HA, cross-region DR, legal admissibility, compliance certification or universal source completeness.

## Go / no-go decision

### Complete frozen baseline

**NO-GO — do not declare `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333` an unqualified passing integrated pilot baseline.**

Reason: the frozen Edge credential-at-rest behavior conflicts with the explicit credential-disclosure no-go criterion in #324. The D13 failures independently prevent claiming the full frozen Console qualification row as PASS.

### Bounded capability subsets

**GO for the explicitly reproduced subsets listed in this report, provided every statement retains its exclusions.**

Those subsets are useful engineering evidence. They may support protocol validation, controlled demonstrations, repaired-candidate comparison, and product planning. They must not be shortened into “the frozen baseline passed everything.”

## Recommended next qualification candidate

Create a separately identified repaired candidate after the relevant post-baseline repairs are integrated and stable. At minimum it should include:

- the #334 Edge credential-at-rest hardening;
- the #342 Console D13 repairs;
- any additional current-main changes intended to be part of the candidate;
- a new immutable candidate SHA;
- reruns of the affected B/D rows plus regression qualification for the capability set intended to be claimed.

The current hosted-Azure work is a separate productization lane and should retain its own qualification records rather than being used to rewrite this frozen result.

## Finalization / independent review

This report is not a final declaration until:

1. IPQ-A, IPQ-B and IPQ-C result branches are synchronized to then-current `main`, rerun on exact head and independently reviewed;
2. this IPQ-G branch is synchronized after those result records are merged;
3. `IPQ-G Integrated Evidence Pack`, CI, Security Audit, CodeQL, Formal Specs, Benchmarks, Apalache and Lean all pass on the exact final report head;
4. the evidence-disclosure audit passes;
5. all review threads are resolved;
6. LanternProtocol independently approves the exact final report head.

After that review, #324/#365 may close with the decision **NO-GO for the complete frozen baseline / GO for bounded reproduced subsets**. Closing #317, if chosen under its exit semantics, must be described as completion of the qualification exercise with a NO-GO outcome—not as a passing pilot milestone.
