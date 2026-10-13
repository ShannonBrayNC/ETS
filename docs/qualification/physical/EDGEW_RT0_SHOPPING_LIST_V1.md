# EDGEW-RT0-DUT Shopping List v1

Status: procurement candidate  
Qualification target class: `EDGE-RT0`  
Physical reference: `EDGEW-RT0-DUT`

## Recommended build

| Priority | Item | Recommended part / SKU | Qty | Purpose | Buy now? |
| --- | --- | --- | ---: | --- | --- |
| Required | Base appliance | Protectli Vault Pro `VP2430e` | 1 | Primary physical DUT | Yes |
| Required | Discrete TPM | Protectli TPM-02, SKU `AC-TPM-002`, Infineon SLB 9670 | 1 | Hardware-backed key-custody qualification | Yes |
| Required | RAM | Crucial `CT32G48C40S5.M16A1` 32 GB DDR5-4800 **or** Protectli-installed equivalent from its tested list | 1 | Reference memory | Yes |
| Required | Primary NVMe | Reputable 1 TB M.2 2280 NVMe with SMART/NVMe health telemetry and published endurance | 1 | Edge OS/evidence/proof storage | Yes |
| Required | Ethernet patch cables | Cat6, individually labeled | 6-8 | Four DUT paths plus observer/router links | If needed |
| Recommended | Managed lab switch | TP-Link `TL-SG108E` current hardware revision | 1 | VLANs, port mirroring, deterministic network fault/observation point | Yes unless an existing managed switch is available |
| Recommended | Controlled power outlet | TP-Link Tapo `P110M` or equivalent ETL-listed local/Matter controllable outlet | 1 | Independently commanded abrupt-power cases; not sole evidence source | Yes before physical power tests |
| Recommended | External artifact drive | 1 TB+ USB 3 SSD | 1 | Pristine images, cloned tamper target, retained artifacts | Reuse existing if available |
| Recommended | USB Ethernet adapter | Linux-supported 1 GbE or 2.5 GbE adapter | 1 | Dedicated observer/fault path when workstation NIC count is limited | Only if needed |
| Optional | Ambient sensor | USB/Bluetooth temperature logger with exportable readings | 1 | Independent ambient/thermal context | Later |
| Optional | Small UPS | Line-interactive UPS with USB status | 1 | Controlled recovery/UPS behavior experiments; not used to mask abrupt-power case | Later |

## Current known pricing anchors

As of 2026-09-13:

- Protectli VP2430e bare platform: **$419** from Protectli.
- Protectli TPM-02 (`AC-TPM-002`): **$49** from Protectli.

RAM, NVMe, switch, smart-plug, and cable pricing changes frequently; record vendor, listing URL, purchase date, exact SKU, and delivered hardware revision in the procurement record rather than treating a quoted web price as part of the qualification identity.

## Procurement recommendation

For RT0, prefer ordering the RAM and NVMe installed/tested by Protectli when the price difference is reasonable. The first DUT is a reference artifact; reducing uncontrolled component-lot variation is more valuable than saving a small amount on RAM or storage.

If sourcing memory separately, use a part currently present on Protectli's VP2430/VP2430e tested list and record the full module identity. Do not substitute a similarly named 16 GB Crucial module: Protectli documents qualification failures for some 16 GB manufacturing variants.

## Storage recommendation

Use a **1 TB NVMe** for RT0. A 512 GB drive satisfies the historical minimum, but 1 TB gives us enough room to:

- preserve qualification artifacts locally during a run;
- exercise watermarks without immediately consuming the host;
- retain a realistic 300 GB metadata/proof allocation target;
- create controlled dedicated test volumes;
- run bounded soak and recovery testing with safety headroom.

Do not use the host root filesystem as the disk-exhaustion target. Create a dedicated qualification volume or quota.

## Power-control note

A smart outlet is acceptable as a lab actuator for cutting AC to the DUT power supply, but its app/cloud log is not sufficient evidence by itself. The test must retain an independent observer timeline and the DUT's pre-cut/post-recovery evidence state. Prefer Matter/local control or a management network that remains available when the DUT data network is deliberately partitioned.

## Existing-hardware reuse

The old Linksys and D-Link routers can defer some purchases:

- either can provide a physically separate NAT/DHCP segment;
- either can be used as a real link/reconnect/failure boundary;
- WAN disconnect/reconnect can support offline/sync-recovery testing;
- if syslog is exposed, capture its exact emitted bytes and classify the format before binding it to a legacy qualification profile;
- do not flash alternate firmware until exact model and hardware revision are captured and compatibility is confirmed.

The managed switch remains recommended because port mirroring and deterministic VLAN topology make independent observation cleaner than using a consumer router alone.

## Minimum first-order purchase

The smallest order that advances the physical Edge program materially is:

1. `VP2430e`;
2. `AC-TPM-002` TPM;
3. tested 32 GB RAM;
4. 1 TB NVMe;
5. enough labeled Cat6 cables to isolate management/source/upstream/observer paths.

The existing routers can temporarily provide network segmentation and interruption. The managed switch and controlled power outlet can be added before the corresponding observation and abrupt-power cases.