# Microsoft Operational Health v1

Schema identifiers:

- `ets.connector.microsoft.operational_health_policy.v1`
- `ets.connector.microsoft.operational_posture.v1`

## Purpose

This profile combines Microsoft source health, Graph subscription state, G2C runtime continuity,
Microsoft reconciliation state, and source-scoped Gateway synchronization posture into one
policy-bound operational assessment.

It is not evidence verification. A healthy operational posture does not establish Microsoft source
truth, global completeness, legal admissibility, or the absence of events outside the declared
connector coverage.

## Policy inputs

The v1 policy requires explicit governed values for:

- Graph subscription renewal warning window;
- maximum collection lag;
- maximum source-scoped unsynchronized age; and
- maximum source-scoped queue depth.

There are intentionally no implicit production defaults. Deployment policy must choose these
thresholds for the connector profile and environment.

## Scope binding

Evaluation fails closed unless all supplied state belongs to the declared scope:

- G2C runtime `instance_id` matches the Microsoft connector instance;
- source-scoped queue tenant/workspace matches the ETS tenant/workspace;
- source-scoped queue `source_id` matches the evaluated Gateway source;
- Graph subscription tenant matches the declared Microsoft tenant; and
- a reconciliation record, when supplied, matches the connector instance.

This prevents health data from one tenant, workspace, source, or connector instance from being
used to characterize another.

## Primary-health precedence

The v1 projection selects one primary `ets.connector.health.v1` result while retaining the bounded
posture fields that explain other active conditions. Precedence is:

1. failed source authentication/authorization or other failed source health;
2. removed or disabled Graph subscription;
3. expired Graph subscription;
4. Graph reauthorization requirement;
5. Graph lifecycle gap state;
6. explicit Microsoft reconciliation or G2C continuity gap;
7. source-scoped terminal Gateway synchronization failure;
8. other degraded source/runtime health;
9. source-scoped retryable Gateway synchronization failure;
10. source queue-depth or unsynchronized-age policy breach;
11. missing collection-success time;
12. collection-lag policy breach;
13. Graph subscription renewal-window warning; then
14. the underlying healthy source/runtime result.

The precedence is operational triage ordering, not a trust score and not a ranking of evidence
quality.

## Queue semantics

Queue posture must come from `SourceScopedSyncQueueStatus`. Global queue state is not accepted as
a Microsoft connector-health input because unrelated connectors can share the durable queue.

`latest_active_failure` is current state, not source-specific historical provenance. A synchronized
record clears its per-record error, so this profile does not invent a historical last-failure value
that the durable source-scoped rows cannot reconstruct.

## Collection lag

Collection lag is measured from G2C `last_success_at_utc` to the explicit evaluation timestamp.
A future last-success timestamp fails closed. Exceeding the configured lag threshold degrades the
operational posture but does not itself assert that Microsoft source records are missing.

## Subscription state

An expired subscription degrades continuity posture and requires reconciliation. Removed or
disabled subscriptions are terminal for current collection until operational repair. An active
subscription inside the configured renewal window is degraded as an actionable renewal warning.

## Nonclaims

Every `ets.connector.microsoft.operational_posture.v1` record fixes these claims to false:

- `verification_claimed`
- `source_truth_claimed`
- `completeness_claimed`

Evidence verification remains a separate ETS protocol/verifier concern.

## Follow-on integration

Later G2E-F slices should expose this posture through a read-only, scope-authorized operator API,
render it in Evidence Explorer, include relevant gap declarations in evidence packages, and qualify
multi-tenant isolation, fault injection, deployment/rollback and the 72-hour production-like soak.
