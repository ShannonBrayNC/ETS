#!/bin/bash

# Create schema definition directory if it doesn't exist
mkdir -p ets/core/schemas/lantern

# Define the canonical event schema for lantern reward claims
cat <<EOF > ets/core/schemas/lantern/reward_claim_v1.json
{
  "\$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LanternRewardClaim",
  "description": "ETS provenance event for Lantern Easter egg reward claims",
  "type": "object",
  "required": [
    "eventType",
    "eventVersion",
    "campaignId",
    "claimId",
    "emailHash",
    "consentToSendReward"
  ],
  "properties": {
    "eventType": { "type": "string", "const": "lantern.reward.claim.requested" },
    "eventVersion": { "type": "string", "const": "1.0" },
    "campaignId": { "type": "string" },
    "clientEventId": { "type": "string" },
    "claimId": { "type": "string" },
    "triggerMethod": { "type": "string" },
    "triggerTimestamp": { "type": "string", "format": "date-time" },
    "claimTimestamp": { "type": "string", "format": "date-time" },
    "emailHash": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
    "consentToSendReward": { "type": "boolean" },
    "marketingOptIn": { "type": "boolean" },
    "rewardAssetId": { "type": "string" },
    "verificationStatus": { "type": "string" },
    "sourceSystem": { "type": "string" },
    "processingSystem": { "type": "string" }
  }
}
EOF

# Register the new event type in the core event registry (simulated append)
if [ -f "ets/core/registry.py" ]; then
    sed -i '/REGISTERED_EVENTS = {/a \    "lantern.reward.claim.requested": "ets.core.schemas.lantern.reward_claim_v1",' ets/core/registry.py
else
    echo "Registering Lantern Event in core..."
    echo '{"lantern.reward.claim.requested": "ets/core/schemas/lantern/reward_claim_v1.json"}' >> ets/core/event_registry.json
fi

# Add a test case to verify the schema
mkdir -p ets/core/tests/lantern
cat <<EOF > ets/core/tests/lantern/test_schema.py
import json
from ets.core.verifier import validate_event

def test_lantern_reward_event_schema():
    event = {
        "eventType": "lantern.reward.claim.requested",
        "eventVersion": "1.0",
        "campaignId": "lantern-crisis-v1",
        "claimId": "550e8400-e29b-41d4-a716-446655440000",
        "emailHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "consentToSendReward": True
    }
    assert validate_event(event) == True
EOF

echo "Lantern reward claim event schema implemented."