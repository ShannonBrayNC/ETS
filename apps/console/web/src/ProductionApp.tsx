import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import {
  getArtifact,
  getArtifactProof,
  getAuthorizationContext,
  getHealthSnapshot,
  getLatestTreeHead,
  registerArtifact,
} from "./api";
import { ConnectorsPage } from "./Connectors";
import type {
  ArtifactReceipt,
  ArtifactRecord,
  GatewayAuthorizationContext,
  HealthSnapshot,
  ProofBundle,
  TenantScope,
  TreeHead,
} from "./types";

type Route = "overview" | "evidence" | "collect" | "collect-url" | "collectors" | "admin" | "evidence-detail";
type Theme = "dark" | "light";

function routeFromPath(path: string): { name: Route; artifactId?: string } {
  const match = path.match(/^\/evidence\/([^/]+)$/);
  if (match) return { name: "evidence-detail", artifactId: decodeURIComponent(match[1]) };
  if (path === "/evidence") return { name: "evidence" };
  if (path === "/collect") return { name: "collect" };
  if (path === "/collect/url") return { name: "collect-url" };
  if (path === "/collectors") return { name: "collectors" };
  if (path === "/admin") return { name: "admin" };
  return { name: "overview" };
}

export function ProductionApp() {
  const [route, setRoute] = useState(() => routeFromPath(window.location.pathname));
  const [auth, setAuth] = useState<GatewayAuthorizationContext | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthSnapshot | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>(() => window.localStorage.getItem("ets-console-theme") === "light" ? "light" : "dark");

  useEffect(() => {
    const onPop = () => setRoute(routeFromPath(window.location.pathname));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("ets-console-theme", theme);
  }, [theme]);
  useEffect(() => {
    getAuthorizationContext().then(setAuth).catch((reason: unknown) => setAuthError(messageOf(reason, "Authorization context unavailable")));
    getHealthSnapshot().then(setHealth).catch((reason: unknown) => setHealthError(messageOf(reason, "Health query failed")));
  }, []);

  const navigate = (path: string) => {
    window.history.pushState({}, "", path);
    setRoute(routeFromPath(path));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (authError) return <AuthBoundary title="Authorization required" detail={authError} />;
  if (!auth) return <AuthBoundary title="Loading authorization context…" detail="Resolving server-authorized identity, scope, roles, and capabilities." />;

  const scope: TenantScope = { tenantId: auth.tenant_id, workspaceId: auth.workspace_id };
  const canCreate = auth.capabilities.includes("evidence.create");
  const canManageConnectors = auth.capabilities.includes("connector.manage");
  const canReadConnectors = auth.capabilities.includes("connector.read") || canManageConnectors;
  const canAdmin = auth.capabilities.includes("admin.read");

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="brand"><span className="brand-mark" aria-hidden="true">E</span><div><strong>ETS Console</strong><small>Evidence Transparency System</small></div></div>
      <nav>
        <Nav active={route.name === "overview"} onClick={() => navigate("/")}>Overview</Nav>
        <Nav active={route.name === "evidence" || route.name === "evidence-detail"} onClick={() => navigate("/evidence")}>Evidence</Nav>
        {canCreate && <Nav active={route.name === "collect" || route.name === "collect-url"} onClick={() => navigate("/collect")}>Collect</Nav>}
        {canReadConnectors && <Nav active={route.name === "collectors"} onClick={() => navigate("/collectors")}>Connectors</Nav>}
        {canAdmin && <Nav active={route.name === "admin"} onClick={() => navigate("/admin")}>Administration</Nav>}
      </nav>
      <div className="sidebar-footer"><Status label="Service" value={health?.health ?? "checking"} good={health?.health === "ok"} /><Status label="Ready" value={health ? String(health.ready) : "checking"} good={health?.ready === true} /><div className="version">Version {health?.version ?? "…"}</div></div>
    </aside>

    <div className="content-shell">
      <header className="topbar">
        <div className="scope-context" aria-label="Server-authorized ETS scope"><div><span>Tenant</span><strong>{auth.tenant_id}</strong></div><div><span>Workspace</span><strong>{auth.workspace_id}</strong></div><div className="scope-lock"><span aria-hidden="true">◆</span> Server authorized</div></div>
        <div className="topbar-actions"><button className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "Light" : "Dark"}</button><div className="operator"><span>{auth.roles.join(", ") || "authenticated"}</span><strong>{auth.subject}</strong></div></div>
      </header>

      <main id="main-content" tabIndex={-1}>
        {healthError && <Alert tone="warning">Service diagnostics unavailable: {healthError}</Alert>}
        {auth.authorization_profile === "local_nonproduction" && route.name !== "collectors" && <Alert tone="warning">Local non-production authorization is active. Do not treat this mode as production identity assurance.</Alert>}
        {route.name === "overview" && <Overview health={health} scope={scope} navigate={navigate} />}
        {route.name === "evidence" && <EvidenceIndex navigate={navigate} />}
        {route.name === "collect" && (canCreate ? <Collect scope={scope} actorId={auth.subject} navigate={navigate} /> : <Denied capability="evidence.create" />)}
        {route.name === "collect-url" && (canCreate ? <UrlPlaceholder /> : <Denied capability="evidence.create" />)}
        {route.name === "collectors" && (canReadConnectors ? <ConnectorsPage auth={auth} /> : <Denied capability="connector.read" />)}
        {route.name === "admin" && (canAdmin ? <Administration auth={auth} /> : <Denied capability="admin.read" />)}
        {route.name === "evidence-detail" && route.artifactId && <EvidenceDetail scope={scope} artifactId={route.artifactId} />}
      </main>
    </div>
  </div>;
}

