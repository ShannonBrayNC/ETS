# Microsoft P0 pre-soak gate v1

This gate qualifies the bounded Microsoft connector family as one release candidate before a new 72-hour soak begins. A successful SharePoint path validates shared onboarding and Graph/SharePoint mechanics, but it does not qualify the other P0 workloads by inference.

## P0 candidate boundary

The candidate includes:

- Entra onboarding, consent, and least-privilege credential readiness;
- Entra users and groups delta collection;
- SharePoint and OneDrive metadata/delta collection;
- Purview Management Activity audit collection;
- verified absence of Graph drive-subscription configuration, durable state, broader file
  permission, and callback ingress under ADR-009;
- reconciliation, gap detection, health, and sanitized evidence packaging; and
- the Gateway durable-state probe.

Graph drive subscriptions and their future Entra-RBAC Event Hubs consumer, Teams message content,
Exchange mailbox content, Power Platform runtime, Copilot and Viva, government-cloud variants, and
broad multitenancy are deferred. They must not be represented as qualified by this gate.

## Entry sequence

ADR-009 was approved through #552 and the #537/#539/#541 issue contracts were reconciled. P0 retains
the approved drive-scoped delta-polling path and independently qualifies Purview. The pre-soak gate
remains blocked until the included live slices, recovery matrix, evidence reconciliation, and
candidate freeze complete.

The protected exact-source preparation and RC1B/RC1C preflight order is defined by
[`MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md`](./MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md).

1. Live-qualify every P0 slice on approved source.
2. Execute bounded fault and recovery exercises before the soak, including delta/audit cursor replay, Purview subscription disable/recovery, throttling/backoff, job restart, Gateway state recovery, and evidence-loss fail-closed behavior.
3. Reconcile all results and close evidence gaps.
4. Freeze one approved `main` SHA and one immutable Q0 image digest with passing vulnerability, provenance, and SBOM results.
5. Start a new governed soak attempt. An invalidated attempt is never resumed or counted.

Any source, image, configuration, or identity mutation after freeze requires a fresh Q0 and a new candidate.

Approved decision record:
[`ADR-009-microsoft-graph-drive-subscription-p0.md`](../adr/ADR-009-microsoft-graph-drive-subscription-p0.md).

The first Purview mutation gate is the protected
[`MICROSOFT_P0_RC1C_SUBSCRIPTION_RECOVERY_V1.md`](./MICROSOFT_P0_RC1C_SUBSCRIPTION_RECOVERY_V1.md)
start/stop/restart exercise. A first attempt must begin from an absent `Audit.General`
subscription. A protected retry may begin enabled only when the selected prior protected failure artifact proves mutation and fail-closed
restoration completed with the final state enabled. The gate still
performs an idempotent start, bounded content listing, stop, and restart, and must finish enabled
without a webhook. Passing it does not replace the remaining cursor, content,
replay/idempotency, throttle, gap-recovery, or evidence-loss gates.

## Soak behavior

The soak exercises non-destructive canaries only. Each observation retains exact-source identity,
workload health and continuity, delta/audit cursor progress, Purview subscription posture,
reconciliation state, the Graph deferral boundary, and public-safe evidence. It retains no reusable
credentials, content bodies, or customer identifiers.

Public hostname activation is outside this gate. A successful pre-soak or soak result does not authorize DNS, ingress, or public endpoint activation.

## Exit

The candidate exits only after the governed duration, observation-count, and maximum-gap thresholds are met; every P0 slice remains healthy; final source-to-proof and Gateway durable-state evidence are retained; and no deferred workload is claimed.
