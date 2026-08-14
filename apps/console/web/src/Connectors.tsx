import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createConnectorInstance,
  getConnectorCatalog,
  getConnectorInstances,
  getConnectorRuntime,
  markConnectorGap,
  reconcileConnectorGap,
  setConnectorEnabled,
  testConnectorConnection,
  updateConnectorInstance,
  validateConnectorInstance,
} from "./api";
import type {
  ConnectorDefinition,
  ConnectorHealth,
  ConnectorInstance,
  ConnectorInstanceRecord,
  ConnectorRuntimeState,
  ConnectorSettingField,
  GatewayAuthorizationContext,
  JsonValue,
} from "./types";

type DraftSettings = Record<string, string>;
type CheckpointStrategy = "none" | "source_cursor" | "time_window" | "source_sequence";

interface Draft {
  connectorId: string;
  instanceId: string;
  sourceName: string;
  environment: string;
  credentialRef: string;
  deliveryMode: "push" | "poll";
  intervalSeconds: string;
  batchSize: string;
  checkpointStrategy: CheckpointStrategy;
  captureProfile: string;
  normalizationProfile: string;
  settings: DraftSettings;
}

interface Wizard {
  step: number;
  mode: "create" | "edit";
  record: ConnectorInstanceRecord | null;
  draft: Draft;
  validation: ConnectorHealth | null;
  busy: boolean;
  error: string | null;
  confirmActivation: boolean;
}

const steps = ["Connection", "Scope", "Evidence policy", "Collection", "Test", "Activate"];

const settingFields: Record<string, ConnectorSettingField[]> = {
  "native.syslog": [
    { key: "bind_host", label: "Bind host", type: "text" },
    { key: "bind_port", label: "TLS port", type: "number", min: 1, max: 65535 },
    { key: "max_connections", label: "Max connections", type: "number", min: 1, max: 10000 },
    { key: "max_message_bytes", label: "Max message bytes", type: "number", min: 1, max: 1048576 },
    { key: "read_idle_timeout_seconds", label: "Read idle timeout (seconds)", type: "number", min: 0.1, max: 3600, step: 0.1 },
  ],
  "native.webhook": [
    { key: "bind_host", label: "Bind host", type: "text" },
    { key: "bind_port", label: "HTTPS port", type: "number", min: 1, max: 65535 },
    { key: "max_body_bytes", label: "Max body bytes", type: "number", min: 1, max: 67108864 },
    { key: "max_concurrency", label: "Max concurrency", type: "number", min: 1, max: 10000 },
    { key: "request_timeout_seconds", label: "Request timeout (seconds)", type: "number", min: 0.1, max: 300, step: 0.1 },
  ],
  "native.otlp": [
    { key: "bind_host", label: "Bind host", type: "text" },
    { key: "http_port", label: "OTLP/HTTP port", type: "number", min: 1, max: 65535 },
    { key: "grpc_port", label: "OTLP/gRPC port", type: "number", min: 1, max: 65535 },
    { key: "max_request_bytes", label: "Max request bytes", type: "number", min: 1, max: 67108864 },
    { key: "max_concurrency", label: "Max concurrency", type: "number", min: 1, max: 10000 },
    { key: "processing_timeout_seconds", label: "Processing timeout (seconds)", type: "number", min: 0.1, max: 300, step: 0.1 },
  ],
  "native.file_drop": [
    { key: "intake_root", label: "Intake root", type: "text" },
    { key: "max_concurrent_submissions", label: "Max concurrent submissions", type: "number", min: 1, max: 10000 },
    { key: "max_object_bytes", label: "Max object bytes", type: "number", min: 1, max: 1099511627776 },
    { key: "read_chunk_bytes", label: "Read chunk bytes", type: "number", min: 1, max: 16777216 },
    { key: "graceful_shutdown_seconds", label: "Graceful shutdown (seconds)", type: "number", min: 0.1, max: 3600, step: 0.1 },
  ],
  "github.audit": [
    { key: "organization", label: "GitHub organization", type: "text", required: true },
    { key: "api_version", label: "GitHub API version", type: "text" },
    { key: "include", label: "Audit scope", type: "select", options: ["all", "web", "git"] },
    { key: "request_timeout_seconds", label: "Request timeout (seconds)", type: "number", min: 0.1, max: 60, step: 0.1 },
  ],
};