function AuthBoundary({ title, detail }: { title: string; detail: string }) {
  return <main className="auth-failure-shell"><section className="panel auth-failure-panel"><span className="eyebrow">ETS Console</span><h1>{title}</h1><p>The production Console relies on authenticated server identity and scope. Browser-supplied scope is not a production trust source.</p><div className="alert danger" role="alert">{detail}</div></section></main>;
}

function Nav({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button className={active ? "nav-button active" : "nav-button"} onClick={onClick} aria-current={active ? "page" : undefined}>{children}</button>;
}

function Overview({ health, scope, navigate }: { health: HealthSnapshot | null; scope: TenantScope; navigate: (path: string) => void }) {
  const [head, setHead] = useState<TreeHead | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getLatestTreeHead(scope).then(setHead).catch((reason: unknown) => setError(messageOf(reason, "Tree head unavailable"))); }, [scope.tenantId, scope.workspaceId]);
  return <section><Header eyebrow="Production operator surface" title="Overview" description="Service availability, source observation, and cryptographic verification remain distinct states." />
    <div className="metric-grid"><Metric label="Service health" value={health?.health ?? "checking"} detail="Runtime availability" /><Metric label="Evidence service ready" value={health ? (health.ready ? "yes" : "no") : "checking"} detail="Readiness endpoint" /><Metric label="Tree size" value={String(head?.tree_size ?? "—")} detail="Latest transparency-log head" /><Metric label="Workspace" value={scope.workspaceId} detail={scope.tenantId} /></div>
    {error && <Alert tone="warning">{error}</Alert>}
    <div className="panel-grid"><article className="panel"><h2>Collect evidence</h2><p>Register bytes through the governed artifact API and receive a durable evidence receipt.</p><button className="primary" onClick={() => navigate("/collect")}>Collect file</button></article><article className="panel"><h2>Connector operations</h2><p>Configure Gateway-native and enterprise sources through the versioned connector management contract.</p><button className="secondary" onClick={() => navigate("/collectors")}>Open connectors</button></article></div>
  </section>;
}

