# Legacy SNMPv1 Trap Characterization v1

Status: bounded characterization adapter, not physical qualification  
Tracking: #880  
Observed device: Linksys BEFSR41 v3 / firmware 1.04.12

## Why this exists

The T430 physical lab observed the BEFSR41 LogViewer export as an SNMPv1 Trap over UDP/162 during a bounded LAN-to-WAN flow. That wire behavior is not RFC5424 syslog, so the device must not be forced into `LEGACY-NET-SYSLOG-RT0`.

The characterization order is:

`exact UDP datagram -> SHA-256 commitment -> retained raw bytes -> BER/SNMP parsing -> bounded observations`

Parsing never precedes the exact-byte commitment.

## Capture

On the isolated T430 path, keep:

- Linksys LAN: `192.168.1.1`
- T430 `eno2`: `192.168.1.2`
- Linksys Log: enabled
- Linkviewer destination: T430 LAN address
- Linksys WAN: bounded upstream lab/normal LAN connection

Run:

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"

sudo python3 scripts/qualification/legacy_lab/capture_snmpv1_trap.py \
  --device-label linksys-befsr41-v3 \
  --manufacturer Linksys \
  --model BEFSR41 \
  --hardware-revision V3 \
  --firmware 1.04.12 \
  --bind-ip 192.168.1.2 \
  --interface eno2 \
  --port 162 \
  --seconds 90 \
  --output-dir "/srv/ets-lab/evidence/legacy-snmptrap/linksys-befsr41-v3-$RUN_ID"
```

While the capture is running, generate one bounded LAN-to-WAN flow through the Linksys. The flow itself is not treated as proof of LogViewer delivery; the retained UDP/162 datagram is the observation.

## Parsed observations

The parser can retain:

- transport source/destination IP and port;
- SNMP version;
- community OCTET STRING as cleartext metadata;
- enterprise OID;
- agent-address field;
- generic and specific trap values;
- TimeTicks;
- varbind OIDs and bounded values.

These fields remain observations.

## Identity boundary

SNMPv1 provides no cryptographic source authentication. In particular:

- source IP/MAC can be spoofed;
- the SNMPv1 community value is cleartext metadata, not cryptographic identity;
- the trap `agent-addr` is an asserted message field;
- enterprise OID and varbinds are asserted message content.

Accordingly:

`transport identity != authenticated device identity`

and:

`trap content != semantic truth`

## Completeness boundary

UDP delivery is lossy. An absent trap does not prove that no router event occurred. Capture completeness must remain unknown unless separately established.

## Qualification disposition

The physically observed BEFSR41 behavior makes this device a candidate for a bounded SNMP-trap legacy profile extension and for physical network-fault testing.

It does **not** make the device eligible for `LEGACY-NET-SYSLOG-RT0` as currently observed.

A future `LEGACY-NET-SNMPTRAP-RT0` profile must separately bind exact hardware revision, firmware, configuration, observer, environment, mutation/restart cases, retained evidence, and independent HQP verification before any qualification claim.