const defaults: Record<string, DraftSettings> = {
  "native.syslog": { bind_host: "0.0.0.0", bind_port: "6514", max_connections: "128", max_message_bytes: "65536", read_idle_timeout_seconds: "30" },
  "native.webhook": { bind_host: "0.0.0.0", bind_port: "8443", max_body_bytes: "1048576", max_concurrency: "64", request_timeout_seconds: "30" },
  "native.otlp": { bind_host: "0.0.0.0", http_port: "4318", grpc_port: "4317", max_request_bytes: "4194304", max_concurrency: "64", processing_timeout_seconds: "10" },
  "native.file_drop": { intake_root: "/var/lib/ets/drop", max_concurrent_submissions: "32", max_object_bytes: "1073741824", read_chunk_bytes: "1048576", graceful_shutdown_seconds: "30" },
  "github.audit": { organization: "", api_version: "2022-11-28", include: "all", request_timeout_seconds: "30" },
};

export function ConnectorsPage({ auth }: { auth: GatewayAuthorizationContext }) {
  const [catalog, setCatalog] = useState<ConnectorDefinition[]>([]);
  const [instances, setInstances] = useState<ConnectorInstanceRecord[]>([]);
  const [runtime, setRuntime] = useState<Record<string, ConnectorRuntimeState>>({});
  const [health, setHealth] = useState<Record<string, ConnectorHealth>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [wizard, setWizard] = useState<Wizard | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [definitions, records] = await Promise.all([getConnectorCatalog(), getConnectorInstances()]);
      setCatalog(definitions);
      setInstances(records);
      const states = await Promise.all(records.map(async (record) => {
        try {
          return [record.instance.instance_id, await getConnectorRuntime(record.instance.instance_id)] as const;
        } catch {
          return null;
        }
      }));
      setRuntime(Object.fromEntries(states.filter((item) => item !== null)) as Record<string, ConnectorRuntimeState>);
    } catch (reason) {
      setError(messageOf(reason, "Connector management data is unavailable"));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const summary = useMemo(() => {
    const states = Object.values(runtime);
    return {
      configured: instances.length,
      enabled: instances.filter((item) => item.instance.enabled).length,
      gaps: states.filter((item) => item.gap_open).length,
      attention: states.filter((item) => item.observation_state !== "healthy_observation").length,
    };
  }, [instances, runtime]);

  const selectedRecord = instances.find((item) => item.instance.instance_id === selected) ?? null;
  const selectedRuntime = selectedRecord ? runtime[selectedRecord.instance.instance_id] : undefined;
  const selectedHealth = selectedRecord ? health[selectedRecord.instance.instance_id] : undefined;

  const testConnection = async (record: ConnectorInstanceRecord) => {
    setError(null);
    try {
      const result = await testConnectorConnection(record.instance.instance_id);
      setHealth((current) => ({ ...current, [record.instance.instance_id]: result }));
    } catch (reason) {
      setError(messageOf(reason, "Connection test failed"));
    }
  };

  const toggle = async (record: ConnectorInstanceRecord) => {
    const enabled = !record.instance.enabled;
    if (!window.confirm(`Confirm ${enabled ? "activation" : "disable"} for ${record.instance.instance_id}?`)) return;
    try {
      const next = await setConnectorEnabled(record, enabled);
      setInstances((current) => current.map((item) => item.instance.instance_id === next.instance.instance_id ? next : item));
    } catch (reason) {
      setError(messageOf(reason, "Connector state change failed"));
    }
  };

  const changeGap = async (record: ConnectorInstanceRecord, reconcile: boolean) => {
    if (!reconcile && !window.confirm(`Record a known collection gap for ${record.instance.instance_id}?`)) return;
    try {
      const next = reconcile
        ? await reconcileConnectorGap(record.instance.instance_id)
        : await markConnectorGap(record.instance.instance_id);
      setRuntime((current) => ({ ...current, [record.instance.instance_id]: next }));
    } catch (reason) {
      setError(messageOf(reason, "Gap operation failed"));
    }
  };

  const onSaved = (record: ConnectorInstanceRecord) => {
    setInstances((current) => {
      const found = current.some((item) => item.instance.instance_id === record.instance.instance_id);
      return found
        ? current.map((item) => item.instance.instance_id === record.instance.instance_id ? record : item)
        : [...current, record];
    });
    setWizard(null);
    setSelected(record.instance.instance_id);
    void refresh();
  };

  return (
    <section className="connectors-page">
      <header className="page-header connector-header">
        <div>
          <span>Settings · Connectors</span>
          <h1>Connector operations</h1>
          <p>Source observation, Gateway health, ETS commitment, and cryptographic verification are separate states. No opaque trust score is used.</p>
        </div>
        <button className="primary" disabled={catalog.length === 0} onClick={() => catalog[0] && setWizard(createWizard(catalog[0]))}>Add connector</button>
      </header>

      {auth.authorization_profile === "local_nonproduction" && (
        <div className="alert warning" role="status">Local non-production authorization is active. Production identity and scope must be server-derived.</div>
      )}
      {error && <div className="alert danger" role="alert">{error}</div>}

      <div className="metric-grid">
        <Metric label="Configured" value={summary.configured} detail="Connector instances" />
        <Metric label="Enabled" value={summary.enabled} detail="Collection configured on" />
        <Metric label="Known gaps" value={summary.gaps} detail="Explicit continuity gaps" />
        <Metric label="Needs attention" value={summary.attention} detail="Degraded or unknown" />
      </div>

      <div className="connector-section-heading"><div><span>Executive summary</span><h2>Source posture</h2></div><button className="secondary compact" onClick={() => void refresh()} disabled={busy}>{busy ? "Refreshing…" : "Refresh"}</button></div>

      <div className="connector-table-wrap">
        <table className="connector-table">
          <thead><tr><th>Connector</th><th>Source</th><th>Enabled</th><th>Observation</th><th>Gap</th><th>Last success</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>
            {instances.map((record) => {
              const state = runtime[record.instance.instance_id];
              const definition = catalog.find((item) => item.connector_id === record.instance.connector_id);
              return <tr key={record.instance.instance_id}>
                <td><button className="table-link" onClick={() => setSelected(record.instance.instance_id)}>{definition?.display_name ?? record.instance.connector_id}</button><small>{record.instance.instance_id}</small></td>
                <td>{record.instance.source.name}<small>{record.instance.source.environment}</small></td>
                <td><Badge tone={record.instance.enabled ? "good" : "neutral"} label={record.instance.enabled ? "Enabled" : "Disabled"} /></td>
                <td><Observation state={state} /></td>
                <td><Badge tone={state?.gap_open ? "danger" : "good"} label={state?.gap_open ? "Known gap" : "No open gap"} /></td>
                <td>{formatTime(state?.last_success_at_utc)}</td>
                <td><button className="secondary compact" onClick={() => setSelected(record.instance.instance_id)}>Inspect</button></td>
              </tr>;
            })}
          </tbody>
        </table>
        {!busy && instances.length === 0 && <div className="empty-state">No connector instances are configured for this server-authorized scope.</div>}
      </div>

      <div className="connector-section-heading"><div><span>Catalog</span><h2>Available integrations</h2></div></div>
      <div className="connector-catalog-grid">
        {catalog.map((definition) => {
          const supported = Boolean(settingFields[definition.connector_id]);
          return <article className="connector-card" key={definition.connector_id}>
            <div className="connector-card-topline"><span>{formatClass(definition.implementation_class)}</span><span>v{definition.adapter_version}</span></div>
            <h3>{definition.display_name}</h3><p>{definition.description}</p>
            <div className="tag-row">{definition.capabilities.delivery_modes.map((mode) => <span key={mode}>{mode}</span>)}{definition.source_classes.slice(0, 3).map((source) => <span key={source}>{source}</span>)}</div>
            <button className="secondary" disabled={!supported} onClick={() => supported && setWizard(createWizard(definition))}>{supported ? "Configure" : "UX profile pending"}</button>
          </article>;
        })}
      </div>

      {selectedRecord && <aside className="connector-drawer" aria-label="Connector details">
        <div className="drawer-header"><div><span>Connector instance</span><h2>{selectedRecord.instance.source.name}</h2></div><button className="icon-button" aria-label="Close connector details" onClick={() => setSelected(null)}>×</button></div>
        <dl className="detail-list">
          <div><dt>Instance</dt><dd>{selectedRecord.instance.instance_id}</dd></div>
          <div><dt>Type</dt><dd>{selectedRecord.instance.connector_id}</dd></div>
          <div><dt>Scope</dt><dd>{auth.tenant_id} / {auth.workspace_id}</dd></div>
          <div><dt>Credential reference</dt><dd>{selectedRecord.instance.authentication.credential_ref ?? "Not required"}</dd></div>
          <div><dt>Observation</dt><dd>{humanObservation(selectedRuntime?.observation_state)}</dd></div>
          <div><dt>Connection test</dt><dd>{selectedHealth ? `${selectedHealth.state}: ${selectedHealth.message}` : "Not run in this session"}</dd></div>
        </dl>
        <p className="boundary-note">Operational health is not ETS cryptographic verification and does not establish source truth or completeness.</p>
        <div className="drawer-actions">
          <button className="secondary" onClick={() => setWizard(editWizard(selectedRecord, catalog))}>Edit configuration</button>
          <button className="secondary" onClick={() => void testConnection(selectedRecord)}>Test connection</button>
          <button className={selectedRecord.instance.enabled ? "danger-button" : "primary"} onClick={() => void toggle(selectedRecord)}>{selectedRecord.instance.enabled ? "Disable" : "Activate"}</button>
          {selectedRuntime?.gap_open
            ? <button className="secondary" onClick={() => void changeGap(selectedRecord, true)}>Reconcile gap</button>
            : <button className="text-button" onClick={() => void changeGap(selectedRecord, false)}>Record known gap</button>}
        </div>
      </aside>}

      {wizard && <ConnectorWizard auth={auth} catalog={catalog} state={wizard} setState={setWizard} onSaved={onSaved} />}
    </section>
  );
}

