"""Static Dark Pro assets for the authenticated ETS Fleet portal."""

from __future__ import annotations

FLEET_DARK_PRO_HTML = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Lantern Fleet</title>
  <link rel="stylesheet" href="/fleet/assets/app.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to fleet content</a>
  <header class="topbar">
    <div>
      <p class="eyebrow">LANTERN PROTOCOL</p>
      <h1>Fleet Dark Pro</h1>
    </div>
    <div class="topbar-actions">
      <span id="session-role" class="muted" aria-live="polite">Authenticated</span>
      <button id="theme-toggle" type="button" class="button secondary">Light mode</button>
    </div>
  </header>

  <main id="main" tabindex="-1">
    <section class="boundary" aria-labelledby="boundary-title">
      <h2 id="boundary-title">Operational state boundaries</h2>
      <p>
        Connection, signed heartbeat, lifecycle authorization, device health, and evidence
        verification are separate signals. Online does not mean healthy, uncompromised,
        complete, or evidence-verified.
      </p>
    </section>

    <section aria-labelledby="overview-title">
      <div class="section-heading">
        <div>
          <p class="eyebrow">AUTHORIZED SCOPE</p>
          <h2 id="overview-title">Fleet overview</h2>
        </div>
        <button id="refresh" type="button" class="button">Refresh</button>
      </div>
      <div id="metrics" class="metrics" aria-live="polite"></div>
    </section>

    <section aria-labelledby="devices-title">
      <div class="section-heading">
        <div>
          <p class="eyebrow">DEVICE REGISTRY</p>
          <h2 id="devices-title">Devices</h2>
        </div>
      </div>
      <div class="table-wrap" role="region" aria-label="Fleet devices" tabindex="0">
        <table>
          <thead>
            <tr>
              <th scope="col">Device</th>
              <th scope="col">Lifecycle</th>
              <th scope="col">Transport</th>
              <th scope="col">Heartbeat</th>
              <th scope="col">Attestation</th>
              <th scope="col">Software</th>
            </tr>
          </thead>
          <tbody id="device-rows"></tbody>
        </table>
      </div>
      <p id="empty-state" class="empty" hidden>No devices are visible in your authorized scope.</p>
    </section>

    <section id="detail-panel" class="detail" aria-labelledby="detail-title" hidden>
      <div class="section-heading">
        <div>
          <p class="eyebrow">DEVICE DETAIL</p>
          <h2 id="detail-title" tabindex="-1">Selected device</h2>
        </div>
        <button id="detail-close" type="button" class="button secondary">Close</button>
      </div>
      <dl id="detail-fields" class="detail-grid"></dl>
    </section>

    <p id="status-message" class="status-message" role="status" aria-live="polite"></p>
  </main>

  <script src="/fleet/assets/app.js" defer></script>
</body>
</html>
"""

FLEET_DARK_PRO_CSS = r"""
:root {
  color-scheme: dark;
  --bg: #0a0d12;
  --panel: #11161f;
  --panel-2: #171e29;
  --text: #f4f7fb;
  --muted: #a8b3c4;
  --line: #2b3442;
  --accent: #79b8ff;
  --focus: #d7ecff;
  --danger: #ffb4ab;
  --warning: #ffd8a8;
  --ok: #b8f3c5;
}

:root[data-theme="light"] {
  color-scheme: light;
  --bg: #f5f7fa;
  --panel: #ffffff;
  --panel-2: #edf1f6;
  --text: #111821;
  --muted: #526071;
  --line: #cfd7e2;
  --accent: #005ea8;
  --focus: #003d73;
  --danger: #8d1d18;
  --warning: #704400;
  --ok: #176b2c;
}

* { box-sizing: border-box; }
html { background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
body { margin: 0; min-height: 100vh; background: var(--bg); }
button, a { font: inherit; }
button:focus-visible, a:focus-visible, [tabindex]:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 3px;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: -4rem;
  padding: .75rem 1rem;
  background: var(--text);
  color: var(--bg);
  z-index: 10;
}
.skip-link:focus { top: 1rem; }

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  padding: 1.25rem clamp(1rem, 4vw, 3rem);
  border-bottom: 1px solid var(--line);
  background: var(--panel);
  position: sticky;
  top: 0;
  z-index: 5;
}
.topbar h1, h2 { margin: 0; }
.topbar-actions, .section-heading { display: flex; align-items: center; gap: 1rem; }
.section-heading { justify-content: space-between; margin: 0 0 1rem; }

