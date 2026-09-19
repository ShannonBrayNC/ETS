# Wave 1 — Physical ETS Edge Execution Plan

**Tracking:** #814  
**Depends on for final published claim:** #798  
**Base profile:** `ets.edge.hardware-qualification.v1`  
**Execution priority lock:** `HARDWARE_QUALIFICATION_EXECUTION_ORDER.md`

## 1. Objective

Wave 1 moves ETS Edge from virtual/container execution to a named physical x86-64 reference target without prematurely making TPM, Secure Boot, or hardware-backed keys prerequisites for the first physical qualification gate.

The first question is operational and evidentiary:

> Do the same ETS Edge evidence, durability, offline, recovery, synchronization, and independent-verification semantics survive real hardware and real failure stimuli?

The hardware-identity question follows after that answer is supported by retained evidence.

## 2. Reference sequence

Wave 1 uses three reference classes, but only Edge Compact R0 is on the critical path.

| Class | Purpose | Initial trust boundary | Gate |
|---|---|---|---|
| Edge Compact R0 | Fastest physical x86-64 transition from Edge Virtual | software-volume signer; no hardware attestation required | Wave 1 critical path |
| Edge Compact ARM | Constrained/development reference for low-cost deployment | platform-specific; no production assumption | Parallel/follow-on constrained qualification |
| Edge Enterprise R1 | Strong hardware identity and custody boundary | TPM 2.0, Secure Boot, hardware-backed signer, protected storage | Begins after R0 semantics are clean |

## 3. Edge Compact R0 declaration

The first R0 run must explicitly retain:

```yaml
qualification_class: EDGE_COMPACT_R0
identity_profile: software_volume
hardware_attested: false
secure_boot_verified: false
hardware_key_protection: false
```

If the chosen physical machine happens to contain TPM 2.0 or support Secure Boot, their presence does not change the R0 claim. They remain outside the mandatory R0 trust boundary unless a separate profile explicitly brings them into scope.

## 4. Canonical physical qualification path

```text
provision immutable/documented image
→ boot
→ establish/restore bounded device identity
→ capture evidence
→ local durable commit
→ generate/export proof
→ remove upstream connectivity
→ continue local capture
→ inject bounded failure
→ recover
→ reconnect
→ resume synchronization
→ compare local/upstream checkpoints
→ independently verify retained HQP package away from the DUT
→ publish or withhold bounded qualification claim
```

## 5. Named DUT requirement

No R0 qualification run starts until a single physical DUT is named and fingerprinted.

The manifest must capture at minimum:

- manufacturer and exact model;
- hardware revision or board/system revision where available;
- CPU architecture/model;
- memory capacity;
- storage manufacturer/model/capacity/firmware;
- NIC manufacturer/model/firmware when material;
- BIOS/UEFI version;
- OS image/build identity;
- kernel/runtime version;
- Edge source revision, artifact digest, and configuration digest;
- signer/key-custody posture;
- power-control method;
- independent observer/controller identity.

Serial numbers may be retained internally as the asset binding while public reports use a stable non-secret asset identifier.

## 6. Independent observer rule

The Edge DUT must never be the sole historian of a physical qualification stimulus.

For every injected failure, the bench controller or an independent observer records:

- intended stimulus;
- stimulus start/end or transition time;
- control mechanism used;
- observer identity;
- any external measurement available;
- whether the stimulus actually occurred as commanded.

The retained comparison is:

```text
intended stimulus
→ independent stimulus observation
→ Edge observation
→ Edge response
→ resulting physical/logical state
→ recovered evidence/proof state
→ independent verifier result
```

The independent observer does not need to interpret the event semantically. Its role is to prevent the DUT from becoming the sole source for both the claimed event and the evidence that the event occurred.

## 7. Bench architecture

The minimum R0 bench consists of:

1. **DUT** — one x86-64 mini-PC/SFF with SSD/NVMe and Ethernet.
2. **Verifier/controller** — separate host capable of collecting the HQP package and running `python -m ets.hqp_verify` away from the DUT.
3. **Controlled power boundary** — independently actuated switched outlet/PDU/relay appropriate for the DUT power draw.
4. **Controlled network boundary** — managed switch, dedicated router/bridge, or host-controlled link capable of deterministic disconnect/reconnect and impairment without disturbing unrelated infrastructure.
5. **Dedicated qualification storage boundary** — test volume/allocation that can be driven toward configured pressure thresholds without unintentionally exhausting the host root filesystem.
6. **Time-fault boundary** — isolated test method for wall-clock displacement or time-source interruption that does not alter enterprise/home infrastructure.
7. **Recovery media** — known-good boot/recovery image plus documented restore procedure.

