import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_ETS_API_BASE_URL ?? 'http://localhost:8000'

export default function App() {
  const [tree, setTree] = useState(null)
  const [events, setEvents] = useState([])
  const [eventId, setEventId] = useState('')
  const [proof, setProof] = useState(null)
  const [verification, setVerification] = useState(null)
  const [error, setError] = useState(null)

  async function loadTree() {
    setError(null)
    const data = await requestJson(`${API}/api/v1/log/head`)
    setTree(data)
  }

  async function loadEvents() {
    setError(null)
    const data = await requestJson(`${API}/api/v1/events?limit=50&offset=0`)
    setEvents(data.items)
  }

  async function loadProof() {
    if (!eventId) return
    setError(null)
    setVerification(null)
    const data = await requestJson(`${API}/api/v1/proofs/inclusion/${encodeURIComponent(eventId)}`)
    setProof(data)
  }

  async function verifyProof() {
    if (!proof) return
    setError(null)
    const data = await requestJson(`${API}/api/v1/verify/inclusion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(proof),
    })
    setVerification(data)
  }

  useEffect(() => {
    loadTree().catch((err) => setError(err.message))
    loadEvents().catch((err) => setError(err.message))
  }, [])

  return (
    <div style={{ padding: 20, fontFamily: 'Arial' }}>
      <h1>ETS Dashboard</h1>

      {error && (
        <section>
          <h2>API Error</h2>
          <pre>{error}</pre>
        </section>
      )}

      <section>
        <h2>Tree Head</h2>
        <pre>{JSON.stringify(tree, null, 2)}</pre>
      </section>

      <section>
        <h2>Events</h2>
        <button onClick={() => loadEvents().catch((err) => setError(err.message))}>Refresh</button>
        <table>
          <thead>
            <tr>
              <th>Index</th>
              <th>Event ID</th>
              <th>Type</th>
              <th>Hash</th>
            </tr>
          </thead>
          <tbody>
            {events.map((entry) => (
              <tr key={entry.event.event_id}>
                <td>{entry.log_index}</td>
                <td>
                  <button
                    onClick={() => {
                      setEventId(entry.event.event_id)
                      setProof(null)
                      setVerification(null)
                    }}
                  >
                    {entry.event.event_id}
                  </button>
                </td>
                <td>{entry.event.event_type}</td>
                <td>{entry.event_hash}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Verify Event</h2>
        <input value={eventId} onChange={(e) => setEventId(e.target.value)} placeholder="Event ID" />
        <button onClick={() => loadProof().catch((err) => setError(err.message))}>Get Proof</button>
        <button onClick={() => verifyProof().catch((err) => setError(err.message))} disabled={!proof}>
          Verify Proof
        </button>
        <pre>{JSON.stringify(proof, null, 2)}</pre>
        <pre>{JSON.stringify(verification, null, 2)}</pre>
      </section>
    </div>
  )
}

async function requestJson(url, options) {
  const res = await fetch(url, options)
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data?.error?.message ?? `Request failed: ${res.status}`)
  }
  return data
}
