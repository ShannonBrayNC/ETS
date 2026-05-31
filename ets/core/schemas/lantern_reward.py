from dataclasses import dataclass
from typing import Optional

@dataclass
class LanternRewardClaimRequested:
    eventType: str = "lantern.reward.claim.requested"
    eventVersion: str = "1.0"
    campaignId: str = "lantern-crisis-v1"
    clientEventId: str = ""
    claimId: str = ""
    triggerMethod: str = "typed:LANTERN"
    triggerTimestamp: str = ""
    claimTimestamp: str = ""
    emailHash: str = ""
    consentToSendReward: bool = False
    marketingOptIn: bool = False
    rewardAssetId: str = "lantern-book-digital-v1"
    verificationStatus: str = "requires_human_review_or_system_verified"
    sourceSystem: str = "echomedia-website"
    processingSystem: str = "signalforge"