Optional but valuable instrumentation includes an independent power meter, USB/serial console capture, or a separate packet-capture observer.

## 8. Gate matrix

### R0.1 Provisioning and build identity

**Stimulus:** wipe/reinstall from documented media or immutable deployment procedure.  
**Required evidence:** image/build/configuration digests, install transcript/receipt, boot identity, SBOM/provenance material where required by HQP-3.  
**Pass:** the installed runtime is unambiguously bound to the retained build identity.

### R0.2 Device identity persistence

**Stimulus:** repeated orderly reboots.  
**Pass:** declared device identity persists as designed, signer posture remains `software_volume`, and no reusable bootstrap secret appears in retained logs/evidence.

### R0.3 Normal sustained capture

**Stimulus:** representative sustained source traffic.  
**Pass:** authoritative acknowledgements correspond to recoverable committed records and exported proofs independently verify.

### R0.4 Upstream loss / offline capture

**Stimulus:** controller removes the upstream route/link.  
**Pass:** local capture/commit/proof remains available, pending synchronization is bounded and explicit, and no cloud dependency is required for local proof.

### R0.5 Idle hard-power interruption

**Stimulus:** independently cut DUT power while Edge is idle after known committed state.  
**Pass:** acknowledged records survive, recovery state is explicit, and prior proof/checkpoint material remains independently verifiable.

### R0.6 Capture hard-power interruption

**Implementation tracking:** #884  

**Stimulus:** cut power during controlled active ingestion.  
**Pass:** acknowledged commits survive; any in-flight/non-authoritative item is explicitly recoverable, rejected, or absent according to documented transaction semantics; no silent acknowledged loss occurs.

### R0.7 Synchronization hard-power interruption

**Implementation tracking:** #886  

**Stimulus:** cut power during active synchronization after a known local pending set exists.  
**Pass:** restart/reconnect resumes idempotently, no unintended logical duplicate is created, and local/upstream checkpoints can be reconciled.

### R0.8 Disk pressure/exhaustion

**Implementation tracking:** #888

**Stimulus:** drive only the dedicated qualification volume through configured high and critical watermarks.  
**Pass:** deterministic backpressure/rejection occurs before unsafe acknowledgement; previously committed evidence remains intact; normal operation returns after space restoration without rewriting history.

### R0.9 Queue saturation/backpressure

**Implementation tracking:** #890  

**Stimulus:** bounded synthetic load exceeds configured queue item/byte policy.  
**Pass:** explicit backpressure/rejection; no unintended drop of already accepted records; queue returns to supported state.

### R0.10 Network instability

**Implementation tracking:** #893  

**Stimulus:** repeat disconnect/reconnect and, where supported by the isolated harness, bounded latency/loss.  
**Pass:** retry state remains explicit, synchronization resumes, and local sequence history does not change merely because transport is unstable.

### R0.11 Clock displacement

**Implementation tracking:** #895  

**Stimulus:** controlled wall-clock degradation/rollback or isolated time-source failure.  
**Pass:** clock uncertainty/fault is retained, monotonic evidence ordering is not silently rewritten, and interpretation can distinguish event ordering from wall-clock quality.

### R0.12 Valid upgrade

**Implementation tracking:** #897  

**Stimulus:** apply an approved Edge software upgrade.  
**Pass:** build transition is explicitly recorded, prior commitments remain verifiable, and post-upgrade capture/proof functions normally.

### R0.13 Failed upgrade and rollback

**Implementation tracking:** #899  

**Stimulus:** use an intentionally invalid/incomplete qualification upgrade path designed to fail safely.  
**Pass:** the system fails boundedly, rollback/recovery is explicit, and committed evidence is not silently lost or rewritten.

### R0.14 Recovery media

**Implementation tracking:** #901