main { width: min(1400px, 100%); margin: 0 auto; padding: 2rem clamp(1rem, 4vw, 3rem) 4rem; }
section { margin-bottom: 2rem; }

.eyebrow {
  margin: 0 0 .25rem;
  color: var(--accent);
  font-size: .75rem;
  font-weight: 800;
  letter-spacing: .12em;
}
.muted { color: var(--muted); }
.boundary, .detail {
  padding: 1rem 1.25rem;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}
.boundary p { margin-bottom: 0; color: var(--muted); max-width: 90ch; }

.button {
  border: 1px solid var(--accent);
  border-radius: 9px;
  background: var(--accent);
  color: #06101c;
  padding: .6rem .9rem;
  cursor: pointer;
  font-weight: 750;
}
.button.secondary {
  background: transparent;
  color: var(--text);
  border-color: var(--line);
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
  gap: .75rem;
}
.metric {
  min-height: 92px;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
}
.metric dt { color: var(--muted); font-size: .8rem; }
.metric dd { margin: .35rem 0 0; font-size: 1.65rem; font-weight: 800; }

.table-wrap {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}
table { width: 100%; border-collapse: collapse; min-width: 900px; }
th, td { padding: .8rem .9rem; text-align: left; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-size: .78rem; letter-spacing: .04em; }
tbody tr:last-child td { border-bottom: 0; }
.device-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  text-align: left;
  font-weight: 750;
}
.device-id { display: block; margin-top: .2rem; color: var(--muted); font-size: .75rem; }

.status {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  padding: .2rem .45rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  white-space: nowrap;
}
.status::before { content: "●"; font-size: .65rem; }
.status[data-kind="online"]::before,
.status[data-kind="current"]::before,
.status[data-kind="enrolled"]::before { color: var(--ok); }
.status[data-kind="offline"]::before,
.status[data-kind="stale"]::before { color: var(--warning); }
.status[data-kind="revoked"]::before,
.status[data-kind="quarantined"]::before { color: var(--danger); }

.detail-grid {
  display: grid;
  grid-template-columns: minmax(180px, .6fr) minmax(220px, 1.4fr);
  gap: .6rem 1rem;
}
.detail-grid dt { color: var(--muted); }
.detail-grid dd { margin: 0; overflow-wrap: anywhere; }
.empty, .status-message { color: var(--muted); }

@media (max-width: 720px) {
  .topbar, .section-heading { align-items: flex-start; flex-direction: column; }
  .topbar { position: static; }
  .detail-grid { grid-template-columns: 1fr; }
}
"""

FLEET_DARK_PRO_JS = r"""
"use strict";

const byId = (id) => document.getElementById(id);
const metricLabels = [
  ["total", "Visible devices"],
  ["enrolled", "Enrolled"],
  ["online", "Transport online"],
  ["offline", "Transport offline"],
  ["heartbeat_current", "Heartbeat current"],
  ["heartbeat_stale", "Heartbeat stale"],
  ["quarantined", "Quarantined"],
  ["revoked", "Revoked"],
  ["expiring_certificates", "Certificates expiring"],
  ["hardware_attested", "Hardware attested"]
];

function statusNode(value) {
  const span = document.createElement("span");
  span.className = "status";
  span.dataset.kind = String(value);
  span.textContent = String(value).replaceAll("_", " ");
  return span;
}

function textCell(value) {
  const td = document.createElement("td");
  td.textContent = value == null ? "—" : String(value);
  return td;
}

function renderMetrics(data) {
  const root = byId("metrics");
  const nodes = metricLabels.map(([key, label]) => {
    const dl = document.createElement("dl");
    dl.className = "metric";
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = String(data[key] ?? 0);
    dl.append(dt, dd);
    return dl;
  });
  root.replaceChildren(...nodes);
}

