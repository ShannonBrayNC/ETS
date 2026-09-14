# Legacy Router Lab Inventory and Characterization Template

Status: unexecuted inventory template  
Related: `EDGEW-RT0-VT0`, HQP-4 legacy network reuse, #796, #797

## Device A — Linksys

- Manufacturer: Linksys
- Model: `<capture from label>`
- Hardware revision: `<capture from label>`
- Serial/asset ID: `<local lab identifier; do not publish serial if not needed>`
- Stock/alternate firmware: `<capture>`
- Firmware version/build: `<capture>`
- CPU/architecture if known: `<capture>`
- Ethernet port count/speeds: `<capture>`
- WAN port behavior: `<capture>`
- DHCP server: `<yes/no/version if exposed>`
- DNS forwarder: `<yes/no>`
- NTP client/server behavior: `<capture>`
- Remote syslog configurable: `<yes/no>`
- Logging transport: `<UDP/TCP/TLS/unknown>`
- Destination port: `<capture>`
- First exact received datagram hex/SHA-256: `<capture during characterization>`
- Observed syslog framing/format: `<RFC5424 VERSION 1 / RFC3164-like / vendor-specific / none>`
- OpenWrt support checked: `<not_checked/supported/unsupported>`
- Alternate firmware action authorized: `false`

## Device B — D-Link

- Manufacturer: D-Link
- Model: `<capture from label>`
- Hardware revision: `<capture from label>`
- Serial/asset ID: `<local lab identifier; do not publish serial if not needed>`
- Stock/alternate firmware: `<capture>`
- Firmware version/build: `<capture>`
- CPU/architecture if known: `<capture>`
- Ethernet port count/speeds: `<capture>`
- WAN port behavior: `<capture>`
- DHCP server: `<yes/no/version if exposed>`
- DNS forwarder: `<yes/no>`
- NTP client/server behavior: `<capture>`
- Remote syslog configurable: `<yes/no>`
- Logging transport: `<UDP/TCP/TLS/unknown>`
- Destination port: `<capture>`
- First exact received datagram hex/SHA-256: `<capture during characterization>`
- Observed syslog framing/format: `<RFC5424 VERSION 1 / RFC3164-like / vendor-specific / none>`
- OpenWrt support checked: `<not_checked/supported/unsupported>`
- Alternate firmware action authorized: `false`

## Safe use before characterization is complete

Both routers may be used immediately as lab infrastructure for:

- a separate DHCP/NAT source segment;
- physical link interruption/reconnect;
- WAN disconnect/reconnect;
- router reboot while Edge remains active;
- route/default-gateway change;
- DNS forwarder interruption if applicable;
- source address churn observation;
- real physical network state around the virtual Edge twin.

These uses do not require the router to be trusted as an evidence source.

## Legacy evidence-source decision

After exact-byte capture of emitted logs:

1. If the device emits RFC 5424 VERSION 1 UDP matching the existing HQP-4 legacy network profile, it may become a candidate named physical legacy DUT after the remaining profile prerequisites are met.
2. If it emits RFC 3164-like or vendor-specific UDP, retain the observation and create a bounded adapter/profile extension rather than pretending it meets the RFC 5424 profile.
3. If it exposes no remote logging, keep it as network-fault infrastructure only.

Source IP, source port, hostname, app name, and router UI identity are observations unless a stronger authenticated source-identity mechanism is independently established.

## Alternate firmware boundary

Do not flash OpenWrt, DD-WRT, Tomato, or vendor-recovery firmware until exact model and hardware revision are recorded and compatibility/recovery procedures are confirmed. A failed flash can destroy a useful legacy test device and erase the stock-firmware behavior we may want to characterize.

If alternate firmware is later used, stock and alternate firmware become distinct test configurations and MUST NOT share a qualification claim by assumption.