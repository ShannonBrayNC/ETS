"""Bounded credential-safe HTTPS transport for Gateway-to-Core relay."""

from __future__ import annotations

import json
from email.message import Message
from typing import Any, NoReturn, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.core import LogEntry
from ets.gateway.core_relay import (
    CoreRelayRetryableError,
    CoreRelayTerminalError,
    ScopedBearerTokenProvider,
    core_event_json,
)
from ets.runtime.sync_queue import SyncRecord

CORE_RELAY_USER_AGENT = "ets-gateway-core-relay/1.0"
CORE_RELAY_MAXIMUM_RESPONSE_BYTES = 1024 * 1024
CORE_RELAY_MAXIMUM_TIMEOUT_SECONDS = 60.0
CORE_RELAY_MAXIMUM_BEARER_BYTES = 16 * 1024


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> NoReturn:
        raise CoreRelayTerminalError(
            "ETS Core relay refused a redirect on a credential-bearing request"
        )


class ETSCoreHttpRelayClient:
    """Submit exact local EvidenceEvents to one configured private ETS Core endpoint."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 15.0,
        maximum_response_bytes: int = CORE_RELAY_MAXIMUM_RESPONSE_BYTES,
    ) -> None:
        self._base_url = _validate_base_url(base_url)
        if not 0.1 <= timeout_seconds <= CORE_RELAY_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("Core relay timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_response_bytes <= CORE_RELAY_MAXIMUM_RESPONSE_BYTES:
            raise ValueError("Core relay maximum_response_bytes exceeds qualified bound")
        self._timeout_seconds = timeout_seconds
        self._maximum_response_bytes = maximum_response_bytes
        self._opener = build_opener(_RejectRedirects())

    def relay(
        self,
        entry: LogEntry,
        record: SyncRecord,
        token_provider: ScopedBearerTokenProvider,
    ) -> dict[str, Any]:
        """Append one event or reconcile a prior successful append after a lost acknowledgement."""

        with token_provider.acquire(
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
        ) as lease:
            bearer = _bearer_text(lease.reveal())
            try:
                response = self._request_json(
                    method="POST",
                    path="/api/v1/events",
                    bearer=bearer,
                    body=core_event_json(entry),
                )
            except HTTPError as exc:
                if exc.code == 409:
                    return self._reconcile_existing(entry, bearer)
                self._raise_http_error(exc)
            except CoreRelayTerminalError:
                raise
            except (TimeoutError, URLError, OSError) as exc:
                raise CoreRelayRetryableError(
                    "ETS Core relay request failed before acknowledgement"
                ) from exc

        return _validate_append_acknowledgement(response, entry)

    def _reconcile_existing(self, entry: LogEntry, bearer: str) -> dict[str, Any]:
        event_id = quote(entry.event.event_id, safe="")
        try:
            response = self._request_json(
                method="GET",
                path=f"/api/v1/events/{event_id}",
                bearer=bearer,
                body=None,
            )
        except HTTPError as exc:
            self._raise_http_error(exc)
        except CoreRelayTerminalError:
            raise
        except (TimeoutError, URLError, OSError) as exc:
            raise CoreRelayRetryableError(
                "ETS Core duplicate reconciliation failed before acknowledgement"
            ) from exc

        event_hash = response.get("event_hash")
        event = response.get("event")
        if event_hash != entry.event_hash or not isinstance(event, dict):
            raise CoreRelayTerminalError(
                "ETS Core duplicate reconciliation did not match the local immutable event"
            )
        if event.get("event_id") != entry.event.event_id:
            raise CoreRelayTerminalError(
                "ETS Core duplicate reconciliation returned a different event identity"
            )
        return {
            "status": "already_present",
            "event_id": entry.event.event_id,
            "event_hash": entry.event_hash,
            "core_log_index": response.get("log_index"),
        }

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        bearer: str,
        body: bytes | None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {bearer}",
            "User-Agent": CORE_RELAY_USER_AGENT,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers=headers,
        )
        with self._opener.open(request, timeout=self._timeout_seconds) as response:
            response_body = response.read(self._maximum_response_bytes + 1)
            if len(response_body) > self._maximum_response_bytes:
                raise CoreRelayTerminalError(
                    "ETS Core response exceeded the qualified byte bound"
                )
            _validate_json_content_type(response.headers.get("Content-Type"))
        try:
            decoded = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CoreRelayTerminalError(
                "ETS Core response was not valid UTF-8 JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise CoreRelayTerminalError("ETS Core response JSON must be an object")
        return cast(dict[str, Any], decoded)

    @staticmethod
    def _raise_http_error(exc: HTTPError) -> NoReturn:
        if exc.code in {408, 425, 429} or 500 <= exc.code <= 599:
            raise CoreRelayRetryableError(
                f"ETS Core relay returned retryable HTTP {exc.code}"
            ) from exc
        if exc.code in {401, 403}:
            raise CoreRelayTerminalError(
                "ETS Core rejected the scoped relay credential"
            ) from exc
        raise CoreRelayTerminalError(
            f"ETS Core relay rejected the request with HTTP {exc.code}"
        ) from exc


def _validate_base_url(value: str) -> str:
    candidate = value.strip().rstrip("/")
    parsed = urlsplit(candidate)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Core relay base_url must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Core relay base_url must not contain user information")
    if parsed.query or parsed.fragment:
        raise ValueError("Core relay base_url must not contain query or fragment data")
    if parsed.path not in {"", "/"}:
        raise ValueError("Core relay base_url must not contain a path")
    return candidate


def _bearer_text(material: bytes) -> str:
    if not material or len(material) > CORE_RELAY_MAXIMUM_BEARER_BYTES:
        raise CoreRelayTerminalError("scoped Core relay credential is outside qualified bounds")
    try:
        token = material.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CoreRelayTerminalError(
            "scoped Core relay credential must be ASCII bearer material"
        ) from exc
    if any(character in token for character in "\r\n"):
        raise CoreRelayTerminalError("scoped Core relay credential contains invalid characters")
    return token


def _validate_json_content_type(value: str | None) -> None:
    if value is None:
        raise CoreRelayTerminalError("ETS Core response omitted Content-Type")
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise CoreRelayTerminalError("ETS Core response Content-Type is not JSON")


def _validate_append_acknowledgement(
    response: dict[str, Any],
    entry: LogEntry,
) -> dict[str, Any]:
    if response.get("event_id") != entry.event.event_id:
        raise CoreRelayTerminalError("ETS Core acknowledged a different event identity")
    if response.get("event_hash") != entry.event_hash:
        raise CoreRelayTerminalError("ETS Core acknowledged a different immutable event hash")
    log_index = response.get("log_index")
    proof_url = response.get("inclusion_proof_url")
    tree_head = response.get("tree_head")
    if not isinstance(log_index, int) or log_index < 0:
        raise CoreRelayTerminalError("ETS Core acknowledgement omitted a valid log index")
    if not isinstance(proof_url, str) or not proof_url.startswith("/"):
        raise CoreRelayTerminalError("ETS Core acknowledgement omitted a valid proof URL")
    if not isinstance(tree_head, dict):
        raise CoreRelayTerminalError("ETS Core acknowledgement omitted the signed tree head")
    return {
        "status": "accepted",
        "event_id": entry.event.event_id,
        "event_hash": entry.event_hash,
        "core_log_index": log_index,
        "inclusion_proof_url": proof_url,
        "tree_head": tree_head,
    }
