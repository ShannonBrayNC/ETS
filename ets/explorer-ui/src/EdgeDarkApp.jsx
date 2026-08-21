import React, { useEffect, useMemo, useState } from 'react'

const UI_API = '/edge/ui/v1'

function nowPayload() {
  return {
    message: 'ETS Edge Dark Pro demonstration event',
    scenario: 'edge-dark-pro-demo',
    generated_at_utc: new Date().toISOString(),
    synthetic: true,
  }
}

export default function EdgeDarkApp() {
  const [theme, setTheme] = useState(() => localStorage.getItem('ets-edge-theme') || 'dark')
  const [status, setStatus] = useState(null)
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [proof, setProof] = useState(null)
  const [verification, setVerification] = useState(null)
  const [bundle, setBundle] = useState(null)
  const [captureReceipt, setCaptureReceipt] = useState(null)
  const [syncResult, setSyncResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const selectedEvent = useMemo(
    () => events.find((entry) => entry?.event?.event_id === selectedEventId) ?? null,
    [events, selectedEventId],
  )

  useEffect(() => {
    document.documentElement.dataset.edgeTheme = theme
    localStorage.setItem('ets-edge-theme', theme)
  }, [theme])

  useEffect(() => {
    run(async () => {
      await refreshAll()
    })
  }, [])

  async function run(fn) {
    setBusy(true)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function refreshAll() {
    const [statusData, eventData] = await Promise.all([
      requestJson(`${UI_API}/status`),
      requestJson(`${UI_API}/events`),
    ])
    setStatus(statusData)
    const items = eventData.items ?? []
    setEvents(items)
    if (!selectedEventId && items.length > 0) {
      setSelectedEventId(items[0].event?.event_id ?? '')
    }
  }

  async function captureSynthetic() {
    const receipt = await requestJson(`${UI_API}/capture`, {
      method: 'POST',
      body: JSON.stringify({ payload: nowPayload() }),
    })
    setCaptureReceipt(receipt)
    setSelectedEventId(receipt.event_id)
    setProof(null)
    setVerification(null)
    setBundle(null)
    await refreshAll()
  }

  async function runSync() {
    const result = await requestJson(`${UI_API}/sync`, {
      method: 'POST',
      body: JSON.stringify({ limit: 50 }),
    })
    setSyncResult(result)
    await refreshAll()
  }

  async function loadProof() {
    if (!selectedEventId) return
    const data = await requestJson(
      `${UI_API}/proofs/inclusion/${encodeURIComponent(selectedEventId)}`,
    )
    setProof(data)
    setVerification(null)
  }

  async function verifyProof() {
    if (!proof) return
    const data = await requestJson(`${UI_API}/verify/inclusion`, {
      method: 'POST',
      body: JSON.stringify(proof),
    })
    setVerification(data)
  }

  async function exportBundle() {
    if (!selectedEventId) return
    const data = await requestJson(`${UI_API}/bundles/${encodeURIComponent(selectedEventId)}`)
    setBundle(data)
    downloadJson(`ets-edge-${safeFilename(selectedEventId)}-proof-bundle.json`, data)
  }

  const identity = status?.device_identity
  const sync = status?.sync
  const tree = status?.tree_head
  const ready = status?.ready?.status === 'ready' || status?.ready?.ready === true
  const queueCount = Number(sync?.pending ?? 0) + Number(sync?.retryable_failure ?? 0)
  const transportState = sync?.upstream_status ?? 'unknown'

  return (
    <div className="edge-app">
      <aside className="edge-sidebar" aria-label="ETS Edge navigation">
        <div className="edge-brand">
          <span className="edge-brand-mark" aria-hidden="true">E</span>
          <div>
            <strong>ETS Edge</strong>
            <span>Dark Pro</span>
          </div>
        </div>
        <nav>
          <a href="#overview">Overview</a>
          <a href="#evidence">Evidence</a>
          <a href="#sources">Sources</a>
          <a href="#sync">Synchronization</a>
          <a href="#device">Device</a>
        </nav>
        <div className="edge-sidebar-foot">
          <span className="edge-kicker">Local management</span>
          <strong>No browser secrets</strong>
          <small>Edge Virtual / software custody</small>
        </div>
      </aside>

      <main className="edge-main">
        <header className="edge-topbar">
          <div>
            <span className="edge-kicker">Evidence Transparency System</span>
            <h1>Edge Operations</h1>
            <p>Capture locally. Prove independently. Synchronize when available.</p>
          </div>
          <div className="edge-top-actions">
            <button className="edge-button secondary" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
            <button className="edge-button" disabled={busy} onClick={() => run(refreshAll)}>Refresh</button>
          </div>
        </header>

        {error && (
          <section className="edge-alert bad" role="alert">
            <strong>Operator action required</strong>
            <span>{error}</span>
          </section>
        )}

        <section id="overview" className="edge-section" aria-labelledby="overview-heading">
          <div className="edge-section-heading">
            <div>
              <span className="edge-kicker">Overview</span>
              <h2 id="overview-heading">Node posture</h2>
            </div>
            <StatePill tone={ready ? 'good' : 'warn'} text={ready ? 'Ready' : 'Not ready'} />
          </div>

          <div className="edge-metric-grid">
            <Metric label="Device identity" value={shortIdentity(identity?.device_id)} detail={identity?.hardware_attested ? 'Hardware attested' : 'Software-demo custody'} />
            <Metric label="Capture" value={status?.health?.status === 'ok' ? 'Available' : 'Unknown'} detail="Local evidence commitment" />
            <Metric label="Sync queue" value={String(queueCount)} detail={`Upstream ${transportState}`} />
            <Metric label="Tree size" value={String(tree?.tree_size ?? 0)} detail={tree?.signature ? 'Signed tree head' : 'Local signing profile'} />
          </div>

          <div className="edge-card-grid">
            <Card title="Integrity boundary">
              <KeyValue label="Node readiness" value={ready ? 'Ready' : 'Not ready'} />
              <KeyValue label="Signer" value={tree?.signature ? 'Signed' : 'Software local'} />
              <KeyValue label="Evidence verification" value={verification?.valid ? 'Verified' : verification ? 'Failed' : 'Not evaluated'} />
              <p className="edge-note">Node health, connectivity, observation completeness, and cryptographic verification are separate states.</p>
            </Card>
            <Card title="Fleet enrollment">
              <KeyValue label="State" value={status?.fleet?.enrollment_state ?? 'Not configured'} />
              <KeyValue label="Heartbeat" value={status?.fleet?.heartbeat_state ?? 'Not configured'} />
              <KeyValue label="Attestation" value={identity?.hardware_attested ? 'Hardware' : 'Software demo'} />
              <p className="edge-note">Fleet identity will bind this public device identity to the #481 enrollment contract without exposing a reusable device secret.</p>
            </Card>
          </div>
        </section>

        <section id="evidence" className="edge-section" aria-labelledby="evidence-heading">
          <div className="edge-section-heading">
            <div>
              <span className="edge-kicker">Evidence</span>
              <h2 id="evidence-heading">Source to proof</h2>
            </div>
            <button className="edge-button" disabled={busy} onClick={() => run(captureSynthetic)}>Capture synthetic event</button>
          </div>

          {captureReceipt && (
            <section className="edge-alert good" aria-live="polite">
              <strong>Local evidence committed</strong>
              <span>{captureReceipt.event_id}</span>
            </section>
          )}

          <div className="edge-table-wrap">
            <table className="edge-table">
              <thead><tr><th>Index</th><th>Event</th><th>Type</th><th>Digest</th></tr></thead>
              <tbody>
                {events.length === 0 && <tr><td colSpan="4">No evidence events are currently available.</td></tr>}
                {events.map((entry) => (
                  <tr key={entry.event?.event_id} className={entry.event?.event_id === selectedEventId ? 'selected' : ''}>
                    <td>{entry.log_index}</td>
                    <td><button className="edge-link" onClick={() => { setSelectedEventId(entry.event.event_id); setProof(null); setVerification(null); setBundle(null) }}>{entry.event?.event_id}</button></td>
                    <td>{entry.event?.event_type}</td>
                    <td><code>{entry.event_hash?.slice(0, 18)}…</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="edge-card-grid">
            <Card title="Selected evidence">
              <KeyValue label="Event ID" value={selectedEventId || 'None selected'} />
              <KeyValue label="Source" value={selectedEvent?.event?.source_system ?? '—'} />
              <KeyValue label="Content hash" value={selectedEvent?.event?.content_hash ? `${selectedEvent.event.content_hash.slice(0, 28)}…` : '—'} />
              <div className="edge-inline-actions">
                <button className="edge-button secondary" disabled={busy || !selectedEventId} onClick={() => run(loadProof)}>Get proof</button>
                <button className="edge-button secondary" disabled={busy || !proof} onClick={() => run(verifyProof)}>Verify</button>
                <button className="edge-button secondary" disabled={busy || !selectedEventId} onClick={() => run(exportBundle)}>Export bundle</button>
              </div>
            </Card>
            <Card title="Verification">
              <KeyValue label="Inclusion proof" value={proof ? 'Loaded' : 'Not loaded'} />
              <KeyValue label="Result" value={verification?.valid ? 'Verified' : verification ? 'Verification failed' : 'Pending'} />
              <KeyValue label="Reason" value={verification?.reason ?? '—'} />
              <StatePill tone={verification?.valid ? 'good' : verification ? 'bad' : 'neutral'} text={verification?.valid ? 'Cryptographically verified' : verification ? 'Verification failed' : 'Awaiting verification'} />
            </Card>
          </div>

          {(proof || bundle) && (
            <details className="edge-advanced">
              <summary>Advanced protocol material</summary>
              <pre>{JSON.stringify(bundle ?? proof, null, 2)}</pre>
            </details>
          )}
        </section>

        <section id="sources" className="edge-section" aria-labelledby="sources-heading">
          <div className="edge-section-heading">
            <div>
              <span className="edge-kicker">Sources</span>
              <h2 id="sources-heading">Capture boundaries</h2>
            </div>
          </div>
          <div className="edge-metric-grid">
            <Metric label="Webhook" value="Available" detail="Exact-byte SHA-256 capture" />
            <Metric label="Syslog" value={status?.syslog?.listener_state ?? 'Unknown'} detail={`Accepted ${status?.syslog?.accepted ?? 0} / rejected ${status?.syslog?.rejected ?? 0}`} />
            <Metric label="File / OTLP" value="Gateway track" detail="Not claimed by this Edge profile" />
            <Metric label="Raw payload retention" value="Disabled" detail="Metadata/proof profile" />
          </div>
        </section>

        <section id="sync" className="edge-section" aria-labelledby="sync-heading">
          <div className="edge-section-heading">
            <div>
              <span className="edge-kicker">Synchronization</span>
              <h2 id="sync-heading">Offline-safe queue</h2>
            </div>
            <button className="edge-button" disabled={busy} onClick={() => run(runSync)}>Run safe sync</button>
          </div>
          <div className="edge-card-grid">
            <Card title="Queue state">
              <KeyValue label="Pending" value={String(sync?.pending ?? 0)} />
              <KeyValue label="Retryable" value={String(sync?.retryable_failure ?? 0)} />
              <KeyValue label="Terminal" value={String(sync?.terminal_failure ?? 0)} />
              <KeyValue label="Synchronized" value={String(sync?.synchronized ?? 0)} />
            </Card>
            <Card title="Upstream">
              <KeyValue label="Status" value={transportState} />
              <KeyValue label="Oldest pending" value={sync?.oldest_pending_at ?? '—'} />
              <KeyValue label="Last sync result" value={syncResult ? `${syncResult.synchronized}/${syncResult.attempted} synchronized` : 'Not run this session'} />
              <p className="edge-note">Stopping the demo upstream demonstrates continued local capture. Restart it, then run safe sync to show ordered recovery.</p>
            </Card>
          </div>
        </section>

        <section id="device" className="edge-section" aria-labelledby="device-heading">
          <div className="edge-section-heading">
            <div>
              <span className="edge-kicker">Device</span>
              <h2 id="device-heading">Identity and enrollment</h2>
            </div>
          </div>
          <div className="edge-card-grid">
            <Card title="Public identity">
              <KeyValue label="Device ID" value={identity?.device_id ?? 'Unavailable'} />
              <KeyValue label="Algorithm" value={identity?.signing_algorithm ?? '—'} />
              <KeyValue label="Public key ID" value={identity?.signing_public_key_id ?? '—'} />
              <KeyValue label="Fingerprint" value={identity?.public_key_fingerprint_sha256 ? `${identity.public_key_fingerprint_sha256.slice(0, 32)}…` : '—'} />
            </Card>
            <Card title="Key custody">
              <KeyValue label="Custody" value={identity?.key_custody ?? 'Unknown'} />
              <KeyValue label="Hardware attested" value={identity?.hardware_attested ? 'Yes' : 'No'} />
              <KeyValue label="Profile" value="Edge Virtual Demo" />
              <p className="edge-note">This surface intentionally does not display, accept, export, or store the local API key or signing private key.</p>
            </Card>
          </div>
        </section>
      </main>
    </div>
  )
}

function Metric({ label, value, detail }) {
  return <article className="edge-metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>
}

function Card({ title, children }) {
  return <article className="edge-card"><h3>{title}</h3>{children}</article>
}

function KeyValue({ label, value }) {
  return <div className="edge-key-value"><span>{label}</span><strong title={String(value)}>{value}</strong></div>
}

function StatePill({ tone, text }) {
  return <span className={`edge-state ${tone}`}><span aria-hidden="true">●</span>{text}</span>
}

async function requestJson(url, options = {}) {
  const headers = {
    Accept: 'application/json',
    'X-ETS-UI-Request': '1',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers ?? {}),
  }
  const response = await fetch(url, { ...options, headers, credentials: 'same-origin' })
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    throw new Error(`Edge UI service returned an invalid response (${response.status})`)
  }
  if (!response.ok) {
    throw new Error(data?.error?.message ?? data?.detail ?? `Request failed: ${response.status}`)
  }
  return data
}

function shortIdentity(value) {
  if (!value) return 'Unavailable'
  return value.length > 24 ? `${value.slice(0, 21)}…` : value
}

function safeFilename(value) {
  return value.replace(/[^a-zA-Z0-9_.-]/g, '_').slice(0, 96)
}

function downloadJson(name, value) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}
