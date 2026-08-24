import base64
import json
import sys
from email.message import Message
from pathlib import Path
from types import ModuleType, SimpleNamespace
from urllib.request import Request

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-microsoft-rc1c-subscription-recovery.yml"
).read_text(encoding="utf-8")
BICEP = (
    ROOT / "infra" / "azure" / "ets-live-microsoft-rc1c-subscription-recovery.bicep"
).read_text(encoding="utf-8")
DOC = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1C_SUBSCRIPTION_RECOVERY_V1.md"
).read_text(encoding="utf-8")
SEQUENCE = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md"
).read_text(encoding="utf-8")
PRE_SOAK = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_PRE_SOAK_GATE_V1.md"
).read_text(encoding="utf-8")
BICEP_WORKFLOW = (ROOT / ".github" / "workflows" / "hosted-azure-bicep.yml").read_text(
    encoding="utf-8"
)


def _recovery_script() -> str:
    marker = "var recoveryScript = '''"
    start = BICEP.index(marker) + len(marker)
    end = BICEP.index("\n'''", start)
    return BICEP[start:end]


def _token(tenant_id: str, client_id: str) -> str:
    claims = {
        "aud": "https://manage.office.com",
        "tid": tenant_id,
        "appid": client_id,
        "roles": ["ActivityFeed.Read"],
    }
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "header." + encoded + ".signature"


class FixtureResponse:
    def __init__(self, payload: object | None, *, empty: bool = False) -> None:
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        self._body = b"" if empty else json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FixtureResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, limit: int) -> bytes:
        assert limit == 2 * 1024 * 1024 + 1
        return self._body


