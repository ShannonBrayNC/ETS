import ast
import base64
import json
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "live-microsoft-rc1b-preflight.yml").read_text(
    encoding="utf-8"
)
BICEP = (ROOT / "infra" / "azure" / "ets-live-microsoft-rc1b-preflight.bicep").read_text(
    encoding="utf-8"
)
DOC = (ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1B_LIVE_PREFLIGHT_V1.md").read_text(
    encoding="utf-8"
)
BICEP_WORKFLOW = (ROOT / ".github" / "workflows" / "hosted-azure-bicep.yml").read_text(
    encoding="utf-8"
)


def _probe_script() -> str:
    marker = "var probeScript = '''"
    start = BICEP.index(marker) + len(marker)
    end = BICEP.index("\n'''", start)
    return BICEP[start:end]


def _probe_function(name: str) -> object:
    tree = ast.parse(_probe_script(), filename="ets-live-microsoft-rc1b-preflight.py")
    function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace: dict[str, object] = {}
    exec(compile(ast.fix_missing_locations(module), "<rc1b-probe-function>", "exec"), namespace)
    return namespace[name]


def test_rc1b_preflight_is_manual_protected_and_exact_source_pinned() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in WORKFLOW
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in WORKFLOW
    assert "registry/repository@sha256:<digest>" in WORKFLOW
    assert "RESULT_ISSUE: '540'" in WORKFLOW


def test_rc1b_preflight_requires_exact_private_runtime_and_identity_set() -> None:
    for term in (
        "expected exactly one deployment-authoritative Microsoft Gateway",
        "live Microsoft Gateway ingress must remain internal",
        "live Microsoft Gateway must remain single replica",
        "live Microsoft Gateway image differs from the approved digest",
        "live Microsoft Gateway must attach exactly four user-assigned identities",
        "live Microsoft runtime identity client IDs are not distinct",
        "live Microsoft identity assignment set contains drift",
    ):
        assert term in WORKFLOW
    assert "ETS_GATEWAY_DIRECTORY_MANAGED_IDENTITY_CLIENT_ID" in WORKFLOW
    assert "ETS_GATEWAY_PURVIEW_MANAGED_IDENTITY_CLIENT_ID" in WORKFLOW
    assert "ETS_GATEWAY_MICROSOFT_APPLICATION_ID" in WORKFLOW


def test_rc1b_job_attaches_only_directory_runtime_and_pull_identities() -> None:
    assert "'${registryPullIdentityResourceId}': {}" in BICEP
    assert "'${directoryIdentityResourceId}': {}" in BICEP
    assert "identity: registryPullIdentityResourceId\n          lifecycle: 'None'" in BICEP
    assert "identity: directoryIdentityResourceId\n          lifecycle: 'Main'" in BICEP
    assert "sharePointIdentityResourceId" not in BICEP
    assert "purviewIdentityResourceId" not in BICEP
    assert "ManagedIdentityCredential(client_id=DIRECTORY_CLIENT_ID)" in BICEP


def test_rc1b_graph_preflight_is_bounded_read_only_and_proves_denial() -> None:
    assert '"/v1.0/users/delta?$select=id&$top=1"' in BICEP
    assert '"/v1.0/groups/delta?$select=id&$top=1"' in BICEP
    assert 'method="GET"' in BICEP
    assert "if drive_status != 403:" in BICEP
    assert "directory identity was not denied access to the SharePoint drive" in BICEP
    assert "MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024" in BICEP
    assert "Microsoft Graph delta continuation escaped the qualified boundary" in BICEP


def test_rc1b_preflight_requires_stable_durable_state_and_core_sync() -> None:
    for term in (
        'connect_ro("connector-runtime.db")',
        'connect_ro("gateway-events.db")',
        'connect_ro("gateway-sync.db")',
        'item["checkpoint_kind"] == "delta"',
        'item["retry_count"] == 0',
        'item["observation_state"] == "healthy_observation"',
        'not item["gap_open"]',
        'not item["lease_active"]',
        'event_state["users"]["observed"]',
        'event_state["groups"]["observed"]',
        'source_id = capture.get("source_id")',
        'source_id == USERS_INSTANCE_ID',
        'source_id == GROUPS_INSTANCE_ID',
        'failure_code = core_sync_failure_code(queue_state)',
    ):
        assert term in BICEP


def test_rc1b_evidence_is_sanitized_and_does_not_widen_claims() -> None:
    for term in (
        '"raw_directory_payload_retained": False',
        '"customer_identifiers_retained": False',
        '"reusable_credential_retained": False',
        '"public_evidence_safe": True',
        '"rc1b_live_qualified": False',
        '"soak_clock_started": False',
    ):
        assert term in BICEP
    for key in (
        "raw_directory_payload_retained",
        "customer_identifiers_retained",
        "reusable_credential_retained",
        "rc1b_live_qualified",
        "soak_clock_started",
    ):
        assert f'"{key}"' in WORKFLOW
    assert "tombstone/replay/throttle/recovery gates remain" in WORKFLOW
    assert "No live preflight is performed merely by merging these assets." in DOC
    assert "Passing it is not completion of #540" in DOC
    assert "Microsoft source truth or universal tenant completeness" in DOC


