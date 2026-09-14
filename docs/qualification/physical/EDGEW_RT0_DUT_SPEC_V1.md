# EDGEW-RT0-DUT Reference Specification v1

Status: procurement / physical qualification candidate  
Qualification target class: `EDGE-RT0`  
Physical reference implementation name: `EDGEW-RT0-DUT`  
Parent qualification issue: #796  
Related physical readiness PR: #811

## 1. Naming boundary

`EDGEW-RT0-DUT` is the procurement and build specification for the first physical Device Under Test. It does **not** create a new qualification methodology or replace the existing `EDGE-RT0` target class.

A machine is not an `EDGEW-RT0-DUT` qualification result merely because it matches this specification. Qualification remains bound to the exact manufacturer, model, hardware revision, serial/asset identifier, firmware, installed components, immutable ETS build/configuration, execution environment, HQP-1 package, and independent HQP-2 verifier result.

## 2. Preferred reference platform

### Protectli Vault Pro VP2430e

Preferred base SKU: `VP2430e`

Required/reference configuration:

| Component | EDGEW-RT0-DUT requirement | Preferred reference |
| --- | --- | --- |
| Architecture | x86-64 | Intel N150, x86_64-v3 |
| CPU | >=4 physical cores/threads; virtualization extensions | Intel N150, 4C/4T, VT-x/VT-d |
| Memory | 16 GiB minimum; 32 GiB reference | 32 GiB DDR5 SO-DIMM |
| Primary storage | >=512 GB high-quality NVMe; 1 TB reference | 1 TB M.2 2280 NVMe |
| Network | >=2 independent Ethernet interfaces; 4 preferred | 4x Intel I226-V 2.5GbE |
| TPM | TPM 2.0 capability required to characterize; discrete TPM preferred for hardware-custody profile | Protectli TPM-02 / Infineon SLB 9670 |
| Firmware | UEFI required; exact firmware and digest/version retained | Protectli AMI or coreboot |
| Secure Boot | Record actual posture; do not infer from UEFI alone | AMI/coreboot capability-dependent |
| Console | Out-of-band/local recovery console strongly preferred | Included serial console cable |
| Cooling | Passive/fanless preferred for deterministic thermal characterization | Fanless aluminum chassis |
| Power | External DC supply that can be cut by independent switched outlet | Included 12 V / 5 A supply |
| OS | Ubuntu LTS x86-64 | Ubuntu 24.04 LTS reference install |

Protectli states the VP2430e is functionally the VP2430 without eMMC, uses an Intel N150, four Intel I226-V 2.5GbE interfaces, supports VT-x/VT-d, M.2 NVMe, AMI/coreboot, and an optional TPM 2.0 module.

## 3. Memory baseline

Reference memory is **32 GiB**. This is above the historical 16 GiB Edge minimum to provide qualification headroom and local diagnostic/virtualization capacity without making 32 GiB a customer-facing minimum.

Preferred modules are limited to vendor-qualified parts for the first DUT. Protectli currently lists the following as validated on the VP2430/VP2430e family:

- Crucial `CT32G48C40S5.M16A1`, 32 GB DDR5-4800;
- Kingston `KVR56S46BD8-32`, 32 GB DDR5-5600, operated at the platform-supported rate.

The exact module manufacturer, full part number, manufacturing origin where visible, SPD data, and memory test result MUST be retained in the DUT inventory. Do not substitute a nominally identical part silently.

## 4. Storage baseline

Reference primary storage is **1 TB M.2 2280 NVMe**. The platform link is PCIe Gen 3 x2; faster drives may negotiate downward.

Selection priorities:

1. documented SMART/NVMe health telemetry;
2. reputable vendor and stable firmware;
3. published endurance rating;
4. power-loss behavior that can be measured rather than assumed;
5. replacement availability;
6. 1 TB capacity to preserve test headroom while retaining the 300 GB Edge metadata/proof sizing objective.

The first physical DUT MUST record:

- drive manufacturer/model;
- serial number;
- firmware revision;
- namespace/capacity;
- logical/physical block size;
- SMART/NVMe health baseline;
- power-on hours and data-unit counters before qualification;
- filesystem and mount options;
- encryption posture;
- post-soak health counters.

A second internal 2.5-inch SSD is **not** required for RT0. The preferred first build keeps the platform's larger component heatsink configuration intact and uses external/observer storage for pristine images and retained qualification artifacts.

## 5. TPM and key-custody profiles

The VP2430e supports firmware TPM 2.0 under AMI and an optional discrete TPM. The reference physical qualification should include the Protectli TPM-02 (`AC-TPM-002`, Infineon SLB 9670) so the first named DUT can characterize genuine discrete hardware-backed key custody.

Two signer subprofiles are allowed but MUST NOT be conflated:

- `EDGEW-RT0-SWKEY`: software-key pilot behavior; useful for compatibility and recovery testing, not hardware-backed custody;
- `EDGEW-RT0-DTPM`: discrete TPM 2.0 signer/custody behavior; preferred physical qualification target.

A run using one signer profile cannot qualify the other by equivalence.

## 6. Network interface assignment

The four physical NICs should be assigned deterministically and retained by PCI path and MAC address:

| Logical role | Preferred port use |
| --- | --- |
| `nic0-management` | operator/management only |
| `nic1-source` | source/legacy-device ingress |
| `nic2-upstream` | Gateway/Verifier/upstream synchronization |
| `nic3-fault-observer` | isolated lab/fault/packet-observation path |

Port labels are operational roles, not security proofs. Qualification evidence must record Linux interface name, permanent MAC address, PCI address, negotiated speed, switch/router attachment, VLAN, and route table.

## 7. Physical lab envelope

Required before destructive/fault-injection cases:

- independently controlled switched power outlet;
- separate observer host;
- separate HQP-2 verification context;
- recoverable base image and checksum;
- isolated qualification network;
- controlled network partition mechanism;
- packet capture from outside the DUT where applicable;
- external artifact retention path;
- temperature/power observation where available;
- dedicated test credentials and keys;
- no production secrets or production signing keys.

## 8. Minimum qualification inventory record

Before `preflight_authorized=true`, record at least:

- base manufacturer/model/SKU;
- chassis serial/asset ID;
- motherboard/platform revision if exposed;
- CPU model and microcode;
- RAM part number/capacity/SPD fingerprint;
- NVMe model/serial/firmware/health baseline;
- TPM vendor/model/firmware and EK/public identity material allowed by policy;
- AMI/coreboot version and configuration digest/export where possible;
- Secure Boot state;
- kernel, OS image, boot parameters;
- NIC PCI paths/MACs/driver/firmware;
- power supply model/rating;
- ambient condition and physical topology;
- immutable ETS build and configuration digests.

## 9. Acceptance boundary

Matching this specification establishes only **DUT readiness**. It does not establish durability, security, evidence completeness, production readiness, semantic truth, regulatory compliance, safety certification, or physical qualification.

Physical qualification still requires execution of the HQP-3 Edge corpus, a sealed HQP-1 execution package, and eligible independent HQP-2 verification.