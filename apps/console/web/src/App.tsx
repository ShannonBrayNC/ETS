import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  getArtifact,
  getArtifactProof,
  getHealthSnapshot,
  getLatestTreeHead,
  registerArtifact,
} from "./api";
import type {
  ArtifactReceipt,
  ArtifactRecord,
  HealthSnapshot,
  ProofBundle,
  TenantScope,
  TreeHead,
} from "./types";

type Route =
  | { name: "overview" }
  | { name: "evidence" }
  | { name: "collect" }
  | { name: "collect-url" }
  | { name: "collectors" }
  | { name: "admin" }
  | { name: "evidence-detail"; artifactId: string };

const defaultScope: TenantScope = {
  tenantId: "tenant_demo",
  workspaceId: "workspace_alpha",
};

function parseRoute(pathname: string): Route {
  const match = pathname.match(/^\/evidence\/([^/]+)$/);
  if (match) return { name: "evidence-detail", artifactId: decodeURIComponent(match[1]) };
  if (pathname === "/evidence") return { name: "evidence" };
  if (pathname === "/collect/url") return { name: "collect-url" };
  if (pathname === "/collect") return { name: "collect" };
  if (pathname === "/collectors") return { name: "collectors" };
  if (pathname === "/admin") return { name: "admin" };
  return { name: "overview" };
}

function useRoute(): [Route, (path: string) => void] {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setRoute(parseRoute(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = (path: string) => {
    window.history.pushState({}, "", path);
    setRoute(parseRoute(path));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return [route, navigate];
}

export function App() {
  const [route, navigate] = useRoute();
  const [scope, setScope] = useState<TenantScope>(defaultScope);
  const [health, setHealth] = useState<HealthSnapshot | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    getHealthSnapshot()
      .then(setHealth)
      .catch((error: unknown) => setHealthError(error instanceof Error ? error.message : "Health query failed"));
  }, []);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">E</span>
          <div>
            <strong>ETS Console</strong>
            <small>Evidence Transparency System</small>
          </div>
        </div>
        <nav>
          <NavButton active={route.name === "overview"} onClick={() => navigate("/")}>Overview</NavButton>
          <NavButton active={route.name === "evidence" || route.name === "evidence-detail"} onClick={() => navigate("/evidence")}>Evidence</NavButton>
          <NavButton active={route.name === "collect" || route.name === "collect-url"} onClick={() => navigate("/collect")}>Collect</NavButton>
          <NavButton active={route.name === "collectors"} onClick={() => navigate("/collectors")}>Collectors</NavButton>
          <NavButton active={route.name === "admin"} onClick={() => navigate("/admin")}>Administration</NavButton>
        </nav>
        <div className="sidebar-footer">
          <StatusPill label="Service" state={health?.health === "ok" ? "good" : "neutral"} value={health?.health ?? "checking"} />
          <StatusPill label="Ready" state={health?.ready ? "good" : "neutral"} value={health ? String(health.ready) : "checking"} />
          <div className="version">Version {health?.version ?? "…"}</div>
        </div>
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <ScopeEditor scope={scope} onChange={setScope} />
          <div className="operator">Operator <strong>console-user</strong></div>
        </header>

        <main id="main-content" tabIndex={-1}>
          {healthError && <InlineAlert tone="warning">Service diagnostics unavailable: {healthError}</InlineAlert>}
          {route.name === "overview" && <Overview health={health} scope={scope} navigate={navigate} />}
          {route.name === "evidence" && <EvidenceIndex navigate={navigate} />}
          {route.name === "collect" && <CollectFile scope={scope} navigate={navigate} />}
          {route.name === "collect-url" && <UrlCollectorPlaceholder />}
          {route.name === "collectors" && <CollectorsPlaceholder navigate={navigate} />}
          {route.name === "admin" && <AdminPlaceholder scope={scope} />}
          {route.name === "evidence-detail" && (
            <EvidenceDetail scope={scope} artifactId={route.artifactId} />
          )}
        </main>
      </div>
    </div>
  );
}

