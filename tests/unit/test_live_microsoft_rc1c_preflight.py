import base64
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from urllib.request import Request

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "live-microsoft-rc1c-preflight.yml").read_text(
    encoding="utf-8"
)
BICEP = (ROOT / "infra" / "azure" / "ets-live-microsoft-rc1c-preflight.bicep").read_text(
    encoding="utf-8"
)
DOC = (ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1C_LIVE_PREFLIGHT_V1.md").read_text(
    encoding="utf-8"
)
GRAPH_DOC = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_GRAPH_LIFECYCLE_COMPOSITION_V1.md"
).read_text(encoding="utf-8")
BICEP_WORKFLOW = (ROOT / ".github" / "workflows" / "hosted-azure-bicep.yml").read_text(
    encoding="utf-8"
)


def _probe_script() -> str:
    marker = "var probeScript = '''"
    start = BICEP.index(marker) + len(marker)
    end = BICEP.index("\n'''", start)
    return BICEP[start:end]


def test_rc1c_preflight_is_manual_protected_and_exact_source_pinned() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in WORKFLOW
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in WORKFLOW
    assert "registry/repository@sha256:<digest>" in WORKFLOW
    assert "RESULT_ISSUE: '539'" in WORKFLOW


def test_rc1c_preflight_requires_private_runtime_and_absent_graph_activation() -> None:
    for term in (
        "expected exactly one deployment-authoritative Microsoft Gateway",
        "live Microsoft Gateway ingress must remain internal",
        "live Microsoft Gateway must remain single replica",
        "live Microsoft Gateway image differs from the approved digest",
        "live Microsoft Gateway must attach exactly four user-assigned identities",
        "live Microsoft runtime identity client IDs are not distinct",
        "live Microsoft identity assignment set contains drift",
        "Graph lifecycle configuration is present before permission and ingress approval",
    ):
        assert term in WORKFLOW
    for name in (
        "ETS_GATEWAY_GRAPH_NOTIFICATION_URL",
        "ETS_GATEWAY_GRAPH_CLIENT_STATE",
        "ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON",
    ):
        assert name in WORKFLOW


def test_rc1c_job_attaches_only_purview_runtime_and_pull_identities() -> None:
    assert "'${registryPullIdentityResourceId}': {}" in BICEP
    assert "'${purviewIdentityResourceId}': {}" in BICEP
    assert "identity: registryPullIdentityResourceId\n          lifecycle: 'None'" in BICEP
    assert "identity: purviewIdentityResourceId\n          lifecycle: 'Main'" in BICEP
    assert "directoryIdentityResourceId" not in BICEP
    assert "sharePointIdentityResourceId" not in BICEP
    assert "ManagedIdentityCredential(client_id=PURVIEW_CLIENT_ID)" in BICEP


def test_rc1c_purview_probe_is_exact_role_bounded_and_read_only() -> None:
    for term in (
        'MANAGEMENT_SCOPE = MANAGEMENT_ROOT + "/.default"',
        'if claims.get("aud") != MANAGEMENT_ROOT:',
        'roles != ["ActivityFeed.Read"]',
        'if "scp" in claims:',
        '"/activity/feed/subscriptions/list?"',
        '"PublisherIdentifier": MICROSOFT_TENANT_ID',
        'method="GET"',
        "MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024",
        "if len(subscriptions) > 16:",
        'content_type != "Audit.General"',
        'if item.get("webhook") is not None:',
    ):
        assert term in BICEP
    assert "/subscriptions/start" not in BICEP
    assert "/subscriptions/stop" not in BICEP
    assert 'method="POST"' not in BICEP


