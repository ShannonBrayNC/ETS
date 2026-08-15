import type {
  ArtifactReceipt,
  ArtifactRecord,
  ConnectorDefinition,
  ConnectorHealth,
  ConnectorInstance,
  ConnectorInstanceListResponse,
  ConnectorInstanceRecord,
  ConnectorRuntimeState,
  GatewayAuthorizationContext,
  HealthSnapshot,
  ProofBundle,
  TenantScope,
  TreeHead,
} from "./types";
import {
  ConnectorManagementError,
  decorateConnectorHealth,
  diagnosticFromResponse,
} from "./connectorDiagnostics";

const jsonHeaders = { "Content-Type": "application/json" } as const;
const managementBase = (import.meta.env.VITE_ETS_MANAGEMENT_BASE ?? "").replace(/\/$/, "");
const localManagementTenant = import.meta.env.DEV ? import.meta.env.VITE_ETS_LOCAL_TENANT : undefined;
const localManagementWorkspace = import.meta.env.DEV
  ? import.meta.env.VITE_ETS_LOCAL_WORKSPACE
  : undefined;

function managementUrl(path: string): string {
  return `${managementBase}${path}`;
}

function managementHeaders(includeJson = false): HeadersInit {
  return {
    ...(includeJson ? jsonHeaders : {}),
    ...(localManagementTenant ? { "X-ETS-Tenant": localManagementTenant } : {}),
    ...(localManagementWorkspace ? { "X-ETS-Workspace": localManagementWorkspace } : {}),
  };
}

function scopeHeaders(scope: TenantScope, correlationId?: string): HeadersInit {
  return {
    "X-ETS-Tenant": scope.tenantId,
    "X-ETS-Workspace": scope.workspaceId,
    ...(correlationId ? { "X-Correlation-ID": correlationId } : {}),
  };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string; message?: string };
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // Keep the transport-level diagnostic when the body is not JSON.
    }
    const diagnostic = diagnosticFromResponse(response, detail);
    if (diagnostic) throw new ConnectorManagementError(diagnostic);
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

async function readText(response: Response): Promise<string> {
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.text();
}

export async function getAuthorizationContext(): Promise<GatewayAuthorizationContext> {
  return readJson<GatewayAuthorizationContext>(
    await fetch(managementUrl("/api/v2/auth/context"), {
      credentials: "same-origin",
      headers: managementHeaders(),
    }),
  );
}

export async function getHealthSnapshot(): Promise<HealthSnapshot> {
  const [health, ready, version] = await Promise.allSettled([
    fetch("/health").then((response) => readJson<Record<string, unknown>>(response)),
    fetch("/ready").then((response) => readJson<Record<string, unknown>>(response)),
    fetch("/version").then((response) => readJson<Record<string, unknown>>(response)),
  ]);

  const healthBody = health.status === "fulfilled" ? health.value : {};
  const readyBody = ready.status === "fulfilled" ? ready.value : {};
  const versionBody = version.status === "fulfilled" ? version.value : {};

  return {
    health: health.status === "fulfilled" ? "ok" : "unknown",
    ready:
      ready.status === "fulfilled" &&
      (readyBody.ready === true || readyBody.status === "ready" || readyBody.status === "ok"),
    version:
      typeof versionBody.version === "string"
        ? versionBody.version
        : typeof healthBody.version === "string"
          ? healthBody.version
          : "unknown",
  };
}

export async function registerArtifact(
  scope: TenantScope,
  actorId: string,
  file: File,
  metadata: Record<string, unknown>,
): Promise<ArtifactReceipt> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);

  const artifactId = `artifact_${crypto.randomUUID().replaceAll("-", "")}`;
  const correlationId = `console_${crypto.randomUUID()}`;

  const response = await fetch("/evidence/register", {
    method: "POST",
    headers: {
      ...jsonHeaders,
      ...scopeHeaders(scope, correlationId),
    },
    body: JSON.stringify({
      artifact_id: artifactId,
      artifact_base64: btoa(binary),
      tenant_id: scope.tenantId,
      workspace_id: scope.workspaceId,
      content_type: file.type || "application/octet-stream",
      metadata: {
        filename: file.name,
        byte_size: file.size,
        collection_surface: "ets-console",
        ...metadata,
      },
      source_system: "ets-console",
      actor_id: actorId,
      correlation_id: correlationId,
    }),
  });

  return readJson<ArtifactReceipt>(response);
}

export async function getArtifact(scope: TenantScope, artifactId: string): Promise<ArtifactRecord> {
  const response = await fetch(`/evidence/${encodeURIComponent(artifactId)}`, {
    headers: scopeHeaders(scope),
  });
  return readJson<ArtifactRecord>(response);
}

