# ETS Edge Hardware Qualification Corpus v1

**Status:** HQP-3 candidate specification  
**Tracking:** #796  
**Parent:** #140  
**Source requirements:** #141, #142, #143, #144, #145  
**Depends on:** HQP-0 #790, HQP-1 #794, HQP-2 #795

## 1. Purpose

This specification translates the still-applicable ETS Edge requirements into an executable hardware qualification corpus.

It does **not** convert historical issue checkboxes, software CI, the Edge Virtual demo, or a successful unit/integration test into physical qualification evidence.

A physical Edge claim is supportable only when the qualification package binds:

`exact DUT/revision -> exact firmware/security posture -> immutable build/config -> measured environment -> executed corpus -> retained observations/results -> Evidence Objects -> HQP-1 run/report -> HQP-2 independent verification`

The authoritative machine-readable artifacts are:

- `docs/qualification/profiles/ets-edge-hardware-qualification-v1.json`
- `docs/qualification/corpora/ets-edge-hqp-corpus-v1.json`
- `schemas/qualification/v1/edge-hardware-qualification-corpus.schema.json`
- `ets/qualification/edge_corpus.py`

## 2. Qualification status remains independent from capability maturity

An Edge implementation can be feature-complete for a particular function while the associated hardware qualification state remains `not_tested`, `lab_tested`, `failed`, or otherwise bounded.

Likewise, passing this corpus does not by itself establish:

- general availability;
- production readiness;
- legal admissibility;
- regulatory compliance;
- observation completeness;
- semantic truth of source assertions;
- qualification of another device or hardware revision.

## 3. EDGE-RT0 reference target class

`EDGE-RT0` is the first Edge hardware qualification **target class**. It is not a manufacturer/model and it is not independently qualified.

Every physical run MUST replace the class-level abstraction with the exact DUT identity recorded in the HQP-1 run:

- manufacturer;
- model;
- hardware revision;
- serial or asset identity where available;
- boot firmware;
- storage model/firmware;
- TPM/HSM/software signer profile;
- immutable software artifact/configuration identity.

The first qualification run also records these environment dimensions:

- power source;
- power-control method;
- network topology;
- network fault-injection method;
- storage filesystem;
- operating-system/kernel runtime;
- time source;
- ambient condition;
- upstream/verifier endpoint used by the lab.

Changing a claim-critical field requires requalification unless a separately reviewed equivalence profile explicitly permits a narrower conclusion.

## 4. Lab controls

A physical EDGE-RT0 run requires, at minimum:

1. an independent observer host or equivalent observer boundary;
2. controlled power interruption for the power-loss case;
3. controlled network partition for the synchronization case;
4. an isolated qualification filesystem, clone, or known-good recovery image;
5. a separate HQP-2 verifier environment.

Private keys, reusable bootstrap secrets, bearer credentials, and other secret material MUST NOT be retained in the qualification artifact set.

## 5. Corpus

| Case | Family | Execution mode | Primary provenance |
| --- | --- | --- | --- |
| `EDGE-HQP-BLD-001` | build identity/provenance | operator assisted | #140, #145 |
| `EDGE-HQP-ID-001` | identity/enrollment/key custody | operator assisted | #140, #141, #145 |
| `EDGE-HQP-SEC-001` | boot/storage security posture | observation only | #141, #145 |
| `EDGE-HQP-DUR-001` | durable commit/restart | automated or operator assisted | #140, #142, #145 |
| `EDGE-HQP-PWR-001` | abrupt power loss/recovery | physical fault injection | #140, #142, #145 |
| `EDGE-HQP-DSK-001` | disk watermark/exhaustion | physical fault injection | #140, #141, #142, #145 |
| `EDGE-HQP-BPR-001` | bounded queue/backpressure | automated or operator assisted | #140, #142, #145 |
| `EDGE-HQP-OFF-001` | offline operation | automated or operator assisted | #140, #142, #143 |
| `EDGE-HQP-SYN-001` | network partition/resumable sync | physical fault injection | #140, #143, #145 |
| `EDGE-HQP-CHK-001` | checkpoint/proof continuity | automated or operator assisted | #140, #142, #143, #145 |
| `EDGE-HQP-TIM-001` | clock degradation/rollback | physical fault injection | #140, #141 |
| `EDGE-HQP-KEY-001` | key unavailability/rotation | operator assisted | #140, #141, #142, #145 |
| `EDGE-HQP-TMP-001` | storage corruption/tamper | physical fault injection | #140, #141, #142, #145 |
| `EDGE-HQP-UPD-001` | update/rollback/recovery | operator assisted | #140, #145 |
| `EDGE-HQP-BKR-001` | backup/restore | operator assisted | #141, #142, #144, #145 |
| `EDGE-HQP-CAP-001` | capacity/soak | automated or operator assisted | #140, #143, #145 |
| `EDGE-HQP-OPS-001` | source-to-proof/export workflow | operator assisted | #140, #144, #145 |

Every case has:

- historical requirement references;
- execution mode and driver identifier;
- explicit preconditions;
- required retained artifact roles;
- assertion identifiers;
- HQP stimulus class;
- required observation classes;
- resulting-state expectations;
- pass criteria;
- safety and recovery boundaries.

## 6. Physical fault injection is bounded

The fault-injection cases are not destructive-testing licenses.

