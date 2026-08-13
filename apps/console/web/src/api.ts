import type {
  ArtifactReceipt,
  ArtifactRecord,
  HealthSnapshot,
  ProofBundle,
  TenantScope,
  TreeHead,
} from "./types";

const jsonHeaders = { "Content-Type": "application/json" } as const;

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
      actor_id: "console-user",
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
