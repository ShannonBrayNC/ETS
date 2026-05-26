# ETS Governance Semantics

This document defines a bounded human-governance model for ETS research. It is
not legal advice and does not define legally sufficient dispute handling.

## Scope

ETS can report technical evidence states such as proof validity, quorum
acceptance, fork suspicion, and omission suspicion. Human governance decides
what an organization does with those states.

The reference semantics in `ets.governance.escalation` classify cases as:

- `accepted`: no escalation signal is present and verifier quorum was accepted;
- `escalated`: one or more technical or policy signals require human review.

Arbitration is required when an escalated case includes a policy override,
legal hold, or multiple reviewers.

## Signals

- `proof_valid`
- `proof_invalid`
- `fork_suspected`
- `omission_suspected`
- `policy_override_requested`
- `legal_hold`

## Limitations

The model does not decide legal truth, liability, intent, organizational
authority, or whether an override is ethically appropriate. It only makes the
handoff from verifiable protocol evidence to human review explicit and
testable.