function renderDevices(data) {
  const body = byId("device-rows");
  const rows = data.items.map((item) => {
    const tr = document.createElement("tr");

    const deviceCell = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "device-link";
    button.textContent = item.friendly_name;
    button.addEventListener("click", () => loadDetail(item.device_id));
    const deviceId = document.createElement("span");
    deviceId.className = "device-id";
    deviceId.textContent = item.device_id;
    deviceCell.append(button, deviceId);

    const lifecycle = document.createElement("td");
    lifecycle.append(statusNode(item.registration_state));
    const transport = document.createElement("td");
    transport.append(statusNode(item.transport_presence));
    const heartbeat = document.createElement("td");
    heartbeat.append(statusNode(item.heartbeat_posture));

    const attestation = textCell(
      item.hardware_attested
        ? `${item.attestation_class} · hardware`
        : `${item.attestation_class} · software/demo`
    );
    const software = textCell(item.software_version ?? "—");

    tr.append(deviceCell, lifecycle, transport, heartbeat, attestation, software);
    return tr;
  });

  body.replaceChildren(...rows);
  byId("empty-state").hidden = rows.length !== 0;
}

function appendDetailPair(root, label, value) {
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = label;
  dd.textContent = value == null ? "—" : String(value);
  root.append(dt, dd);
}

async function requestJson(path) {
  const response = await fetch(path, {
    method: "GET",
    credentials: "same-origin",
    headers: { "Accept": "application/json" }
  });
  if (!response.ok) {
    throw new Error(`Fleet request failed (${response.status})`);
  }
  return response.json();
}

async function loadDetail(deviceId) {
  try {
    const detail = await requestJson(`/fleet/bff/v1/devices/${encodeURIComponent(deviceId)}`);
    const root = byId("detail-fields");
    root.replaceChildren();
    appendDetailPair(root, "Device ID", detail.device_id);
    appendDetailPair(root, "Friendly name", detail.friendly_name);
    appendDetailPair(root, "Enrollment", detail.registration_state);
    appendDetailPair(root, "Transport presence", detail.transport_presence);
    appendDetailPair(root, "Signed heartbeat", detail.heartbeat_posture);
    appendDetailPair(root, "Tenant", detail.tenant_id);
    appendDetailPair(root, "Workspace", detail.workspace_id);
    appendDetailPair(root, "Authentication", detail.auth_method);
    appendDetailPair(root, "Attestation", detail.attestation_class);
    appendDetailPair(root, "Certificate", detail.certificate_posture);
    appendDetailPair(root, "Software", detail.software_version);
    appendDetailPair(root, "Profile", detail.profile_version);
    appendDetailPair(root, "Public identity fingerprint", detail.public_key_fingerprint_sha256);
    appendDetailPair(root, "Evidence verified", detail.evidence_verified ? "yes" : "no");
    appendDetailPair(root, "Health asserted", detail.health_asserted ? "yes" : "no");
    byId("detail-panel").hidden = false;
    byId("detail-title").focus();
  } catch (error) {
    byId("status-message").textContent = error.message;
  }
}

async function refreshFleet() {
  const status = byId("status-message");
  status.textContent = "Refreshing fleet data…";
  try {
    const [session, overview, devices] = await Promise.all([
      requestJson("/fleet/bff/v1/session"),
      requestJson("/fleet/bff/v1/overview"),
      requestJson("/fleet/bff/v1/devices?offset=0&limit=100")
    ]);
    byId("session-role").textContent = session.roles.join(" · ");
    renderMetrics(overview);
    renderDevices(devices);
    status.textContent = "Fleet data refreshed.";
  } catch (error) {
    status.textContent = error.message;
  }
}

byId("theme-toggle").addEventListener("click", () => {
  const root = document.documentElement;
  const light = root.dataset.theme === "light";
  root.dataset.theme = light ? "dark" : "light";
  byId("theme-toggle").textContent = light ? "Light mode" : "Dark mode";
});

byId("refresh").addEventListener("click", refreshFleet);
byId("detail-close").addEventListener("click", () => {
  byId("detail-panel").hidden = true;
});
refreshFleet();
"""
