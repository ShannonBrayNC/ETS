# ETS-RFC-0004: Federation

The RC5 lab topology contains three log nodes, two verifier nodes, and one
witness node. Quorum decisions are modeled by verifier votes and a threshold.

Federation experiments focus on fork detection and omission findings against
synthetic datasets. Production federation, witness gossip, and public monitor
networks are future work.

## Federation Assessment Request

The reference API exposes `POST /api/v1/federation/assess` for deterministic
laboratory assessment of verifier observations. The request contains:

- `threshold`: positive integer quorum threshold;
- `observations`: verifier observations, each with a unique `verifier_id` and a
  `SignedTreeHead`.

The assessment groups observations by `(log_id, tree_size, root_hash)`. Quorum
is met when at least `threshold` distinct verifier IDs report the same group.

## Fork Suspicion

A fork conflict is reported when two or more root hashes are observed for the
same `(log_id, tree_size)` view. ETS treats this as disagreement evidence, not
as proof of which log operator or verifier is faulty.

The reference implementation returns `accepted=false` when a quorum exists but
any same-view conflict is present.

## Limitations

The RC federation endpoint does not perform network gossip, key discovery,
Byzantine consensus, legal attestation, or completeness proof. It is a
deterministic protocol laboratory primitive for reproducing root-agreement,
fork-suspicion, and quorum behavior.

## Asynchronous Network Research Profile

ETS research experiments may model federation communication as a bounded
message queue with seeded delay and packet loss. Each run must record:

- random seed;
- minimum and maximum delivery delay;
- packet-loss probability;
- partial-synchrony bound used for the experiment.

This profile supports reproducible delay/loss measurements. It does not define
a production gossip protocol and does not prove safety or liveness under a
Byzantine asynchronous adversary.

## Fairness-Scoped Liveness Profile

ETS liveness claims are conditional. A laboratory run may state bounded
progress only when all of the following assumptions are declared:

- partitions eventually heal;
- adversarial pressure is bounded;
- replay, witness propagation, and stale-state recovery are weakly fair when
  enabled;
- stale verifiers can request and process recovery state.

Under those assumptions, ETS may evaluate replay eventuality, witness
propagation completion, stale-state recovery, and convergence after adversarial
pressure. Without those assumptions, ETS reports no liveness guarantee.
