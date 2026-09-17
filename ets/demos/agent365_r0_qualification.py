"""Repeatable end-to-end qualification for the frozen Agent 365 + Ranger R0 demo.

This harness is intentionally bounded.  It exercises the exact reference mission used by
our P0 demonstration from Microsoft-side authorization through Gateway dispatch, Ranger
R0 motion/stop evidence, Evidence Object v1/v2 closure, durable custody, process-style
store reopen, and mission_id reconstruction.

It is a software/reference qualification, not a substitute for live-tenant Graph/Agent
365 acquisition or a physical-hardware run.  Those observations can replace the bounded
reference inputs without changing the mission/evidence contracts exercised here.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from ets.demos.agent365_r0_mission import (
    SharePointMissionArtifactV1,
    authorize_mission,
    create_pending_mission,
)
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayR0DispatchBundle,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    SqliteMissionDispatchLedger,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0BoundaryRecordV1,
    RangerR0MotionDirectiveV1,
    RangerR0MotionStartObservationV1,
    RangerR0ReceiptMotionBoundary,
    RangerR0ResultObservationV1,
    RangerR0StopDirectiveV1,
    RangerR0StopObservationV1,
    SqliteRangerR0ReceiptLedger,
)
from ets.ranger.agent365_r0_evidence import build_agent365_r0_consequence_closure
from ets.ranger.agent365_r0_evidence_v2 import (
    SCENARIO_ID,
    promote_agent365_r0_closure_to_v2,
    verify_agent365_r0_evidence_v2,
)
from ets.ranger.agent365_r0_mission_store import SQLiteRangerR0MissionBundleStore

POLICY_VERSION = "r0-forward-stop-policy.v1"
DEFAULT_AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
DEFAULT_ARTIFACT_REF = "sharepoint://ETS-R0-Missions/items/reference"
DEFAULT_VEHICLE_ID = "ets-ranger:r0-demo"
DEFAULT_CONTROLLER_ID = "ranger-controller:r0"
DEFAULT_PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}


class Agent365R0QualificationError(RuntimeError):
    """Raised when the reference mission cannot complete the frozen P0 evidence chain."""


class Agent365R0QualificationReport(BaseModel):
    """Portable summary emitted only after the retained chain re-verifies after reopen."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.e2e-qualification.v1"] = (
        "ets.demo.agent365-r0.e2e-qualification.v1"
    )
    mission_id: str
    scenario_id: str
    policy_version: str
    authorization_artifact_ref: str
    stage_count: int
    retained_mission_count_after_restart: int
    decision_event_id: str
    decision_event_digest: str
    evidence_object_v1_id: str
    evidence_object_v1_hash: str
    evidence_object_v2_id: str
    evidence_object_v2_identity_hash: str
    chain_verified: Literal[True] = True
    evidence_object_v2_verified: Literal[True] = True
    physical_result_supported: Literal[True] = True
    truth_claim_supported: Literal[False] = False
    claim_boundary: str = (
        "reference_qualification_proves_contract_correlation_integrity_durable_reconstruction_"
        "and_independent_stopped_result_observation_but_not_unbounded_physical_truth"
    )


