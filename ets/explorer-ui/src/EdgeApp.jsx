import React, { useEffect, useMemo, useState } from 'react'

import ExplorerApp from './App.jsx'
import './edge-dark-pro.css'

const DEFAULT_API = import.meta.env.VITE_ETS_API_BASE_URL ?? ''

async function requestJson(url, options = {}) {
  const response = await fetch(url, options)
  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { detail: text }
    }
  }
  if (!response.ok) {
    const detail = payload?.error?.message ?? payload?.detail ?? `HTTP ${response.status}`
    throw new Error(detail)
  }
  return payload
}

function StatePill({ label, value, tone = 'neutral' }) {
  return (
    <div className={`edge-state edge-state-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function DataCard({ title, children }) {
  return (
    <section className="edge-card">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

export default function EdgeApp() {
  const [identity, setIdentity] = useState(null)
  const [ready, setReady] = useState(null)
  const [version, setVersion] = useState(null)
  const [sync, setSync] = useState(null)
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const apiBase = useMemo(() => DEFAULT_API.replace(/\/$/, ''), [])

  async function loadPublicStatus() {
    const [readyPayload, versionPayload, identityPayload] = await Promise.all([
      requestJson(`${apiBase}/ready`),
      requestJson(`${apiBase}/version`),
      requestJson(`${apiBase}/edge/v1/device/identity`),
    ])
    setReady(readyPayload)
    setVersion(versionPayload)
    setIdentity(identityPayload)
  }

  async function loadProtectedStatus() {
    if (!apiKey) return
    const payload = await requestJson(`${apiBase}/edge/v1/sync/status`, {
      headers: { 'X-ETS-API-Key': apiKey },
    })
    setSync(payload)
  }

  async function run(action) {
    setError(null)
    setBusy(true)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Edge status request failed')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    run(loadPublicStatus)
  }, [])

  const custody = identity?.key_custody ?? 'unknown'
  const attestation = identity?.hardware_attested === true
    ? 'Hardware attested'
    : identity?.hardware_attested === false
      ? 'Software demo'
      : 'Unknown'
  const isReady = ready?.ready === true || ready?.status === 'ready'
  const queueDepth = sync?.queue_depth ?? 'Protected'
  const upstream = sync?.upstream_state ?? sync?.upstream_status ?? 'Protected'

  return (
    <main className="edge-dark-shell">
      <header className="edge-command-header">
        <div>
          <p className="edge-kicker">Lantern Protocol · Evidence Transparency System</p>
          <h1>ETS Edge</h1>
          <p className="edge-subtitle">Local evidence capture, independent verification, and disruption-safe synchronization.</p>
        </div>
        <div className="edge-header-actions">
          <button type="button" className="edge-secondary" disabled={busy} onClick={() => run(loadPublicStatus)}>
            Refresh status
          </button>
        </div>
      </header>

      <section className="edge-state-grid" aria-label="Edge status summary">
        <StatePill label="Node" value={isReady ? 'Ready' : 'Not ready'} tone={isReady ? 'good' : 'warn'} />
        <StatePill label="Identity" value={identity?.device_id ? 'Established' : 'Unknown'} tone={identity?.device_id ? 'good' : 'warn'} />
        <StatePill label="Key custody" value={custody} />
        <StatePill label="Attestation" value={attestation} tone={identity?.hardware_attested ? 'good' : 'neutral'} />
        <StatePill label="Sync queue" value={String(queueDepth)} tone={sync && Number(sync.queue_depth ?? 0) > 0 ? 'warn' : 'neutral'} />
        <StatePill label="Upstream" value={String(upstream)} />
      </section>

      {error && <div className="edge-alert" role="alert"><strong>Status unavailable.</strong> {error}</div>}

      <section className="edge-dashboard-grid">
        <DataCard title="Device identity">
          <dl className="edge-detail-list">
            <div><dt>Device ID</dt><dd>{identity?.device_id ?? 'Loading…'}</dd></div>
            <div><dt>Public key fingerprint</dt><dd>{identity?.public_key_fingerprint ?? identity?.fingerprint ?? 'Loading…'}</dd></div>
            <div><dt>Key custody</dt><dd>{custody}</dd></div>
            <div><dt>Hardware attested</dt><dd>{identity?.hardware_attested === true ? 'Yes' : 'No'}</dd></div>
          </dl>
          <p className="edge-boundary-note">This screen exposes public identity metadata only. Private signing material is never returned to the browser.</p>
        </DataCard>

        <DataCard title="Runtime">
          <dl className="edge-detail-list">
            <div><dt>Profile</dt><dd>{version?.profile ?? version?.service ?? 'ETS Edge Virtual'}</dd></div>
            <div><dt>Version</dt><dd>{version?.version ?? version?.release ?? 'Current build'}</dd></div>
            <div><dt>Readiness</dt><dd>{isReady ? 'Ready' : 'Not ready'}</dd></div>
            <div><dt>API origin</dt><dd>{apiBase || 'Same origin'}</dd></div>
          </dl>
        </DataCard>

        <DataCard title="Protected synchronization status">
          <p className="edge-card-copy">Enter the local Edge API key only when protected operator status is needed. The key is held in component memory for this page session and is not written to browser storage.</p>
          <label className="edge-secret-label">
            Local API key
            <input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Session only"
            />
          </label>
          <div className="edge-action-row">
            <button type="button" disabled={busy || !apiKey} onClick={() => run(loadProtectedStatus)}>Load protected status</button>
            <button type="button" className="edge-secondary" disabled={!apiKey && !sync} onClick={() => { setApiKey(''); setSync(null) }}>Clear session key</button>
          </div>
          <dl className="edge-detail-list compact">
            <div><dt>Queue depth</dt><dd>{sync?.queue_depth ?? 'Protected'}</dd></div>
            <div><dt>Oldest pending</dt><dd>{sync?.oldest_pending_age_seconds ?? 'Protected'}</dd></div>
            <div><dt>Last success</dt><dd>{sync?.last_success_at_utc ?? sync?.last_success ?? 'Protected'}</dd></div>
            <div><dt>Upstream</dt><dd>{upstream}</dd></div>
          </dl>
        </DataCard>
      </section>

      <section className="edge-boundary-banner" aria-label="Security boundary">
        <strong>Security boundary:</strong> Edge management remains local-first. This UI does not require inbound Internet management access, and online status must not be interpreted as proof of device integrity, source truth, or observation completeness.
      </section>

      <section className="edge-workbench">
        <div className="edge-section-heading">
          <p className="edge-kicker">Evidence workbench</p>
          <h2>Capture · Prove · Verify</h2>
          <p>The existing ETS Explorer workflows remain available beneath the Edge operator shell so the current demo retains append, proof, artifact verification, offline queue, and export behavior.</p>
        </div>
        <ExplorerApp />
      </section>
    </main>
  )
}
