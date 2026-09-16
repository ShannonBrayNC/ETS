# Wave 1 — Edge Compact R0 Bench Bootstrap

**Tracking:** #816  
**Parent:** #814  
**Schema:** `schemas/qualification/v1/edge-compact-r0-bench-manifest.schema.json`  
**Template:** `docs/qualification/manifests/edge-compact-r0-template.json`

## Purpose

This bootstrap is the transition from repository-defined HQP tooling to a named physical Edge Compact R0 device.

It answers a narrow question before any fault is injected:

> Is the physical device and independent test bench identified precisely enough to begin the R0 qualification corpus without allowing the DUT to become its own historian?

Passing this bootstrap is **not** physical qualification. It only means the bench is sufficiently specified to begin HQP-3 execution.

## Claim boundary

Edge Compact R0 deliberately keeps the initial identity boundary weak and explicit:

```text
qualification_class=EDGE_COMPACT_R0
identity_profile=software_volume
hardware_attested=false
secure_boot_verified=false
hardware_key_protection=false
```

A machine may physically contain TPM 2.0 or support Secure Boot. Those features remain outside the mandatory R0 claim unless a later profile explicitly brings them into scope.

## Bootstrap CLI

The bootstrap entrypoint is:

```bash
python -m ets.physical_edge
```

### 1. Collect a read-only draft fingerprint

Run this on the candidate x86-64 Linux DUT:

```bash
python -m ets.physical_edge fingerprint \
  --asset-id EDGE-R0-001 \
  --output edge-r0-001.manifest.json
```

The command may read:

- `/sys/class/dmi/id/*` for manufacturer, product, board and BIOS identity;
- `/proc/cpuinfo` and `/proc/meminfo`;
- `/sys/class/net/*` for local interface identity and driver binding;
- `/etc/os-release`;
- `lsblk` using JSON/read-only inventory mode;
- `git rev-parse HEAD` when run from a repository checkout.

The fingerprint command does **not**:

- cut or cycle power;
- disconnect or impair networking;
- fill storage;
- change the system clock or time source;
- modify BIOS/UEFI/Secure Boot state;
- rotate keys;
- reimage or restore the DUT;
- invoke any fault-injection action.

The generated manifest remains `draft` because automatic discovery is not sufficient to establish claim-critical identity.

### 2. Complete operator-confirmed fields

The operator reviews the fingerprint and supplies or confirms at least:

- manufacturer;
- exact model;
- hardware/system revision;
- stable internal asset identifier;
- CPU model and x86-64 architecture;
- memory capacity;
- storage model and firmware;
- network interface inventory;
- BIOS/UEFI firmware identity;
- immutable Edge source revision;
- Edge artifact SHA-256 digest;
- configuration SHA-256 digest.

Then set:

```json
"claim_critical_fields_confirmed_by_operator": true
```

This field means a human checked the inventory against the physical DUT and available firmware/system information. It does not mean the DUT passed any qualification test.

## Independent observer and verifier

The manifest requires both an observer declaration and HQP verifier declaration.

The observer/controller may be one external bench host, but it must not be the DUT. It records the commanded stimulus and independent evidence that the stimulus actually occurred.

Example:

```json
"observer": {
  "observer_id": "observer-lab-a",
  "observer_host_id": "bench-controller-001",
  "observation_method": "controller journal plus switched-power, link-state and packet observations",
  "independent_from_dut": true
},
"verifier": {
  "verifier_host_id": "bench-controller-001",
  "verifier_identity": "hqp2-clean-verifier",
  "command": "python -m ets.hqp_verify",
  "independent_from_dut": true
}
```

The final HQP-2 verification is still performed from a clean verifier context after the physical corpus is captured.

## Required bench-control declarations

The R0 manifest requires exactly one declaration for each control class.

| Control | Primary R0 cases | Required independent evidence |
|---|---|---|
| `power` | R0.5, R0.6, R0.7 | switched outlet/PDU state, power meter, controller receipt or equivalent |
| `network` | R0.4, R0.7, R0.10 | switch/router/link-state record and preferably packet observation |
| `storage` | R0.8, R0.9, R0.13–R0.15 | controller-side fill/load command plus filesystem/storage measurements |
| `clock` | R0.11 | independent time-source/controller record of displacement or degradation |
| `recovery` | R0.12–R0.14 | recovery-media identity, operator action record and post-boot state |

Every disruptive control requires `operator_approval_required=true`.

The bootstrap schema permanently requires:

```json
"bootstrap_cli_executes_action": false
```

That field prevents the discovery/validation tool from evolving silently into a destructive harness.

## 3. Check readiness

At any point, show blockers without failing the shell step:

```bash
python -m ets.physical_edge readiness \
  --manifest edge-r0-001.manifest.json
```

When the manifest is believed complete:

```bash
python -m ets.physical_edge validate-manifest \
  --manifest edge-r0-001.manifest.json
```

Exit status:

- `0` — bench manifest contains all required readiness bindings;
- `2` — one or more readiness blockers remain;
- parsing/schema errors — malformed or contract-invalid manifest.

A successful validation means **ready to begin physical qualification**, not `qualified`.

## Relationship to HQP-3

The bench manifest exists immediately before the executable Edge corpus.

```text
R0 bench manifest
→ named DUT and independent controls confirmed
→ HQP-3 Edge physical cases executed
→ HQP-1 retained run package
→ producer seals lab result
→ HQP-2 independent verification
→ HQP-5 qualification-index entry if eligible
```

The bootstrap therefore supplies the stable identity and environment anchors consumed by the later run package; it does not replace the run package.

## R0.1–R0.17 mapping

The bootstrap is a prerequisite for all R0 cases, but its strongest direct mappings are:

- **R0.1** — pins physical DUT and immutable build/configuration identity;
- **R0.2** — establishes the device identity that must persist across reboot;
- **R0.4/R0.10** — names the controlled network boundary and observer;
- **R0.5–R0.7** — names the switched-power mechanism and independent observation;
- **R0.8/R0.9** — names the dedicated storage/load boundary;
- **R0.11** — names the isolated clock-fault method;
- **R0.12–R0.14** — names update/recovery media and control method;
- **R0.17** — identifies the independent HQP-2 verifier host and command.

## Safety rule

The bootstrap may discover and validate. It does not inject faults.

Physical stimuli begin only under the individual HQP-3 case safety/recovery boundaries after the manifest is complete and the operator has deliberately initiated that test.

A failed physical test is retained as evidence. Do not mutate a failed package to manufacture a pass.

## First lab use

For the first physical Edge candidate:

1. Install the intended Linux/Edge image on a dedicated x86-64 mini-PC/SFF candidate.
2. Run `fingerprint` on the DUT.
3. Review and complete all claim-critical identity/build fields.
4. Configure the external controller/verifier.
5. Document the five control classes and how each transition will be independently observed.
6. Change `manifest_state` to `ready_for_qualification` only after those bindings are complete.
7. Run `validate-manifest`.
8. If green, begin R0.1 and retain this manifest with the HQP qualification evidence.

Do not add a qualification-index claim merely because this bootstrap passes.
