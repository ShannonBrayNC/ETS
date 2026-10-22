"""Execute the actual embedded coordinator helpers without network or dispatch."""

import ast
import base64
import json
import re
import textwrap
from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github/workflows/live-m365-source-to-proof-soak.yml"
)
SOURCE = textwrap.dedent(
    WORKFLOW.read_text().split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
)


def helpers(**values):
    tree = ast.parse(SOURCE)
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"latest_state", "decode_state", "parse_time", "enforce_completion_gap"}
    ]
    namespace = dict(
        base64=base64,
        json=json,
        re=re,
        datetime=datetime,
        timezone=timezone,
        state_marker="ETS_MICROSOFT_P0_SOAK_STATE_B64=",
        api_base="https://example.invalid",
        issue_number=541,
        max_gap_minutes=110,
    )
    namespace.update(values)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(WORKFLOW), "exec"), namespace)
    return namespace


def comment(status):
    value = {"schema_version": "ets.live_microsoft.p0_soak.state.v1", "status": status}
    encoded = base64.urlsafe_b64encode(json.dumps(value).encode()).decode()
    return {"body": f"<!-- ETS_MICROSOFT_P0_SOAK_STATE_B64={encoded} -->"}


def test_latest_state_reads_beyond_first_hundred_comments():
    pages = [[comment("active")] + [{"body": "ordinary comment"}] * 99, [comment("invalidated")]]
    calls = []

    def api(method, url):
        calls.append(url)
        return pages[len(calls) - 1]

    assert helpers(api_json=api)["latest_state"]()["status"] == "invalidated"
    assert calls[-1].endswith("page=2")


def test_exact_full_page_fetches_empty_next_page():
    pages = [[comment("active")] * 100, []]
    assert helpers(api_json=lambda *args: pages.pop(0))["latest_state"]()["status"] == "active"
    assert not pages


def test_non_array_page_fails_closed():
    with pytest.raises(RuntimeError, match="array"):
        helpers(api_json=lambda *args: {})["latest_state"]()


@pytest.mark.parametrize("minute,allowed", [(109, True), (110, True), (111, False), (153, False)])
def test_completion_gap_uses_actual_completed_time(minute, allowed):
    check = helpers()["enforce_completion_gap"]
    prior = {"last_success_at": "2026-10-22T00:00:00Z"}
    completed = datetime.fromtimestamp(
        datetime(2026, 10, 22, tzinfo=UTC).timestamp() + minute * 60, UTC
    )
    if allowed:
        check(prior, completed)
    else:
        with pytest.raises(RuntimeError, match="completion"):
            check(prior, completed)


def test_initial_attempt_has_no_prior_gap():
    helpers()["enforce_completion_gap"](None, datetime.now(UTC))


def test_completion_check_precedes_success_count_and_noop_explained():
    assert SOURCE.index("enforce_completion_gap(prior, completed_at)") < SOURCE.index(
        "success_count = 1 if prior"
    )
    assert "this green " in SOURCE and "workflow is not soak qualification or progress." in SOURCE


def run_coordinator(monkeypatch, tmp_path, latest, minutes):
    """Execute all top-level workflow control flow with I/O boundaries replaced."""
    monkeypatch.chdir(tmp_path)
    evidence = tmp_path / "evidence/live-m365-source-to-proof-soak"
    evidence.mkdir(parents=True)
    env = {
        "GITHUB_REPOSITORY": "example/ETS",
        "GH_TOKEN": "synthetic-not-a-credential",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_RUN_ID": "1000",
        "GITHUB_SHA": "a" * 40,
        "SOAK_ISSUE": "541",
        "RC1D_WORKFLOW": "rc1d.yml",
        "SOURCE_WORKFLOW": "source.yml",
        "RC1B_WORKFLOW": "rc1b.yml",
        "RC1C_WORKFLOW": "rc1c.yml",
        "STATE_WORKFLOW": "state.yml",
        "CONNECTOR_INSTANCE_ID": "synthetic",
        "MIN_SOAK_HOURS": "72",
        "MIN_SUCCESSFUL_OBSERVATIONS": "72",
        "MAX_GAP_MINUTES": "110",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for key in ("RC1D_RUN_ID", "START_CONFIRMATION", "REQUESTED_MARKER", "RESTART_ACTIVE"):
        monkeypatch.delenv(key, raising=False)
    calls = {"dispatch": [], "posts": []}
    times = iter(minutes)

    def dispatch(workflow, inputs=None):
        calls["dispatch"].append(workflow)
        return {"id": len(calls["dispatch"])}

    def forbidden_api(*args):
        raise AssertionError("unexpected network API operation")

    replacements = {
        "api_json": forbidden_api,
        "latest_state": lambda: latest,
        "prior_failed_coordinator_run": lambda *args: None,
        "utc_now": lambda: datetime.fromtimestamp(
            datetime(2026, 10, 22, tzinfo=UTC).timestamp() + next(times) * 60, UTC
        ),
        "dispatch": dispatch,
        "wait_for_success": lambda *args: None,
        "download_artifact": lambda *args: {},
        "validate_source_observation": lambda *args: None,
        "validate_rc1b": lambda *args: None,
        "validate_rc1c": lambda *args: None,
        "validate_state": lambda *args: None,
        "post_state": lambda state, *args: calls["posts"].append(state),
    }
    tree = ast.parse(SOURCE)
    tree.body = [
        node
        for node in tree.body
        if not (isinstance(node, ast.FunctionDef) and node.name in replacements)
    ]
    return compile(tree, str(WORKFLOW), "exec"), replacements, calls, evidence


def test_late_completion_invalidates_without_increment(monkeypatch, tmp_path):
    prior = {
        "status": "active",
        "attempt_id": "synthetic-attempt",
        "rc1d_workflow_run_id": 10,
        "release_source_sha": "a" * 40,
        "release_image": "example@sha256:" + "b" * 64,
        "release_image_digest": "sha256:" + "b" * 64,
        "marker": "synthetic-marker",
        "started_at": "2026-10-22T00:00:00Z",
        "last_success_at": "2026-10-22T00:00:00Z",
        "success_count": 2,
    }
    program, namespace, calls, evidence = run_coordinator(
        monkeypatch, tmp_path, prior, [100, 111, 112]
    )
    with pytest.raises(RuntimeError, match="completion"):
        exec(program, namespace)
    assert len(calls["dispatch"]) == 4
    assert len(calls["posts"]) == 1
    assert calls["posts"][0]["status"] == "invalidated"
    assert calls["posts"][0]["success_count"] == 2
    assert json.loads((evidence / "observation.json").read_text())["status"] == "invalidated"


def test_inactive_schedule_writes_only_skipped_evidence(monkeypatch, tmp_path):
    program, namespace, calls, evidence = run_coordinator(
        monkeypatch, tmp_path, {"status": "invalidated"}, []
    )
    with pytest.raises(SystemExit) as stopped:
        exec(program, namespace)
    assert stopped.value.code == 0
    assert calls == {"dispatch": [], "posts": []}
    assert json.loads((evidence / "observation.json").read_text())["status"] == (
        "skipped_no_active_attempt"
    )
    assert "not soak qualification or progress" in (tmp_path / "summary.md").read_text()
