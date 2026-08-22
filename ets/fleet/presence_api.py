"""Thin HTTP ingress adapter for ETS Fleet presence operations."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError

from ets.fleet.presence import HeartbeatEnvelope, PresenceDecision
from ets.fleet.presence_ops import FleetPresenceCoordinator

MAX_EVENT_GRID_BODY_BYTES = 64 * 1024
MAX_EVENT_GRID_EVENTS = 16
MAX_HEARTBEAT_BODY_BYTES = 16 * 1024
_VALIDATION_EVENT = "Microsoft.EventGrid.SubscriptionValidationEvent"

EventGridAuthenticator = Callable[[Request], bool]


def build_fleet_presence_router(
    *,
    coordinator: FleetPresenceCoordinator,
    expected_iothub_resource_id: str,
    production: bool,
    event_grid_authenticator: EventGridAuthenticator | None = None,
) -> APIRouter:
    """Build bounded Fleet ingress routes without embedding Azure credentials in the app."""

    expected_source = expected_iothub_resource_id.rstrip("/").lower()
    if not expected_source:
        raise ValueError("expected IoT Hub resource ID is required")
    if production and event_grid_authenticator is None:
        raise ValueError("production Event Grid ingress requires Microsoft Entra authentication")

    router = APIRouter(prefix="/fleet/v1", tags=["fleet-presence"])

    @router.post("/azure/event-grid")
    async def event_grid_ingress(request: Request) -> dict[str, object]:
        if production:
            assert event_grid_authenticator is not None
            if not event_grid_authenticator(request):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="authenticated Event Grid delivery required",
                )

        body = await _bounded_body(request, MAX_EVENT_GRID_BODY_BYTES, "Event Grid")
        payload = _load_json(body, "Event Grid payload")
        if not isinstance(payload, list) or not payload:
            raise HTTPException(status_code=422, detail="Event Grid payload must be a non-empty array")
        if len(payload) > MAX_EVENT_GRID_EVENTS:
            raise HTTPException(status_code=413, detail="Event Grid batch exceeds event limit")
        if not all(isinstance(item, dict) for item in payload):
            raise HTTPException(status_code=422, detail="Event Grid batch items must be objects")

        events = [dict(item) for item in payload]
        if len(events) == 1 and _event_type(events[0]) == _VALIDATION_EVENT:
            return _validation_response(events[0], expected_source=expected_source)
        if any(_event_type(item) == _VALIDATION_EVENT for item in events):
            raise HTTPException(
                status_code=422,
                detail="subscription validation event must be delivered alone",
            )

        now = datetime.now(UTC)
        decisions = [
            coordinator.ingest_transport(item, received_at_utc=now)
            for item in events
        ]
        return {
            "accepted": sum(1 for item in decisions if item.accepted),
            "rejected": sum(1 for item in decisions if not item.accepted),
            "results": [_decision_payload(item) for item in decisions],
        }

    @router.post("/heartbeat")
    async def heartbeat_ingress(request: Request) -> dict[str, object]:
        body = await _bounded_body(request, MAX_HEARTBEAT_BODY_BYTES, "heartbeat")
        payload = _load_json(body, "heartbeat envelope")
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="heartbeat envelope must be a JSON object")
        try:
            envelope = HeartbeatEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail="heartbeat envelope failed validation") from exc
        decision = coordinator.ingest_heartbeat(
            envelope,
            received_at_utc=datetime.now(UTC),
        )
        return _decision_payload(decision)

    return router


async def _bounded_body(request: Request, limit: int, label: str) -> bytes:
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            if int(declared_length) > limit:
                raise HTTPException(status_code=413, detail=f"{label} body exceeds size limit")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid Content-Length") from exc
    body = await request.body()
    if len(body) > limit:
        raise HTTPException(status_code=413, detail=f"{label} body exceeds size limit")
    return body


def _load_json(body: bytes, label: str) -> Any:
    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} must be valid JSON") from exc


def _event_type(event: dict[str, Any]) -> str:
    value = event.get("eventType", event.get("type", ""))
    return value if isinstance(value, str) else ""


def _validation_response(event: dict[str, Any], *, expected_source: str) -> dict[str, str]:
    source = event.get("topic", event.get("source", ""))
    if not isinstance(source, str) or source.rstrip("/").lower() != expected_source:
        raise HTTPException(status_code=403, detail="unexpected Event Grid validation source")
    data = event.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="validation event data must be an object")
    validation_code = data.get("validationCode")
    if not isinstance(validation_code, str) or not 1 <= len(validation_code) <= 256:
        raise HTTPException(status_code=422, detail="validation code is missing or invalid")
    return {"validationResponse": validation_code}


def _decision_payload(decision: PresenceDecision) -> dict[str, object]:
    state = decision.state
    return {
        "accepted": decision.accepted,
        "reason": decision.reason.value,
        "device_id": decision.device_id,
        "transport_presence": None if state is None else state.transport_presence.value,
        "heartbeat_posture": None if state is None else state.heartbeat_posture.value,
        "registration_state": (
            None
            if state is None or state.registration_state is None
            else state.registration_state.value
        ),
        "evidence_verified": False,
        "health_asserted": False,
    }
