# Lantern Reward Claim Provenance

## Purpose

This document defines the ETS provenance event for Lantern Crisis Simulator
Easter egg reward claims. The event lets EchoMedia website and SignalForge
record that a visitor discovered the Easter egg, granted reward-delivery
consent, and requested the digital book reward without requiring ETS to store
the raw email address.

## Event Type

`lantern.reward.claim.requested`

## Canonical Schema

The canonical JSON schema lives at:

`ets/core/schemas/lantern/reward_claim_v1.json`

The registry entry lives at:

`ets/core/event_registry.json`

## Required Fields

| Field | Requirement |
| --- | --- |
| `eventType` | Must be `lantern.reward.claim.requested`. |
| `eventVersion` | Must be `1.0`. |
| `campaignId` | Campaign identifier, for example `lantern-crisis-v1`. |
| `clientEventId` | Client-generated discovery event identifier. |
| `claimId` | Server-side reward claim identifier. |
| `triggerMethod` | Must be one of the allowed trigger methods. |
| `triggerTimestamp` | UTC timestamp when the Easter egg was triggered. |
| `claimTimestamp` | UTC timestamp when the reward claim was submitted. |
| `emailHash` | SHA-256 hash of the normalized email address. |
| `consentToSendReward` | Consent to send the reward. |
| `marketingOptIn` | Separate marketing consent. Defaults to false in code. |
| `rewardAssetId` | Reward asset identifier, for example `lantern-book-digital-v1`. |
| `verificationStatus` | Review or system-verification status. |
| `sourceSystem` | System that captured the claim, for example `echomedia-website`. |
| `processingSystem` | System processing the claim, for example `signalforge`. |

## Allowed Trigger Methods

| Trigger method | Meaning |
| --- | --- |
| `typed:LANTERN` | Visitor typed `LANTERN` into the Crisis Simulator interface. |

## Consent Boundary

`consentToSendReward` and `marketingOptIn` are distinct fields.

- `consentToSendReward=true` authorizes reward delivery only.
- `marketingOptIn=true` may be used only when the website separately captures
  marketing consent.
- ETS should not infer marketing consent from reward-delivery consent.
- ETS should not require or store the raw email address.

## Email Hashing

The emitting system should normalize the email address before hashing:

1. Trim leading and trailing whitespace.
2. Lowercase the address.
3. SHA-256 hash the normalized UTF-8 string.
4. Send only the 64-character lowercase hex digest to ETS.

Raw email belongs only in the reward delivery system when operationally needed.

## Signing Requirements

The `signature` field is optional in the schema because this event may be
prepared before a signing provider is available. When signing is available, the
emitting system should sign the canonical event payload and include:

- `algorithm`
- `keyId`
- `value`

Unsigned events should remain reviewable but should not be treated as stronger
than the surrounding ETS proof bundle, Merkle inclusion proof, and approval
state.

## Retention And Minimization

- Retain the ETS event only as long as needed for reward audit, duplicate claim
  detection, and campaign reporting.
- Retain raw email outside ETS only in systems responsible for reward delivery.
- Do not include IP address, browser fingerprint, or unrelated profile data in
  this event.
- Use `claimId`, `clientEventId`, and `emailHash` for dedupe instead of raw PII.

## Emission Path

1. EchoMedia website captures Easter egg discovery and reward form submission.
2. Website normalizes and hashes the email address locally or sends it to the
   reward API for hashing before ETS submission.
3. SignalForge creates or receives the ETS-compatible event.
4. ETS validates the event shape and records/notarizes the provenance event.
5. Downstream reward delivery uses `claimId` and delivery-system data, not raw
   email stored in ETS.

## Boundary Statement

ETS proves that the recorded provenance event and related proof artifacts have
not changed since notarization. ETS does not prove that the visitor owns the
email address, that the reward was delivered, or that marketing consent exists
unless those facts are separately captured and proven by their source systems.