function NavButton({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return (
    <button className={active ? "nav-button active" : "nav-button"} onClick={onClick} aria-current={active ? "page" : undefined}>
      {children}
    </button>
  );
}

function ScopeEditor({ scope, onChange }: { scope: TenantScope; onChange: (scope: TenantScope) => void }) {
  return (
    <div className="scope-editor" aria-label="Current ETS scope">
      <label>
        Tenant
        <input value={scope.tenantId} onChange={(event) => onChange({ ...scope, tenantId: event.target.value })} />
      </label>
      <label>
        Workspace
        <input value={scope.workspaceId} onChange={(event) => onChange({ ...scope, workspaceId: event.target.value })} />
      </label>
    </div>
  );
}

function Overview({ health, scope, navigate }: { health: HealthSnapshot | null; scope: TenantScope; navigate: (path: string) => void }) {
  const [treeHead, setTreeHead] = useState<TreeHead | null>(null);
  const [treeError, setTreeError] = useState<string | null>(null);

  useEffect(() => {
    getLatestTreeHead(scope)
      .then(setTreeHead)
      .catch((error: unknown) => setTreeError(error instanceof Error ? error.message : "Tree head unavailable"));
  }, [scope]);

  return (
    <section>
      <PageHeader eyebrow="Production operator surface" title="Overview" description="Service health and evidence integrity are shown separately. A healthy node does not imply that every evidence item is verified." />
      <div className="metric-grid">
        <Metric title="Service health" value={health?.health ?? "checking"} detail="Runtime availability" />
        <Metric title="Evidence service ready" value={health ? (health.ready ? "yes" : "no") : "checking"} detail="Readiness endpoint" />
        <Metric title="Tree size" value={String(treeHead?.tree_size ?? "—")} detail="Latest signed/log head" />
        <Metric title="Workspace" value={scope.workspaceId} detail={scope.tenantId} />
      </div>
      {treeError && <InlineAlert tone="warning">Latest tree head could not be read: {treeError}</InlineAlert>}
      <div className="panel-grid">
        <article className="panel">
          <h2>Start collecting evidence</h2>
          <p>Register source bytes through the governed ETS artifact API and receive a proof receipt immediately.</p>
          <button className="primary" onClick={() => navigate("/collect")}>Collect file</button>
        </article>
        <article className="panel">
          <h2>Web Collector</h2>
          <p>Public URL collection is the next production slice. The Console route is reserved now so the workflow stays consistent.</p>
          <button className="secondary" onClick={() => navigate("/collect/url")}>View planned flow</button>
        </article>
      </div>
    </section>
  );
}

function EvidenceIndex({ navigate }: { navigate: (path: string) => void }) {
  const [artifactId, setArtifactId] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = artifactId.trim();
    if (trimmed) navigate(`/evidence/${encodeURIComponent(trimmed)}`);
  };

  return (
    <section>
      <PageHeader eyebrow="Evidence inventory" title="Evidence" description="Search and filter inventory APIs will follow. This first vertical slice supports direct artifact lookup and receipt navigation." />
      <article className="panel">
        <form onSubmit={submit} className="lookup-form">
          <label htmlFor="artifact-id">Artifact ID</label>
          <div className="input-action">
            <input id="artifact-id" value={artifactId} onChange={(event) => setArtifactId(event.target.value)} placeholder="artifact_…" />
            <button className="primary" type="submit">Open evidence</button>
          </div>
        </form>
      </article>
      <InlineAlert tone="info">Inventory pagination and multi-field filtering remain intentionally outside this first scaffold. Direct evidence lookup uses the production ETS artifact route.</InlineAlert>
    </section>
  );
}

