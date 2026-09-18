# BEFSR41 Legacy HTTP Log Acquisition and Correlation

**Program:** Lantern Protocol — Evidence Transparency System (ETS)  
**Workstream:** Legacy hardware qualification  
**Target:** Linksys BEFSR41 v3, firmware 1.04.12  
**Issue:** #882  
**Status:** Initial bounded implementation

## Objective

This profile treats the BEFSR41 HTTP log pages as **device assertions** that can be
acquired and preserved without pretending that the router is a trustworthy clock,
a cryptographic identity, or an independent observer.

The invariant is: **preserve the exact router response body before interpreting it.**

A parsed row such as 192.168.1.2 -> 1.1.1.1 -> HTTP means ETS observed the router
asserting that flow in its log UI. It does not, by itself, prove that the flow
occurred. Independent packet observation remains a separate evidence source.

## Qualification state

The T430 lab has established that:

- physical Ethernet and carrier loss/recovery are observable;
- the LAN management endpoint is reachable on the isolated Linksys LAN;
- WAN DHCP, routing, NAT and a bounded LAN-to-WAN HTTP flow work;
- the Outgoing Log records 192.168.1.2 -> 1.1.1.1 -> HTTP;
- the System Log records a more detailed TCP tuple;
- router System Log time is relative/weak and is not authoritative wall-clock time;
- a later dedicated UDP/162 LogViewer reproduction captured zero packets with zero
  kernel drops.

The current engineering path therefore does not depend on LogViewer push export.

## Preservation boundary

ets.qualification.legacy_http creates a LegacyHttpCaptureV1 envelope containing the
source label and URL, endpoint kind, observer identity, observer-side UTC acquisition
time, HTTP status/content type, exact body byte length and SHA-256, plus explicit
claim-boundary flags.

The capture explicitly states:

- authenticated_device_identity = false
- completeness_proven = false
- semantic_truth_proven = false
- independent_observation = false

The source URL validator rejects embedded credentials. Router credentials must not
appear in retained URLs, fixtures, issue comments, or committed artifacts.

The retained body and metadata are private by default: 0600 files in a 0700
directory.

## T430 bounded runbook

Use only the isolated/authorized lab topology. Keep the T430 management path
separate from the Linksys test interface.

### 1. Establish the bounded route

~~~bash
sudo ip route replace 1.1.1.1/32 via 192.168.1.1 dev eno2
ip route get 1.1.1.1
~~~

The route check should identify 192.168.1.1, eno2, and the isolated T430 source
address.

### 2. Start independent packet observation

Retain packet evidence separately from the router assertion:

~~~bash
mkdir -p ~/Desktop/ETS/artifacts/befsr41-http
chmod 700 ~/Desktop/ETS/artifacts/befsr41-http

sudo timeout 45 tcpdump -ni eno2 -s 0   -w ~/Desktop/ETS/artifacts/befsr41-http/independent-flow.pcap   'host 1.1.1.1'
~~~

### 3. Generate one bounded LAN-to-WAN event

~~~bash
curl -4   --interface 192.168.1.2   --max-time 10   -I http://1.1.1.1/ || true
~~~

The network response is independent T430 observation. It does not prove what the
router will log.

### 4. Acquire the router log page without retaining credentials

Use a local credential mechanism appropriate for the isolated bench. Do not put a
password into the output filename, URL, artifact metadata, repository, or issue.

A shell prompt keeps the password out of shell history:

~~~bash
read -rsp 'Linksys password: ' LINKSYS_PASSWORD
echo
export LINKSYS_PASSWORD

curl --fail --silent --show-error   --user ":$LINKSYS_PASSWORD"   --output /tmp/befsr41-outgoing.html   http://192.168.1.1/outLogTable.htm

unset LINKSYS_PASSWORD
~~~

If the device requires a non-empty username, provide it from a separate environment
variable rather than committing it to examples or artifacts.

For the System Log, use the exact read-only URL shown by the browser for the current
firmware. Do not assume every BEFSR41 revision uses the same CGI path.

### 5. Preserve before interpretation

~~~bash
python -m ets.qualification.legacy_http capture   --input /tmp/befsr41-outgoing.html   --output-dir ~/Desktop/ETS/artifacts/befsr41-http/outgoing   --source-label 'linksys-befsr41v3-fw-1.04.12'   --source-url 'http://192.168.1.1/outLogTable.htm'   --endpoint-kind outgoing_log   --observer-id 't430-eno2'
~~~

The command emits the capture ID, SHA-256, raw-artifact path, metadata path and
normalized-record path.

### 6. Verify retained bytes

~~~bash
python -m ets.qualification.legacy_http verify   --metadata /path/to/capture.json   --raw /path/to/raw.http-body.bin
~~~

Exit code 0 means the current bytes match the retained SHA-256 and byte length. A
one-byte mutation must fail verification.

### 7. Hash the independent packet artifact

~~~bash
sha256sum ~/Desktop/ETS/artifacts/befsr41-http/independent-flow.pcap
~~~

The PCAP and router HTTP body are separate evidence artifacts and should remain so.

### 8. Remove the bounded route

~~~bash
sudo ip route del 1.1.1.1/32 via 192.168.1.1 dev eno2
~~~

## Parsing semantics

### Outgoing Log

The bounded parser projects only source_lan_ip, destination and service. No source
timestamp is invented because the observed Outgoing Log table does not provide one.

### System Log

The bounded parser recognizes the observed form:

~~~text
HH:MM:SS TCP from <src-ip>:<src-port> to <dst-ip>:<dst-port>
~~~

The time is stored as relative_time with source_time_quality set to
device-relative-untrusted. It is not interpreted as UTC or local civil time.

## Correlation semantics

For an Outgoing Log assertion, ETS can match source IP, destination IP, and
service/destination port.

For a System Log TCP assertion, ETS can match transport, source IP, source port,
destination IP and destination port.

A successful match may set corroborates_device_assertion = true, while the same
correlation result continues to state that authenticated device identity,
completeness and semantic truth are not proven.

## Evidence Architecture mapping

~~~text
CONTROLLED ACTION / CONSEQUENCE
T430 independently observes the network flow
               |
               v
DEVICE ASSERTION
BEFSR41 Outgoing/System Log asserts a corresponding flow
               |
               v
ETS ACQUISITION
exact HTTP bytes + observer UTC + SHA-256 + bounded parser
               |
               v
CORRELATION
explicit matching fields without identity/completeness/truth upgrade
~~~

This lets a legacy device participate in Evidence Architecture even with weak time,
old HTTP management, no trustworthy cryptographic identity, and no reproducible
modern push telemetry.

## Nonclaims

This implementation does not claim that:

- the BEFSR41 is an authenticated source;
- HTTP Basic authentication protects the evidence channel;
- source IP or MAC identifies a physical device;
- router logs are complete;
- a missing log entry proves an event did not occur;
- a present log entry proves semantic truth;
- observer receipt time equals event occurrence time;
- this characterization qualifies the device for production use;
- the device is eligible for LEGACY-NET-SYSLOG-RT0.

The implementation is a bounded characterization and preservation mechanism for the
legacy-hardware qualification lane.