export async function getArtifactProof(scope: TenantScope, artifactId: string): Promise<ProofBundle> {
  const response = await fetch(`/evidence/${encodeURIComponent(artifactId)}/proof`, {
    headers: scopeHeaders(scope),
  });
  return readJson<ProofBundle>(response);
}

export async function getLatestTreeHead(scope: TenantScope): Promise<TreeHead> {
  const response = await fetch("/tree-head/latest", { headers: scopeHeaders(scope) });
  return readJson<TreeHead>(response);
}

export async function getVersionText(): Promise<string> {
  return readText(await fetch("/version"));
}

export async function getConnectorCatalog(): Promise<ConnectorDefinition[]> {
  return readJson<ConnectorDefinition[]>(
    await fetch(managementUrl("/gateway/connectors/v1/catalog"), {
      credentials: "same-origin",
      headers: managementHeaders(),
    }),
  );
}

export async function getConnectorInstances(): Promise<ConnectorInstanceRecord[]> {
  const response = await readJson<ConnectorInstanceListResponse>(
    await fetch(managementUrl("/gateway/connectors/v1/instances"), {
      credentials: "same-origin",
      headers: managementHeaders(),
    }),
  );
  return response.items;
}

export async function createConnectorInstance(
  instance: ConnectorInstance,
): Promise<ConnectorInstanceRecord> {
  return readJson<ConnectorInstanceRecord>(
    await fetch(managementUrl("/gateway/connectors/v1/instances"), {
      method: "POST",
      credentials: "same-origin",
      headers: managementHeaders(true),
      body: JSON.stringify(instance),
    }),
  );
}

export async function updateConnectorInstance(
  record: ConnectorInstanceRecord,
  instance: ConnectorInstance,
): Promise<ConnectorInstanceRecord> {
  return readJson<ConnectorInstanceRecord>(
    await fetch(
      managementUrl(`/gateway/connectors/v1/instances/${encodeURIComponent(instance.instance_id)}`),
      {
        method: "PUT",
        credentials: "same-origin",
        headers: managementHeaders(true),
        body: JSON.stringify({ instance, expected_revision: record.revision }),
      },
    ),
  );
}

export async function validateConnectorInstance(instance: ConnectorInstance): Promise<ConnectorHealth> {
  const health = await readJson<ConnectorHealth>(
    await fetch(managementUrl("/gateway/connectors/v1/validate"), {
      method: "POST",
      credentials: "same-origin",
      headers: managementHeaders(true),
      body: JSON.stringify(instance),
    }),
  );
  return decorateConnectorHealth(health);
}

export async function testConnectorConnection(instanceId: string): Promise<ConnectorHealth> {
  const health = await readJson<ConnectorHealth>(
    await fetch(
      managementUrl(
        `/gateway/connectors/v1/instances/${encodeURIComponent(instanceId)}/test-connection`,
      ),
      { method: "POST", credentials: "same-origin", headers: managementHeaders() },
    ),
  );
  return decorateConnectorHealth(health);
}

export async function setConnectorEnabled(
  record: ConnectorInstanceRecord,
  enabled: boolean,
): Promise<ConnectorInstanceRecord> {
  const action = enabled ? "enable" : "disable";
  return readJson<ConnectorInstanceRecord>(
    await fetch(
      managementUrl(
        `/gateway/connectors/v1/instances/${encodeURIComponent(record.instance.instance_id)}/${action}`,
      ),
      {
        method: "POST",
        credentials: "same-origin",
        headers: managementHeaders(true),
        body: JSON.stringify({ expected_revision: record.revision }),
      },
    ),
  );
}

export async function getConnectorRuntime(instanceId: string): Promise<ConnectorRuntimeState> {
  return readJson<ConnectorRuntimeState>(
    await fetch(
      managementUrl(
        `/gateway/connectors/v1/instances/${encodeURIComponent(instanceId)}/runtime`,
      ),
      { credentials: "same-origin", headers: managementHeaders() },
    ),
  );
}

export async function markConnectorGap(instanceId: string): Promise<ConnectorRuntimeState> {
  return readJson<ConnectorRuntimeState>(
    await fetch(
      managementUrl(
        `/gateway/connectors/v1/instances/${encodeURIComponent(instanceId)}/gaps/detect`,
      ),
      { method: "POST", credentials: "same-origin", headers: managementHeaders() },
    ),
  );
}

export async function reconcileConnectorGap(instanceId: string): Promise<ConnectorRuntimeState> {
  return readJson<ConnectorRuntimeState>(
    await fetch(
      managementUrl(
        `/gateway/connectors/v1/instances/${encodeURIComponent(instanceId)}/gaps/reconcile`,
      ),
      { method: "POST", credentials: "same-origin", headers: managementHeaders() },
    ),
  );
}
