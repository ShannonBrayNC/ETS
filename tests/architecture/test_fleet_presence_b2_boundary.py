from __future__ import annotations

import ast
from pathlib import Path

OPS = Path("ets/fleet/presence_ops.py")
SQLITE = Path("ets/fleet/presence_sqlite.py")
INGRESS = Path("ets/fleet/presence_api.py")
DOC = Path("docs/fleet/ETS_FLEET_PRESENCE_B2.md")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def test_b2_does_not_embed_azure_sdk_or_product_plane_dependencies() -> None:
    imports = _imports(OPS) | _imports(SQLITE) | _imports(INGRESS)
    forbidden_prefixes = ("azure", "ets.core", "ets.edge", "ets.gateway")
    assert not any(
        imported == prefix or imported.startswith(prefix + ".")
        for imported in imports
        for prefix in forbidden_prefixes
    )


def test_production_event_grid_has_no_shared_secret_fallback() -> None:
    source = INGRESS.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "production and event_grid_authenticator is none" in lowered
    assert "microsoft entra authentication" in lowered
    assert "query_params" not in source
    assert "sharedaccesssignature" not in lowered
    assert "connectionstring" not in lowered
    assert "api_key" not in lowered


def test_ingress_is_bounded_and_does_not_assert_truth_or_health() -> None:
    source = INGRESS.read_text(encoding="utf-8")
    assert "MAX_EVENT_GRID_BODY_BYTES" in source
    assert "MAX_EVENT_GRID_EVENTS" in source
    assert "MAX_HEARTBEAT_BODY_BYTES" in source
    assert '"evidence_verified": False' in source
    assert '"health_asserted": False' in source


def test_sqlite_store_uses_durable_journaling_and_outbox() -> None:
    source = SQLITE.read_text(encoding="utf-8")
    assert "PRAGMA journal_mode=WAL" in source
    assert "PRAGMA synchronous=FULL" in source
    assert "material_transitions" in source
    assert "operator_notifications" in source
    assert "delivered_at_utc IS NULL" in source


def test_notification_payload_is_bounded_and_contains_no_customer_evidence() -> None:
    source = OPS.read_text(encoding="utf-8")
    assert "OperatorNotification" in source
    assert "max_length=512" in source
    forbidden = (
        "raw_evidence",
        "customer_payload",
        "private_key",
        "access_token",
        "connection_string",
    )
    for token in forbidden:
        assert token not in source.lower()


def test_documentation_preserves_presence_truth_boundary() -> None:
    text = DOC.read_text(encoding="utf-8").lower()
    assert "presence is not health" in text
    assert "heartbeat is not evidence verification" in text
    assert "microsoft entra" in text
    assert "no shared secret" in text
    assert "outbox" in text
