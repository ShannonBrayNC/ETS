#!/usr/bin/env python3
"""Offline evidence lint only: no network, dispatch, credentials, or freeze mutation."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

RUNS = {
    "workflow_run_id": "live-microsoft-rc1d-pre-soak-reconciliation.yml",
    "q0_workflow_run_id": "hosted-azure-q0-image.yml",
    "rc1b_workflow_run_id": "live-microsoft-rc1b-preflight.yml",
    "rc1c_workflow_run_id": "live-microsoft-rc1c-subscription-recovery.yml",
    "rc1c_live_health_workflow_run_id": "live-microsoft-rc1c-preflight.yml",
    "gateway_baseline_state_workflow_run_id": "live-sharepoint-state-boundary-probe.yml",
    "gateway_fault_stage_workflow_run_id": "live-sharepoint-relay-fault-stage.yml",
    "gateway_recovery_workflow_run_id": "live-sharepoint-relay-recovery.yml",
    "gateway_state_workflow_run_id": "live-sharepoint-state-boundary-probe.yml",
}
TRUE_FIELDS = (
    "q0_vulnerability_gate_passed",
    "q0_sbom_retained",
    "q0_provenance_required",
    "rc1b_live_qualified",
    "rc1c_live_qualified",
    "rc1c_live_health_verified",
    "gateway_fault_stage_verified",
    "gateway_recovery_verified",
    "gateway_durable_state_healthy",
    "graph_drive_subscriptions_deferred",
    "graph_subscription_configuration_absent",
    "public_evidence_safe",
    "pre_soak_reconciliation_passed",
    "freeze_ready",
)
FALSE_FIELDS = (
    "graph_subscription_operation_performed",
    "public_gateway_callback_configured",
    "broader_graph_file_permission_claimed",
    "credential_retained",
    "customer_identifiers_retained",
    "candidate_frozen",
    "soak_clock_started",
)


def check(bundle: dict, source: str) -> list[str]:
    errors = []
    candidate = bundle.get("reconciliation", {})
    if not re.fullmatch("[0-9a-f]{40}", source):
        errors.append("expected source must be a full canonical commit SHA")
    if candidate.get("schema_version") != "ets.live_microsoft.rc1d_pre_soak_candidate.v2":
        errors.append("missing RC1D v2 reconciliation")
    if candidate.get("candidate_source_sha") != source:
        errors.append("RC1D source does not match intended final main")
    image = candidate.get("candidate_image", "")
    if not isinstance(image, str) or not re.fullmatch(
        r"etsq1a352eb89\.azurecr\.io/[^@\s]+@sha256:[0-9a-f]{64}", image
    ):
        errors.append("missing canonical immutable private ACR image")
    elif candidate.get("candidate_image_digest") != image.rsplit("@", 1)[1]:
        errors.append("image digest is inconsistent")
    for key in TRUE_FIELDS:
        if candidate.get(key) is not True:
            errors.append(f"RC1D predicate not true: {key}")
    for key in FALSE_FIELDS:
        if candidate.get(key) is not False:
            errors.append(f"RC1D boundary not false: {key}")
    runs = bundle.get("runs", {})
    selected = {}
    times = {}
    for key, workflow in RUNS.items():
        run_id = candidate.get(key)
        if type(run_id) is not int or run_id <= 0:
            errors.append(f"missing valid run ID: {key}")
            continue
        run = runs.get(str(run_id), {})
        selected[key] = run
        expected = dict(
            id=run_id,
            head_sha=source,
            head_branch="main",
            event="workflow_dispatch",
            status="completed",
            conclusion="success",
            path=f".github/workflows/{workflow}",
        )
        for field, value in expected.items():
            if run.get(field) != value:
                errors.append(f"{key}: run metadata mismatch: {field}")
        try:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
            if created.tzinfo is None or updated.tzinfo is None or updated < created:
                raise ValueError("invalid run chronology")
            times[key] = (created, updated)
        except (KeyError, ValueError, TypeError, AttributeError):
            errors.append(f"{key}: missing or invalid timezone-aware run chronology")
    for key in RUNS:
        if key == "workflow_run_id":
            continue
        if key not in times or "workflow_run_id" not in times:
            errors.append(f"missing prerequisite completion proof: {key}")
        elif times[key][1] >= times["workflow_run_id"][0]:
            errors.append(f"prerequisite did not complete before RC1D: {key}")
    chains = [
        ["rc1c_workflow_run_id", "rc1c_live_health_workflow_run_id", "workflow_run_id"],
        [
            "gateway_baseline_state_workflow_run_id",
            "gateway_fault_stage_workflow_run_id",
            "gateway_recovery_workflow_run_id",
            "gateway_state_workflow_run_id",
            "workflow_run_id",
        ],
    ]
    for chain in chains:
        for before, after in zip(chain, chain[1:], strict=False):
            try:
                end = datetime.fromisoformat(selected[before]["updated_at"].replace("Z", "+00:00"))
                start = datetime.fromisoformat(selected[after]["created_at"].replace("Z", "+00:00"))
                if end.tzinfo is None or start.tzinfo is None or start <= end:
                    raise ValueError("overlapping or unzoned runs")
            except (KeyError, ValueError, TypeError, AttributeError):
                errors.append(f"missing strict completed-before-started proof: {before} -> {after}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle", type=Path, help="JSON with reconciliation and runs keyed by run ID"
    )
    parser.add_argument("--source", required=True, help="full intended final main SHA")
    args = parser.parse_args()
    try:
        errors = check(json.loads(args.bundle.read_text()), args.source)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        errors = [f"invalid or unreadable evidence bundle: {type(exc).__name__}"]
    print(
        json.dumps(
            {
                "evidence_lint": "NO_GO" if errors else "PASS_OFFLINE_ONLY",
                "launch_authorized": False,
                "live_readback_verified": False,
                "errors": errors,
                "remaining_operator_gates": [
                    "Verify current main still equals source after all intended fixes merge.",
                    "Retrieve artifacts; verify runtime, identities, roles, scope and marker.",
                    "Approve resource cost and bounded recovery/deployment operations separately.",
                    "Approve cadence and a new soak start; never resume the invalid attempt.",
                ],
            },
            indent=2,
        )
    )
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
