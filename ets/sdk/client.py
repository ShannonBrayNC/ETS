"""Remote synchronous and asynchronous clients for ETS Application SDK v1."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ets.core import ConsistencyProof, EvidenceEvent, EvidenceProofBundle, InclusionProof, SignedTreeHead
from ets.sdk.errors import ETSApplicationError, classify_api_error
from ets.sdk.local import create_evidence
from ets.sdk.models import (
    APPLICATION_SDK_COMPATIBILITY_V1,
    EventCommitReceiptV1,
    EventPageV1,
    EventRecordV1,
    ServiceHealthV1,
    ServiceVersionV1,
)
from ets.verifier.service import (
    TreeHeadTrustStore,
    VerifierOutcome,
    VerifierPolicy,
    verify_offline_bundle,
    verify_online_event,
)

_DEFAULT_TIMEOUT_SECONDS = 10.0
_DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class _EventAppendWireResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    event_id: str = Field(min_length=1, max_length=128)
    log_index: int = Field(ge=0)
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    tree_head: SignedTreeHead
    inclusion_proof_url: str = Field(min_length=1, max_length=4096)


@dataclass(frozen=True)
class _ClientConfig:
    base_url: str
    hostname: str
    api_key: str | None
    bearer_token: str | None
    tenant_id: str | None
    workspace_id: str | None
    allow_insecure_http: bool
    timeout_seconds: float
    max_response_bytes: int

    def headers(self, correlation_id: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "X-ETS-SDK-Contract": APPLICATION_SDK_COMPATIBILITY_V1.sdk_contract,
        }
        if self.api_key is not None:
            headers["X-ETS-API-Key"] = self.api_key
        if self.bearer_token is not None:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.tenant_id is not None and self.workspace_id is not None:
            headers["X-ETS-Tenant"] = self.tenant_id
            headers["X-ETS-Workspace"] = self.workspace_id
        if correlation_id is not None:
            if not 1 <= len(correlation_id) <= 200:
                raise ETSApplicationError(
                    "validation_failed",
                    "correlation_id must be between 1 and 200 characters",
                )
            headers["X-Correlation-ID"] = correlation_id
        return headers


def _configuration(
    base_url: str,
    *,
    api_key: str | None,
    bearer_token: str | None,
    tenant_id: str | None,
    workspace_id: str | None,
    allow_insecure_http: bool,
    timeout_seconds: float,
    max_response_bytes: int,
) -> _ClientConfig:
    if api_key is not None and bearer_token is not None:
        raise ETSApplicationError(
            "unsafe_configuration",
            "api_key and bearer_token are mutually exclusive",
        )
    if api_key is not None and not api_key.strip():
        raise ETSApplicationError("unsafe_configuration", "api_key must not be empty")
    if bearer_token is not None and not bearer_token.strip():
        raise ETSApplicationError("unsafe_configuration", "bearer_token must not be empty")
    if (tenant_id is None) != (workspace_id is None):
        raise ETSApplicationError(
            "unsafe_configuration",
            "tenant_id and workspace_id must be configured together",
        )
    if bearer_token is not None and tenant_id is not None:
        raise ETSApplicationError(
            "unsafe_configuration",
            "production bearer authentication derives ETS scope from authenticated claims; "
            "do not configure tenant/workspace headers",
        )
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ETSApplicationError(
            "unsafe_configuration",
            "timeout_seconds must be greater than zero and at most 60",
        )
    if max_response_bytes < 1024 or max_response_bytes > 16 * 1024 * 1024:
        raise ETSApplicationError(
            "unsafe_configuration",
            "max_response_bytes must be between 1 KiB and 16 MiB",
        )

    parsed = urlsplit(base_url)
    if parsed.scheme not in {"https", "http"} or parsed.hostname is None:
        raise ETSApplicationError(
            "unsafe_configuration",
            "base_url must be an absolute HTTP(S) URL with a host",
        )
    if parsed.username is not None or parsed.password is not None:
        raise ETSApplicationError(
            "unsafe_configuration",
            "base_url must not contain embedded credentials",
        )
    if parsed.query or parsed.fragment:
        raise ETSApplicationError(
            "unsafe_configuration",
            "base_url must not contain a query string or fragment",
        )

    hostname = parsed.hostname.lower()
    if parsed.scheme == "http" and (
        not allow_insecure_http or hostname not in _LOOPBACK_HOSTS
    ):
        raise ETSApplicationError(
            "unsafe_configuration",
            "HTTP is allowed only for an explicitly enabled loopback ETS Dev endpoint",
        )

    return _ClientConfig(
        base_url=base_url.rstrip("/"),
        hostname=hostname,
        api_key=api_key,
        bearer_token=bearer_token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        allow_insecure_http=allow_insecure_http,
        timeout_seconds=timeout_seconds,
        max_response_bytes=max_response_bytes,
    )


def _mapping_json(response: httpx.Response) -> Mapping[str, Any] | None:
    try:
        payload: object = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        return cast(Mapping[str, Any], payload)
    return None


def _raise_api_error(response: httpx.Response) -> None:
    payload = _mapping_json(response)
    error = payload.get("error") if payload is not None else None
    api_code: str | None = None
    message = f"ETS API returned HTTP {response.status_code}"
    correlation_id: str | None = None
    details: Any | None = None
    if isinstance(error, dict):
        raw_code = error.get("code")
        raw_message = error.get("message")
        raw_correlation = error.get("correlation_id")
        api_code = raw_code if isinstance(raw_code, str) else None
        message = raw_message if isinstance(raw_message, str) else message
        correlation_id = raw_correlation if isinstance(raw_correlation, str) else None
        details = error.get("details")
    raise ETSApplicationError(
        classify_api_error(api_code, response.status_code),
        message,
        status_code=response.status_code,
        correlation_id=correlation_id,
        api_code=api_code,
        details=details,
    )


def _validate_response_size(response: httpx.Response, max_response_bytes: int) -> None:
    if len(response.content) > max_response_bytes:
        raise ETSApplicationError(
            "server_error",
            "ETS API response exceeded the configured response-size limit",
            status_code=response.status_code,
        )


def _parse_model[ModelT: BaseModel](
    model_type: type[ModelT],
    response: httpx.Response,
) -> ModelT:
    try:
        return model_type.model_validate_json(response.content)
    except ValidationError as exc:
        raise ETSApplicationError(
            "server_error",
            f"ETS API returned an invalid {model_type.__name__} response",
            status_code=response.status_code,
        ) from exc


def _event_id_path(event_id: str) -> str:
    if not event_id:
        raise ETSApplicationError("validation_failed", "event_id is required")
    return quote(event_id, safe="")


def _pagination(limit: int, offset: int) -> dict[str, int]:
    if not 1 <= limit <= 500:
        raise ETSApplicationError("validation_failed", "limit must be between 1 and 500")
    if offset < 0:
        raise ETSApplicationError("validation_failed", "offset must be non-negative")
    return {"limit": limit, "offset": offset}


def _consistency_params(from_size: int, to_size: int | None) -> dict[str, int]:
    if from_size < 0:
        raise ETSApplicationError("validation_failed", "from_size must be non-negative")
    params = {"from_size": from_size}
    if to_size is not None:
        if to_size < from_size:
            raise ETSApplicationError(
                "validation_failed",
                "to_size must be greater than or equal to from_size",
            )
        params["to_size"] = to_size
    return params


def _receipt(response: httpx.Response) -> EventCommitReceiptV1:
    wire = _parse_model(_EventAppendWireResponse, response)
    return EventCommitReceiptV1(
        event_id=wire.event_id,
        log_index=wire.log_index,
        event_hash=wire.event_hash,
        tree_head=wire.tree_head,
        inclusion_proof_url=wire.inclusion_proof_url,
    )


class ETSClient:
    """Synchronous ETS Application SDK v1 client.

    The client intentionally performs no automatic retries. Callers must decide
    retry policy using their own event identity/idempotency semantics.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        allow_insecure_http: bool = False,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = _configuration(
            base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            allow_insecure_http=allow_insecure_http,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )
        self._client = httpx.Client(
            base_url=self._config.base_url,
            timeout=self._config.timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    def __enter__(self) -> ETSClient:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str | None = None,
        json: object | None = None,
        params: Mapping[str, object] | None = None,
    ) -> httpx.Response:
        try:
            response = self._client.request(
                method,
                path,
                headers=self._config.headers(correlation_id),
                json=json,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise ETSApplicationError("transport_error", "ETS API request failed") from exc
        _validate_response_size(response, self._config.max_response_bytes)
        if response.is_error:
            _raise_api_error(response)
        return response

    def health(self) -> ServiceHealthV1:
        return _parse_model(ServiceHealthV1, self._request("GET", "/health"))

    def version(self) -> ServiceVersionV1:
        return _parse_model(ServiceVersionV1, self._request("GET", "/version"))

    def check_compatibility(self) -> ServiceVersionV1:
        version = self.version()
        if version.api_version not in APPLICATION_SDK_COMPATIBILITY_V1.api_versions:
            raise ETSApplicationError(
                "incompatible_version",
                f"ETS API version {version.api_version!r} is not supported by "
                f"{APPLICATION_SDK_COMPATIBILITY_V1.sdk_contract}",
            )
        return version

    def capture(
        self,
        evidence: EvidenceEvent | Mapping[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> EventCommitReceiptV1:
        event = create_evidence(evidence)
        response = self._request(
            "POST",
            "/api/v1/events",
            correlation_id=correlation_id,
            json=event.model_dump(mode="json"),
        )
        return _receipt(response)

    def get_event(
        self,
        event_id: str,
        *,
        correlation_id: str | None = None,
    ) -> EventRecordV1:
        response = self._request(
            "GET",
            f"/api/v1/events/{_event_id_path(event_id)}",
            correlation_id=correlation_id,
        )
        return _parse_model(EventRecordV1, response)

    def list_events(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        correlation_id: str | None = None,
    ) -> EventPageV1:
        response = self._request(
            "GET",
            "/api/v1/events",
            correlation_id=correlation_id,
            params=_pagination(limit, offset),
        )
        return _parse_model(EventPageV1, response)

    def inclusion_proof(
        self,
        event_id: str,
        *,
        correlation_id: str | None = None,
    ) -> InclusionProof:
        response = self._request(
            "GET",
            f"/api/v1/proofs/inclusion/{_event_id_path(event_id)}",
            correlation_id=correlation_id,
        )
        return _parse_model(InclusionProof, response)

    def consistency_proof(
        self,
        from_size: int,
        *,
        to_size: int | None = None,
        correlation_id: str | None = None,
    ) -> ConsistencyProof:
        response = self._request(
            "GET",
            "/api/v1/proofs/consistency",
            correlation_id=correlation_id,
            params=_consistency_params(from_size, to_size),
        )
        return _parse_model(ConsistencyProof, response)

    def bundle(
        self,
        event_id: str,
        *,
        correlation_id: str | None = None,
    ) -> EvidenceProofBundle:
        response = self._request(
            "GET",
            f"/api/v1/bundles/{_event_id_path(event_id)}",
            correlation_id=correlation_id,
        )
        return _parse_model(EvidenceProofBundle, response)

    def verify_offline(
        self,
        bundle: EvidenceProofBundle | Mapping[str, Any],
        *,
        trust_store: TreeHeadTrustStore | None = None,
        policy: VerifierPolicy | None = None,
    ) -> VerifierOutcome:
        return verify_offline_bundle(bundle, trust_store=trust_store, policy=policy)

    def verify_online(
        self,
        event_id: str,
        *,
        trust_store: TreeHeadTrustStore | None = None,
        policy: VerifierPolicy | None = None,
        correlation_id: str | None = None,
    ) -> VerifierOutcome:
        _event_id_path(event_id)
        return verify_online_event(
            self._config.base_url,
            event_id,
            trust_store=trust_store,
            policy=policy,
            headers=self._config.headers(correlation_id),
            allowed_hosts=(self._config.hostname,),
            allow_insecure_http=self._config.allow_insecure_http,
            timeout_seconds=self._config.timeout_seconds,
            max_response_bytes=self._config.max_response_bytes,
        )


class AsyncETSClient:
    """Asynchronous ETS Application SDK v1 client with the same wire semantics."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        allow_insecure_http: bool = False,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = _configuration(
            base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            allow_insecure_http=allow_insecure_http,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

    async def __aenter__(self) -> AsyncETSClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()

    @property
    def base_url(self) -> str:
        return self._config.base_url

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str | None = None,
        json: object | None = None,
        params: Mapping[str, object] | None = None,
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method,
                path,
                headers=self._config.headers(correlation_id),
                json=json,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise ETSApplicationError("transport_error", "ETS API request failed") from exc
        _validate_response_size(response, self._config.max_response_bytes)
        if response.is_error:
            _raise_api_error(response)
        return response

    async def health(self) -> ServiceHealthV1:
        return _parse_model(ServiceHealthV1, await self._request("GET", "/health"))

    async def version(self) -> ServiceVersionV1:
        return _parse_model(ServiceVersionV1, await self._request("GET", "/version"))

    async def check_compatibility(self) -> ServiceVersionV1:
        version = await self.version()
        if version.api_version not in APPLICATION_SDK_COMPATIBILITY_V1.api_versions:
            raise ETSApplicationError(
                "incompatible_version",
                f"ETS API version {version.api_version!r} is not supported by "
                f"{APPLICATION_SDK_COMPATIBILITY_V1.sdk_contract}",
            )
        return version

    async def capture(
        self,
        evidence: EvidenceEvent | Mapping[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> EventCommitReceiptV1:
        event = create_evidence(evidence)
        response = await self._request(
            "POST",
            "/api/v1/events",
            correlation_id=correlation_id,
            json=event.model_dump(mode="json"),
        )
        return _receipt(response)

    async def get_event(
        self,
        event_id: str,
        *,
        correlation_id: str | None = None,
    ) -> EventRecordV1:
        response = await self._request(
            "GET",
            f"/api/v1/events/{_event_id_path(event_id)}",
            correlation_id=correlation_id,
        )
        return _parse_model(EventRecordV1, response)

    async def list_events(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        correlation_id: str | None = None,
    ) -> EventPageV1:
        response = await self._request(
            "GET",
            "/api/v1/events",
            correlation_id=correlation_id,
            params=_pagination(limit, offset),
        )
        return _parse_model(EventPageV1, response)

    async def inclusion_proof(
        self,
        event_id: str,
        *,
        correlation_id: str | None = None,
    ) -> InclusionProof:
        response = await self._request(
            "GET",
            f"/api/v1/proofs/inclusion/{_event_id_path(event_id)}",
            correlation_id=correlation_id,
        )
        return _parse_model(InclusionProof, response)

    async def consistency_proof(
        self,
        from_size: int,
        *,
        to_size: int | None = None,
        correlation_id: str | None = None,
    ) -> ConsistencyProof:
        response = await self._request(
            "GET",
            "/api/v1/proofs/consistency",
            correlation_id=correlation_id,
            params=_consistency_params(from_size, to_size),
        )
        return _parse_model(ConsistencyProof, response)

    async def bundle(
        self,
        event_id: str,
        *,
        correlation_id: str | None = None,
    ) -> EvidenceProofBundle:
        response = await self._request(
            "GET",
            f"/api/v1/bundles/{_event_id_path(event_id)}",
            correlation_id=correlation_id,
        )
        return _parse_model(EvidenceProofBundle, response)

    def verify_offline(
        self,
        bundle: EvidenceProofBundle | Mapping[str, Any],
        *,
        trust_store: TreeHeadTrustStore | None = None,
        policy: VerifierPolicy | None = None,
    ) -> VerifierOutcome:
        return verify_offline_bundle(bundle, trust_store=trust_store, policy=policy)

    async def verify_online(
        self,
        event_id: str,
        *,
        trust_store: TreeHeadTrustStore | None = None,
        policy: VerifierPolicy | None = None,
        correlation_id: str | None = None,
    ) -> VerifierOutcome:
        _event_id_path(event_id)
        return await asyncio.to_thread(
            verify_online_event,
            self._config.base_url,
            event_id,
            trust_store=trust_store,
            policy=policy,
            headers=self._config.headers(correlation_id),
            allowed_hosts=(self._config.hostname,),
            allow_insecure_http=self._config.allow_insecure_http,
            timeout_seconds=self._config.timeout_seconds,
            max_response_bytes=self._config.max_response_bytes,
        )
