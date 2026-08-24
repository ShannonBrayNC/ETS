from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEQUENCE = ROOT / "docs" / "connectors" / "MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md"
RC1B = ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1B_LIVE_PREFLIGHT_V1.md"
RC1C = ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1C_LIVE_PREFLIGHT_V1.md"
RC1C_RECOVERY = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1C_SUBSCRIPTION_RECOVERY_V1.md"
)
PRE_SOAK = ROOT / "docs" / "connectors" / "MICROSOFT_P0_PRE_SOAK_GATE_V1.md"


def test_microsoft_p0_live_sequence_orders_protected_release_gates() -> None:
    text = SEQUENCE.read_text(encoding="utf-8")

    ordered = (
        "live-gateway-identity-bootstrap.yml",
        "provision-microsoft-p0-connector-app-roles.ps1",
        "hosted-azure-q0-image.yml",
        "live-core-gateway-deployment.yml",
        "live-microsoft-rc1b-preflight.yml",
        "live-microsoft-rc1c-preflight.yml",
        "live-microsoft-rc1c-subscription-recovery.yml",
    )
    positions = [text.index(value) for value in ordered]
    assert positions == sorted(positions)


def test_microsoft_p0_live_sequence_preserves_least_privilege_and_nonclaims() -> None:
    text = SEQUENCE.read_text(encoding="utf-8")

    for required in (
        "User.Read.All",
        "Group.Read.All",
        "ActivityFeed.Read",
        "Graph lifecycle configuration",
        "Purview subscription mutation",
        "freeze a candidate",
        "72-hour soak",
        "Do not reuse",
        "#479",
    ):
        assert required in text

    for doc in (RC1B, RC1C, RC1C_RECOVERY, PRE_SOAK):
        assert "MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md" in doc.read_text(encoding="utf-8")
