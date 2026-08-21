# ETS AI Witness Reference Hardware

Status: pilot BOM candidate  
Date: 2026-08-21

## 1. Reference platform decision

The AI Witness pilot does not require local model inference. Its critical workloads are evidence capture, canonicalization, hashing, hardware-backed signing, encrypted buffering, attestation, replay, and authenticated transport. The reference platform is therefore an enterprise x86 micro/1 L system with discrete TPM 2.0 rather than a GPU appliance.

### Primary reference platform

**Lenovo ThinkCentre M90q Gen 6**

Qualification configuration target:

- Intel Q870-class configuration;
- discrete TPM 2.0, TCG certified;
- UEFI Secure Boot enabled;
- Intel vPro Enterprise-capable SKU preferred for fleet manageability;
- 32 GiB RAM minimum for the named pilot BOM;
- 1 TB high-endurance PCIe Gen4 NVMe for the evidence queue and appliance state;
- a second NVMe device SHOULD be fitted for recovery/staging or qualification telemetry where the selected chassis/SKU permits it;
- optional Ethernet expansion SHOULD be used when needed to physically separate management/upstream traffic from observation ingress;
- chassis-intrusion switch enabled where supported.

The M90q Gen 6 family documentation lists a discrete TCG-certified TPM 2.0, Secure Boot, chassis-intrusion support, and enterprise manageability options. Exact purchased MTM/SKU, TPM manufacturer, TPM firmware, BIOS revision, NIC option, memory modules, and NVMe model MUST be frozen in the physical qualification evidence pack rather than inferred from family-level documentation.

### Secondary reference platform

**Dell Pro Micro QCM1250**

The Dell platform is retained as a second-vendor qualification target because current platform documentation identifies Q870/Q670 variants with discrete TPM 2.0 support and BIOS controls for TPM state, attestation hierarchy, key-storage hierarchy, and Secure Boot.

A successful Lenovo qualification does not automatically qualify the Dell platform or vice versa. Each named hardware revision requires its own TPM/firmware/boot/power-loss evidence.

## 2. Pilot BOM

| Component | Reference requirement |
| --- | --- |
| Chassis | Enterprise micro/1 L chassis with serviceable NVMe and chassis intrusion support |
| CPU | x86-64, 4+ physical cores / 8+ logical threads |
| RAM | 32 GiB reference; 16 GiB absolute profile floor |
| Primary storage | 1 TB high-endurance NVMe, PCIe Gen4 preferred |
| Recovery/staging storage | Separate NVMe or independently bootable authenticated recovery medium |
| TPM | Discrete TPM 2.0 for primary qualification; exact manufacturer/firmware recorded |
| Firmware | UEFI with Secure Boot and measured-boot event logging |
| Network | At least two logical security zones; physical second NIC preferred where practical |
| Time | RTC plus authenticated network time using NTS where available |
| Power | OEM PSU; qualification includes abrupt AC removal and recovery testing |
| Cooling | OEM cooling; temperature and throttling captured during seven-day soak |
| Tamper | Chassis intrusion/tamper state captured when supported |

## 3. Operating-system baseline

The conservative pilot baseline is **Ubuntu Server 24.04 LTS x86-64**, minimized and fully patched at image freeze.

Reasons:

- long-lived LTS maintenance baseline;
- Secure Boot-capable UEFI deployment;
- mature systemd/TPM/Linux measured-boot tooling;
- Ubuntu Noble currently packages `tpm2-tools` 5.6;
- predictable automation surface for the qualification harness.

The exact installed package manifest and image digest MUST be retained. Later Ubuntu LTS releases MAY be qualified independently; the pilot evidence must never silently float to a different OS image.

## 4. Storage layout

Recommended pilot layout:

1. EFI System Partition / signed boot path;
2. immutable or tightly managed operating-system root;
3. encrypted application state;
4. encrypted Witness durable queue;
5. reserved free-space threshold for recovery and SQLite/WAL operation;
6. authenticated recovery image or separate recovery media.

Full-volume encryption complements but does not replace the application-layer AES-GCM queue encryption contract.

## 5. Network boundary

Preferred interfaces:

- **management/upstream**: Gateway enrollment, ETS synchronization, NTS, update metadata/targets, fleet management;
- **observation ingress**: authenticated local/remote AI runtime adapters.

Where only one physical interface is present, VLAN/VRF/firewall separation MAY implement the two logical zones for development, but the physical pilot SHOULD qualify a multi-interface configuration when the deployment threat model requires stronger isolation.

Default inbound policy is deny except for explicitly configured authenticated adapter/management surfaces. The Witness does not operate as a transparent network tap in the base profile.

## 6. TPM capability freeze

Before provisioning a production Witness signing key, capture at minimum:

- `tpm2_getcap properties-fixed`;
- `tpm2_getcap algorithms`;
- `tpm2_getcap ecc-curves`;
- `tpm2_getcap pcrs`;
- TPM manufacturer and firmware properties;
- SHA-256 PCR-bank availability;
- P-256 ECDSA capability;
- Secure Boot state;
- measured-boot event-log availability.

The default signer profile requires TPM-native ECDSA P-256/SHA-256. If the named device does not expose that capability, it is not eligible for the default physical Witness profile.

## 7. Manufacturing/provisioning boundary

The qualification harness in the repository is intentionally read-only with respect to TPM ownership and key provisioning. Manufacturing/enrollment must separately define:

- EK/AK provenance and enrollment;
- Witness signing-key creation template and authorization policy;
- queue-sealing object/policy;
- transport/device certificate issuance;
- persistent-handle allocation if used;
- recovery authorization;
- Gateway/fleet enrollment;
- signed image/update trust roots;
- secure erase/decommission procedure.

No diagnostic script should contain `tpm2_clear`, implicit hierarchy reconfiguration, or automatic persistent-handle replacement.

## 8. Qualification exit criteria

A named BOM becomes a reference AI Witness appliance only after:

- all software PR gates pass;
- actual TPM capabilities and key attributes are captured;
- ECDSA P-256 Witness signing executes without private-key export;
- Secure/Measured Boot appraisal passes positive and negative variants;
- encrypted queue survives the power-cut matrix;
- update interruption/recovery and rollback defenses pass;
- NTS/clock-degradation cases pass;
- Gateway enrollment/revocation cases pass;
- seven-day soak completes without silent evidence loss;
- exact BOM, firmware, image, and evidence hashes are independently reviewed.
