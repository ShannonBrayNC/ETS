"""Authenticated demo API for Agent 365 + Ranger R0 mission reconstruction.

This module exposes the verified mission-indexed reconstruction added by Step 6 as a
read-only HTTP boundary. Callers provide the exact ``mission_id`` and receive the
query-friendly retained-chain manifest plus explicit verifier status. Raw retained
source bytes are intentionally not returned by this endpoint.
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, model_validator

from ets.api.auth import AuthError, AuthPolicy, LocalHeaderAuthPolicy
from ets.demos.agent365_r0_correlation import Agent365R0CorrelationBundleV1
from ets.ranger.agent365_r0_correlation_store import (
    Agent365R0CorrelationStoreError,
    SQLiteAgent365R0CorrelationStore,
)
from ets.ranger.agent365_r0_mission_query import (
    RangerR0MissionChainManifest,
    RangerR0MissionIndex,
    RangerR0MissionQueryError,
)


class RangerR0MissionVerifierStatus(BaseModel):
    """Verifier state returned with one reconstructed mission chain."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    chain_verified: Literal[True] = True
    evidence_object_v2_verified: Literal[True] = True
    physical_result_supported: bool
    truth_claim_supported: Literal[False] = False
    verification_boundary: str = (
        "verified_retained_chain_and_independent_result_observation_do_not_establish_"
        "unbounded_physical_truth"
    )


class Agent365R0MissionCorrelationStatus(BaseModel):
    """Sanitized Microsoft observation state returned without raw source payload bodies."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    state: Literal["observed", "not_observed"]
    bundle: Agent365R0CorrelationBundleV1 | None = None
    raw_source_payloads_returned: Literal[False] = False
    tool_execution_success_proves_sharepoint_state: Literal[False] = False
    agent365_observation_proves_physical_result: Literal[False] = False
    claim_boundary: str = (
        "mission_api_returns_sanitized_agent365_correlation_references_not_raw_source_or_"
        "independent_physical_proof"
    )

    @model_validator(mode="after")
    def validate_state(self) -> Agent365R0MissionCorrelationStatus:
        if self.state == "observed" and self.bundle is None:
            raise ValueError("observed Agent 365 correlation requires a retained bundle")
        if self.state == "not_observed" and self.bundle is not None:
            raise ValueError("not_observed Agent 365 correlation cannot include a bundle")
        return self


class RangerR0MissionAPIResponse(BaseModel):
    """External demo representation of one verified Agent 365 + R0 mission."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.mission-api-response.v1"] = (
        "ets.demo.agent365-r0.mission-api-response.v1"
    )
    mission_id: str
    manifest: RangerR0MissionChainManifest
    verifier: RangerR0MissionVerifierStatus
    agent365_correlation: Agent365R0MissionCorrelationStatus | None = None


def create_agent365_r0_mission_app(
    mission_index: RangerR0MissionIndex,
    *,
    auth_policy: AuthPolicy | None = None,
    correlation_store: SQLiteAgent365R0CorrelationStore | None = None,
) -> FastAPI:
    """Create the read-only authenticated API for the frozen R0 demonstration."""

    request_auth_policy = auth_policy or LocalHeaderAuthPolicy()
    app = FastAPI(
        title="ETS Agent 365 + Ranger R0 Mission API",
        version="0.1.0",
        description=(
            "Authenticated mission_id lookup for the frozen Agent 365 + Ranger R0 "
            "evidence-chain demonstration."
        ),
    )
    app.state.mission_index = mission_index
    app.state.agent365_correlation_store = correlation_store

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "agent365-r0-mission-api"}

    @app.get(
        "/api/v1/demos/agent365-r0/missions/{mission_id}",
        response_model=RangerR0MissionAPIResponse,
        response_model_exclude_none=True,
        tags=["demo", "verifier"],
    )
    def get_mission(
        mission_id: str,
        request: Request,
    ) -> RangerR0MissionAPIResponse:
        _authorize_evidence_read(request, request_auth_policy)
        try:
            reconstruction = mission_index.reconstruct(mission_id)
        except RangerR0MissionQueryError as exc:
            if exc.code == "mission_not_found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": exc.code, "message": str(exc)},
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc

        manifest = reconstruction.manifest
        correlation = _correlation_status(mission_id, correlation_store)
        return RangerR0MissionAPIResponse(
            mission_id=mission_id,
            manifest=manifest,
            verifier=RangerR0MissionVerifierStatus(
                physical_result_supported=manifest.physical_result_supported,
            ),
            agent365_correlation=correlation,
        )

    return app


def _correlation_status(
    mission_id: str,
    store: SQLiteAgent365R0CorrelationStore | None,
) -> Agent365R0MissionCorrelationStatus | None:
    if store is None:
        return None
    if not store.contains(mission_id):
        return Agent365R0MissionCorrelationStatus(state="not_observed")
    try:
        bundle = store.load(mission_id)
    except Agent365R0CorrelationStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    if bundle.mission_id != mission_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "correlation_mission_mismatch",
                "message": "retained Agent 365 correlation belongs to another mission_id",
            },
        )
    return Agent365R0MissionCorrelationStatus(
        state="observed",
        bundle=bundle,
    )


def _authorize_evidence_read(request: Request, auth_policy: AuthPolicy) -> None:
    try:
        context = auth_policy.authenticate(request)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ETS_AUTH_REQUIRED", "message": str(exc)},
        ) from exc

    if not context.has_capability("evidence.read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ETS_EVIDENCE_READ_FORBIDDEN",
                "message": "authenticated principal lacks evidence.read capability",
            },
        )


__all__ = [
    "Agent365R0MissionCorrelationStatus",
    "RangerR0MissionAPIResponse",
    "RangerR0MissionVerifierStatus",
    "create_agent365_r0_mission_app",
]
