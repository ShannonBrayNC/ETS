import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.lantern import (
    LanternEventSignature,
    LanternRewardClaimEvent,
    LanternRewardTriggerMethod,
    LanternRewardVerificationStatus,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "ets/core/schemas/lantern/reward_claim_v1.json"
REGISTRY_PATH = ROOT / "ets/core/event_registry.json"
DOC_PATH = ROOT / "docs/lantern/REWARD_CLAIM_PROVENANCE.md"


def make_reward_claim(**overrides: object) -> LanternRewardClaimEvent:
    data: dict[str, object] = {
        "eventType": "lantern.reward.claim.requested",
        "eventVersion": "1.0",
        "campaignId": "lantern-crisis-v1",
        "clientEventId": "client-event-001",
        "claimId": "claim-001",
        "triggerMethod": "typed:LANTERN",
        "triggerTimestamp": datetime(2026, 5, 26, 8, 0, tzinfo=UTC),
        "claimTimestamp": datetime(2026, 5, 26, 8, 1, tzinfo=UTC),
        "emailHash": "a" * 64,
        "consentToSendReward": True,
        "marketingOptIn": False,
        "rewardAssetId": "lantern-book-digital-v1",
        "verificationStatus": "requires_human_review",
        "sourceSystem": "echomedia-website",
        "processingSystem": "signalforge",
    }
    data.update(overrides)
    return LanternRewardClaimEvent.model_validate(data)


def test_reward_claim_contract_accepts_expected_event() -> None:
    event = make_reward_claim()

    assert event.event_type == "lantern.reward.claim.requested"
    assert event.trigger_method == LanternRewardTriggerMethod.TYPED_LANTERN
    assert event.verification_status == LanternRewardVerificationStatus.REQUIRES_HUMAN_REVIEW
    assert event.consent_to_send_reward is True
    assert event.marketing_opt_in is False


def test_reward_claim_contract_rejects_raw_email_and_unknown_trigger() -> None:
    with pytest.raises(ValidationError):
        make_reward_claim(emailHash="visitor@example.com")

    with pytest.raises(ValidationError):
        make_reward_claim(triggerMethod="clicked-button")


def test_reward_claim_contract_keeps_reward_and_marketing_consent_distinct() -> None:
    event = make_reward_claim(consentToSendReward=True, marketingOptIn=False)

    assert event.consent_to_send_reward is True
    assert event.marketing_opt_in is False


def test_reward_claim_contract_accepts_optional_signature() -> None:
    event = make_reward_claim(
        signature={
            "algorithm": "ed25519",
            "keyId": "website-signing-key",
            "value": "signature-value",
        }
    )

    assert event.signature == LanternEventSignature(
        algorithm="ed25519",
        keyId="website-signing-key",
        value="signature-value",
    )


def test_reward_claim_schema_matches_issue_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    assert (
        registry["lantern.reward.claim.requested"]
        == "ets/core/schemas/lantern/reward_claim_v1.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["eventType"]["const"] == "lantern.reward.claim.requested"
    assert schema["properties"]["triggerMethod"]["enum"] == ["typed:LANTERN"]
    assert schema["properties"]["emailHash"]["pattern"] == "^[a-f0-9]{64}$"
    assert "signature" in schema["properties"]
    assert "rawEmail" not in schema["properties"]


def test_reward_claim_documentation_covers_privacy_consent_and_emission() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for required in [
        "consentToSendReward",
        "marketingOptIn",
        "typed:LANTERN",
        "Raw email belongs only in the reward delivery system",
        "EchoMedia website",
        "SignalForge",
        "Signing Requirements",
        "Retention And Minimization",
    ]:
        assert required in text
