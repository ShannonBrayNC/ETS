import type { ConnectorHealth, ConnectorOperationCode } from "./types";

export type ConnectorDiagnosticCategory =
  | "authorization"
  | "configuration_policy"
  | "source_authentication"
  | "source_availability"
  | "collection_continuity"
  | "gateway_runtime"
  | "upstream_sync";

export interface ConnectorDiagnostic {
  schemaVersion: "ets.connector.diagnostic.v1";
  category: ConnectorDiagnosticCategory;
  code: string;
  message: string;
  httpStatus: number | null;
}

const schemaHeader = "X-ETS-Connector-Diagnostic-Schema";
const categoryHeader = "X-ETS-Connector-Diagnostic-Category";
const codeHeader = "X-ETS-Connector-Diagnostic-Code";
const schemaVersion = "ets.connector.diagnostic.v1" as const;
const codePattern = /^[a-z0-9_]{1,64}$/;

const categories = new Set<ConnectorDiagnosticCategory>([
  "authorization",
  "configuration_policy",
  "source_authentication",
  "source_availability",
  "collection_continuity",
  "gateway_runtime",
  "upstream_sync",
]);

const labels: Record<ConnectorDiagnosticCategory, string> = {
  authorization: "Authorization",
  configuration_policy: "Configuration / policy",
  source_authentication: "Source authentication",
  source_availability: "Source availability",
  collection_continuity: "Collection continuity",
  gateway_runtime: "Gateway runtime",
  upstream_sync: "Upstream synchronization",
};

const actions: Record<ConnectorDiagnosticCategory, string> = {
  authorization: "Confirm the authenticated role, capability, tenant, and workspace scope.",
  configuration_policy: "Review the connector settings, policy binding, and qualified adapter profile.",
  source_authentication: "Verify the opaque credential reference, source permissions, and credential lifecycle.",
  source_availability: "Check source reachability, throttling, service health, and the documented retry window.",
  collection_continuity: "Inspect the checkpoint, known-gap state, and reconciliation history before resuming collection.",
  gateway_runtime: "Refresh current state, resolve revision conflicts or runtime dependencies, then retry the operation.",
  upstream_sync: "Inspect retry state and durable synchronization status before advancing source progress.",
};

const healthCategories: Record<ConnectorOperationCode, ConnectorDiagnosticCategory> = {
  ok: "gateway_runtime",
  unsupported: "configuration_policy",
  invalid_config: "configuration_policy",
  authentication_failed: "source_authentication",
  authorization_failed: "source_authentication",
  throttled: "source_availability",
  retryable_error: "source_availability",
  terminal_error: "source_availability",
  gap_detected: "collection_continuity",
  unknown_observation: "collection_continuity",
  incompatible_version: "configuration_policy",
};

export class ConnectorManagementError extends Error {
  readonly diagnostic: ConnectorDiagnostic;

  constructor(diagnostic: ConnectorDiagnostic) {
    super(formatConnectorDiagnostic(diagnostic));
    this.name = "ConnectorManagementError";
    this.diagnostic = diagnostic;
  }
}

export function diagnosticFromResponse(
  response: Response,
  message: string,
): ConnectorDiagnostic | null {
  if (response.headers.get(schemaHeader) !== schemaVersion) return null;

  const categoryValue = response.headers.get(categoryHeader);
  const code = response.headers.get(codeHeader);
  if (!isDiagnosticCategory(categoryValue) || code === null || !codePattern.test(code)) {
    return null;
  }

  return {
    schemaVersion,
    category: categoryValue,
    code,
    message,
    httpStatus: response.status,
  };
}

export function decorateConnectorHealth(health: ConnectorHealth): ConnectorHealth {
  if (health.code === "ok") return health;

  const diagnostic: ConnectorDiagnostic = {
    schemaVersion,
    category: healthCategories[health.code],
    code: health.code,
    message: health.message,
    httpStatus: null,
  };
  return { ...health, message: formatConnectorDiagnostic(diagnostic) };
}

export function formatConnectorDiagnostic(diagnostic: ConnectorDiagnostic): string {
  return `${labels[diagnostic.category]} · ${diagnostic.code}: ${diagnostic.message} Next action: ${actions[diagnostic.category]}`;
}

function isDiagnosticCategory(value: string | null): value is ConnectorDiagnosticCategory {
  return value !== null && categories.has(value as ConnectorDiagnosticCategory);
}