function ConnectorWizard({ auth, catalog, state, setState, onSaved }: {
  auth: GatewayAuthorizationContext;
  catalog: ConnectorDefinition[];
  state: Wizard;
  setState: (state: Wizard | null) => void;
  onSaved: (record: ConnectorInstanceRecord) => void;
}) {
  const definition = catalog.find((item) => item.connector_id === state.draft.connectorId);
  const fields = definition ? settingFields[definition.connector_id] ?? [] : [];
  const needsCredential = definition?.capabilities.authentication_methods[0] === "bearer";
  const connectionReady = Boolean(state.draft.instanceId.trim() && state.draft.sourceName.trim() && state.draft.environment.trim() && (!needsCredential || state.draft.credentialRef.trim()));
  const policyReady = Boolean(state.draft.captureProfile.trim() && state.draft.normalizationProfile.trim());
  const canNext = state.step < 5 && (state.step !== 0 || connectionReady) && (state.step !== 2 || policyReady) && (state.step !== 4 || state.validation?.code === "ok");

  const patchDraft = (patch: Partial<Draft>) => setState({ ...state, draft: { ...state.draft, ...patch }, validation: null, error: null });
  const selectDefinition = (connectorId: string) => {
    const next = catalog.find((item) => item.connector_id === connectorId);
    if (next) setState({ ...createWizard(next), mode: state.mode, record: state.record });
  };
  const validate = async () => {
    if (!definition) return;
    setState({ ...state, busy: true, error: null, validation: null });
    try {
      const result = await validateConnectorInstance(buildInstance(state.draft, definition, auth, false));
      setState({ ...state, busy: false, error: null, validation: result });
    } catch (reason) {
      setState({ ...state, busy: false, validation: null, error: messageOf(reason, "Connector validation failed") });
    }
  };
  const save = async (activate: boolean) => {
    if (!definition) return;
    if (activate && !state.confirmActivation) {
      setState({ ...state, error: "Confirm activation before enabling source collection." });
      return;
    }
    setState({ ...state, busy: true, error: null });
    try {
      const enabled = state.mode === "edit" ? (state.record?.instance.enabled ?? false) : activate;
      const instance = buildInstance(state.draft, definition, auth, enabled);
      const saved = state.mode === "edit" && state.record
        ? await updateConnectorInstance(state.record, instance)
        : await createConnectorInstance(instance);
      onSaved(saved);
    } catch (reason) {
      setState({ ...state, busy: false, error: messageOf(reason, "Connector save failed") });
    }
  };

  return <div className="modal-backdrop" role="presentation"><div className="connector-modal" role="dialog" aria-modal="true" aria-labelledby="connector-wizard-title">
    <div className="drawer-header"><div><span>{state.mode === "create" ? "Add connector" : "Edit connector"}</span><h2 id="connector-wizard-title">{steps[state.step]}</h2></div><button className="icon-button" aria-label="Close connector wizard" onClick={() => setState(null)}>×</button></div>
    <ol className="wizard-steps" aria-label="Connector setup progress">{steps.map((label, index) => <li key={label} className={index === state.step ? "active" : index < state.step ? "done" : ""}><span>{index + 1}</span>{label}</li>)}</ol>
    {state.error && <div className="alert danger" role="alert">{state.error}</div>}
    <div className="wizard-body">
      {state.step === 0 && definition && <>
        <div className="form-grid">
          <label>Connector type<select value={state.draft.connectorId} disabled={state.mode === "edit"} onChange={(event) => selectDefinition(event.target.value)}>{catalog.filter((item) => settingFields[item.connector_id]).map((item) => <option key={item.connector_id} value={item.connector_id}>{item.display_name}</option>)}</select></label>
          <label>Instance ID<input value={state.draft.instanceId} disabled={state.mode === "edit"} onChange={(event) => patchDraft({ instanceId: event.target.value })} /></label>
          <label>Source name<input value={state.draft.sourceName} onChange={(event) => patchDraft({ sourceName: event.target.value })} /></label>
          <label>Environment<input value={state.draft.environment} onChange={(event) => patchDraft({ environment: event.target.value })} /></label>
          <label>Authentication method<input readOnly value={definition.capabilities.authentication_methods[0] ?? "none"} /></label>
          <label>Credential reference<input value={state.draft.credentialRef} onChange={(event) => patchDraft({ credentialRef: event.target.value })} placeholder={needsCredential ? "provider://opaque-reference" : "Not required for this profile"} /><small>Opaque reference only. Reusable credential values are never displayed here.</small></label>
        </div>
        {fields.length > 0 && <fieldset className="settings-fieldset"><legend>Connector settings</legend><div className="form-grid">{fields.map((field) => <SettingInput key={field.key} field={field} value={state.draft.settings[field.key] ?? ""} onChange={(value) => patchDraft({ settings: { ...state.draft.settings, [field.key]: value } })} />)}</div></fieldset>}
      </>}
      {state.step === 1 && <div className="scope-lock-panel"><span>Server-authorized scope</span><h3>{auth.tenant_id} / {auth.workspace_id}</h3><p>Tenant and workspace come from the authenticated server context. Source payloads and browser fields cannot grant ETS scope.</p></div>}
      {state.step === 2 && <div className="form-grid"><label>Capture profile<input value={state.draft.captureProfile} onChange={(event) => patchDraft({ captureProfile: event.target.value })} /></label><label>Normalization profile<input value={state.draft.normalizationProfile} onChange={(event) => patchDraft({ normalizationProfile: event.target.value })} /></label><div className="evidence-boundary wide"><span>Source</span><b>→</b><span>Capture / minimization</span><b>→</b><span>Normalization</span><b>→</b><span>ETS evidence candidate</span></div><p className="boundary-note wide">Policy and normalization occur before immutable commitment. This is not a verification result.</p></div>}
      {state.step === 3 && definition && <div className="form-grid"><label>Delivery mode<select value={state.draft.deliveryMode} onChange={(event) => patchDraft({ deliveryMode: event.target.value as "push" | "poll" })}>{definition.capabilities.delivery_modes.map((mode) => <option key={mode} value={mode}>{mode}</option>)}</select></label>{state.draft.deliveryMode === "poll" && <label>Poll interval (seconds)<input type="number" min="1" max="86400" value={state.draft.intervalSeconds} onChange={(event) => patchDraft({ intervalSeconds: event.target.value })} /></label>}<label>Batch size<input type="number" min="1" max="10000" value={state.draft.batchSize} onChange={(event) => patchDraft({ batchSize: event.target.value })} /></label><label>Checkpoint strategy<select value={state.draft.checkpointStrategy} onChange={(event) => patchDraft({ checkpointStrategy: event.target.value as CheckpointStrategy })}><option value="none">None</option><option value="source_cursor">Source cursor</option><option value="time_window">Time window</option><option value="source_sequence">Source sequence</option></select></label></div>}
      {state.step === 4 && definition && <div className="test-panel"><h3>Pre-activation contract validation</h3><p>Validate configuration before persistence. A live source test is available on the governed saved instance before activation.</p><button className="secondary" onClick={() => void validate()} disabled={state.busy}>{state.busy ? "Validating…" : "Validate configuration"}</button>{state.validation && <div className={`health-callout ${state.validation.state}`}><strong>{state.validation.state}</strong><span>{state.validation.code}</span><p>{state.validation.message}</p></div>}<CandidatePreview draft={state.draft} definition={definition} auth={auth} /></div>}
      {state.step === 5 && <div className="activation-panel"><h3>{state.mode === "edit" ? "Save configuration changes" : "Choose activation state"}</h3><p>Activation changes source-observation behavior and is auditable. It does not assert source truth, completeness, or verification.</p>{state.mode === "create" && <label className="confirmation-check"><input type="checkbox" checked={state.confirmActivation} onChange={(event) => setState({ ...state, confirmActivation: event.target.checked, error: null })} />I understand activation enables the configured source collection path.</label>}</div>}
    </div>
    <div className="wizard-footer"><button className="text-button" onClick={() => setState(null)}>Cancel</button><div>{state.step > 0 && <button className="secondary" onClick={() => setState({ ...state, step: state.step - 1, error: null })}>Back</button>}{canNext && <button className="primary" onClick={() => setState({ ...state, step: state.step + 1, error: null })}>Continue</button>}{state.step === 5 && state.mode === "create" && <><button className="secondary" onClick={() => void save(false)} disabled={state.busy}>Save disabled</button><button className="primary" onClick={() => void save(true)} disabled={state.busy || !state.confirmActivation}>Activate connector</button></>}{state.step === 5 && state.mode === "edit" && <button className="primary" onClick={() => void save(false)} disabled={state.busy}>Save changes</button>}</div></div>
  </div></div>;
}

