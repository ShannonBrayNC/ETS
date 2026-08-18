# Microsoft Reconciliation Gap v1

Schema identifier: `ets.connector.microsoft.reconciliation_gap.v1`

## Purpose

This profile records operational collection-continuity uncertainty for Microsoft connectors. It is
layered above the generic G2C runtime state so operators can distinguish an observed possible gap,
an active reconciliation attempt, its bounded outcome, and later operator acknowledgement.

This state is not ETS evidence verification. A recovered or acknowledged gap does not prove that
Microsoft was truthful, that the source was globally complete, or that no events existed outside
the connector's declared coverage.

## States

| State | Meaning |
|---|---|
| `possible` | A qualified signal indicates collection continuity may have been interrupted. Missing source records are not yet asserted. |
| `reconciling` | ETS is actively attempting bounded source reconciliation from approved state. |
| `recovered` | The bounded reconciliation attempt completed without a known residual gap in the declared recovery scope. This is not a universal completeness claim. |
| `partial` | Reconciliation recovered some observations but a known continuity limitation remains. |
| `unrecoverable` | The qualified recovery mechanism cannot reconstruct the declared gap period. |
| `acknowledged` | An operator acknowledged a terminal outcome. The original `recovered`, `partial`, or `unrecoverable` outcome remains preserved. |

Qualified transitions are:

`possible -> reconciling -> recovered|partial|unrecoverable -> acknowledged`

Acknowledgement cannot skip reconciliation and cannot erase a partial or unrecoverable outcome.

## Reasons

The initial bounded profile recognizes:

- `missed_notification`
- `subscription_removed`
- `subscription_expired`
- `delta_state_expired`
- `webhook_outage`
- `worker_outage`
- `queue_outage`
- `operator_declared`

Additional reasons require an explicit contract change rather than free-form exception text.

## Operator acknowledgement

Acknowledgement creates a normal `ets.connector.admin_audit.v1` event with action
`microsoft_reconciliation_gap_acknowledged`. The audit event records actor and authorized
ETS tenant/workspace scope. Acknowledgement is administrative disposition only; it does not
convert an unresolved continuity limitation into a successful recovery.

## Health projection

Microsoft operational health is projected from source health, G2C runtime state, and the current
reconciliation gap. The projection uses these precedence rules:

1. A failed source health result remains failed; a continuity projection does not hide an
   authentication, authorization, configuration, or terminal source failure.
2. `possible` and `reconciling` gaps report degraded `gap_detected` health.
3. `partial` and `unrecoverable` outcomes remain degraded after acknowledgement.
4. A recovered gap may return to the underlying source health only when G2C no longer reports an
   open collection gap.
5. Pending Gateway retries and unknown observation continuity prevent an otherwise reachable
   source from being reported as fully healthy.

This profile intentionally does not yet claim queue/dead-letter telemetry, subscription-expiration
monitoring, Explorer presentation, package export, multi-tenant qualification, or the 72-hour soak.
Those remain later G2E-F release slices under issue #309.
