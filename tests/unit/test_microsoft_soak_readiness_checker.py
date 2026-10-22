import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "checker", Path(__file__).resolve().parents[2] / "scripts/check_microsoft_soak_readiness.py"
)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def bundle():
    candidate = dict.fromkeys(checker.TRUE_FIELDS, True)
    candidate.update(dict.fromkeys(checker.FALSE_FIELDS, False))
    candidate.update(
        schema_version="ets.live_microsoft.rc1d_pre_soak_candidate.v2",
        candidate_source_sha="a" * 40,
        candidate_image="etsq1a352eb89.azurecr.io/ets/hosted-q1@sha256:" + "b" * 64,
        candidate_image_digest="sha256:" + "b" * 64,
    )
    runs = {}
    # RC1D must run last; all other run order follows the contract.
    keys = list(checker.RUNS)[1:] + ["workflow_run_id"]
    for index, key in enumerate(keys, 1):
        candidate[key] = index
        runs[str(index)] = dict(
            id=index,
            head_sha="a" * 40,
            head_branch="main",
            event="workflow_dispatch",
            status="completed",
            conclusion="success",
            path=".github/workflows/" + checker.RUNS[key],
            created_at=f"2026-10-22T00:{index * 2:02}:00Z",
            updated_at=f"2026-10-22T00:{index * 2 + 1:02}:00Z",
        )
    return dict(reconciliation=candidate, runs=runs)


def test_missing_evidence_is_no_go():
    assert checker.check({}, "a" * 40)


def test_complete_synthetic_bundle_only_validates_offline_contract():
    assert checker.check(bundle(), "a" * 40) == []


def test_source_drift_is_rejected():
    assert checker.check(bundle(), "c" * 40)


def test_missing_fault_stage_is_rejected():
    value = bundle()
    value["reconciliation"].pop("gateway_fault_stage_verified")
    assert checker.check(value, "a" * 40)


def test_overlapping_recovery_health_runs_are_rejected():
    value = bundle()
    value["runs"]["4"]["created_at"] = "2026-10-22T00:06:00Z"
    assert checker.check(value, "a" * 40)


def test_green_scheduled_run_cannot_supply_manual_gate():
    value = bundle()
    value["runs"]["1"]["event"] = "schedule"
    assert checker.check(value, "a" * 40)


def test_q0_and_rc1b_must_complete_before_rc1d():
    for run_id in ("1", "2"):
        value = bundle()
        value["runs"][run_id]["created_at"] = "2026-10-23T00:00:00Z"
        value["runs"][run_id]["updated_at"] = "2026-10-23T00:01:00Z"
        assert checker.check(value, "a" * 40)


def test_every_run_rejects_impossible_chronology():
    value = bundle()
    for run_id in value["runs"]:
        changed = bundle()
        changed["runs"][run_id]["created_at"] = "2026-10-24T00:00:00Z"
        assert checker.check(changed, "a" * 40)


def test_every_run_requires_timezone_and_timestamps():
    for timestamp in (None, "2026-10-22T00:00:00", "not-a-timestamp"):
        value = bundle()
        value["runs"]["1"]["updated_at"] = timestamp
        assert checker.check(value, "a" * 40)
