# EDGE-RT0 Physical Qualification Execution Runbook v1

Status: **execution readiness only — no physical qualification claim**  
Tracking: #796  
Parent: #140  
Profile: `ets.edge.hardware-qualification.v1` / `1.0.0`  
Corpus: `ets.edge.hardware-qualification.corpus.v1` / `1.0.0`

## 1. Purpose

This runbook prepares the first named physical ETS Edge DUT for the HQP-3 execution gate. It does not identify a manufacturer/model and it does not assert that any test has been executed.

The first physical target must satisfy the existing Edge MVP baseline unless a reviewed deviation says otherwise:

- x86-64 Ubuntu LTS appliance;
- at least 4 CPU cores;
- at least 16 GiB RAM;
- at least 512 GB high-endurance SSD/NVMe;
- TPM 2.0 preferred, with a declared software-key profile permitted for the first pilot where the profile and claim boundary explicitly say so.

ARM64, Raspberry Pi-class, ruggedized, and industrial targets are separate future qualification targets and must not inherit this result.

## 2. Qualification boundary

A physical result is bounded to the exact:

`DUT → hardware revision → firmware/security-element posture → immutable build/configuration → qualification environment → test cases → observations → resulting states → retained Evidence Objects/artifacts → HQP-2 result`

`EDGE-RT0` is only a target class. Before execution, replace every class-level placeholder with the actual manufacturer, model, revision, serial/asset identity, firmware, storage identity/firmware, signer/security-element posture, software commit/artifact/configuration digests, and environment values.

A repository CI pass, simulator pass, virtual Edge pass, or completed runbook is not physical qualification evidence.

## 3. Required lab roles and separation

Assign these roles before execution:

1. **DUT operator** — performs approved setup, stimuli, recovery, and evidence export.
2. **Independent observer** — records externally observable fault application and resulting state from a host that is not the DUT.
3. **Evidence custodian** — seals retained artifacts, digests, manifests, and transfer records.
4. **HQP-2 verifier operator** — runs verification from an independent environment after producer capture is sealed.

One person may fill more than one human role in a small lab, but the independent verifier execution environment must remain logically and operationally independent from the DUT/producer runtime.

## 4. Minimum lab controls

Do not start the physical run until all are available:

- independent observer host;
- controlled power-interruption mechanism dedicated to the DUT;
- controlled network-partition mechanism limited to the qualification path;
- isolated qualification storage or a recoverable whole-device image;
- tested recovery media;
- external HQP-2 verifier environment;
- dedicated qualification signing/bootstrap material;
- a pristine evidence-store backup or clone before destructive/tamper cases;
- thermal/resource monitoring for capacity testing;
- stop conditions for power, storage, thermal, endurance, and evidence-integrity faults.

Never retain passwords, bootstrap secrets, private signing keys, or reusable credentials in the evidence package.

## 5. Preflight — exact DUT binding

Complete `edge-rt0-dut-readiness.template.json` and save the populated copy under a run-specific directory outside the template tree.

Required device firmware fields from HQP-3:

- `boot_firmware`
- `storage_model_firmware`
- `tpm_or_signer_profile`

Required environment dimensions:

- `power_source`
- `power_control_method`
- `network_topology`
- `network_fault_injection_method`
- `storage_filesystem`
- `os_kernel_runtime`
- `time_source`
- `ambient_condition`
- `upstream_verifier_endpoint`

Record, at minimum:

- manufacturer/model/revision and serial or asset ID;
- CPU, memory, storage manufacturer/model/capacity/firmware;
- UEFI/BIOS and Secure Boot state;
- TPM/HSM/software signer type and immutable public identity where applicable;
- Ubuntu release and kernel;
- filesystem and mount topology;
- NIC identity and dedicated qualification network path;
- ETS repository commit, built artifact digest, configuration digest, and SBOM/provenance reference;
- exact external observer and verifier build identities.

If any claim-critical field is unknown, stop. Do not substitute `EDGE-RT0` for a missing physical identity.

## 6. Recovery baseline before fault injection

Before any disruptive test:

1. image or otherwise preserve a recoverable baseline;
2. prove recovery media boots;
3. capture a baseline evidence/proof inventory;
4. verify at least one retained proof away from the DUT;
5. confirm the independent observer can timestamp and retain power/network/fault receipts;
6. confirm storage cleanup/recovery cannot exhaust the host root filesystem;
7. confirm all fault mechanisms affect only the qualification target/path.

If the recovery baseline cannot be demonstrated, the disruptive phase is **not authorized**.

## 7. Recommended physical execution sequence

The normative corpus retains all 17 required cases. This sequence is an operational ordering designed to reduce the chance that a destructive or recovery-dependent case invalidates later evidence.

### Phase A — identity and non-destructive posture

1. `EDGE-HQP-BLD-001` — build identity/provenance.
2. `EDGE-HQP-ID-001` — identity, enrollment, bootstrap handling, key custody.
3. `EDGE-HQP-SEC-001` — Secure Boot/storage/signer posture observation.

Exit condition: exact DUT/build/security posture is retained and independently inspectable.

### Phase B — durability and bounded normal degradation

4. `EDGE-HQP-DUR-001` — durable commit and controlled restart.
5. `EDGE-HQP-BPR-001` — bounded queue/backpressure using intentionally small qualification limits.
6. `EDGE-HQP-OFF-001` — offline capture/proof with only the dedicated upstream path disabled.
7. `EDGE-HQP-CHK-001` — checkpoint/inclusion-proof continuity.
8. `EDGE-HQP-OPS-001` — operator source-to-proof/export path and external verification.

