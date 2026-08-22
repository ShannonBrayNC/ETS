# ETS Fleet Presence B2

Status: implementation candidate for FLEET-B2 / #515.

## Purpose

FLEET-B2 connects the provider-neutral B1 presence engine to durable operational storage, bounded HTTP ingress, and a retryable operator-notification outbox.

The architecture preserves four independent concepts:

1. authoritative ETS enrollment and lifecycle state;
2. provider transport presence;
3. ETS signed-heartbeat freshness;
4. evidence verification and semantic interpretation.

**Presence is not health.** A device being connected does not prove that the device is functioning correctly, producing complete evidence, or behaving according to policy.

**Heartbeat is not evidence verification.** A current signed heartbeat proves only that an authorized device credential signed the bounded heartbeat accepted by the configured Fleet policy. It does not prove that all evidence is complete or semantically true.

## Components

### `ets.fleet.presence_sqlite`

`SQLitePresenceStore` is the durable single-node reference implementation for the B1 `PresenceStore` contract and the B2 notification outbox.

It persists:

- the latest bounded `PresenceState` per canonical ETS device;
- accepted Event Grid transport event IDs;
- observed boot/session IDs;
- deduplicated material transition records;
- pending/delivered operator-notification records.

SQLite uses WAL journaling, `synchronous=FULL`, foreign-key enforcement, and explicit transactions for grouped transition/outbox writes. Raw customer evidence, credentials, private keys, tokens, connection strings, and Azure management credentials are not stored.

The SQLite implementation is a reference durable store for a single Fleet service node. A horizontally scaled production control plane should implement the same ports using a transactional shared datastore and preserve the same uniqueness and replay invariants.

### `ets.fleet.presence_ops`

`FleetPresenceCoordinator` converts accepted B1 state changes into bounded material administrative transitions.

Current material transition types are:

- first online;
- reconnect after a meaningful outage threshold;
- persistent disconnect;
- signed heartbeat stale while transport remains online;
- signer/signature/enrollment identity mismatch;
- quarantine;
- revocation.

Each transition receives a deterministic transition key. Repeated evaluation therefore cannot create duplicate notifications for the same material condition.

The coordinator rate-bounds notifications per device and time window. When the notification limit is reached, the transition can still be retained while another outbound notification is suppressed. This prevents notification delivery from becoming an attacker-controlled amplification path.

Operator notifications contain only generated operational text, canonical device identity, bounded status values, and the administrative transition reference. They contain no customer payload, raw evidence, keys, credentials, tokens, or sensitive network configuration.

The outbox is retryable: notification delivery is not marked complete until the configured `OperatorNotifier` returns successfully.

### `ets.fleet.presence_api`

The HTTP adapter exposes two bounded routes:

- `POST /fleet/v1/azure/event-grid`
- `POST /fleet/v1/heartbeat`

The adapter is deliberately thin. It performs transport-level size/shape/authentication checks and then delegates identity, sequence, lifecycle, signature, and replay decisions to the B1 runtime.

## Azure Event Grid authentication

Production Event Grid webhook delivery must be protected with **Microsoft Entra ID** authentication. The router refuses to start in production mode without an `event_grid_authenticator` supplied by the hosting composition.

There is **no shared secret fallback**. The Fleet ingress does not consume Event Grid query-string client secrets, IoT Hub connection strings, SAS credentials, or static API keys.

Microsoft Event Grid endpoint ownership validation is supported for the Event Grid event schema. A subscription validation event must:

- arrive as the only event in the batch;
- originate from the configured IoT Hub resource;
- carry a bounded validation code;
- satisfy the production Entra authentication boundary before a validation response is returned.

The normal B1 source, subject, device ID, event-type, and sequence checks remain authoritative for transport events after the webhook handshake.

For an Azure production deployment, the preferred composition is:

`IoT Hub -> Event Grid -> Entra-protected Fleet ingress -> FleetPresenceCoordinator -> shared durable store -> notification worker`

A managed-identity-backed Event Grid destination such as Service Bus/Event Hubs followed by a private processor is also compatible with the same B1/B2 contracts and can be selected when a fully private ingestion topology is required.

## Signed heartbeat endpoint

The heartbeat route accepts only a bounded strict `ets.fleet.heartbeat.v1` envelope. Device authentication is the detached signature bound to the authoritative active Fleet enrollment; the service does not issue or accept a reusable shared secret for heartbeat authentication.

The route:

- limits request size before model validation;
- requires a JSON object;
- validates the strict heartbeat envelope;
- delegates current enrollment, scope, signer, signature, replay, boot-session, sequence, and clock-skew checks to B1;
- returns bounded status/reason fields only;
- explicitly returns `evidence_verified=false` and `health_asserted=false`.

## Debounce and transition semantics

A disconnect event updates transport state immediately but does not create a persistent-disconnect notification until the configured disconnect threshold expires. If a device reconnects before that threshold, transient churn produces no persistent-disconnect alert.

A reconnect notification is generated only when the prior accepted transport state was offline for at least the configured meaningful-outage threshold.

Heartbeat stale evaluation uses trusted service receipt time from B1. Device-reported time remains contextual metadata and is not the sole freshness clock.

## Notification safety

The operator destination is intentionally outside the Fleet semantic model and is implemented through `OperatorNotifier`. This permits email, Teams, Slack, SMS, or another company-controlled destination later without changing device identity or presence semantics.

Notification delivery must preserve these requirements:

- plaintext/bounded generated content only;
- no credentials, tokens, keys, SAS values, certificates, customer payloads, raw evidence, or sensitive network configuration;
- deterministic transition dedupe;
- bounded per-device notification rate;
- retries through the durable outbox;
- no claim that presence equals health or evidence truth.

## Recovery and restart behavior

On restart, the durable store restores the latest presence state and replay sets. A previously accepted Event Grid event remains a duplicate after restart, and material transition keys prevent the same first-online/reconnect/stale/disconnect notification from being re-enqueued.

Pending outbox notifications remain pending until a notifier successfully delivers them and marks them delivered.

## Tests and abuse cases

The B2 test suite covers:

- SQLite restart state recovery;
- transport-event dedupe across restart;
- first-online and reconnect transition dedupe;
- persistent-disconnect debounce;
- heartbeat-stale evaluation;
- lifecycle revocation notification;
- retryable notification outbox;
- per-device notification flood bounding;
- production Event Grid authentication requirement;
- Event Grid subscription validation handshake;
- B1 wrong-source rejection through the HTTP adapter;
- heartbeat body-size limits;
- explicit no-health/no-evidence-verification response semantics;
- architecture guards against Azure SDK/product-plane coupling and shared-secret fallbacks.

## Remaining deployment work

B2 creates the durable/runtime boundary but does not deploy an Azure Event Grid subscription or company notification destination by itself. Production deployment still requires:

1. hosting the Fleet ingress behind a validated Microsoft Entra application boundary or selecting a managed-identity-backed queue/event-stream destination;
2. granting only the minimum Event Grid delivery identity permissions;
3. selecting the shared production datastore for multi-replica Fleet operation;
4. configuring the company-controlled notification adapter/destination;
5. running a live Edge -> IoT Hub -> Event Grid -> Fleet ingress -> heartbeat -> notification qualification and retaining sanitized evidence.

Until that live qualification is executed, B2 code qualification must not be represented as proof that the physical Azure presence/notification path is operational.