class _BoundaryRun(BaseModel):
    """Internal typed marker is intentionally not serialized as evidence."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    records: tuple[RangerR0BoundaryRecordV1, ...]
    motion_directive: RangerR0MotionDirectiveV1
    stop_directive: RangerR0StopDirectiveV1


def run_agent365_r0_reference_qualification(
    workdir: str | Path,
    *,
    mission_id: str | None = None,
    started_at: datetime | None = None,
    authorization_artifact_ref: str = DEFAULT_ARTIFACT_REF,
) -> Agent365R0QualificationReport:
    """Run the frozen reference mission and prove it survives durable reconstruction."""

    actual_mission_id = mission_id or str(uuid4())
    if not actual_mission_id.strip():
        raise Agent365R0QualificationError("mission_id must be a non-empty string")

    t0 = (started_at or datetime.now(UTC)).astimezone(UTC)
    base = Path(workdir)
    run_dir = base / actual_mission_id
    run_dir.mkdir(parents=True, exist_ok=True)

    mission = _authorized_mission(actual_mission_id, t0)
    dispatch = _dispatch(
        run_dir,
        mission,
        observed_at=t0,
        authorization_artifact_ref=authorization_artifact_ref,
    )
    boundary = _run_boundary(run_dir, mission, dispatch, t0=t0)

    closure = build_agent365_r0_consequence_closure(
        mission,
        dispatch,
        boundary.records,
        motion_directive=boundary.motion_directive,
        stop_directive=boundary.stop_directive,
    )
    bundle = promote_agent365_r0_closure_to_v2(closure)
    verification = verify_agent365_r0_evidence_v2(bundle)
    if not verification.valid or not verification.physical_result_supported:
        raise Agent365R0QualificationError(
            "Evidence Object v2 did not verify with an independently supported physical result"
        )

    store_path = run_dir / "mission-bundles.db"
    store = SQLiteRangerR0MissionBundleStore(store_path)
    try:
        store.save(bundle)
    finally:
        store.close()

    # Treat reopen as the minimum restart boundary: only durable bytes are available now.
    reopened = SQLiteRangerR0MissionBundleStore(store_path)
    try:
        retained_ids = reopened.mission_ids()
        reconstruction = reopened.build_index().reconstruct(actual_mission_id)
    finally:
        reopened.close()

    manifest = reconstruction.manifest
    if manifest.evidence_object_v1_hash != closure.evidence_object_hash:
        raise Agent365R0QualificationError(
            "reconstructed Evidence Object v1 hash differs after durable restart"
        )
    if manifest.evidence_object_v2_identity_hash != bundle.evidence_object_identity_hash:
        raise Agent365R0QualificationError(
            "reconstructed Evidence Object v2 identity differs after durable restart"
        )
    if not manifest.physical_result_supported:
        raise Agent365R0QualificationError(
            "reconstructed mission no longer supports the independent stopped result"
        )

    report = Agent365R0QualificationReport(
        mission_id=actual_mission_id,
        scenario_id=SCENARIO_ID,
        policy_version=POLICY_VERSION,
        authorization_artifact_ref=authorization_artifact_ref,
        stage_count=len(boundary.records),
        retained_mission_count_after_restart=len(retained_ids),
        decision_event_id=manifest.decision_event_id,
        decision_event_digest=manifest.decision_event_digest,
        evidence_object_v1_id=manifest.evidence_object_v1_id,
        evidence_object_v1_hash=manifest.evidence_object_v1_hash,
        evidence_object_v2_id=manifest.evidence_object_v2_id,
        evidence_object_v2_identity_hash=manifest.evidence_object_v2_identity_hash,
    )
    _write_report(run_dir / "qualification-report.json", report)
    return report


def _authorized_mission(mission_id: str, authorized_at: datetime) -> SharePointMissionArtifactV1:
    pending = create_pending_mission(
        policy_version=POLICY_VERSION,
        command_parameters=DEFAULT_PARAMETERS,
        mission_id_factory=lambda: mission_id,
    )
    return authorize_mission(
        pending,
        authorized_by_object_id=DEFAULT_AUTHORIZER_ID,
        authorized_at=authorized_at,
    )


def _dispatch(
    run_dir: Path,
    mission: SharePointMissionArtifactV1,
    *,
    observed_at: datetime,
    authorization_artifact_ref: str,
) -> GatewayR0DispatchBundle:
    request = GatewayR0MotionRequestV1(
        mission_id=mission.mission_id,
        policy_version=POLICY_VERSION,
        command_parameters=FrozenR0CommandParameters.model_validate(DEFAULT_PARAMETERS),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref=authorization_artifact_ref,
        delivery_id=f"qualification:{mission.mission_id}",
    )
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(run_dir / "gateway.db"))
    return guard.dispatch(request, mission, observed_at=observed_at)


def _run_boundary(
    run_dir: Path,
    mission: SharePointMissionArtifactV1,
    dispatch: GatewayR0DispatchBundle,
    *,
    t0: datetime,
) -> _BoundaryRun:
    boundary = RangerR0ReceiptMotionBoundary(
        SqliteRangerR0ReceiptLedger(run_dir / "ranger.db"),
        vehicle_id=DEFAULT_VEHICLE_ID,
        controller_id=DEFAULT_CONTROLLER_ID,
    )

    receipt = boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=t0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )
    authorized = boundary.authorize_motion(
        mission.mission_id,
        observed_at=t0 + timedelta(milliseconds=20),
        observed_monotonic_ns=20_000_000,
    )
    started = boundary.record_motion_started(
        RangerR0MotionStartObservationV1(
            mission_id=mission.mission_id,
            observer_id="sensor:encoder-fusion",
            observed_at=t0 + timedelta(milliseconds=30),
            observed_monotonic_ns=30_000_000,
            speed_mps=0.12,
            distance_travelled_m=0.01,
        )
    )
    stop_observed = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=mission.mission_id,
            observer_id="sensor:forward-range",
            observed_at=t0 + timedelta(seconds=2),
            observed_monotonic_ns=2_000_000_000,
            distance_travelled_m=0.40,
            elapsed_s=1.98,
            obstacle_distance_m=0.40,
        )
    )
    if stop_observed is None:
        raise Agent365R0QualificationError("reference stop condition did not trigger")

    stop_decided = boundary.decide_stop(
        mission.mission_id,
        observed_at=t0 + timedelta(seconds=2, milliseconds=5),
        observed_monotonic_ns=2_005_000_000,
    )
    stop_actuated = boundary.actuate_stop(
        mission.mission_id,
        observed_at=t0 + timedelta(seconds=2, milliseconds=10),
        observed_monotonic_ns=2_010_000_000,
    )
    result = boundary.record_result_observed(
        RangerR0ResultObservationV1(
            mission_id=mission.mission_id,
            observer_id="sensor:pose-witness",
            observed_at=t0 + timedelta(seconds=2, milliseconds=400),
            observed_monotonic_ns=2_400_000_000,
            speed_mps=0.0,
            distance_travelled_m=0.43,
            stationary_duration_ms=300,
        )
    )

    return _BoundaryRun(
        records=(
            receipt.receipt,
            authorized.record,
            started,
            stop_observed,
            stop_decided,
            stop_actuated.record,
            result,
        ),
        motion_directive=authorized.directive,
        stop_directive=stop_actuated.directive,
    )


def _write_report(path: Path, report: Agent365R0QualificationReport) -> None:
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workdir",
        default="qualification-output/agent365-r0",
        help="directory that will retain qualification ledgers, bundle store, and report",
    )
    parser.add_argument("--mission-id", default=None)
    args = parser.parse_args()

    report = run_agent365_r0_reference_qualification(
        args.workdir,
        mission_id=args.mission_id,
    )
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()


__all__ = [
    "Agent365R0QualificationError",
    "Agent365R0QualificationReport",
    "run_agent365_r0_reference_qualification",
]