function CollectFile({ scope, navigate }: { scope: TenantScope; navigate: (path: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [classification, setClassification] = useState("internal");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<ArtifactReceipt | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setReceipt(null);
    try {
      const created = await registerArtifact(scope, file, { classification });
      setReceipt(created);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Artifact registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <PageHeader eyebrow="Evidence collection" title="Collect file" description="ETS hashes the submitted bytes, records governed metadata, appends an evidence event, and returns a receipt. This workflow does not assert that the submitted content is semantically true." />
      <article className="panel collect-panel">
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Classification
              <select value={classification} onChange={(event) => setClassification(event.target.value)}>
                <option value="public">Public</option>
                <option value="internal">Internal</option>
                <option value="confidential">Confidential</option>
              </select>
            </label>
            <label>
              Source system
              <input value="ets-console" readOnly />
            </label>
          </div>
          <label className="drop-zone">
            <strong>{file ? file.name : "Choose evidence file"}</strong>
            <span>{file ? `${file.size.toLocaleString()} bytes · ${file.type || "application/octet-stream"}` : "Select a file to register with ETS"}</span>
            <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <button className="primary" type="submit" disabled={!file || busy}>{busy ? "Collecting…" : "Collect evidence"}</button>
        </form>
      </article>
      {error && <InlineAlert tone="danger">Collection failed: {error}</InlineAlert>}
      {receipt && (
        <article className="panel receipt" aria-live="polite">
          <div className="receipt-heading"><span className="verification-icon" aria-hidden="true">✓</span><div><h2>Evidence registered</h2><p>ETS returned a durable receipt for the submitted artifact.</p></div></div>
          <DefinitionList rows={[
            ["Artifact ID", receipt.artifact_id],
            ["SHA-256", receipt.artifact_hash],
            ["Event ID", receipt.event_id],
            ["Log index", String(receipt.block_number)],
            ["Timestamp", receipt.timestamp_utc],
          ]} />
          <button className="primary" onClick={() => navigate(`/evidence/${encodeURIComponent(receipt.artifact_id)}`)}>View evidence</button>
        </article>
      )}
    </section>
  );
}

function EvidenceDetail({ scope, artifactId }: { scope: TenantScope; artifactId: string }) {
  const [artifact, setArtifact] = useState<ArtifactRecord | null>(null);
  const [proof, setProof] = useState<ProofBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [proofError, setProofError] = useState<string | null>(null);
  const [advanced, setAdvanced] = useState(false);

  useEffect(() => {
    setArtifact(null);
    setProof(null);
    setError(null);
    setProofError(null);
    getArtifact(scope, artifactId)
      .then(setArtifact)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Evidence lookup failed"));
    getArtifactProof(scope, artifactId)
      .then(setProof)
      .catch((reason: unknown) => setProofError(reason instanceof Error ? reason.message : "Proof unavailable"));
  }, [scope, artifactId]);

  const exportProof = () => {
    if (!proof) return;
    const blob = new Blob([JSON.stringify(proof, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${artifactId}-ets-proof.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (error) return <section><PageHeader eyebrow="Evidence detail" title={artifactId} description="Evidence could not be loaded." /><InlineAlert tone="danger">{error}</InlineAlert></section>;
  if (!artifact) return <section><PageHeader eyebrow="Evidence detail" title={artifactId} description="Loading evidence and proof material…" /></section>;

  return (
    <section>
      <PageHeader eyebrow="Evidence detail" title={artifact.artifact_id} description="Cryptographic and provenance properties are presented separately from semantic claims about the artifact's contents." />
      <div className="integrity-banner">
        <div><span className="verification-icon" aria-hidden="true">✓</span><strong>Artifact registered</strong></div>
        <p>Registration confirms ETS received and hashed the submitted bytes. Proof availability and verification are separate checks.</p>
      </div>
      <div className="panel-grid">
        <article className="panel">
          <h2>Artifact</h2>
          <DefinitionList rows={[
            ["SHA-256", artifact.artifact_hash],
            ["Content type", artifact.content_type],
            ["Byte size", artifact.byte_size.toLocaleString()],
            ["Reference", artifact.reference_uri],
            ["Ingested", artifact.ingestion_timestamp_utc],
          ]} />
        </article>
        <article className="panel">
          <h2>Transparency log</h2>
          <DefinitionList rows={[
            ["Event ID", artifact.event_id],
            ["Log index", String(artifact.log_index)],
            ["Proof", proof ? "available" : proofError ? "unavailable" : "loading"],
          ]} />
          {proof && <button className="primary" onClick={exportProof}>Export proof JSON</button>}
          {proofError && <p className="field-error">{proofError}</p>}
        </article>
      </div>
      <article className="panel">
        <div className="panel-heading-row"><h2>Metadata</h2><button className="text-button" onClick={() => setAdvanced((value) => !value)}>{advanced ? "Hide advanced" : "Show advanced protocol data"}</button></div>
        <pre className="json-view">{JSON.stringify(artifact.metadata, null, 2)}</pre>
        {advanced && (
          <div className="advanced-block">
            <h3>Artifact record</h3>
            <pre className="json-view">{JSON.stringify(artifact, null, 2)}</pre>
            <h3>Proof bundle</h3>
            <pre className="json-view">{proof ? JSON.stringify(proof, null, 2) : proofError ?? "Loading…"}</pre>
          </div>
        )}
      </article>
      <InlineAlert tone="info">ETS verification concerns declared cryptographic properties of submitted evidence and proof material. It does not independently establish real-world truth, observation completeness, legal admissibility, or regulatory compliance.</InlineAlert>
    </section>
  );
}

function UrlCollectorPlaceholder() {
  return (
    <section>
      <PageHeader eyebrow="P2 · Web Collector" title="Capture public URL" description="This route is reserved for the asynchronous governed web collector in issue #210." />
      <article className="panel">
        <label>Public URL<input placeholder="https://example.org/evidence" disabled /></label>
        <p className="muted">The production collector will return a durable job ID and capture policy-approved response, screenshot, text, hashes, and provenance through isolated workers.</p>
        <button className="primary" disabled>Submit collection job</button>
      </article>
    </section>
  );
}

function CollectorsPlaceholder({ navigate }: { navigate: (path: string) => void }) {
  return (
    <section>
      <PageHeader eyebrow="Collection operations" title="Collectors" description="Collector health and queue state will arrive with the Web Collector runtime." />
      <article className="panel">
        <h2>Public Web Collector</h2>
        <p>Status: not installed in P1.</p>
        <button className="secondary" onClick={() => navigate("/collect/url")}>View collection route</button>
      </article>
    </section>
  );
}

function AdminPlaceholder({ scope }: { scope: TenantScope }) {
  return (
    <section>
      <PageHeader eyebrow="Administrative boundary" title="Administration" description="P1 exposes scope context only. Trust-changing controls will be added behind explicit role and audit boundaries." />
      <article className="panel">
        <DefinitionList rows={[["Tenant", scope.tenantId], ["Workspace", scope.workspaceId], ["Role", "operator (development placeholder)"], ["Signing keys", "server-side only"]]} />
      </article>
    </section>
  );
}

function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="page-header"><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></header>;
}

function Metric({ title, value, detail }: { title: string; value: string; detail: string }) {
  return <article className="metric"><span>{title}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function DefinitionList({ rows }: { rows: Array<[string, string]> }) {
  return <dl className="definition-list">{rows.map(([term, value]) => <div key={term}><dt>{term}</dt><dd>{value}</dd></div>)}</dl>;
}

function InlineAlert({ tone, children }: { tone: "info" | "warning" | "danger"; children: string }) {
  return <div className={`alert ${tone}`} role={tone === "danger" ? "alert" : "status"}>{children}</div>;
}

function StatusPill({ label, state, value }: { label: string; state: "good" | "neutral"; value: string }) {
  return <div className={`status-pill ${state}`}><span>{label}</span><strong>{value}</strong></div>;
}
