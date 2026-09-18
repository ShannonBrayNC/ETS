# Legacy Router Characterization on the T430 v1

Status: executable lab characterization  
Tracking: #878  
Candidate profile: `LEGACY-NET-SYSLOG-RT0`

The immediate next hardware task is to characterize the existing Linksys and D-Link devices on the dedicated Ubuntu T430 before deciding whether either device belongs in the RFC 5424 legacy-source profile.

## First command

Run this from the T430:

```bash
cd ~/Desktop/ETS
python3 scripts/qualification/legacy_lab/characterize_router.py inventory
```

This performs no network changes. It prints interfaces, addresses, default routes, neighbor observations, and existing UDP 514/5514 listeners.

## NIC safety gate

Do not use an interface that currently carries an active default route. The characterization harness enforces this rule.

The intended topology is:

`T430 management NIC -> normal LAN`

`T430 dedicated lab NIC -> Linksys or D-Link LAN port`

The first path remains untouched. The second path is the isolated characterization path.

## Record the physical device first

Before changing firmware or factory-resetting anything, record locally:

- manufacturer;
- exact model;
- hardware revision;
- current stock firmware/build;
- LAN/WAN MAC where useful locally;
- available remote-log/syslog configuration;
- whether the syslog destination port is configurable;
- whether the device is still stock firmware.

Do not commit serial numbers, SSIDs, MAC addresses, or credentials to the public repository unless there is a specific need and the information has been reviewed for publication.

## Exact-byte syslog characterization

If the router can send remote syslog to a configurable port, use UDP 5514 first so the capture can run without privileged port binding:

```bash
python3 scripts/qualification/legacy_lab/characterize_router.py capture \
  --interface <DEDICATED_LAB_NIC> \
  --device-label linksys-a \
  --manufacturer Linksys \
  --model '<MODEL_FROM_LABEL>' \
  --hardware-revision '<REV_FROM_LABEL>' \
  --firmware '<FIRMWARE_FROM_UI>' \
  --port 5514 \
  --seconds 60
```

Configure the router's remote-log destination to the isolated T430 NIC IPv4 address shown by the inventory command. During the 60-second window, generate only a synthetic/non-sensitive event such as a lab login/logout, DHCP lease operation, or controlled test configuration event.

If the router only supports UDP 514, rerun the same command under `sudo` with `--port 514`.

## Evidence order

For every received datagram the helper:

1. receives the exact UDP payload;
2. computes SHA-256 over those exact bytes;
3. writes the raw datagram as a local binary artifact;
4. only then classifies its framing;
5. records source IP/port and RFC header fields as observations, not authenticated identity.

The default metadata does not copy the syslog MSG or structured-data content. Raw bytes remain local in the retained binary artifact.

## Decision result

The session produces one of three dispositions:

- `rfc5424_profile_candidate` — at least one message begins with RFC 5424 VERSION 1 framing and the device can proceed to exact-profile preflight after configuration binding;
- `bounded_adapter_or_fault_infrastructure_candidate` — traffic exists but is RFC 3164-like or vendor-specific; retain it and define an explicit adapter/profile extension rather than claiming RFC 5424;
- `no_remote_syslog_observed` — keep the device as physical network-fault infrastructure unless another supported export path is found.

None of these dispositions is a qualification result.

## Linksys/D-Link value even without syslog

A router that emits no useful log format still gives us a real physical boundary for:

- link loss/recovery;
- router reboot;
- WAN disconnect/reconnect;
- DHCP/NAT state change;
- route/default-gateway change;
- source-address churn;
- later comparison of virtual versus physical network interruption.

That is useful to the Edge program without pretending the router is an authenticated evidence source.

## Firmware boundary

Do not flash OpenWrt, DD-WRT, Tomato, or recovery firmware during this pass. Stock behavior must be retained first. Alternate firmware, if later approved, becomes a separate configuration and cannot inherit the stock-firmware claim.

## Claim boundary

This work establishes device characterization only. It does not establish authenticated source identity, completeness, semantic truth, physical Edge qualification, compliance, safety, or production readiness.
