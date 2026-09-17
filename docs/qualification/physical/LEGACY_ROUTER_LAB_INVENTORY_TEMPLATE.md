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

## Device C — Linksys WGA600N wireless bridge

- Manufacturer: Linksys
- Model: WGA600N Dual-Band Wireless-N Gaming Adapter
- Hardware revision: `<capture from label>`
- Serial/asset ID: `<local lab identifier; do not publish serial if not needed>`
- Stock firmware version/build: `<capture>`
- Ethernet interface: `<capture negotiated speed during characterization>`
- Wireless bridge mode: supported
- 2.4 GHz support: 802.11b/g/n
- 5 GHz support: 802.11a/n
- Band selection: 2.4 GHz, 5 GHz, or both as exposed by stock firmware
- Channel width: Auto 20/40 MHz or other stock-firmware selections
- Wireless security observed/configured: `<None/WEP/WPA-Personal/WPA2-Personal/other>`
- Management IP: `<capture; stock documentation uses 192.168.1.250 in standard mode and 192.168.1.251 for LAN Party master mode>`
- Management credentials changed from factory defaults: `<yes/no>`
- Connected SSID/BSSID: `<capture locally; redact if published>`
- Configured band/channel: `<capture>`
- Association/reassociation timestamps retained: `<yes/no>`
- Ethernet carrier transitions retained by observer: `<yes/no>`
- Packet-loss/latency observations retained: `<yes/no>`
- Alternate firmware action authorized: `false`

### Intended WGA600N role

The WGA600N is lab bridge/fault-injection infrastructure, not an authenticated evidence source or qualified observer. Its useful boundary is:

`wired source or EDGEW-RT0-VT0 interface -> Ethernet -> WGA600N -> 802.11a/b/g/n link -> lab AP/router`

This lets the lab introduce a real legacy wireless hop while keeping the Edge runtime virtual or physical. Useful experiments include:

- 2.4 GHz versus 5 GHz path comparison;
- controlled wireless disconnect/reassociation while Edge remains active;
- AP/router reboot with the Ethernet-side system unchanged;
- channel/band change and resulting interruption/recovery;
- WPA2-Personal credential rotation and failed/recovered association;
- bounded signal degradation by distance/attenuation rather than modifying the DUT;
- comparison of Ethernet carrier state, packet loss, latency, and Edge synchronization behavior across the wireless boundary.

The WGA600N must not establish claims about modern Wi-Fi behavior, radio security beyond its supported legacy modes, authenticated source identity, or EDGEW-RT0 physical NIC reliability. Any observation made by its management interface is supporting evidence only and should be corroborated by an independent observer where the claim depends on wireless state.

## Safe use before characterization is complete

The Linksys and D-Link routers may be used immediately as lab infrastructure for:

- a separate DHCP/NAT source segment;
- physical link interruption/reconnect;
- WAN disconnect/reconnect;
- router reboot while Edge remains active;
- route/default-gateway change;
- DNS forwarder interruption if applicable;
- source address churn observation;
- real physical network state around the virtual Edge twin.

The WGA600N may additionally be used as a legacy wireless bridge to add a real 2.4/5 GHz network segment between a wired source/virtual interface and the lab AP/router.

These uses do not require any of the devices to be trusted as evidence sources.

## Legacy evidence-source decision

After exact-byte capture of emitted logs from the Linksys/D-Link routers:

1. If a device emits RFC 5424 VERSION 1 UDP matching the existing HQP-4 legacy network profile, it may become a candidate named physical legacy DUT after the remaining profile prerequisites are met.
2. If it emits RFC 3164-like or vendor-specific UDP, retain the observation and create a bounded adapter/profile extension rather than pretending it meets the RFC 5424 profile.
3. If it exposes no remote logging, keep it as network-fault infrastructure only.

The WGA600N does not need to emit syslog to be useful; its primary role is network-medium fault injection and wireless-bridge characterization.

Source IP, source port, hostname, app name, router UI identity, SSID/BSSID, and adapter UI state are observations unless a stronger authenticated source-identity mechanism is independently established.

## Alternate firmware boundary

Do not flash OpenWrt, DD-WRT, Tomato, or vendor-recovery firmware until exact model and hardware revision are recorded and compatibility/recovery procedures are confirmed. A failed flash can destroy a useful legacy test device and erase the stock-firmware behavior we may want to characterize.

If alternate firmware is later used, stock and alternate firmware become distinct test configurations and MUST NOT share a qualification claim by assumption.
