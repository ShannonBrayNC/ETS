import { useEffect, useState } from "react";

import { getMicrosoftOperationalPosture } from "./api";
import type { MicrosoftOperationalPosture } from "./types";

export function MicrosoftPosturePanel({ instanceId }: { instanceId: string }) {
  const [posture, setPosture] = useState<MicrosoftOperationalPosture | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setPosture(null);
    setError(null);
    setLoading(true);

    getMicrosoftOperationalPosture(instanceId)
      .then((result) => {
        if (active) setPosture(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(messageOf(reason, "Microsoft operational posture is unavailable"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [instanceId]);

  if (loading) {
    return (
      <section aria-label="Microsoft operational posture">
        <h3>Microsoft operational posture</h3>
        <p>Loading subscription, collection, queue, and reconciliation state…</p>
      </section>
    );
  }

  if (error || !posture) {
    return (
      <section aria-label="Microsoft operational posture">
        <h3>Microsoft operational posture</h3>
        <div className="alert warning" role="status">
          {error ?? "Microsoft operational posture is unavailable"}
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Microsoft operational posture">
      <h3>Microsoft operational posture</h3>
      <div className={`health-callout ${posture.health.state}`}>
        <strong>{humanHealth(posture.health.state)}</strong>
        <span>{posture.health.code}</span>
        <p>{posture.health.message}</p>
      </div>
      <dl className="detail-list">
        <div>
          <dt>Subscription</dt>
          <dd>{humanSubscription(posture.subscription_status)}</dd>
        </div>
        <div>
          <dt>Subscription expires</dt>
          <dd>{formatTime(posture.subscription_expiration_date_time)}</dd>
        </div>
        <div>
          <dt>Collection lag</dt>
          <dd>{formatDuration(posture.collection_lag_seconds)}</dd>
        </div>
        <div>
          <dt>Gateway queue</dt>
          <dd>{posture.queue_depth.toLocaleString()} unsynchronized records</dd>
        </div>
        <div>
          <dt>Oldest unsynchronized</dt>
          <dd>{formatDuration(posture.oldest_unsynchronized_age_seconds)}</dd>
        </div>
        <div>
          <dt>Active sync failures</dt>
          <dd>
            {posture.retryable_failure_count.toLocaleString()} retryable /{" "}
            {posture.terminal_failure_count.toLocaleString()} terminal
          </dd>
        </div>
        <div>
          <dt>Reconciliation</dt>
          <dd>{humanReconciliation(posture)}</dd>
        </div>
        <div>
          <dt>Policy profile</dt>
          <dd>{posture.policy_profile_id}</dd>
        </div>
        <div>
          <dt>Evaluated</dt>
          <dd>{formatTime(posture.evaluated_at_utc)}</dd>
        </div>
      </dl>
      <p className="boundary-note">
        This is an operational assessment only. ETS cryptographic verification, Microsoft source
        truth, and source completeness remain separate claims and are not asserted by this view.
      </p>
    </section>
  );
}

function humanHealth(value: MicrosoftOperationalPosture["health"]["state"]): string {
  if (value === "healthy") return "Operationally healthy";
  if (value === "degraded") return "Operationally degraded";
  if (value === "failed") return "Operational failure";
  return "Operational state unknown";
}

function humanSubscription(value: MicrosoftOperationalPosture["subscription_status"]): string {
  if (value === "active") return "Active";
  if (value === "reauthorization_required") return "Reauthorization required";
  if (value === "removed") return "Removed";
  return "Disabled";
}

function humanReconciliation(posture: MicrosoftOperationalPosture): string {
  if (!posture.reconciliation_status) return "No active reconciliation record";
  const status = posture.reconciliation_status.replaceAll("_", " ");
  const outcome = posture.reconciliation_outcome
    ? ` · outcome ${posture.reconciliation_outcome}`
    : "";
  return `${status}${outcome}`;
}

function formatDuration(value: number | null): string {
  if (value === null) return "Not established";
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${Math.round(value / 3600)}h`;
}

function formatTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function messageOf(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
