"""Authenticated demo API for Agent 365 + Ranger R0 mission reconstruction.

This module exposes the verified mission-indexed reconstruction added by Step 6 as a
read-only HTTP boundary. Callers provide the exact ``mission_id`` and receive the
query-friendly retained-chain manifest plus explicit verifier status. Raw retained
source bytes are intentionally not returned by this endpoint.
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from ets.api.auth import AuthError, AuthPolicy, LocalHeaderAuthPolicy
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


class RangerR0MissionAPIResponse(BaseModel):
    """External demo representation of one verified Agent 365 + R0 mission."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.mission-api-response.v1"] = (
        "ets.demo.agent365-r0.mission-api-response.v1"
    )
    mission_id: str
    manifest: RangerR0MissionChainManifest
    verifier: RangerR0MissionVerifierStatus


def create_agent365_r0_mission_app(
    mission_index: RangerR0MissionIndex,
    *,
    auth_policy: AuthPolicy | None = None,
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

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "agent365-r0-mission-api"}

    @app.get(
        "/api/v1/demos/agent365-r0/missions/{mission_id}",
        response_model=RangerR0MissionAPIResponse,
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
        return RangerR0MissionAPIResponse(
            mission_id=mission_id,
            manifest=manifest,
            verifier=RangerR0MissionVerifierStatus(
                physical_result_supported=manifest.physical_result_supported,
            ),
        )

    return app


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
    "RangerR0MissionAPIResponse",
    "RangerR0MissionVerifierStatus",
    "create_agent365_r0_mission_app",
]
