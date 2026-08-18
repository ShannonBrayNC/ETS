# Microsoft Operational Failure-Injection Qualification v1

## Purpose

This qualification composes the production Microsoft operational-state primitives under controlled
synthetic faults and verifies that they project into `ets.connector.microsoft.operational_posture.v1`
without becoming ETS cryptographic verification claims.

It intentionally uses deterministic in-process Graph lifecycle observations, reconciliation state,
and the durable Gateway synchronization queue. It does not require destructive faults against a
live Microsoft tenant and does not claim live-cloud coverage.

## Qualified scenarios

The matrix exercises:

1. **Missed Graph lifecycle notification**
   - applies a real `missed` Graph lifecycle transition;
   - opens a Microsoft reconciliation gap with reason `missed_notification`;
   - requires degraded `gap_detected` posture and visible `possible` reconciliation state.

2. **Subscription removed**
   - applies `subscriptionRemoved` through the Graph lifecycle state machine;
   - requires failed `terminal_error` operational posture.

3. **Reauthorization required**
   - applies `reauthorizationRequired` through the Graph lifecycle state machine;
   - requires degraded `authorization_failed` posture.

4. **Source token/authentication failure**
   - injects failed `authentication_failed` source health;
   - requires source failure to retain precedence.

5. **Source authorization/consent failure**
   - injects failed `authorization_failed` source health;
   - requires source failure to retain precedence.

6. **Graph throttling**
   - injects degraded `throttled` source health;
   - requires throttling to remain visible rather than being promoted to healthy.

7. **Expired delta state / unrecoverable continuity**
   - drives `possible -> reconciling -> unrecoverable` with reason `delta_state_expired`;
   - requires degraded gap posture and explicit unrecoverable outcome.

8. **Worker outage**
   - drives `possible -> reconciling` with reason `worker_outage`;
   - requires degraded gap posture while reconciliation is active.

9. **Durable queue terminal failure and isolation**
   - injects terminal failures for an unrelated source and unrelated tenant first;
   - requires the target Microsoft source to remain healthy;
   - then injects a terminal failure for the target source and requires degraded `terminal_error`;
   - uses the real `SyncQueue` and `source_scoped_sync_queue_status()` boundary.

10. **Recovered continuity**
    - drives `possible -> reconciling -> recovered`;
    - closes the G2C runtime gap and Graph gap state;
    - requires the posture to return to the underlying healthy source state while retaining the
      reconciliation outcome as `recovered`.

## Qualification boundary

Every resulting operational posture is required to preserve:

- `verification_claimed = false`
- `source_truth_claimed = false`
- `completeness_claimed = false`

The matrix therefore qualifies operational reaction and recovery semantics only. It does not alter
or invoke the ETS cryptographic verifier.

## Relationship to live qualification

This test is the deterministic synthetic/mock failure-injection layer required before live release
qualification. It does not replace:

- live EchoMedia tenant testing;
- Graph service throttling observed from Microsoft infrastructure;
- real consent/token expiry;
- external webhook/network outage injection;
- multi-node worker failure in Azure;
- 72-hour production-like soak evidence; or
- deployment/rollback/offboarding qualification.

Those remain separate G2E-F release gates.