function SettingInput({ field, value, onChange }: { field: ConnectorSettingField; value: string; onChange: (value: string) => void }) {
  return <label>{field.label}{field.type === "select"
    ? <select value={value} onChange={(event) => onChange(event.target.value)}>{field.options?.map((option) => <option key={option} value={option}>{option}</option>)}</select>
    : <input type={field.type} value={value} min={field.min} max={field.max} step={field.step} onChange={(event) => onChange(event.target.value)} />}{field.help && <small>{field.help}</small>}</label>;
}

function CandidatePreview({ draft, definition, auth }: { draft: Draft; definition: ConnectorDefinition; auth: GatewayAuthorizationContext }) {
  const preview = {
    source: { connector: definition.connector_id, source_name: draft.sourceName, environment: draft.environment },
    policy: { capture_profile: draft.captureProfile, server_authorized_scope: `${auth.tenant_id}/${auth.workspace_id}` },
    normalization: { profile: draft.normalizationProfile, representation: "pre-commit evidence candidate" },
    commitment: "not performed in preview",
  };
  return <div className="candidate-preview"><span>Preview · no source payload committed</span><pre>{JSON.stringify(preview, null, 2)}</pre></div>;
}

function createWizard(definition: ConnectorDefinition): Wizard {
  const mode = definition.capabilities.delivery_modes[0] ?? "push";
  return { step: 0, mode: "create", record: null, validation: null, busy: false, error: null, confirmActivation: false, draft: {
    connectorId: definition.connector_id,
    instanceId: `${definition.connector_id.replaceAll(".", "-")}-01`,
    sourceName: definition.display_name,
    environment: "production",
    credentialRef: "",
    deliveryMode: mode,
    intervalSeconds: mode === "poll" ? "60" : "",
    batchSize: definition.connector_id === "github.audit" ? "100" : "500",
    checkpointStrategy: definition.capabilities.checkpointing ? "time_window" : "none",
    captureProfile: `capture.${definition.connector_id}.v1`,
    normalizationProfile: `normalize.${definition.connector_id}.v1`,
    settings: { ...(defaults[definition.connector_id] ?? {}) },
  } };
}

