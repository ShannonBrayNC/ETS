# Microsoft P0 pre-soak gate v1

This gate qualifies the bounded Microsoft connector family as one release candidate before a new 72-hour soak begins. A successful SharePoint path validates shared onboarding and Graph/SharePoint mechanics, but it does not qualify the other P0 workloads by inference.

## P0 candidate boundary

The candidate includes:

- Entra onboarding, consent, and least-privilege credential readiness;
- Graph subscription validation, renewal, expiry recovery, and notification deduplication;
- Entra users and groups delta collection;
- SharePoint and OneDrive metadata/delta collection;
- Purview Management Activity audit collection;
- reconciliation, gap detection, health, and sanitized evidence packaging; and
- the Gateway durable-state probe.

Teams message content, Exchange mailbox content, Power Platform runtime, Copilot and Viva, government-cloud variants, and broad multitenancy are deferred. They must not be represented as qualified by this gate.

## Entry sequence

1. Live-qualify every P0 slice on approved source.
2. Execute bounded fault and recovery exercises before the soak, including cursor replay, subscription expiry, throttling/backoff, job restart, Gateway state recovery, and evidence-loss fail-closed behavior.
3. Reconcile all results and close evidence gaps.
4. Freeze one approved `main` SHA and one immutable Q0 image digest with passing vulnerability, provenance, and SBOM results.
5. Start a new governed soak attempt. An invalidated attempt is never resumed or counted.

Any source, image, configuration, or identity mutation after freeze requires a fresh Q0 and a new candidate.

## Soak behavior

The soak exercises non-destructive canaries only. Each observation retains exact-source identity, workload health and continuity, cursor or subscription progress, reconciliation state, and public-safe evidence. It retains no reusable credentials, content bodies, or customer identifiers.

Public hostname activation is outside this gate. A successful pre-soak or soak result does not authorize DNS, ingress, or public endpoint activation.

## Exit

The candidate exits only after the governed duration, observation-count, and maximum-gap thresholds are met; every P0 slice remains healthy; final source-to-proof and Gateway durable-state evidence are retained; and no deferred workload is claimed.