Exit condition: acknowledged records survive normal restart/degradation and proof continuity is independently reproducible.

### Phase C — bounded external faults

9. `EDGE-HQP-SYN-001` — controlled network partition and resumable/idempotent synchronization.
10. `EDGE-HQP-TIM-001` — isolated clock degradation/rollback with explicit uncertainty.

Exit condition: externally applied faults are independently observed; local sequence/history is not silently rewritten.

### Phase D — recoverability and signer lifecycle

11. `EDGE-HQP-BKR-001` — backup/restore to an isolated restore target.
12. `EDGE-HQP-KEY-001` — signer unavailability and rotation using dedicated qualification keys.
13. `EDGE-HQP-UPD-001` — staged update, rollback/recovery, and downgrade-policy behavior.

Exit condition: a known-good restore path exists before higher-risk device/storage faults.

### Phase E — high-disruption physical/storage faults

14. `EDGE-HQP-PWR-001` — abrupt power loss using a switched-power lab harness.
15. `EDGE-HQP-DSK-001` — disk watermark/exhaustion on a dedicated qualification filesystem or quota, never by unintentionally filling the host root filesystem.
16. `EDGE-HQP-TMP-001` — storage corruption/tamper detection on a clone only; preserve the pristine source.

Exit condition: resulting state and recovery are captured independently and no acknowledged-record loss is unexplained.

### Phase F — capacity/soak last

17. `EDGE-HQP-CAP-001` — bounded capacity/soak with resource, thermal, storage, queue, proof-latency, and sync-throughput monitoring.

Capacity measurements are measurements, not production SLAs. Stop on any predefined hardware-safety, thermal, storage-endurance, or evidence-integrity threshold.

## 8. Evidence-retention structure

Use a run-specific immutable directory structure such as:

```text
<run-id>/
  00-manifests/
  01-baseline/
  BLD-001/
  ID-001/
  SEC-001/
  DUR-001/
  BPR-001/
  OFF-001/
  CHK-001/
  OPS-001/
  SYN-001/
  TIM-001/
  BKR-001/
  KEY-001/
  UPD-001/
  PWR-001/
  DSK-001/
  TMP-001/
  CAP-001/
  hqp1/
  hqp2/
  custody/
```

For every case retain:

- starting-state evidence;
- authority/stimulus record;
- DUT observations;
- independent-observer observations where the stimulus/result is physically external;
- resulting-state evidence;
- required corpus artifact roles;
- assertion results;
- deviations/waivers and approval artifacts if any;
- artifact digests and byte lengths;
- Evidence Object references.

Do not let the DUT be the only source of evidence that a power cut, network partition, clock fault, or resulting physical/system state occurred.

## 9. HQP-1 assembly and producer-side seal

After all required cases are complete:

1. assemble the exact HQP-1 run package;
2. validate it against `ets.edge.hardware-qualification.v1` and the Edge corpus;
3. confirm every required corpus artifact role and assertion is linked;
4. resolve or explicitly retain every deviation;
5. seal only to `lab_tested` using the Edge producer tooling;
6. retain the sealed run/report digests and complete artifact map.

The producer must not set `qualified` or `qualified_with_deviation` as self-attested authority.

## 10. HQP-2 independent verification

Transfer the sealed profile bytes, HQP-1 run/report bytes, and retained artifact payload map to the independent verifier environment.

HQP-2 must independently check, among other things:

- schema/profile binding;
- run/report canonical digests;
- retained artifact bytes;
- Evidence Object bindings;
- test inventory and linkage;
- deviation/waiver policy;
- disposition eligibility;
- verifier execution independence.

A physical qualification claim is eligible only after HQP-2 returns a valid result supporting the claimed disposition. An `indeterminate` or `invalid` result is not publishable as qualified.

## 11. HQP-5 publication handoff

After HQP-2 succeeds, prepare a qualification-index record that binds the result to:

- exact profile version/digest;
- exact DUT/revision/identity digest;
- immutable build/configuration identity;
- retained package/run/report digests and locator;
- independent verifier identity/build/result digest;
- limitations and non-claims;
- validity window and requalification triggers;
- supersession state;
- roadmap capability state without conflating maturity and qualification.

Until that record is reviewed and published, roadmap language should remain `qualification in progress` or equivalent—not `qualified`.

## 12. Stop / invalidate conditions

Stop the run or mark the affected case invalid when:

- the actual DUT identity differs from the sealed manifest;
- the software/configuration digest changes without a new binding;
- an observer clock/source becomes untrustworthy without explicit uncertainty handling;
- a fault affects systems outside the dedicated qualification boundary;
- recovery requires rewriting evidence history;
- raw evidence/artifacts cannot be retained with stable digests;
- a required independent observation is missing;
- a private key or reusable secret is found in retained evidence;
- a safety/thermal/endurance threshold is exceeded.

Do not silently repair evidence to make a case pass. Retain the failure and resulting state.

## 13. Exit gate for #796

The first physical Edge gate is satisfied only when one **named** x86-64 Edge DUT executes the complete required corpus, produces a sealed HQP-1 package, and receives an eligible valid HQP-2 independent-verifier result with all limitations retained.

This runbook alone does not satisfy #796.