**Stimulus:** rebuild runtime from known recovery media according to the documented procedure.  
**Pass:** the package distinguishes restored retained evidence from regenerated runtime state and preserves identity/custody transitions rather than pretending continuity where none exists.

### R0.15 Capacity/endurance soak

**Stimulus:** extended repeated capture → offline → reconnect → sync cycles with bounded resource measurements.  
**Pass:** no unexplained evidence-chain discontinuity, unbounded queue/storage growth, silent loss, or material resource leak appears within the declared run duration and load envelope.

### R0.16 Source-to-proof operator workflow

**Stimulus:** operator takes one representative source event from ingress through local evidence, export, and independent verification.  
**Pass:** an external reviewer can trace source observation → Edge evidence object/proof → resulting retained package without hidden manual reconstruction.

### R0.17 Independent verification

**Stimulus:** move the completed retained HQP package to the independent verifier/controller environment.  
**Pass:** `python -m ets.hqp_verify` determines the package is structurally complete, digest-consistent, Evidence-Object-bound, test-complete, and eligible for its claimed disposition without trusting producer narrative.

## 9. Automation boundary

The harness should automate deterministic orchestration and collection, but automation must not create false confidence about physical stimuli.

### Safe candidates for automation

- build/configuration identity capture;
- baseline state capture;
- synthetic ingestion/load generation;
- network route/link state changes when performed on a dedicated test boundary;
- bounded storage fill/release on a dedicated volume;
- queue load generation;
- checkpoint/proof export;
- run-package assembly;
- artifact hashing;
- verifier execution;
- report generation.

### Requires explicit physical/control evidence

- hard power interruption;
- BIOS/UEFI/security posture changes;
- storage-device replacement;
- recovery-media boot/reimage;
- any action that can damage the DUT or erase the sole evidence copy.

The harness must record the controller command and an independent observation that the requested physical/control transition occurred.

## 10. Failure policy

A failed test is valuable evidence. Do not repair or rewrite the package to make it pass.

When a case fails:

1. seal/retain the failed run;
2. preserve all external observer artifacts;
3. classify whether the outcome is a DUT failure, harness failure, invalid execution, or profile ambiguity;
4. create the engineering fix separately;
5. run a new qualification package after remediation;
6. retain linkage between failed and replacement runs.

## 11. Qualification index publication

No R0 claim is published as `qualified` or `qualified_with_deviation` until the final HQP package is independently verified and inserted into `docs/qualification/qualification-index-v1.json` under the rules in `QUALIFICATION_INDEX_V1.md`.

The first successful claim must state its limitations prominently, including:

```text
hardware_attested=false
secure_boot_verified=false
hardware_key_protection=false
```

A reader must not be able to confuse successful R0 physical semantics with hardware-backed device identity.

## 12. Parallel lanes

Wave 1 Edge execution does not block the existing Android or legacy-hardware work.

- **Lane A — Edge:** prepare bench → fingerprint named R0 DUT → execute R0.1–R0.17 → independently verify → publish bounded index entry.
- **Lane B — ETS Mobile Android:** continue Android beta-readiness/device qualification using the shared HQP semantics already defined by HQP-4.
- **Lane C — legacy hardware:** continue physical adapter/syslog/source qualification using the HQP-4 legacy binding.

All three lanes reuse the same qualification evidence vocabulary and independent-verifier boundary.

## 13. Exit gate

Wave 1 Edge Compact R0 exits only when a fresh named x86-64 physical Edge DUT can be provisioned from documented media, complete the required physical fault matrix, continue bounded offline capture, recover from approved interruptions, synchronize without silent acknowledged loss or unintended logical duplication, and produce a retained HQP package independently verified away from the DUT.

The exit claim is bounded to the exact DUT/revision/build/profile recorded in the qualification index.

## 14. Next gate — Edge Enterprise R1

After R0 is clean, the next work changes the root of identity and custody rather than the core evidence semantics:

```yaml
qualification_class: EDGE_ENTERPRISE_R1
identity_profile: hardware_backed
hardware_attested: true
tpm_version: "2.0"
secure_boot_verified: true
hardware_key_protection: true
encrypted_storage: true
```

Enterprise R1 must rerun all claim-critical cases affected by the new boot, signer, storage, and recovery boundaries. It may reuse R0 methodology; it may not inherit R0 qualification by implication.
