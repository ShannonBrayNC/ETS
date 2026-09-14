# EDGEW-RT0-VT0 Virtual Twin Plan v1

Status: pre-hardware executable simulation plan  
Maps to physical target class: `EDGE-RT0`  
Physical reference: `EDGEW-RT0-DUT`  
Virtual twin identifier: `EDGEW-RT0-VT0`

## 1. Purpose

`EDGEW-RT0-VT0` exists to exercise the Edge qualification machinery before physical hardware arrives. It is intended to find software, orchestration, recovery, observer, packaging, and verifier defects early.

A successful virtual run is a **simulated qualification result**. It MUST NOT be promoted to `lab_tested`, `qualified`, `qualified_with_deviation`, pilot-ready hardware, or production-ready hardware.

## 2. Recommended host

Preferred host: Linux with KVM/QEMU/libvirt.

Reference guest envelope:

| VM | vCPU | RAM | Storage | NICs | Role |
| --- | ---: | ---: | --- | ---: | --- |
| `edgew-rt0-vt0-dut` | 4 | 16 GiB | 64 GiB OS + sparse 512 GiB qualification disk | 4 | Edge DUT twin |
| `edgew-rt0-vt0-observer` | 2 | 4 GiB | 64 GiB | 2 | independent packet/fault/timeline observer |
| `edgew-rt0-vt0-verifier` | 2 | 4 GiB | 64 GiB | 1 | clean HQP-2/proof verification context |
| `edgew-rt0-vt0-upstream` | 2 | 4 GiB | 64 GiB | 2 | Gateway/upstream synchronization target |

The virtual DUT should run Ubuntu 24.04 LTS x86-64 to match the intended first physical software baseline even if the KVM host runs another supported Ubuntu LTS version.

## 3. Virtual firmware and TPM

Where host support permits:

- UEFI guest firmware: OVMF;
- virtual TPM: `swtpm` TPM 2.0;
- Secure Boot may be enabled in a separate virtual subprofile.

These features exercise ETS integration and failure behavior only. `swtpm` is not a substitute for the Protectli discrete TPM and cannot establish physical hardware-backed key custody.

## 4. Four-interface virtual topology

Create four logically separate networks matching the future physical port roles:

- `vt-mgmt`: operator/management;
- `vt-source`: source and legacy-device ingress;
- `vt-upstream`: Gateway/upstream synchronization;
- `vt-fault`: independent observer/fault-injection path.

The DUT receives one vNIC on each network. The observer attaches to `vt-source` and `vt-fault`; the upstream VM attaches to `vt-upstream`; the verifier remains outside the DUT trust boundary.

Do not treat vNIC MAC addresses as physical NIC identity. The virtual manifest must retain interface UUID/MAC/libvirt network and host bridge bindings explicitly.

## 5. Existing Linksys/D-Link integration

The old routers are useful before the DUT arrives.

Recommended physical/virtual hybrid topology:

`source VM or legacy source -> old router -> host physical NIC/bridge -> EDGEW-RT0-VT0 source vNIC`

Use one router as the active source-side boundary and the second as an alternate/recovery topology. This gives the VM real external network-state changes instead of simulating every fault inside one hypervisor.

Safe initial uses:

- DHCP lease acquisition/renewal/change;
- NAT state change;
- WAN/uplink disconnect and reconnect;
- router reboot while the DUT remains running;
- DNS availability changes if the router provides DNS forwarding;
- route/default-gateway changes;
- MTU/throughput characterization;
- source IP/MAC churn observation;
- packet capture from an independent observer path when possible.

Before using router-generated logs as a qualification source, record exact manufacturer, model, hardware revision, firmware version, configured logging destination, transport, and observed datagram bytes. The existing legacy network profile requires RFC 5424 VERSION 1 UDP; do not assume an older consumer router satisfies that profile.

Do not flash OpenWrt/DD-WRT or other alternate firmware until the exact router model and hardware revision are recorded and compatibility is confirmed.

## 6. Virtualized HQP-3 coverage

