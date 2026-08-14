"""Bounded Microsoft Graph webhook ingress for G2E-B.

Endpoint validation and notification parsing remain a pre-admission boundary. When a
resource committer is configured, validated resource observations must complete the
shared Gateway local-append and durable-sync path before the webhook reports committed
acceptance. Lifecycle notifications remain operational subscription/gap state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from threading import Lock
from typing import Protocol

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response

from ets.connectors.enterprise.microsoft_graph import (
    GRAPH_DEFAULT_MAXIMUM_BODY_BYTES,
    MicrosoftGraphNotificationError,
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
    apply_graph_lifecycle_event,
    parse_graph_notification_collection,
    validate_graph_validation_token,
)
from ets.gateway.host import (
    GatewayHostController,
    GatewayHostLimitError,
    GatewayHostSaturatedError,
    UnsupportedContentEncodingError,
)
from ets.gateway.microsoft_graph_commit import (
    MicrosoftGraphResourceCommitRetryableError,
    MicrosoftGraphResourceCommitter,
    MicrosoftGraphResourceCommitTerminalError,
)

GRAPH_WEBHOOK_PATH = "/gateway/v1/microsoft/graph"


class MicrosoftGraphWebhookBodyTooLarge(ValueError):
    """Raised when a Graph webhook body exceeds its qualified byte bound."""


class MicrosoftGraphWebhookBodyTimeout(ValueError):
    """Raised when the Graph request body misses the pre-commit read deadline."""


class MicrosoftGraphSubscriptionStore(Protocol):
    """Operational subscription state required by the webhook trust boundary."""

    def snapshot(self) -> Mapping[str, MicrosoftGraphSubscriptionStateV1]: ...

    def apply_lifecycle(
        self,
        notification: MicrosoftGraphNotificationV1,
    ) -> MicrosoftGraphSubscriptionStateV1: ...


class InMemoryMicrosoftGraphSubscriptionStore:
    """Thread-safe non-durable store for tests and explicit local composition."""

    def __init__(
        self,
        subscriptions: Mapping[str, MicrosoftGraphSubscriptionStateV1],
    ) -> None:
        self._lock = Lock()
        self._subscriptions = dict(subscriptions)

    def snapshot(self) -> Mapping[str, MicrosoftGraphSubscriptionStateV1]:
        with self._lock:
            return dict(self._subscriptions)

    def apply_lifecycle(
        self,
        notification: MicrosoftGraphNotificationV1,
    ) -> MicrosoftGraphSubscriptionStateV1:
        with self._lock:
            try:
                current = self._subscriptions[notification.subscription_id]
            except KeyError as exc:
                raise MicrosoftGraphNotificationError(
                    "Graph lifecycle notification references an unknown subscription"
                ) from exc
            updated = apply_graph_lifecycle_event(current, notification)
            self._subscriptions[updated.subscription_id] = updated
            return updated


def create_microsoft_graph_webhook_app(
    subscription_store: MicrosoftGraphSubscriptionStore,
    *,
    resource_committer: MicrosoftGraphResourceCommitter | None = None,
    host_controller: GatewayHostController | None = None,
    maximum_body_bytes: int = GRAPH_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_notifications: int = 100,
) -> FastAPI:
    """Create the bounded Graph webhook app with optional governed commitment."""

    if maximum_body_bytes < 1:
        raise ValueError("maximum_body_bytes must be positive")
    if not 1 <= maximum_notifications <= 100:
        raise ValueError("maximum_notifications must be between 1 and 100")

    app = FastAPI(title="ETS Gateway Microsoft Graph Webhook", version="0.2.0-g2e-b")
    host = host_controller or GatewayHostController()

    @app.post(GRAPH_WEBHOOK_PATH)
    async def receive_graph_webhook(request: Request) -> Response:
        try:
            host.validate_headers(request.scope.get("headers", ()))
            host.validate_content_encoding(request.headers.get("Content-Encoding"))
            async with host.admission():
                validation_response = _validation_response(request)
                if validation_response is not None:
                    return validation_response

                if request.query_params:
                    raise MicrosoftGraphNotificationError(
                        "Graph notification request contains unsupported query parameters"
                    )
                _validate_json_content_type(request)
                try:
                    async with asyncio.timeout(host.policy.body_read_timeout_seconds):
                        body = await _read_bounded_body(request, maximum_body_bytes)
                except TimeoutError as exc:
                    raise MicrosoftGraphWebhookBodyTimeout(
                        "Graph webhook body read exceeded pre-commit deadline"
                    ) from exc

                batch = parse_graph_notification_collection(
                    body,
                    subscriptions=subscription_store.snapshot(),
                    maximum_body_bytes=maximum_body_bytes,
                    maximum_notifications=maximum_notifications,
                )
                lifecycle_updates = 0
                resource_commits = 0
                for notification in batch.notifications:
                    if notification.kind == "lifecycle":
                        subscription_store.apply_lifecycle(notification)
                        lifecycle_updates += 1
                    elif resource_committer is not None:
                        await asyncio.to_thread(resource_committer.commit, notification)
                        resource_commits += 1

        except UnsupportedContentEncodingError:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"detail": "Graph webhook content encoding is not qualified"},
            )
        except GatewayHostLimitError:
            return JSONResponse(
                status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
                content={"detail": "Graph webhook headers exceed configured host limits"},
            )
        except GatewayHostSaturatedError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Graph webhook host concurrency is saturated"},
                headers={"Retry-After": "1"},
            )
        except MicrosoftGraphWebhookBodyTimeout:
            return JSONResponse(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                content={"detail": "Graph webhook body read exceeded pre-commit deadline"},
            )
        except MicrosoftGraphWebhookBodyTooLarge:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Graph webhook body exceeds configured limit"},
            )
        except MicrosoftGraphResourceCommitRetryableError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Graph resource commitment is temporarily unavailable"},
                headers={"Retry-After": "1"},
            )
        except MicrosoftGraphResourceCommitTerminalError:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "Graph resource observation failed Gateway admission"},
            )
        except MicrosoftGraphNotificationError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "invalid Microsoft Graph webhook request"},
            )

        if resource_committer is None:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "accepted_pre_commit",
                    "notification_count": len(batch.notifications),
                    "lifecycle_updates": lifecycle_updates,
                },
            )

        acceptance = "accepted_committed" if resource_commits else "accepted_operational"
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": acceptance,
                "notification_count": len(batch.notifications),
                "resource_commits": resource_commits,
                "lifecycle_updates": lifecycle_updates,
            },
        )

    return app


def _validation_response(request: Request) -> Response | None:
    values = request.query_params.getlist("validationToken")
    if not values:
        return None
    if len(values) != 1 or len(request.query_params.multi_items()) != 1:
        raise MicrosoftGraphNotificationError(
            "Graph endpoint validation requires exactly one validationToken"
        )
    token = validate_graph_validation_token(values[0])
    return Response(
        content=token,
        status_code=status.HTTP_200_OK,
        headers={"Content-Type": "text/plain"},
    )


def _validate_json_content_type(request: Request) -> None:
    media_type = request.headers.get("Content-Type", "").partition(";")[0].strip().lower()
    if media_type != "application/json":
        raise MicrosoftGraphNotificationError(
            "Graph notification request requires application/json"
        )


async def _read_bounded_body(request: Request, maximum: int) -> bytes:
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise MicrosoftGraphNotificationError(
                "Graph webhook Content-Length is invalid"
            ) from exc
        if declared_length < 0:
            raise MicrosoftGraphNotificationError(
                "Graph webhook Content-Length is invalid"
            )
        if declared_length > maximum:
            raise MicrosoftGraphWebhookBodyTooLarge(
                "Graph webhook body exceeds configured limit"
            )

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > maximum:
            raise MicrosoftGraphWebhookBodyTooLarge(
                "Graph webhook body exceeds configured limit"
            )
        chunks.append(chunk)
    return b"".join(chunks)
