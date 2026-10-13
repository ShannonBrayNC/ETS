import {
  ETS_API_VERSION,
  ETS_APPLICATION_SDK_CONTRACT,
  type EventAppendWireResponse,
  type EventCommitReceipt,
  type ServiceHealth,
  type ServiceVersion,
} from "./contracts.js";
import { EtsApplicationError, classifyApiError } from "./errors.js";

export interface EtsClientOptions {
  baseUrl: string;
  apiKey?: string;
  bearerToken?: string;
  tenantId?: string;
  workspaceId?: string;
  allowInsecureLoopbackHttp?: boolean;
  fetchImpl?: typeof fetch;
}

function validate(options: EtsClientOptions): URL {
  const url = new URL(options.baseUrl);
  if (options.apiKey && options.bearerToken) {
    throw new EtsApplicationError("unsafe_configuration", "apiKey and bearerToken are mutually exclusive");
  }
  if ((options.tenantId === undefined) !== (options.workspaceId === undefined)) {
    throw new EtsApplicationError("unsafe_configuration", "tenantId and workspaceId must be configured together");
  }
  if (options.bearerToken && options.tenantId) {
    throw new EtsApplicationError(
      "unsafe_configuration",
      "Bearer authentication derives ETS scope from authenticated claims",
    );
  }
  if (url.protocol === "http:") {
    const loopback = url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "::1";
    if (!options.allowInsecureLoopbackHttp || !loopback) {
      throw new EtsApplicationError(
        "unsafe_configuration",
        "HTTP is allowed only for an explicitly enabled loopback ETS Dev endpoint",
      );
    }
  } else if (url.protocol !== "https:") {
    throw new EtsApplicationError("unsafe_configuration", "baseUrl must use HTTP(S)");
  }
  return url;
}

export class EtsClient {
  readonly #url: URL;
  readonly #fetch: typeof fetch;

  constructor(private readonly options: EtsClientOptions) {
    this.#url = validate(options);
    this.#fetch = options.fetchImpl ?? fetch;
  }

  health(): Promise<ServiceHealth> {
    return this.#request<ServiceHealth>("health");
  }

  version(): Promise<ServiceVersion> {
    return this.#request<ServiceVersion>("version");
  }

  async checkCompatibility(): Promise<ServiceVersion> {
    const version = await this.version();
    if (version.api_version !== ETS_API_VERSION) {
      throw new EtsApplicationError(
        "incompatible_version",
        `ETS API version '${version.api_version}' is not supported by ${ETS_APPLICATION_SDK_CONTRACT}`,
      );
    }
    return version;
  }

  async capture(event: unknown, correlationId?: string): Promise<EventCommitReceipt> {
    const wire = await this.#request<EventAppendWireResponse>(
      "api/v1/events",
      { method: "POST", body: JSON.stringify(event) },
      correlationId,
    );
    return {
      ...wire,
      schema_version: "ets.sdk.event_commit_receipt.v1",
      commitment_state: "committed_local",
    };
  }

  getEvent(eventId: string): Promise<unknown> {
    return this.#request(`api/v1/events/${encodeURIComponent(requireEventId(eventId))}`);
  }

  getBundle(eventId: string): Promise<unknown> {
    return this.#request(`api/v1/bundles/${encodeURIComponent(requireEventId(eventId))}`);
  }

  getInclusionProof(eventId: string): Promise<unknown> {
    return this.#request(`api/v1/proofs/inclusion/${encodeURIComponent(requireEventId(eventId))}`);
  }

  getConsistencyProof(fromSize: number, toSize?: number): Promise<unknown> {
    if (!Number.isInteger(fromSize) || fromSize < 0 || (toSize !== undefined && toSize < fromSize)) {
      throw new EtsApplicationError("validation_failed", "Consistency proof sizes are invalid");
    }
    const query = new URLSearchParams({ from_size: String(fromSize) });
    if (toSize !== undefined) query.set("to_size", String(toSize));
    return this.#request(`api/v1/proofs/consistency?${query}`);
  }

  async #request<T>(path: string, init: RequestInit = {}, correlationId?: string): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    headers.set("X-ETS-SDK-Contract", ETS_APPLICATION_SDK_CONTRACT);
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    if (this.options.apiKey) headers.set("X-ETS-API-Key", this.options.apiKey);
    if (this.options.bearerToken) {
      headers.set("Authorization", `Bearer ${this.options.bearerToken}`);
    } else if (this.options.tenantId && this.options.workspaceId) {
      headers.set("X-ETS-Tenant", this.options.tenantId);
      headers.set("X-ETS-Workspace", this.options.workspaceId);
    }
    if (correlationId) headers.set("X-Correlation-ID", correlationId);

    let response: Response;
    try {
      response = await this.#fetch(new URL(path, this.#url), { ...init, headers, redirect: "error" });
    } catch (error) {
      throw new EtsApplicationError(
        "transport_error",
        error instanceof Error ? `ETS API request failed: ${error.message}` : "ETS API request failed",
      );
    }

    const payload = await response.json() as unknown;
    if (!response.ok) {
      const envelope = payload as { error?: { code?: string; message?: string; correlation_id?: string } };
      const apiCode = envelope.error?.code;
      throw new EtsApplicationError(
        classifyApiError(apiCode, response.status),
        envelope.error?.message ?? `ETS API returned HTTP ${response.status}`,
        response.status,
        apiCode,
        envelope.error?.correlation_id,
      );
    }
    return payload as T;
  }
}

function requireEventId(eventId: string): string {
  if (!eventId.trim()) throw new EtsApplicationError("validation_failed", "eventId is required");
  return eventId;
}