### Abrupt power loss

Use a switched-power lab harness, a known-good recovery path, and synthetic evidence. Never run the case on uncontrolled production hardware.

### Disk exhaustion

Fill only a dedicated qualification volume/quota and preserve recovery headroom. Do not intentionally exhaust the host root filesystem.

### Network partition

Partition only the dedicated Edge qualification path and retain independent observer timing for the fault and reconnect.

### Clock rollback/degradation

Use an isolated time source, namespace, VM, or dedicated lab network where possible. Do not alter enterprise/shared time infrastructure.

### Storage tamper

Mutate only a cloned qualification store and retain the pristine source before the mutation.

## 7. Current Edge implementation linkage

The existing Edge Virtual demo already supplies development/lab mechanisms useful for several corpus cases:

- durable SQLite metadata/log state;
- stable software Ed25519 identity;
- protected local HTTP routes;
- webhook/syslog capture;
- local proof generation;
- bounded synchronization queue;
- explicit backpressure;
- offline capture while upstream is stopped;
- restart-safe queue state;
- idempotent replay after reconnect;
- local/upstream checkpoint comparison.

Those capabilities reduce the amount of new harness code required, but they are not substitutes for a physical EDGE-RT0 run. In particular, the current virtual demo explicitly does not claim TPM/HSM custody, Secure Boot, physical power-loss behavior, hardware thermal/endurance limits, or production authentication.

## 8. Execution tooling

The HQP-3 helper is available as:

```text
python -m ets.edge_hqp
```

### Validate the normative profile/corpus relationship

```text
python -m ets.edge_hqp validate-corpus \
  --profile docs/qualification/profiles/ets-edge-hardware-qualification-v1.json \
  --corpus docs/qualification/corpora/ets-edge-hqp-corpus-v1.json
```

### Render the deterministic execution plan

```text
python -m ets.edge_hqp plan \
  --corpus docs/qualification/corpora/ets-edge-hqp-corpus-v1.json
```

### Validate a captured draft HQP-1 run

```text
python -m ets.edge_hqp validate-run \
  --profile docs/qualification/profiles/ets-edge-hardware-qualification-v1.json \
  --corpus docs/qualification/corpora/ets-edge-hqp-corpus-v1.json \
  --run <draft-run.json>
```

The validator requires:

- exact profile ID/version binding;
- all claim-critical device firmware/security fields;
- all required environment dimensions;
- all 17 Edge cases exactly once;
- the declared stimulus class for each case;
- every required observation class;
- every required artifact role;
- every corpus assertion ID;
- waiver behavior consistent with the profile.

### Seal a complete physical capture as `lab_tested`

```text
python -m ets.edge_hqp seal-lab-run \
  --profile docs/qualification/profiles/ets-edge-hardware-qualification-v1.json \
  --corpus docs/qualification/corpora/ets-edge-hqp-corpus-v1.json \
  --run <draft-run.json> \
  --completed-at <ISO-8601-with-timezone> \
  --output-run <sealed-run.json> \
  --output-report <qualification-report.json>
```

The producer tooling deliberately cannot self-promote a run to `qualified` or `qualified_with_deviation`.

It will refuse to seal a `lab_tested` package when:

- a required case is missing;
- a required case is `not_run` or `invalid`;
- a required case failed;
- a non-waivable case is waived;
- required Edge-specific artifacts/observations/assertions are absent.

## 9. Independent verification

The sealed `lab_tested` run/report plus retained artifacts are then transferred to a clean HQP-2 environment.

The independent verifier must not trust:

- the DUT runtime;
- the producer's narrative;
- a screenshot claiming success;
- a historical GitHub issue checkbox;
- an embedded producer-side verifier assertion merely because it says `valid`.

HQP-2 independently checks the retained package and emits its own verification result.

## 10. Important HQP-1 semantic limitation

HQP-1 currently retains resulting-state IDs and digests but does not include an explicit `resulting_state_class` field. HQP-3 therefore makes resulting-state expectations normative in the profile/corpus and verifies the surrounding test/artifact/assertion chain, while HQP-2 continues to report resulting-state semantic-class reconstruction as an explicit limitation.

That limitation MUST NOT be hidden in a physical qualification report. A future versioned HQP execution contract may add the field; doing so requires explicit migration/requalification rules rather than silently changing v1 semantics.

## 11. Disposition and publication rule

A successful HQP-3 producer run means only that the exact DUT produced a complete `lab_tested` package for the captured scope.

A public statement that a device/revision is physically **qualified** additionally requires:

- independent HQP-2 verification;
- exact DUT/revision/build/profile identification;
- retained evidence availability under the declared custody policy;
- explicit deviations/limitations;
- qualification index/publication governance under HQP-5.

## 12. HQP-3 exit gate

HQP-3 is engineering-complete when:

1. the Edge profile and corpus validate one-to-one;
2. the corpus retains traceability to #140-#145;
3. the execution tool validates all required Edge-specific evidence bindings;
4. a synthetic conformance run proves the 17-case package can be assembled and sealed as `lab_tested`;
5. CI confirms the tooling without claiming physical qualification;
6. one named physical Edge DUT can execute the corpus and produce a package consumable by HQP-2.

Items 1-5 are repository/CI deliverables. Item 6 is the first physical lab execution gate and is intentionally not satisfied by CI alone.