All 17 Edge cases can be **preflighted**, but their evidentiary strength differs.

| Case | VT0 status | What VT0 can establish | What still requires physical RT0 |
| --- | --- | --- | --- |
| BLD | strong simulated coverage | build/config/SBOM binding | exact physical installed build identity |
| ID | partial | enrollment, stable logical identity, software/vTPM behavior | physical TPM/security-element custody |
| SEC | partial | UEFI/vTPM/guest storage posture | real firmware, Secure Boot implementation, physical storage posture |
| DUR | strong | committed-state survival across controlled restart | device-specific storage/controller behavior |
| PWR | partial | hard VM termination/recovery logic | actual AC loss, controller/cache/NVMe behavior |
| DSK | strong | dedicated volume watermark/exhaustion behavior | physical drive/endurance/controller behavior |
| BPR | strong | queue bounds/backpressure | hardware performance envelope |
| OFF | strong | offline capture/proof behavior | physical NIC/router/platform behavior |
| SYN | strong | partition/reconnect/idempotent sync | physical network path behavior |
| CHK | strong | proof/checkpoint continuity | physical persistence path |
| TIM | strong simulated | clock degradation/rollback handling | hardware RTC/platform clock behavior |
| KEY | partial | software/vTPM unavailability/rotation | discrete TPM/key-custody behavior |
| TMP | strong simulated | cloned-store mutation/tamper detection | physical storage/fault behavior |
| UPD | strong | update/rollback/recovery flow | firmware/platform update interactions |
| BKR | strong | backup/restore semantics | physical media/recovery path |
| CAP | partial | logical capacity and bounded load behavior | thermal, endurance, CPU/NVMe throughput claims |
| OPS | strong | source-to-proof/export/operator workflow | physical device/user-interface deployment behavior |

## 7. Fault-injection methods

Use bounded methods that preserve a recoverable baseline:

### Restart / abrupt-stop simulation

- graceful restart: guest OS reboot;
- abrupt-stop simulation: hypervisor hard-stop/`virsh destroy` equivalent;
- retain independent observer timestamps around both.

Hard-stopping a VM is **not** evidence of physical power-loss durability.

### Disk pressure

Attach a dedicated sparse virtual block device or quota-limited filesystem. Never exhaust the host root filesystem.

### Network partition

Use one or more of:

- detach the DUT's upstream vNIC;
- drop traffic on the host bridge/firewall;
- physically disconnect/reboot the inserted Linksys/D-Link router;
- apply `tc netem` on a dedicated fault interface for latency/loss/reordering.

Retain observer evidence of when the fault became externally visible and when connectivity returned.

### Clock fault

Use an isolated guest clock/time source. Do not alter the host or shared enterprise time service.

### Key loss

Use dedicated virtual/software qualification keys or vTPM state. Never destroy production key material.

### Tamper

Clone the evidence/storage image, mutate only the clone, verify detection, then discard the clone after retaining artifacts.

## 8. Virtual execution sequence

Recommended order:

1. BLD -> ID -> SEC;
2. DUR -> BKR;
3. BPR -> OFF -> SYN -> CHK -> OPS;
4. TIM -> KEY -> UPD;
5. DSK -> TMP;
6. PWR simulation;
7. CAP last.

This sequence proves recovery and backup paths before increasingly disruptive tests.

## 9. Promotion rule

VT0 results may be used to:

- debug HQP tooling;
- validate test orchestration;
- validate artifact retention;
- validate independent verification;
- rehearse the operator runbook;
- compare future physical behavior against a software baseline.

VT0 results may **not** be used to claim:

- physical hardware qualification;
- TPM/HSM physical key custody;
- Secure Boot platform integrity;
- NVMe power-loss safety;
- storage endurance;
- thermal limits;
- physical network reliability;
- production readiness.

When the physical `EDGEW-RT0-DUT` arrives, its HQP-1 package is a new run with a new exact DUT identity. The VT0 package remains historical simulation evidence and is never rewritten into a physical result.