function editWizard(record: ConnectorInstanceRecord, catalog: ConnectorDefinition[]): Wizard {
  const definition = catalog.find((item) => item.connector_id === record.instance.connector_id);
  if (!definition) throw new Error("Connector definition is unavailable");
  const instance = record.instance;
  return { step: 0, mode: "edit", record, validation: null, busy: false, error: null, confirmActivation: false, draft: {
    connectorId: instance.connector_id,
    instanceId: instance.instance_id,
    sourceName: instance.source.name,
    environment: instance.source.environment,
    credentialRef: instance.authentication.credential_ref ?? "",
    deliveryMode: instance.collection.mode,
    intervalSeconds: instance.collection.interval_seconds?.toString() ?? "",
    batchSize: instance.collection.batch_size.toString(),
    checkpointStrategy: instance.checkpoint.strategy,
    captureProfile: instance.policy.capture_profile,
    normalizationProfile: instance.policy.normalization_profile,
    settings: Object.fromEntries(Object.entries(instance.settings).map(([key, value]) => [key, String(value ?? "")])),
  } };
}

function buildInstance(draft: Draft, definition: ConnectorDefinition, auth: GatewayAuthorizationContext, enabled: boolean): ConnectorInstance {
  const settings: Record<string, JsonValue> = {};
  for (const field of settingFields[definition.connector_id] ?? []) {
    const raw = draft.settings[field.key]?.trim() ?? "";
    if (raw) settings[field.key] = field.type === "number" ? Number(raw) : raw;
  }
  return {
    schema_version: "ets.connector.instance.v1",
    instance_id: draft.instanceId.trim(),
    connector_id: definition.connector_id,
    connector_version: definition.adapter_version,
    enabled,
    scope: { tenant_id: auth.tenant_id, workspace_id: auth.workspace_id },
    source: { name: draft.sourceName.trim(), environment: draft.environment.trim() },
    authentication: { method: definition.capabilities.authentication_methods[0] ?? "none", credential_ref: draft.credentialRef.trim() || null },
    collection: { mode: draft.deliveryMode, interval_seconds: draft.deliveryMode === "poll" ? Number(draft.intervalSeconds || "60") : null, batch_size: Number(draft.batchSize || "500") },
    checkpoint: { strategy: draft.checkpointStrategy, durable: true },
    policy: { capture_profile: draft.captureProfile.trim(), normalization_profile: draft.normalizationProfile.trim() },
    retry: { max_attempts: 8, backoff: "exponential", max_age_seconds: 86400 },
    gap_detection: { enabled: true },
    settings,
  };
}