def test_rc1b_runtime_failure_is_classified_before_job_cleanup() -> None:
    for term in (
        'FAILURE_MARKER = "ETS_M365_RC1B_PREFLIGHT_FAILURE_B64="',
        "sys.excepthook = emit_sanitized_failure",
        '"schema_version": "ets.live_microsoft.rc1b_preflight_runtime_failure.v1"',
        '"failure_code": FAILURE_CODE',
        'FAILURE_CODE = "directory_identity_token_acquisition_failed"',
        'FAILURE_CODE = "users_delta_request_failed"',
        'FAILURE_CODE = "groups_delta_request_failed"',
        'FAILURE_CODE = "directory_sharepoint_negative_control_failed"',
        'FAILURE_CODE = "directory_runtime_state_unavailable"',
        'return "directory_runtime_collection_gap"',
        'return "directory_runtime_retry_pending"',
        'return "directory_runtime_checkpoint_invalid"',
        'return "directory_runtime_initialization_incomplete"',
        'return "directory_runtime_observation_unhealthy"',
        'return "directory_runtime_collection_active"',
        'return "directory_runtime_state_unstable"',
        'FAILURE_CODE = "directory_event_state_incomplete"',
        'FAILURE_CODE = "directory_core_sync_state_unavailable"',
        'return "directory_core_sync_terminal_failure"',
        'return "directory_core_sync_retryable_failure"',
        'return "directory_core_sync_backlog"',
        'return "directory_core_sync_state_invalid"',
        'return "directory_core_sync_observation_absent"',
    ):
        assert term in BICEP

    assert "ETS_M365_RC1B_PREFLIGHT(_FAILURE)?_B64" in WORKFLOW
    assert "RC1B failure marker returned an unexpected public shape" in WORKFLOW
    assert "RC1B failure marker code is not allow-listed" in WORKFLOW
    assert '"failure_code": "bounded_failure_marker_unavailable"' in WORKFLOW
    assert '"schema_version": "ets.live_microsoft.rc1b_preflight_failure.v2"' in WORKFLOW
    assert "Both paths use the same sanitized" in DOC
    assert "if out.is_file():" in WORKFLOW
    assert WORKFLOW.index("az containerapp job logs show") < WORKFLOW.index(
        'if [ "$status" != "Succeeded" ]'
    )


def test_rc1b_runtime_failure_classification_is_ordered_and_bounded() -> None:
    namespace = {"runtime_is_stable": _probe_function("runtime_is_stable")}
    tree = ast.parse(_probe_script(), filename="ets-live-microsoft-rc1b-preflight.py")
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "runtime_failure_code"
    )
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), "<runtime-failure-code>", "exec"), namespace)
    classify = namespace["runtime_failure_code"]
    assert callable(classify)

    def snapshot(**overrides: object) -> dict[str, dict[str, object]]:
        baseline: dict[str, object] = {
            "checkpoint_present": True,
            "checkpoint_revision": 1,
            "checkpoint_kind": "delta",
            "retry_count": 0,
            "last_success_present": True,
            "observation_state": "healthy_observation",
            "gap_open": False,
            "lease_active": False,
        }
        return {"users": {**baseline, **overrides}, "groups": dict(baseline)}

    assert classify(snapshot()) is None
    assert classify(snapshot(lease_active=True)) == "directory_runtime_collection_active"
    assert classify(snapshot(observation_state="unknown")) == (
        "directory_runtime_observation_unhealthy"
    )
    assert classify(snapshot(checkpoint_present=False, checkpoint_kind="none")) == (
        "directory_runtime_initialization_incomplete"
    )
    assert classify(snapshot(checkpoint_revision=0)) == (
        "directory_runtime_initialization_incomplete"
    )
    assert classify(snapshot(checkpoint_kind="page")) == (
        "directory_runtime_initialization_incomplete"
    )
    assert classify(snapshot(checkpoint_kind="invalid")) == (
        "directory_runtime_checkpoint_invalid"
    )
    assert classify(snapshot(retry_count=1)) == "directory_runtime_retry_pending"
    assert classify(snapshot(observation_state="degraded_observation")) == (
        "directory_runtime_retry_pending"
    )
    assert classify(snapshot(gap_open=True)) == "directory_runtime_collection_gap"
    assert classify(
        snapshot(
            gap_open=True,
            retry_count=1,
            checkpoint_kind="invalid",
            lease_active=True,
        )
    ) == "directory_runtime_collection_gap"


