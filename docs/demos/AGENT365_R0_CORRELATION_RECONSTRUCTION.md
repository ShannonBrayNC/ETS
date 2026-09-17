# Durable Agent 365 correlation in mission reconstruction

This gate adds Microsoft runtime correlation to the existing authenticated Ranger R0 mission
lookup without changing the already-verified physical Evidence Object v2 bundle.

## Separation of custody

The physical evidence bundle and the Agent 365 correlation bundle are retained separately and
keyed by the same immutable `mission_id`.

The existing `SQLiteRangerR0MissionBundleStore` remains authoritative for:

- SharePoint authorization artifact retained in the consequence closure;
- Gateway ingress/decision/egress and robot command evidence;
- Ranger motion/stop/result evidence;
- Evidence Object v1/v2;
- the independently supported physical result.

`SQLiteAgent365R0CorrelationStore` retains only the sanitized Agent 365 proposition created by
#852/#854. It does not copy raw OTLP or Agent 365 payload bodies into the mission database.

This separation prevents Microsoft runtime metadata from changing the verifier semantics of an
already-qualified physical chain.

## Retry and conflict semantics

The correlation store is one authoritative bundle per `mission_id`:

- replay of the exact same canonical bundle is idempotent;
- a second different bundle for the same mission fails closed;
- every load verifies the stored canonical JSON SHA-256 before parsing;
- parsed correlation must still contain the requested `mission_id`;
- store schema versions are explicit.

## API representation

When a correlation store is configured, the existing authenticated mission endpoint adds an
`agent365_correlation` section.

`observed` means a digest-verified correlation bundle exists for that mission. The response may
include protected source references, source commitments, package/agent identity references,
invocation/session IDs, trace/span IDs, tool-call IDs, SharePoint item identity, and correlation
bases.

`not_observed` means the physical mission exists and verifies, but the API has no retained Agent
365 runtime correlation for that mission. It does not infer one from SharePoint, Gateway, or R0
records.

If no correlation store is configured at all, the response omits the optional field so the
existing mission API shape remains compatible.

## Privacy and claim boundary

The endpoint continues to require `evidence.read`. Raw retained source bodies and physical source
artifact bytes remain absent from the default response.

The correlation response states two invariants explicitly:

- successful Agent 365 tool execution is **not** proof of SharePoint resource state;
- Agent 365 observation is **not** proof of the physical Ranger result.

The existing physical verifier status is computed only from the verified Ranger evidence chain.
Adding or removing Microsoft runtime correlation cannot turn an unsupported physical result into a
supported one.

## Live demo reconstruction

Once the controlled tenant profile is qualified, one mission lookup can expose references for:

`Agent identity -> invocation/session/trace -> tool execution -> live SharePoint item`

alongside the independently verified existing chain:

`SharePoint authorization -> Gateway -> Ranger command -> motion -> stop -> resulting state`

The single `mission_id` joins those propositions without making any one source the sole historian.
