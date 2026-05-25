from ets.lantern_trust.contracts import LanternGovernanceEvent
from ets.lantern_trust.notary import issue_receipt
from ets.lantern_trust.verifier import verify_receipt


def test_lantern_receipt_verification() -> None:
    event = LanternGovernanceEvent(
        event_id="evt-001",
        source_system="signalforge",
        workspace="opshelm",
        recommendation_id="rec-001",
        event_type="approved",
        actor="christina-ui",
        timestamp_utc="2026-05-24T18:00:00Z",
        payload_hash="abc123",
    )

    receipt = issue_receipt(event, verifier="ets-core")

    assert verify_receipt(receipt) is True