def test_rc1c_embedded_probe_executes_with_sanitized_read_only_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tenant_id = "11111111-1111-1111-1111-111111111111"
    client_id = "22222222-2222-2222-2222-222222222222"
    instance_id = "m365-sharepoint-primary.purview-audit-general"
    instance = {
        "connector_id": "microsoft.purview.activity",
        "authentication": {"credential_ref": "azure-mi://office-365-management/purview"},
        "settings": {
            "content_type": "Audit.General",
            "include_client_ip": False,
            "service_specific_allowlist": [],
        },
    }
    with sqlite3.connect(tmp_path / "connector-runtime.db") as connection:
        connection.executescript(
            """
            CREATE TABLE connector_instances(instance_id TEXT PRIMARY KEY, payload_json TEXT);
            CREATE TABLE connector_runtime(
                instance_id TEXT PRIMARY KEY,
                checkpoint_json TEXT,
                checkpoint_revision INTEGER,
                retry_count INTEGER,
                last_success_at_utc TEXT,
                observation_state TEXT,
                gap_open INTEGER,
                lease_owner TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO connector_instances(instance_id, payload_json) VALUES (?, ?)",
            (instance_id, json.dumps(instance)),
        )
        connection.execute(
            """
            INSERT INTO connector_runtime(
                instance_id, checkpoint_json, checkpoint_revision, retry_count,
                last_success_at_utc, observation_state, gap_open, lease_owner
            ) VALUES (?, NULL, 0, 0, NULL, 'unknown_observation', 0, NULL)
            """,
            (instance_id,),
        )

    claims = {
        "aud": "https://manage.office.com",
        "tid": tenant_id,
        "appid": client_id,
        "roles": ["ActivityFeed.Read"],
    }
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    token = "header." + encoded + ".signature"

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

    class FakeHeaders:
        @staticmethod
        def get_content_type() -> str:
            return "application/json"

    class FakeResponse:
        status = 200
        headers = FakeHeaders()

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def read(limit: int) -> bytes:
            assert limit == 2 * 1024 * 1024 + 1
            return b"[]"

    def fake_urlopen(request: Request, *, timeout: float) -> FakeResponse:
        assert timeout == 30.0
        assert request.method == "GET"
        url = request.full_url
        assert "/activity/feed/subscriptions/list?" in url
        assert "PublisherIdentifier=" in url
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("ETS_RC1C_INSTANCE_ID", "m365-sharepoint-primary")
    monkeypatch.setenv("ETS_RC1C_PURVIEW_CLIENT_ID", client_id)
    monkeypatch.setenv("ETS_RC1C_MICROSOFT_TENANT_ID", tenant_id)
    script = _probe_script().replace(
        'STATE_DIR = Path("/mnt/gateway-state")',
        f"STATE_DIR = Path({str(tmp_path)!r})",
    )

    exec(compile(script, "<rc1c-preflight>", "exec"), {})

    output = capsys.readouterr().out.strip()
    assert output.startswith("ETS_M365_RC1C_PREFLIGHT_B64=")
    payload = json.loads(base64.urlsafe_b64decode(output.split("=", 1)[1]))
    assert payload["purview_subscriptions_list_reachable"] is True
    assert payload["purview_subscription_status"] == "absent"
    assert payload["graph_durable_subscription_present"] is False
    assert payload["customer_identifiers_retained"] is False
    assert payload["rc1c_live_qualified"] is False


def test_rc1c_preflight_reads_state_query_only_and_rejects_graph_state() -> None:
    for term in (
        '"file:" + str(path) + "?mode=ro"',
        'connection.execute("PRAGMA query_only = ON")',
        'connect_ro("connector-runtime.db")',
        '"azure-mi://office-365-management/purview"',
        'settings.get("content_type") != "Audit.General"',
        'settings.get("include_client_ip") is not False',
        'settings.get("service_specific_allowlist") != []',
        'connect_ro("microsoft-graph-subscriptions.db")',
        '"SELECT COUNT(*) FROM graph_subscriptions"',
        "durable Graph subscription state exists before callback authorization",
    ):
        assert term in BICEP


def test_rc1c_evidence_is_sanitized_and_does_not_widen_claims() -> None:
    for term in (
        '"graph_durable_subscription_present": False',
        '"raw_purview_payload_retained": False',
        '"customer_identifiers_retained": False',
        '"reusable_credential_retained": False',
        '"public_evidence_safe": True',
        '"rc1c_live_qualified": False',
        '"soak_clock_started": False',
    ):
        assert term in BICEP
    for key in (
        "graph_callback_ingress_external",
        "graph_lifecycle_configuration_present",
        "graph_subscription_permission_decision_pending",
        "rc1c_live_qualified",
        "soak_clock_started",
    ):
        assert f'"{key}"' in WORKFLOW
    assert "Passing this gate is not completion of #539" in DOC
    assert "Merging the workflow does not execute it." in DOC
    assert "Files.Read.All" in DOC
    assert "Sites.Selected" in DOC
    assert "MUST NOT be represented as live-ready" in " ".join(GRAPH_DOC.split())


def test_hosted_bicep_gate_compiles_rc1c_preflight_template() -> None:
    command = "az bicep build --file infra/azure/ets-live-microsoft-rc1c-preflight.bicep --stdout"
    assert command in BICEP_WORKFLOW