class FixtureOpener:
    def __init__(self, responses: list[FixtureResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[Request] = []

    def open(self, request: Request, *, timeout: float) -> FixtureResponse:
        assert timeout == 30.0
        self.requests.append(request)
        return self.responses.pop(0)


def _install_fixture_modules(
    monkeypatch: pytest.MonkeyPatch,
    *,
    token: str,
    opener: FixtureOpener,
) -> None:
    class FakeCredential:
        def __init__(self, *, client_id: str) -> None:
            assert client_id == "22222222-2222-2222-2222-222222222222"

        def get_token(self, scope: str) -> SimpleNamespace:
            assert scope == "https://manage.office.com/.default"
            return SimpleNamespace(token=token)

        def close(self) -> None:
            return None

    identity_module = ModuleType("azure.identity")
    identity_module.ManagedIdentityCredential = FakeCredential  # type: ignore[attr-defined]
    azure_module = ModuleType("azure")
    azure_module.identity = identity_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.identity", identity_module)
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: opener)
    monkeypatch.setattr("time.sleep", lambda _: None)
    monkeypatch.setenv("ETS_RC1C_PURVIEW_CLIENT_ID", "22222222-2222-2222-2222-222222222222")
    monkeypatch.setenv("ETS_RC1C_MICROSOFT_TENANT_ID", "11111111-1111-1111-1111-111111111111")


def test_rc1c_subscription_recovery_is_manual_protected_and_confirmation_gated() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in WORKFLOW
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in WORKFLOW
    assert 'test "$MUTATION_CONFIRMATION" = "START_STOP_RESTART_AUDIT_GENERAL"' in WORKFLOW
    assert "cancel-in-progress: false" in WORKFLOW
    assert "RESULT_ISSUE: '539'" in WORKFLOW
    assert 'export EXECUTION_STATUS="$status"' in WORKFLOW
    assert 'os.environ.get("EXECUTION_STATUS") != "Succeeded"' in WORKFLOW


def test_rc1c_subscription_recovery_reuses_exact_private_identity_boundary() -> None:
    for term in (
        "expected exactly one deployment-authoritative Microsoft Gateway",
        "live Microsoft Gateway ingress must remain internal",
        "live Microsoft Gateway must remain single replica",
        "live Microsoft Gateway image differs from the approved digest",
        "live Microsoft Gateway must attach exactly four user-assigned identities",
        "live Microsoft runtime identity client IDs are not distinct",
        "live Microsoft identity assignment set contains drift",
        "Graph lifecycle configuration is present inside the P0 deferral",
    ):
        assert term in WORKFLOW
    assert "gatewayStateStorageName" not in BICEP
    assert "volumeMounts: []" in BICEP
    assert "'${registryPullIdentityResourceId}': {}" in BICEP
    assert "'${purviewIdentityResourceId}': {}" in BICEP
    assert "identity: registryPullIdentityResourceId\n          lifecycle: 'None'" in BICEP
    assert "identity: purviewIdentityResourceId\n          lifecycle: 'Main'" in BICEP


def test_rc1c_subscription_recovery_is_exact_audit_general_polling_only() -> None:
    for term in (
        'CONTENT_TYPE = "Audit.General"',
        'MANAGEMENT_SCOPE = MANAGEMENT_ROOT + "/.default"',
        'claims.get("roles") != ["ActivityFeed.Read"]',
        '"subscriptions/start"',
        '"subscriptions/stop"',
        '"subscriptions/list"',
        '"subscriptions/content"',
        'initial_state != "absent"',
        'final_state != "enabled"',
        'failure_code = "recovery_restore_failed"',
        '"webhook_configuration_present"',
        '"start_created_webhook"',
        "MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024",
        "MAXIMUM_CONTENT_DESCRIPTORS = 5000",
    ):
        assert term in BICEP
    assert "graph.microsoft.com" not in BICEP
    assert "webhook_address" not in BICEP


def test_embedded_recovery_executes_absent_start_stop_restart_fixture(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    enabled = {"contentType": "Audit.General", "status": "enabled", "webhook": None}
    opener = FixtureOpener(
        [
            FixtureResponse([]),
            FixtureResponse(enabled),
            FixtureResponse([enabled]),
            FixtureResponse([]),
            FixtureResponse(None, empty=True),
            FixtureResponse([]),
            FixtureResponse(enabled),
            FixtureResponse([enabled]),
        ]
    )
    _install_fixture_modules(
        monkeypatch,
        token=_token(
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ),
        opener=opener,
    )

    exec(compile(_recovery_script(), "<rc1c-subscription-recovery>", "exec"), {})

    output = capsys.readouterr().out.strip()
    assert output.startswith("ETS_M365_RC1C_SUBSCRIPTION_RECOVERY_B64=")
    payload = json.loads(base64.urlsafe_b64decode(output.split("=", 1)[1]))
    assert payload["subscription_initial_state"] == "absent"
    assert payload["content_descriptors_observed"] == 0
    assert payload["subscription_stopped_state"] == "absent"
    assert payload["subscription_final_state"] == "enabled"
    assert payload["qualification_pass"] is True
    assert payload["rc1c_live_qualified"] is False
    assert payload["soak_clock_started"] is False
    assert [request.method for request in opener.requests] == [
        "GET",
        "POST",
        "GET",
        "GET",
        "POST",
        "GET",
        "POST",
        "GET",
    ]
    assert all(request.data is None for request in opener.requests)
    assert all("PublisherIdentifier=" in request.full_url for request in opener.requests)
    assert all("webhook" not in request.full_url.casefold() for request in opener.requests)


def test_embedded_recovery_restores_enabled_after_post_start_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    enabled = {"contentType": "Audit.General", "status": "enabled", "webhook": None}
    opener = FixtureOpener(
        [
            FixtureResponse([]),
            FixtureResponse(enabled),
            FixtureResponse([enabled]),
            FixtureResponse({}),
            FixtureResponse(enabled),
            FixtureResponse([enabled]),
        ]
    )
    _install_fixture_modules(
        monkeypatch,
        token=_token(
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ),
        opener=opener,
    )

    with pytest.raises(SystemExit) as raised:
        exec(compile(_recovery_script(), "<rc1c-subscription-recovery>", "exec"), {})

    assert raised.value.code == 1
    output = capsys.readouterr().out.strip()
    assert output.startswith("ETS_M365_RC1C_SUBSCRIPTION_RECOVERY_FAILURE_B64=")
    payload = json.loads(base64.urlsafe_b64decode(output.split("=", 1)[1]))
    assert payload["failure_code"] == "content_list_shape_invalid"
    assert payload["mutation_attempted"] is True
    assert payload["recovery_attempted"] is True
    assert payload["recovery_restored"] is True
    assert payload["subscription_final_state"] == "enabled"
    assert payload["qualification_pass"] is False


def test_rc1c_subscription_recovery_evidence_is_sanitized_and_nonfinal() -> None:
    for term in (
        '"raw_purview_payload_retained": False',
        '"customer_identifiers_retained": False',
        '"reusable_credential_retained": False',
        '"graph_operation_performed": False',
        '"rc1c_live_qualified": False',
        '"soak_clock_started": False',
        '"purview_subscription_mutation_performed": True',
        '"graph_permission_mutation_performed": False',
        '"graph_subscription_operation_performed": False',
    ):
        assert term in BICEP or term in WORKFLOW
    assert "Merging the workflow does not execute it." in DOC
    assert "Passing this gate is not completion of #539" in DOC
    assert "start/stop/restart" in SEQUENCE
    assert "start/stop/restart" in PRE_SOAK


def test_hosted_bicep_gate_compiles_rc1c_subscription_recovery_template() -> None:
    command = (
        "az bicep build --file "
        "infra/azure/ets-live-microsoft-rc1c-subscription-recovery.bicep --stdout"
    )
    assert command in BICEP_WORKFLOW