function EvidenceIndex({ navigate }: { navigate: (path: string) => void }) {
  const [id, setId] = useState("");
  const submit = (event: FormEvent) => { event.preventDefault(); if (id.trim()) navigate(`/evidence/${encodeURIComponent(id.trim())}`); };
  return <section><Header eyebrow="Evidence inventory" title="Evidence" description="Open a known evidence artifact. Broader inventory filters remain a separate production slice." /><article className="panel"><form className="lookup-form" onSubmit={submit}><label htmlFor="artifact-id">Artifact ID</label><div className="input-action"><input id="artifact-id" value={id} onChange={(event) => setId(event.target.value)} placeholder="artifact_…" /><button className="primary">Open evidence</button></div></form></article></section>;
}

function Collect({ scope, actorId, navigate }: { scope: TenantScope; actorId: string; navigate: (path: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [classification, setClassification] = useState("internal");
  const [receipt, setReceipt] = useState<ArtifactReceipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!file) return; setBusy(true); setError(null);
    try { setReceipt(await registerArtifact(scope, actorId, file, { classification })); }
    catch (reason) { setError(messageOf(reason, "Artifact registration failed")); }
    finally { setBusy(false); }
  };
  return <section><Header eyebrow="Evidence collection" title="Collect file" description="ETS hashes submitted bytes, records governed metadata, appends an evidence event, and returns a receipt. Registration does not establish semantic truth." />
    <article className="panel collect-panel"><form onSubmit={submit}><div className="form-grid"><label>Classification<select value={classification} onChange={(event) => setClassification(event.target.value)}><option value="public">Public</option><option value="internal">Internal</option><option value="confidential">Confidential</option></select></label><label>Source system<input value="ets-console" readOnly /></label></div><label className="drop-zone"><strong>{file?.name ?? "Choose evidence file"}</strong><span>{file ? `${file.size.toLocaleString()} bytes` : "Select a file to register with ETS"}</span><input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label><button className="primary" disabled={!file || busy}>{busy ? "Collecting…" : "Collect evidence"}</button></form></article>
    {error && <Alert tone="danger">Collection failed: {error}</Alert>}
    {receipt && <article className="panel receipt" aria-live="polite"><h2>Evidence registered</h2><Definition rows={[["Artifact ID", receipt.artifact_id], ["SHA-256", receipt.artifact_hash], ["Event ID", receipt.event_id], ["Log index", String(receipt.block_number)], ["Timestamp", receipt.timestamp_utc]]} /><button className="primary" onClick={() => navigate(`/evidence/${encodeURIComponent(receipt.artifact_id)}`)}>View evidence</button></article>}
  </section>;
}

