# Agent 365 + Ranger R0 controlled-tenant profile qualification

This runbook freezes the first real Agent 365 OTLP semantic profile used by the bounded Ranger R0 demonstration. It exists to prevent a convenient synthetic or undocumented attribute mapping from being promoted into an evidence claim.

## Qualification target

The frozen demonstration remains one mission identified by one immutable `mission_id`:

`Agent identity -> invocation/session/trace -> tool execution -> live SharePoint item -> Gateway -> R0 -> independently observed physical result`

Agent 365 telemetry is evidence about the Microsoft agent/runtime/tool boundary. The live SharePoint read-back is the Microsoft resource-state witness. Gateway and R0 retain their own evidence. None of those propositions substitutes for another.

## Preflight

Before the controlled run:

1. Use a dedicated test mission and a fresh UUID `mission_id`.
2. Confirm the SharePoint mission artifact/list used by #848 is reachable and that the exact authorization material can be read back and committed.
3. Confirm Agent 365/OTLP capture is writing the unmodified export into retained source custody before semantic projection.
4. Confirm the Agent 365 catalog/identity observation for the selected agent is retained separately.
5. Confirm the R0 physical boundary remains in safe bench configuration with independent stop capability. Do not expand the motion scenario during profile qualification.

## Capture one controlled interaction

Perform exactly one bounded agent interaction that creates or updates the selected SharePoint mission artifact. Use the same `mission_id` in the application-level mission context.

Retain, before interpretation:

- the Agent 365 catalog/identity source;
- each OTLP export containing the selected runtime and tool spans;
- the source-envelope SHA-256 commitments and protected payload references;
- the live SharePoint mission read-back and its authorization-material commitment.

Do not copy prompts, responses, tokens, or raw OTLP bodies into the qualification packet.

## Enumerate the observed semantic surface

Use the retained decoded `OtlpObservationV1` records to enumerate resource- and record-level **string attribute names**. Values remain in source custody.

Identify which already-retained spans are entering the qualification as:

- runtime/invocation spans; and
- tool-execution spans.

Classification is an explicit qualification input. Do not infer role from span name or timestamp proximity.

## Freeze the profile

Construct `Agent365OtlpAttributeProfileV1` using only keys observed in the controlled capture and supported by the intended semantic interpretation. The profile names the exact keys used for package/agent identity, invocation/session, `mission_id`, tool call/name/status, SharePoint item ID, and authorization commitment.

There are no default Microsoft attribute names in ETS. A different exporter, SDK, tenant configuration, or future Microsoft schema can therefore produce a different profile rather than silently changing evidence semantics.

## Run the qualification gate

Call `qualify_agent365_otlp_profile(...)` with:

- the frozen profile;
- explicitly classified retained runtime spans and source references;
- explicitly classified retained tool spans and source references;
- retained Agent 365 catalog identity observations;
- the live SharePoint correlation anchor.

Without a controlled-tenant attestation, successful execution returns:

`ready_for_live_qualification`

That state means only that the software projection/correlation machinery is internally consistent.

After confirming that the exact inputs came from the controlled live capture, create `Agent365ControlledTenantAttestationV1` using the returned profile SHA-256 and exact source-envelope commitments. Re-run the same function with that attestation. Only an exact match may return:

`qualified`

If the profile, mission, tenant, or retained source commitments drift, the qualification fails closed.

## Retain the qualification packet

Retain both:

- `Agent365ProfileQualificationResultV1.packet`; and
- `Agent365ProfileQualificationResultV1.packet_sha256`.

The packet contains the frozen profile, profile digest, attribute-key inventory, source commitments, source-record references, projected observation IDs, SharePoint correlation commitments, and correlation bases. It deliberately excludes raw OTLP bodies and attribute values.

## First fully live mission

After the profile is `qualified`, run one end-to-end mission without changing the profile or bounded R0 scenario:

1. Create the mission request through the selected Agent 365 agent.
2. Retain Agent identity/runtime/tool observations.
3. Read back and retain the SharePoint mission state independently.
4. Allow Gateway to validate the bounded mission authority.
5. Execute the R0 motion boundary.
6. Retain command receipt, actuation, stop decision, stop actuation, and independent resulting-state observation.
7. Build and verify the existing Evidence Object v1/v2 mission bundle.
8. Persist the Agent 365 correlation bundle separately through #856.
9. Query the authenticated mission reconstruction API by the exact same `mission_id`.
10. Verify that the API reconstructs both the sanitized Microsoft correlation section and the independently verified physical chain without claiming either one proves the other.

## Immediate post-live tests

Once one live mission succeeds, do not broaden functionality. Run contradiction cases first:

- Agent/tool reports success but SharePoint state does not match.
- SharePoint mission exists but authorization commitment differs.
- Tool/runtime trace belongs to another mission.
- Mission is duplicated or expired.
- Gateway receives the mission but R0 does not actuate.
- R0 actuates but the independent resulting-state observer does not support the expected outcome.
- Network interruption occurs between Microsoft-side state and physical execution.

Each contradiction must remain distinguishable in retained evidence rather than collapsing into a single success/failure flag.

## Soak entry gate

Start the integrated multi-hour and then 72-hour soak only after:

- the controlled-tenant profile is frozen and `qualified`;
- one fully live mission reconstructs by `mission_id`;
- the contradiction matrix fails closed as expected; and
- no release-blocking interface or evidence-schema changes remain.
