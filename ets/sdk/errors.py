"""Application SDK error vocabulary independent of a specific transport."""

from __future__ import annotations

from typing import Literal, TypeAlias

SDKErrorCode: TypeAlias = Literal[
    "transport_error",
    "authentication_failed",
    "authorization_failed",
    "not_found",
    "conflict",
    "validation_failed",
    "request_too_large",
    "server_error",
    "unsafe_configuration",
    "incompatible_version",
    "unknown_error",
]


class ETSApplicationError(Exception):
    """Base exception raised by application SDK transports and compatibility checks."""

    def __init__(
        self,
        code: SDKErrorCode,
        message: str,
        *,
        status_code: int | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.correlation_id = correlation_id


_API_CODE_MAP: dict[str, SDKErrorCode] = {
    "ETS_AUTH_REQUIRED": "authentication_failed",
    "ETS_EVENT_NOT_FOUND": "not_found",
    "ETS_EVENT_DUPLICATE": "conflict",
    "ETS_VALIDATION_ERROR": "validation_failed",
    "ETS_REQUEST_TOO_LARGE": "request_too_large",
    "ETS_STORAGE_VALIDATION_ERROR": "server_error",
}


def classify_api_error(api_code: str | None, status_code: int | None) -> SDKErrorCode:
    """Map an ETS API error/status to the stable SDK error vocabulary."""

    if api_code is not None and api_code in _API_CODE_MAP:
        return _API_CODE_MAP[api_code]
    if status_code in {401}:
        return "authentication_failed"
    if status_code in {403}:
        return "authorization_failed"
    if status_code in {404}:
        return "not_found"
    if status_code in {409}:
        return "conflict"
    if status_code in {413}:
        return "request_too_large"
    if status_code in {400, 422}:
        return "validation_failed"
    if status_code is not None and status_code >= 500:
        return "server_error"
    return "unknown_error"