function EvidenceDetail({ scope, artifactId }: { scope: TenantScope; artifactId: string }) {
  const [artifact, setArtifact] = useState<ArtifactRecord | null>(null);
  const [proof, setProof] = useState<ProofBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [advanced, setAdvanced] = useState(false);
  useEffect(() => {
    setArtifact(null); setProof(null); setError(null);
    getArtifact(scope, artifactId).then(setArtifact).catch((reason: unknown) => setError(messageOf(reason, "Evidence lookup failed")));
    getArtifactProof(scope, artifactId).then(setProof).catch(() => setProof(null));
  }, [scope.tenantId, scope.workspaceId, artifactId]);
  const exportProof = () => { if (!proof) return; const url = URL.createObjectURL(new Blob([JSON.stringify(proof, null, 2)], { type: "application/json" })); const link = document.createElement("a"); link.href = url; link.download = `${artifactId}-ets-proof.json`; link.click(); URL.revokeObjectURL(url); };
  if (error) return <section><Header eyebrow="Evidence detail" title={artifactId} description="Evidence could not be loaded." /><Alert tone="danger">{error}</Alert></section>;
  if (!artifact) return <section><Header eyebrow="Evidence detail" title={artifactId} description="Loading evidence and proof material…" /></section>;
  return <section><Header eyebrow="Evidence detail" title={artifact.artifact_id} description="Cryptographic and provenance properties are shown separately from semantic claims about artifact contents." />
    <div className="integrity-banner"><strong>Artifact registered</strong><p>Registration confirms ETS received and hashed submitted bytes. Proof availability and verification are separate checks.</p></div>
    <div className="panel-grid"><article className="panel"><h2>Artifact</h2><Definition rows={[["SHA-256", artifact.artifact_hash], ["Content type", artifact.content_type], ["Byte size", artifact.byte_size.toLocaleString()], ["Reference", artifact.reference_uri], ["Ingested", artifact.ingestion_timestamp_utc]]} /></article><article className="panel"><h2>Transparency log</h2><Definition rows={[["Event ID", artifact.event_id], ["Log index", String(artifact.log_index)], ["Proof", proof ? "available" : "unavailable"]]} />{proof && <button className="primary" onClick={exportProof}>Export proof JSON</button>}</article></div>
    <article className="panel"><div className="panel-heading-row"><h2>Metadata</h2><button className="text-button" onClick={() => setAdvanced(!advanced)}>{advanced ? "Hide advanced" : "Show advanced protocol data"}</button></div><pre className="json-view">{JSON.stringify(artifact.metadata, null, 2)}</pre>{advanced && <div className="advanced-block"><h3>Artifact record</h3><pre className="json-view">{JSON.stringify(artifact, null, 2)}</pre><h3>Proof bundle</h3><pre className="json-view">{proof ? JSON.stringify(proof, null, 2) : "Unavailable"}</pre></div>}</article>
    <Alert tone="info">ETS verification concerns declared cryptographic properties of evidence and proof material. It does not establish real-world truth, observation completeness, legal admissibility, or regulatory compliance.</Alert>
  </section>;
}

function Administration({ auth }: { auth: GatewayAuthorizationContext }) {
  const capabilities = useMemo(() => auth.capabilities.join(", ") || "None", [auth.capabilities]);
  return <section><Header eyebrow="Administrative boundary" title="Administration" description="Identity, scope, roles, and capabilities come from the authenticated server context." /><article className="panel"><Definition rows={[["Subject", auth.subject], ["Tenant", auth.tenant_id], ["Workspace", auth.workspace_id], ["Roles", auth.roles.join(", ") || "None"], ["Capabilities", capabilities], ["Authorization profile", auth.authorization_profile], ["Signing keys", "server-side only"]]} /></article></section>;
}

function UrlPlaceholder() { return <section><Header eyebrow="P2 · Web Collector" title="Capture public URL" description="This route remains unavailable until the governed asynchronous Web Collector API qualifies." /><article className="panel"><label>Public URL<input disabled placeholder="https://example.org/evidence" /></label><button className="primary" disabled>Submit collection job</button></article></section>; }
function Denied({ capability }: { capability: string }) { return <section><Header eyebrow="Authorization boundary" title="Access denied" description={`The authenticated server context does not grant ${capability}.`} /><Alert tone="danger">This route is unavailable for the current role and capability set.</Alert></section>; }
function Header({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <header className="page-header"><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></header>; }
function Metric({ label, value, detail }: { label: string; value: string; detail: string }) { return <article className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>; }
function Definition({ rows }: { rows: Array<[string, string]> }) { return <dl className="definition-list">{rows.map(([term, value]) => <div key={term}><dt>{term}</dt><dd>{value}</dd></div>)}</dl>; }
function Alert({ tone, children }: { tone: "info" | "warning" | "danger"; children: ReactNode }) { return <div className={`alert ${tone}`} role={tone === "danger" ? "alert" : "status"}>{children}</div>; }
function Status({ label, value, good }: { label: string; value: string; good: boolean }) { return <div className={`status-pill ${good ? "good" : "neutral"}`}><span>{label}</span><strong>{value}</strong></div>; }
function messageOf(reason: unknown, fallback: string) { return reason instanceof Error ? reason.message : fallback; }
