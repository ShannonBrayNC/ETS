import React, { useEffect, useMemo, useState } from 'react'

import { electionDemo } from './electionDemo.js'

const DEFAULT_API = import.meta.env.VITE_ETS_API_BASE_URL ?? 'http://localhost:8000'

function sampleEvent() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').toLowerCase()
  return {
    event_id: `evt_demo_${stamp}`,
    tenant_id: 'tenant_demo',
    workspace_id: 'workspace_alpha',
    evidence_id: `evidence_demo_${stamp}`,
    event_type: 'evidence.registered',
    subject_ref: 'case:demo-001',
    content_hash: 'a'.repeat(64),
    content_hash_alg: 'sha256',
    metadata: { case: 'demo', source: 'explorer', sequence: 1 },
    created_at_utc: new Date().toISOString(),
    schema_version: 'ets.event.v1',
    source_system: 'ets-explorer-ui',
    actor_id: 'demo-user',
    correlation_id: `corr_${stamp}`,
    external_refs: { demo: 'local' },
    redaction_profile: 'none',
  }
}

export default function App() {
  const [apiBase, setApiBase] = useState(DEFAULT_API)
  const [tenant, setTenant] = useState('tenant_demo')
  const [workspace, setWorkspace] = useState('workspace_alpha')
  const [bearerToken, setBearerToken] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [health, setHealth] = useState(null)
  const [ready, setReady] = useState(null)
  const [tree, setTree] = useState(null)
  const [events, setEvents] = useState([])
  const [eventId, setEventId] = useState('')
  const [proof, setProof] = useState(null)
  const [verification, setVerification] = useState(null)
  const [certificate, setCertificate] = useState(null)
  const [artifactId, setArtifactId] = useState('artifact_explorer_demo')
  const [artifactFile, setArtifactFile] = useState(null)
  const [artifactReceipt, setArtifactReceipt] = useState(null)
  const [artifactRecord, setArtifactRecord] = useState(null)
  const [artifactProof, setArtifactProof] = useState(null)
  const [artifactVerification, setArtifactVerification] = useState(null)
  const [simulateTamper, setSimulateTamper] = useState(false)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [showTamperDemo, setShowTamperDemo] = useState(false)

  const authHeaders = useMemo(() => {
    const headers = {}
    if (tenant) headers['X-ETS-Tenant'] = tenant
    if (workspace) headers['X-ETS-Workspace'] = workspace
    if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`
    if (apiKey) headers['X-ETS-API-Key'] = apiKey
    return headers
  }, [tenant, workspace, bearerToken, apiKey])

  async function runStep(fn) {
    setError(null)
    setBusy(true)
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function checkStatus() {
    const healthData = await requestJson(`${apiBase}/health`)
    const readyData = await requestJson(`${apiBase}/ready`)
    setHealth(healthData)
    setReady(readyData)
  }

  async function loadTree() {
    const data = await requestJson(`${apiBase}/api/v1/log/head`, { headers: authHeaders })
    setTree(data)
  }

  async function loadEvents() {
    const data = await requestJson(`${apiBase}/api/v1/events?limit=50&offset=0`, { headers: authHeaders })
    setEvents(data.items ?? [])
  }

  async function appendSample() {
    const event = sampleEvent()
    const data = await requestJson(`${apiBase}/api/v1/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify(event),
    })
    setEventId(data.event_id)
    setProof(null)
    setVerification(null)
    setCertificate(null)
    await loadTree()
    await loadEvents()
  }

  async function loadProof() {
    if (!eventId) return
    setVerification(null)
    setCertificate(null)
    const data = await requestJson(`${apiBase}/api/v1/proofs/inclusion/${encodeURIComponent(eventId)}`, {
      headers: authHeaders,
    })
    setProof(data)
  }

  async function verifyProof() {
    if (!proof) return
    const data = await requestJson(`${apiBase}/api/v1/verify/inclusion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify(proof),
    })
    setVerification(data)
  }

  async function generateCertificate() {
    if (!eventId) return
    const data = await requestJson(`${apiBase}/api/v1/bundles/${encodeURIComponent(eventId)}`, {
      headers: authHeaders,
    })
    const cert = await requestJson(`${apiBase}/reports/certificate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify({ bundle: data, format: 'markdown' }),
    })
    setCertificate(cert)
  }

  async function registerArtifact() {
    if (!artifactFile || !artifactId) return
    const artifactBase64 = await fileToBase64(artifactFile)
    const data = await requestJson(`${apiBase}/evidence/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify({
        artifact_id: artifactId,
        artifact_base64: artifactBase64,
        tenant_id: tenant,
        workspace_id: workspace,
        content_type: artifactFile.type || 'application/octet-stream',
        metadata: {
          filename: artifactFile.name,
          demo: 'explorer-artifact-verifier',
          contains_real_pii: false,
        },
        source_system: 'ets-explorer-ui',
      }),
    })
    setArtifactReceipt(data)
    setArtifactVerification(null)
    const record = await requestJson(`${apiBase}/evidence/${encodeURIComponent(artifactId)}`, {
      headers: authHeaders,
    })
    setArtifactRecord(record)
    const bundle = await requestJson(`${apiBase}/evidence/${encodeURIComponent(artifactId)}/proof`, {
      headers: authHeaders,
    })
    setArtifactProof(bundle)
    await loadTree()
    await loadEvents()
  }

  async function verifyArtifact() {
    if (!artifactFile || !artifactId) return
    const original = await artifactFile.arrayBuffer()
    const bytes = new Uint8Array(original)
    const verificationBytes = simulateTamper ? new Uint8Array([...bytes, 46]) : bytes
    const data = await requestJson(`${apiBase}/evidence/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify({
        artifact_id: artifactId,
        artifact_base64: bytesToBase64(verificationBytes),
      }),
    })
    setArtifactVerification(data)
  }

  useEffect(() => {
    runStep(async () => {
      await checkStatus()
      await loadTree()
      await loadEvents()
    })
  }, [])

  const signed = tree?.signature ? 'Signed' : 'Unsigned local'
  const verified = verification?.valid ? 'Verified' : verification ? 'Failed' : 'Not verified'

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Evidence Transparency System</p>
          <h1>ETS Explorer RC Demo</h1>
          <p>Append fictional evidence metadata, fetch a Merkle proof, verify it, and generate a certificate.</p>
        </div>
        <div className="badges">
          <Badge label={ready?.ready ? 'Ready' : 'Not ready'} tone={ready?.ready ? 'good' : 'warn'} />
          <Badge label={signed} tone={tree?.signature ? 'good' : 'warn'} />
          <Badge label={verified} tone={verification?.valid ? 'good' : verification ? 'bad' : 'neutral'} />
          <Badge label={tenant && workspace ? 'Scoped' : 'Unscoped'} tone="neutral" />
        </div>
      </header>

      {error && <Panel title="API Error"><pre>{error}</pre></Panel>}

      <ElectionRcDemo showTamperDemo={showTamperDemo} setShowTamperDemo={setShowTamperDemo} />

      <Panel title="Connection">
        <div className="grid">
          <label>API base URL<input value={apiBase} onChange={(e) => setApiBase(e.target.value)} /></label>
          <label>Tenant header<input value={tenant} onChange={(e) => setTenant(e.target.value)} /></label>
          <label>Workspace header<input value={workspace} onChange={(e) => setWorkspace(e.target.value)} /></label>
          <label>Bearer token<input type="password" value={bearerToken} onChange={(e) => setBearerToken(e.target.value)} /></label>
          <label>Local API key<input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} /></label>
        </div>
        <div className="actions">
          <button disabled={busy} onClick={() => runStep(checkStatus)}>Check health</button>
          <button disabled={busy} onClick={() => runStep(loadTree)}>Load tree</button>
          <button disabled={busy} onClick={() => runStep(loadEvents)}>Refresh events</button>
        </div>
      </Panel>

      <section className="workflow">
        <Step number="1" title="Append sample" text="Create fictional metadata only. No raw evidence bytes are stored." action="Append sample event" onClick={() => runStep(appendSample)} disabled={busy} />
        <Step number="2" title="Fetch proof" text="Request the Merkle inclusion proof for the selected event." action="Get proof" onClick={() => runStep(loadProof)} disabled={busy || !eventId} />
        <Step number="3" title="Verify proof" text="Run the proof through the API verifier." action="Verify" onClick={() => runStep(verifyProof)} disabled={busy || !proof} />
        <Step number="4" title="Certificate" text="Generate a Markdown verification certificate." action="Generate" onClick={() => runStep(generateCertificate)} disabled={busy || !eventId} />
      </section>

      <Panel title="Artifact verifier">
        <div className="artifact-layout">
          <div className="artifact-controls">
            <label>Artifact ID<input value={artifactId} onChange={(e) => setArtifactId(e.target.value)} /></label>
            <label>Artifact file<input type="file" onChange={(e) => setArtifactFile(e.target.files?.[0] ?? null)} /></label>
            <label className="toggle-row">
              <input type="checkbox" checked={simulateTamper} onChange={(e) => setSimulateTamper(e.target.checked)} />
              Simulate tampering before verification
            </label>
            <div className="actions">
              <button disabled={busy || !artifactFile || !artifactId} onClick={() => runStep(registerArtifact)}>Register artifact</button>
              <button disabled={busy || !artifactReceipt} onClick={() => runStep(verifyArtifact)}>Verify artifact</button>
            </div>
          </div>
          <div className="verification-summary">
            <CheckLine label="Hash Match" state={artifactVerification ? artifactVerification.valid : null} />
            <CheckLine label="Chain Valid" state={artifactReceipt ? true : null} />
            <CheckLine label="Merkle Proof" state={artifactProof?.verification_result?.valid ?? null} />
            <CheckLine label="Signature" state={tree?.signature ? true : null} emptyLabel={tree?.signature ? 'Pending' : 'Unsigned local'} />
            <div className={`artifact-result ${artifactVerification?.valid ? 'good' : artifactVerification ? 'bad' : 'neutral'}`}>
              <strong>{artifactVerification?.valid ? 'Verified' : artifactVerification ? 'Verification Failed' : 'Awaiting verification'}</strong>
              <span>{artifactVerification?.reason ?? 'Register an artifact, then verify it or enable tamper simulation.'}</span>
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Events">
        <table>
          <thead><tr><th>Index</th><th>Event ID</th><th>Type</th><th>Hash</th></tr></thead>
          <tbody>
            {events.map((entry) => (
              <tr key={entry.event.event_id}>
                <td>{entry.log_index}</td>
                <td><button className="link-button" onClick={() => { setEventId(entry.event.event_id); setProof(null); setVerification(null); setCertificate(null) }}>{entry.event.event_id}</button></td>
                <td>{entry.event.event_type}</td>
                <td><code>{entry.event_hash?.slice(0, 18)}…</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="Selected event">
        <div className="row">
          <input value={eventId} onChange={(e) => setEventId(e.target.value)} placeholder="Event ID" />
          <button onClick={() => copyText(eventId)} disabled={!eventId}>Copy ID</button>
        </div>
      </Panel>

      <div className="two-column">
        <JsonPanel title="Tree head" data={tree} />
        <JsonPanel title="Proof" data={proof} downloadName="ets-proof.json" />
        <JsonPanel title="Verification" data={verification} />
        <JsonPanel title="Certificate" data={certificate} downloadName="ets-certificate.json" />
        <JsonPanel title="Artifact receipt" data={artifactReceipt} downloadName="ets-artifact-receipt.json" />
        <JsonPanel title="Artifact proof bundle" data={artifactProof} downloadName="ets-artifact-proof.json" />
      </div>
    </div>
  )
}

function ElectionRcDemo({ showTamperDemo, setShowTamperDemo }) {
  const verification = showTamperDemo ? electionDemo.tamperVerification : electionDemo.validVerification
  const statusTone = verification.valid ? 'good' : 'bad'

  return (
    <section className="election-demo">
      <div className="election-demo-header">
        <div>
          <p className="eyebrow">Election RC public verification</p>
          <h2>{electionDemo.jurisdiction} milestone proof</h2>
          <p>
            Fictional evidence metadata, a public Merkle root, and a verifier-visible
            tamper rejection path for screenshots and presentations.
          </p>
        </div>
        <div className="actions">
          <button onClick={() => setShowTamperDemo(false)}>Valid proof</button>
          <button className="danger-button" onClick={() => setShowTamperDemo(true)}>Tamper demo</button>
        </div>
      </div>

      <div className="status-grid">
        <StatusBlock label="Chain integrity" value="Continuous" tone="good" />
        <StatusBlock label="Tree size" value={String(electionDemo.root.treeSize)} tone="neutral" />
        <StatusBlock label="Inclusion proof" value={verification.valid ? 'Verified' : 'Rejected'} tone={statusTone} />
      </div>

      <div className="election-layout">
        <div className="timeline">
          {electionDemo.timeline.map((item) => (
            <article className="timeline-item" key={item.eventId}>
              <span className="timeline-dot" />
              <div>
                <div className="row">
                  <strong>{item.label}</strong>
                  <span className={`privacy-pill ${item.privacyClass}`}>{item.privacyClass}</span>
                </div>
                <p>{item.type}</p>
                <code>{item.eventId}</code>
              </div>
            </article>
          ))}
        </div>

        <div className="proof-card">
          <h3>Milestone Merkle Root</h3>
          <code>{electionDemo.root.merkleRoot}</code>
          <dl>
            <dt>Milestone</dt>
            <dd>{electionDemo.milestone}</dd>
            <dt>Generated</dt>
            <dd>{electionDemo.root.generatedAt}</dd>
            <dt>Verified event</dt>
            <dd>{electionDemo.proof.eventId}</dd>
          </dl>

          <h3>Inclusion Proof</h3>
          <ol className="proof-path">
            {electionDemo.proof.auditPath.map((step) => (
              <li key={`${step.position}-${step.hash}`}>
                <span>{step.position}</span>
                <code>{step.hash.slice(0, 24)}...</code>
              </li>
            ))}
          </ol>

          <div className={`verification-banner ${statusTone}`}>
            <strong>{verification.valid ? 'Proof accepted' : 'Proof rejected'}</strong>
            <span>{verification.reason}</span>
            {showTamperDemo && <code>{electionDemo.tamperVerification.tamperedLeafHash}</code>}
          </div>
        </div>
      </div>
    </section>
  )
}

function StatusBlock({ label, value, tone }) {
  return (
    <div className={`status-block ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function CheckLine({ label, state, emptyLabel = 'Pending' }) {
  const text = state === true ? 'Yes' : state === false ? 'No' : emptyLabel
  const tone = state === true ? 'good' : state === false ? 'bad' : 'neutral'
  return (
    <div className={`check-line ${tone}`}>
      <span>{label}</span>
      <strong>{text}</strong>
    </div>
  )
}

function Badge({ label, tone }) {
  return <span className={`badge ${tone}`}>{label}</span>
}

function Panel({ title, children }) {
  return <section className="panel"><h2>{title}</h2>{children}</section>
}

function JsonPanel({ title, data, downloadName }) {
  return (
    <Panel title={title}>
      <div className="actions">
        <button disabled={!data} onClick={() => copyText(JSON.stringify(data, null, 2))}>Copy</button>
        {downloadName && <button disabled={!data} onClick={() => download(downloadName, JSON.stringify(data, null, 2))}>Download</button>}
      </div>
      <details open={Boolean(data)}><summary>Raw JSON</summary><pre>{data ? JSON.stringify(data, null, 2) : 'Not loaded yet'}</pre></details>
    </Panel>
  )
}

function Step({ number, title, text, action, onClick, disabled }) {
  return <article className="step"><span>{number}</span><h3>{title}</h3><p>{text}</p><button disabled={disabled} onClick={onClick}>{action}</button></article>
}

async function requestJson(url, options) {
  const res = await fetch(url, options)
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    throw new Error(data?.error?.message ?? `Request failed: ${res.status}`)
  }
  return data
}

function copyText(text) {
  if (!text) return
  navigator.clipboard?.writeText(text)
}

function download(name, text) {
  const blob = new Blob([text], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

function fileToBase64(file) {
  return file.arrayBuffer().then((buffer) => bytesToBase64(new Uint8Array(buffer)))
}

function bytesToBase64(bytes) {
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary)
}