def test_rc1b_core_sync_failure_classification_is_ordered_and_bounded() -> None:
    classify = _probe_function("core_sync_failure_code")
    assert callable(classify)

    def snapshot(**overrides: bool) -> dict[str, dict[str, bool]]:
        baseline = {
            "pending": False,
            "in_flight": False,
            "synchronized": True,
            "retryable_failure": False,
            "terminal_failure": False,
            "invalid": False,
        }
        return {"users": {**baseline, **overrides}, "groups": dict(baseline)}

    assert classify(snapshot()) is None
    assert classify(snapshot(synchronized=False)) == "directory_core_sync_observation_absent"
    assert classify(snapshot(invalid=True)) == "directory_core_sync_state_invalid"
    assert classify(snapshot(pending=True)) == "directory_core_sync_backlog"
    assert classify(snapshot(in_flight=True)) == "directory_core_sync_backlog"
    assert classify(snapshot(retryable_failure=True)) == "directory_core_sync_retryable_failure"
    assert classify(snapshot(terminal_failure=True)) == "directory_core_sync_terminal_failure"
    assert classify(
        snapshot(terminal_failure=True, retryable_failure=True, pending=True, invalid=True)
    ) == "directory_core_sync_terminal_failure"


def test_rc1b_failure_marker_retains_no_raw_diagnostics() -> None:
    for term in (
        '"raw_directory_payload_retained": False',
        '"customer_identifiers_retained": False',
        '"reusable_credential_retained": False',
        '"public_evidence_safe": True',
        '"rc1b_live_qualified": False',
        '"soak_clock_started": False',
    ):
        assert term in BICEP
    assert "deletes the private raw log before uploading evidence" in DOC
    assert "trap 'rm -f \"$raw\"' EXIT" in WORKFLOW
    artifact_path = WORKFLOW.split("path: evidence/live-microsoft-rc1b-preflight/*.json", 1)
    assert len(artifact_path) == 2
    assert "microsoft-rc1b-preflight.log" not in artifact_path[1]


def test_rc1b_embedded_probe_and_workflow_python_are_syntactically_valid() -> None:
    ast.parse(_probe_script(), filename="ets-live-microsoft-rc1b-preflight.py")

    remaining = WORKFLOW
    parsed = 0
    while "<<'PY'" in remaining:
        _, remaining = remaining.split("<<'PY'", 1)
        script, remaining = remaining.split("\n          PY", 1)
        ast.parse(
            textwrap.dedent(script).lstrip("\n"),
            filename="live-microsoft-rc1b-preflight-inline.py",
        )
        parsed += 1
    assert parsed >= 4


def test_rc1b_failure_hook_emits_only_the_bounded_public_marker(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    identity_module = ModuleType("azure.identity")
    identity_module.ManagedIdentityCredential = object  # type: ignore[attr-defined]
    azure_module = ModuleType("azure")
    azure_module.identity = identity_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.identity", identity_module)
    monkeypatch.setenv("ETS_RC1B_INSTANCE_ID", "m365-sharepoint-primary")
    monkeypatch.setenv("ETS_RC1B_DIRECTORY_CLIENT_ID", "redacted-client-id")
    monkeypatch.setenv("ETS_RC1B_SHAREPOINT_DRIVE_ID", "redacted-drive-id")
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)

    initialization = _probe_script().split("\ndef request_json", 1)[0]
    namespace: dict[str, object] = {}
    exec(compile(initialization, "<rc1b-preflight-init>", "exec"), namespace)
    namespace["FAILURE_CODE"] = "directory_runtime_state_unstable"
    hook = namespace["emit_sanitized_failure"]
    assert callable(hook)
    hook(RuntimeError, RuntimeError("private diagnostic must not enter marker"), None)

    output = capsys.readouterr().out.strip()
    assert output.startswith("ETS_M365_RC1B_PREFLIGHT_FAILURE_B64=")
    encoded = output.split("=", 1)[1]
    payload = json.loads(base64.urlsafe_b64decode(encoded))
    assert payload == {
        "schema_version": "ets.live_microsoft.rc1b_preflight_runtime_failure.v1",
        "failure_code": "directory_runtime_state_unstable",
        "raw_directory_payload_retained": False,
        "customer_identifiers_retained": False,
        "reusable_credential_retained": False,
        "public_evidence_safe": True,
        "rc1b_live_qualified": False,
        "soak_clock_started": False,
    }
    assert "private diagnostic" not in output
    assert "redacted-client-id" not in output
    assert "redacted-drive-id" not in output


def test_hosted_bicep_gate_compiles_rc1b_preflight_template() -> None:
    command = "az bicep build --file infra/azure/ets-live-microsoft-rc1b-preflight.bicep --stdout"
    assert command in BICEP_WORKFLOW
