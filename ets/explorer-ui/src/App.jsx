import { useEffect, useState } from 'react'

const API = 'http://localhost:8000'

export default function App() {
  const [tree, setTree] = useState(null)
  const [eventId, setEventId] = useState('')
  const [proof, setProof] = useState(null)

  async function loadTree() {
    const res = await fetch(`${API}/tree-head`)
    const data = await res.json()
    setTree(data)
  }

  async function loadProof() {
    if (!eventId) return
    const res = await fetch(`${API}/proof/${eventId}`)
    const data = await res.json()
    setProof(data)
  }

  useEffect(() => {
    loadTree()
  }, [])

  return (
    <div style={{ padding: 20, fontFamily: 'Arial' }}>
      <h1>ETS Dashboard</h1>

      <section>
        <h2>Tree Head</h2>
        <pre>{JSON.stringify(tree, null, 2)}</pre>
      </section>

      <section>
        <h2>Verify Event</h2>
        <input value={eventId} onChange={(e) => setEventId(e.target.value)} placeholder="Event ID" />
        <button onClick={loadProof}>Get Proof</button>
        <pre>{JSON.stringify(proof, null, 2)}</pre>
      </section>
    </div>
  )
}
