"""Machine-verifiable acceptance semantics for ETS VectorRail/VRX.

This module evaluates the bounded laboratory qualification record for the low-energy,
mechanically captive VectorRail/VRX consequence-custody demonstrator. It does not
perform hardware control and does not authorize any expansion of the approved test
envelope.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_ACCEPTANCE_SCHEMA = "ranger.vectorrail-vrx-acceptance.v0.1"
_REQUIRED_GATES = {f"G{i}" for i in range(7)}
_REQUIRED_DRY_RUNS = {
    "BASELINE",
    "INTERLOCK_REJECTION",
    "CONTROLLER_RESET_FAULT",
    "REQUIRED_SENSOR_UNAVAILABLE",
    "CONTRADICTORY_OBSERVATIONS",
    "BLOCKED_MECHANICAL_RESPONSE",
    "FINAL_SAFE_STATE_FAILURE",
}


class VectorRailAcceptanceError(ValueError):
    """Raised when a VRX acceptance record is internally inconsistent."""


def verify_vectorrail_acceptance(record: Mapping[str, Any]) -> bool:
    """Verify semantic consistency of a VectorRail/VRX acceptance record.

    A record marked QUALIFIED is valid only when every G0-G6 gate passes, every
    required dry-run scenario passes, the final safe state is confirmed, and the
    independent acceptance verifier reports VERIFIED.
    """

    if record.get("schema_version") != _ACCEPTANCE_SCHEMA:
        raise VectorRailAcceptanceError(f"schema_version must be {_ACCEPTANCE_SCHEMA}")

    _require_nonempty(record, "acceptance_id")
    _require_nonempty(record, "vrx_device_id")
    _require_sha256(record.get("configuration_digest"), "configuration_digest")
    _require_nonempty(record, "reviewer_id")

    gates = record.get("gates")
    if not isinstance(gates, Sequence) or isinstance(gates, (str, bytes)):
        raise VectorRailAcceptanceError("gates must be an array")

    by_gate: dict[str, Mapping[str, Any]] = {}
    for gate in gates:
        if not isinstance(gate, Mapping):
            raise VectorRailAcceptanceError("gate entries must be objects")
        gate_id = gate.get("gate_id")
        if not isinstance(gate_id, str):
            raise VectorRailAcceptanceError("gate_id must be a string")
        if gate_id in by_gate:
            raise VectorRailAcceptanceError(f"duplicate gate: {gate_id}")
        by_gate[gate_id] = gate
        _verify_gate(gate)

    if set(by_gate) != _REQUIRED_GATES:
        missing = sorted(_REQUIRED_GATES - set(by_gate))
        unexpected = sorted(set(by_gate) - _REQUIRED_GATES)
        raise VectorRailAcceptanceError(
            f"acceptance requires exactly G0-G6 (missing={missing}, unexpected={unexpected})"
        )

    dry_runs = record.get("dry_runs")
    if not isinstance(dry_runs, Sequence) or isinstance(dry_runs, (str, bytes)):
        raise VectorRailAcceptanceError("dry_runs must be an array")

    by_scenario: dict[str, Mapping[str, Any]] = {}
    for dry_run in dry_runs:
        if not isinstance(dry_run, Mapping):
            raise VectorRailAcceptanceError("dry-run entries must be objects")
        scenario = dry_run.get("scenario")
        if not isinstance(scenario, str):
            raise VectorRailAcceptanceError("dry-run scenario must be a string")
        if scenario in by_scenario:
            raise VectorRailAcceptanceError(f"duplicate dry-run scenario: {scenario}")
        by_scenario[scenario] = dry_run
        if dry_run.get("status") not in {"PASS", "FAIL", "NOT_RUN"}:
            raise VectorRailAcceptanceError(f"invalid dry-run status for {scenario}")

    if set(by_scenario) != _REQUIRED_DRY_RUNS:
        missing = sorted(_REQUIRED_DRY_RUNS - set(by_scenario))
        unexpected = sorted(set(by_scenario) - _REQUIRED_DRY_RUNS)
        raise VectorRailAcceptanceError(
            "acceptance requires exactly the seven required dry-run scenarios "
            f"(missing={missing}, unexpected={unexpected})"
        )

    verifier = record.get("verifier")
    if not isinstance(verifier, Mapping):
        raise VectorRailAcceptanceError("verifier must be an object")
    if verifier.get("profile") != "ets.vectorrail.acceptance-verifier.v0.1":
        raise VectorRailAcceptanceError("unsupported verifier profile")
    if verifier.get("status") not in {"VERIFIED", "FAILED", "NOT_RUN"}:
        raise VectorRailAcceptanceError("invalid verifier status")
    digest = verifier.get("evidence_package_digest")
    if digest is not None:
        _require_sha256(digest, "evidence_package_digest")

    qualification = record.get("qualification")
    if qualification not in {"QUALIFIED", "NOT_QUALIFIED"}:
        raise VectorRailAcceptanceError("invalid qualification state")

    all_gates_pass = all(gate.get("status") == "PASS" for gate in by_gate.values())
    all_dry_runs_pass = all(
        dry_run.get("status") == "PASS" for dry_run in by_scenario.values()
    )
    safe_state_confirmed = record.get("final_safe_state") == "CONFIRMED"
    independently_verified = verifier.get("status") == "VERIFIED"

    qualifies = (
        all_gates_pass
        and all_dry_runs_pass
        and safe_state_confirmed
        and independently_verified
    )

    if qualification == "QUALIFIED" and not qualifies:
        raise VectorRailAcceptanceError(
            "QUALIFIED requires all G0-G6 gates PASS, all required dry runs PASS, "
            "final_safe_state CONFIRMED, and verifier VERIFIED"
        )
    if qualification == "NOT_QUALIFIED" and qualifies:
        raise VectorRailAcceptanceError(
            "record is internally inconsistent: all qualification conditions pass "
            "but qualification is NOT_QUALIFIED"
        )

    return True


def _verify_gate(gate: Mapping[str, Any]) -> None:
    gate_id = gate.get("gate_id")
    status = gate.get("status")
    if status not in {"PASS", "FAIL", "NOT_RUN"}:
        raise VectorRailAcceptanceError(f"invalid gate status for {gate_id}")

    checks = gate.get("checks")
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)) or not checks:
        raise VectorRailAcceptanceError(f"{gate_id} checks must be a non-empty array")

    check_statuses: list[str] = []
    seen: set[str] = set()
    for check in checks:
        if not isinstance(check, Mapping):
            raise VectorRailAcceptanceError(f"{gate_id} check entries must be objects")
        check_id = check.get("check_id")
        if not isinstance(check_id, str) or not check_id:
            raise VectorRailAcceptanceError(f"{gate_id} check_id must be non-empty")
        if check_id in seen:
            raise VectorRailAcceptanceError(f"duplicate check_id in {gate_id}: {check_id}")
        seen.add(check_id)
        check_status = check.get("status")
        if check_status not in {"PASS", "FAIL", "NOT_RUN"}:
            raise VectorRailAcceptanceError(f"invalid check status in {gate_id}:{check_id}")
        check_statuses.append(check_status)

    if status == "PASS" and any(item != "PASS" for item in check_statuses):
        raise VectorRailAcceptanceError(
            f"{gate_id} cannot PASS unless every constituent check passes"
        )
    if status == "FAIL" and not any(item == "FAIL" for item in check_statuses):
        raise VectorRailAcceptanceError(
            f"{gate_id} FAIL requires at least one failed constituent check"
        )
    if status == "NOT_RUN" and any(item != "NOT_RUN" for item in check_statuses):
        raise VectorRailAcceptanceError(
            f"{gate_id} NOT_RUN requires every constituent check to be NOT_RUN"
        )


def _require_nonempty(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise VectorRailAcceptanceError(f"{field} must be a non-empty string")
    return result


def _require_sha256(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise VectorRailAcceptanceError(f"{field} must be a sha256 digest")
    suffix = value.removeprefix("sha256:")
    if len(suffix) != 64 or any(ch not in "0123456789abcdef" for ch in suffix):
        raise VectorRailAcceptanceError(f"{field} must be lowercase sha256 hex")


__all__ = ["VectorRailAcceptanceError", "verify_vectorrail_acceptance"]
