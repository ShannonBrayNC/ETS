export type EtsErrorCode =
  | "transport_error"
  | "authentication_failed"
  | "authorization_failed"
  | "not_found"
  | "conflict"
  | "validation_failed"
  | "request_too_large"
  | "server_error"
  | "unsafe_configuration"
  | "incompatible_version"
  | "unknown_error";

export class EtsApplicationError extends Error {
  constructor(
    public readonly code: EtsErrorCode,
    message: string,
    public readonly statusCode?: number,
    public readonly apiCode?: string,
    public readonly correlationId?: string,
  ) {
    super(message);
    this.name = "EtsApplicationError";
  }
}

export function classifyApiError(apiCode: string | undefined, status: number): EtsErrorCode {
  const mapped: Record<string, EtsErrorCode> = {
    ETS_AUTH_REQUIRED: "authentication_failed",
    ETS_AUTH_FORBIDDEN: "authorization_failed",
    ETS_EVENT_NOT_FOUND: "not_found",
    ETS_EVENT_DUPLICATE: "conflict",
    ETS_VALIDATION_ERROR: "validation_failed",
    ETS_REQUEST_TOO_LARGE: "request_too_large",
    ETS_STORAGE_VALIDATION_ERROR: "server_error",
  };
  if (apiCode && mapped[apiCode]) return mapped[apiCode]!;
  if (status === 401) return "authentication_failed";
  if (status === 403) return "authorization_failed";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 413) return "request_too_large";
  if (status === 400 || status === 422) return "validation_failed";
  if (status >= 500) return "server_error";
  return "unknown_error";
}