function Metric({ label, value, detail }: { label: string; value: number; detail: string }) { return <article className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>; }
function Badge({ tone, label }: { tone: "good" | "warning" | "danger" | "neutral"; label: string }) { const icon = tone === "good" ? "●" : tone === "warning" ? "▲" : tone === "danger" ? "!" : "○"; return <span className={`state-badge ${tone}`}><span aria-hidden="true">{icon}</span>{label}</span>; }
function Observation({ state }: { state?: ConnectorRuntimeState }) { if (!state) return <Badge tone="neutral" label="Unknown" />; if (state.observation_state === "healthy_observation") return <Badge tone="good" label="Healthy" />; if (state.observation_state === "collection_gap") return <Badge tone="danger" label="Collection gap" />; if (state.observation_state === "degraded_observation") return <Badge tone="warning" label="Degraded" />; return <Badge tone="neutral" label="Unknown" />; }
function humanObservation(value?: ConnectorRuntimeState["observation_state"]) { return value === "healthy_observation" ? "Healthy observation" : value === "degraded_observation" ? "Degraded observation" : value === "collection_gap" ? "Collection gap" : "Unknown observation"; }
function formatClass(value: ConnectorDefinition["implementation_class"]) { return value === "enterprise_api" ? "Enterprise API" : value === "third_party" ? "Third party" : value[0].toUpperCase() + value.slice(1); }
function formatTime(value?: string | null) { if (!value) return "—"; const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString(); }
function messageOf(reason: unknown, fallback: string) { return reason instanceof Error ? reason.message : fallback; }
