# Microsoft Agent 365 Evidence Acquisition

**Program:** Lantern Protocol — Evidence Transparency System (ETS)  
**Priority:** P0 major roadmap workstream  
**Status:** Active architecture and integration work  
**Updated:** September 2026

## Purpose

Microsoft Agent 365 provides an unusually strong commercial environment for demonstrating the ETS distinction between a **control plane** and an **evidence plane**.

Agent 365, Entra, Defender, Purview, Microsoft Graph, and OpenTelemetry can describe agent identity, authority, configuration, authentication, execution, security observations, and compliance observations. ETS should capture those source observations without treating Microsoft as the sole historian, then independently observe the resulting Microsoft 365 resource state whenever possible.

The target principle is:

> **Agent 365 governs the agent. ETS preserves, correlates, and independently verifies what can be proven about the agent's execution and consequences.**

This workstream is maintained as a top-level priority alongside physical ETS Edge qualification and ETS Mobile / Provenance qualification.

## Priority rule

The Agent 365 workstream remains P0 until ETS has demonstrated a bounded end-to-end flow that includes:

1. authoritative Agent 365 / Entra identity and configuration capture;
2. runtime execution telemetry capture;
3. target-resource pre-state or independently established starting state where practical;
4. tool/action observation;
5. target-resource post-state;
6. ETS Evidence Object projection;
7. cross-observer correlation;
8. independent verification of the resulting evidence bundle.

The workstream may progress in parallel with Edge and Mobile. It must not redefine Agent 365 telemetry as independent evidence merely because ETS copied it.

## Evidence-source classes

ETS should preserve every available evidence-bearing signal class while applying explicit policy to sensitive payload content.

| Source | Evidence captured | ETS question answered |
|---|---|---|
| Agent 365 Agent Registry | agent identity, inventory, publisher, owner, status, capabilities, configuration metadata | What agent existed? |
| Microsoft Graph agent detail surfaces | tools, connected resources, permissions, lifecycle/configuration metadata | What was it configured to do? |
| Entra Agent ID | blueprint, blueprint principal, agent identity, agent-user relationships | Who exactly was the actor? |
| Entra authorization/governance | app roles, delegated/app permissions, RBAC, owner/sponsor relationships, policy context | What authority did it possess? |
| Entra sign-in and audit records | authentication, initiator/performer, target resources, identity/configuration changes | Did this identity authenticate and how did its state change? |
| Agent 365 OpenTelemetry | invocation, session, conversation, model/inference spans, tool calls, agent-to-agent calls, exceptions, timing | What execution did Microsoft's runtime observe? |
| Defender | security detections, CloudAppEvents, gateway/tool activity and related security observations | What did Microsoft's security plane observe? |
| Purview | audit, DLP, information-protection/compliance observations | What did Microsoft's compliance plane observe? |
| Target Microsoft resource | SharePoint, OneDrive, Exchange, Teams, Entra or other resulting state | What externally visible state actually existed? |
| ETS witness | independently acquired state, hashes, timestamps, source identity | What did ETS independently observe? |
| ETS verifier | correlation and verification outputs | Do the independently attributable observations agree? |

## Preserve source before interpretation

ETS must preserve the source representation before normalizing it.

A source acquisition should first create a bounded immutable envelope such as:

```text
MicrosoftSourceEnvelope
{
  source
  source_type
  tenant_id
  acquisition_time
  microsoft_event_time
  api_version
  endpoint_family
  raw_payload_or_protected_reference
  raw_payload_sha256
  collector_identity
  collector_version
  acquisition_sequence
  previous_envelope_hash
  ets_signature
}
```

Sensitive data handling is policy-bound. "Capture everything" means **capture every evidence-bearing signal class**, not indiscriminately persist plaintext prompts, responses, secrets, PII, or document bodies forever. Depending on policy, ETS may retain the full payload, a protected encrypted payload, a stable content commitment/hash, selected normalized attributes, or a reference to content retained under a separate custody policy.

Preservation precedes interpretation. Unknown Microsoft fields should survive collection even when the current ETS normalizer does not yet understand them.

## Canonical ETS object classes

The initial Agent 365 projection should define or bind the following canonical classes:

```text
A365_AGENT_DEFINITION
A365_AGENT_CONFIGURATION
A365_AGENT_IDENTITY
A365_AUTHORITY_STATE
A365_POLICY_STATE
A365_AUTHENTICATION
A365_INVOCATION
A365_SESSION
A365_INFERENCE
A365_TOOL_EXECUTION
A365_AGENT_TO_AGENT
A365_SECURITY_OBSERVATION
A365_COMPLIANCE_OBSERVATION
M365_RESOURCE_PRE_STATE
M365_RESOURCE_POST_STATE
ETS_INDEPENDENT_OBSERVATION
ETS_CONSEQUENCE_VERIFICATION
ETS_CORRELATION_RESULT
```

These are evidence categories, not a claim that all Microsoft interfaces are stable or generally available. The SourceEnvelope records API/version maturity and collector behavior so later verification can distinguish stable, preview, and changed source contracts.

## Evidence graph

The expected graph is:

```text
Agent Blueprint
      |
      +-- Agent Instance
              |
              +-- owner / sponsor
              +-- permissions / policy
              +-- authentication
                      |
                      v
                  Invocation
                    /     \
             inference   tool execution
                             |
                             v
                         target action
                             |
                    resource pre-state
                             |
                          mutation
                             |
                    resource post-state
                             |
                  ETS independent witness
                             |
                       verification
```

A copied Microsoft record remains a Microsoft observation. ETS must preserve observer identity so that Agent 365, Entra, Defender, Purview, the target resource, and ETS itself remain distinguishable observers.

## Consequence custody

The workstream is not complete when ETS can prove that an agent called a tool. For claims about external effects, ETS should attempt to establish the state transition.

Example:

```text
Agent 365: execute_tool = SharePoint.CreateFile
            |
            v
Microsoft API response = success
            |
            v
ETS independently queries SharePoint
            |
            +-- resource ID
            +-- version
            +-- ETag
            +-- content hash/commitment where policy allows
            +-- creator/actor metadata
            +-- created/modified timestamps
            |
            v
ETS_CONSEQUENCE_VERIFICATION
```

When feasible, record both pre-state and post-state. This supports a claim about transition rather than merely proving that an endpoint currently exists.

## Cross-observer verification

Do not collapse all Microsoft-origin observations into a single generic source.

For one event ETS should be able to correlate independently attributable records from:

```text
Agent 365 OTel
+ Entra identity/authentication
+ Defender
+ Purview
+ target Microsoft resource
+ ETS witness
```

Possible correlation results include:

```text
VERIFIED
PARTIALLY_VERIFIED
CONTRADICTORY
MISSING_EXPECTED_EFFECT
UNOBSERVABLE
```

These values describe evidence relationships, not subjective trust or reputation scores.

A contradiction is itself evidence. Example:

```text
Agent 365: tool execution succeeded
Target resource: expected object absent
ETS result: MISSING_EXPECTED_EFFECT
```

## Qualification gates

### A365-Q0 — Inventory and source preservation

Deliver:

- Agent Registry / agent inventory collector;
- detailed agent metadata collector;
- source envelope;
- raw/source-preserving storage policy;
- configuration hashing;
- unknown-field retention;
- deterministic normalization fixtures;
- change detection.

Exit criterion: ETS can reproduce a bounded agent inventory snapshot from retained source envelopes and independently verify the ETS projection.

### A365-Q1 — Identity and authority

Deliver:

- Entra Agent ID and blueprint relationships;
- agent instance lineage;
- owners/sponsors where available;
- app/delegated permission capture;
- Entra/Azure role context where applicable;
- policy/Conditional Access context when available to the collector;
- authority-state Evidence Objects.

Exit criterion: an invocation can be bound to the agent identity and to a retained authority-state observation valid for the relevant time window.

### A365-Q2 — Authentication and audit

Deliver:

- sign-in ingestion;
- audit ingestion;
- initiator/performer/target-resource relationships;
- authentication outcome;
- identity/configuration change history;
- API maturity/version labeling.

Exit criterion: ETS can correlate an agent invocation with the relevant authentication/audit lineage without assuming that identity alone proves execution or consequence.

### A365-Q3 — Runtime / OpenTelemetry

Deliver:

- OTel trace ingestion;
- invocation/session/conversation correlation;
- inference/model span normalization;
- tool execution spans;
- agent-to-agent spans;
- exception and timing evidence;
- span/parent-span preservation;
- privacy policy for prompts, outputs and model payloads.

Exit criterion: ETS can reconstruct a bounded execution tree from retained telemetry while preserving the fact that it is Microsoft's runtime observation.

### A365-Q4 — Microsoft resource consequence custody

Deliver bounded resource observers beginning with Microsoft 365 resources already present in the ETS connector program.

Initial target order:

1. SharePoint / OneDrive;
2. Entra identity/resource mutation cases;
3. Exchange;
4. Teams;
5. additional Microsoft/Azure targets as justified by evidence value.

For supported mutation classes capture, when feasible:

- pre-state;
- action/tool context;
- API response;
- post-state;
- stable resource identity;
- version/ETag;
- content hash or protected commitment where policy allows;
- ETS observation time and observer identity.

Exit criterion: ETS can demonstrate that an Agent 365 action and the independently observed Microsoft resource transition are correlated but separately attributable.

### A365-Q5 — End-to-end independent verification

Deliver:

- cross-observer evidence graph;
- contradiction detection;
- portable verification bundle;
- deterministic verifier result;
- independent replay/reproduction instructions;
- documented uncertainty and unobservable conditions.

Exit criterion: an external verifier can reproduce the bounded identity → authority → execution → target-state → ETS-observation chain from exported artifacts without needing to trust the live agent runtime.

## Initial demonstration

The first commercial demonstration should be deliberately narrow:

```text
Agent 365 agent
   -> Entra Agent ID
   -> Agent 365 / OTel invocation
   -> SharePoint tool action
   -> create or modify a controlled test document
   -> ETS independently retrieves SharePoint resulting state
   -> ETS creates Evidence Objects
   -> ETS correlates identity, authority, invocation, tool call and resource transition
   -> independent ETS verifier reproduces PASS / mismatch result
```

This demonstration directly illustrates the architectural distinction:

```text
CONTROL PLANE
Who is the agent?
What may it do?
What policy governs it?
What did the runtime report?

        versus

EVIDENCE PLANE
What source observations were retained?
What externally changed?
What did ETS independently observe?
Do the observations agree?
Can another party reproduce the verification later?
```

## Dependencies

Agent 365 evidence acquisition reuses rather than replaces:

- ETS Core and Evidence Object semantics;
- ETS Verify;
- ETS Gateway;
- existing Microsoft 365 / Graph connector work;
- identity and workload-authentication qualification;
- source-preserving custody;
- Vault/Black Box where long-term or incident-survivable retention is required;
- AI Witness for general agent-runtime evidence patterns.

## Non-goals

This workstream does not:

- claim that Microsoft telemetry independently proves the underlying real-world event;
- treat a successful tool call as proof of a resulting external state;
- require ETS to store sensitive plaintext when a commitment/reference satisfies the evidentiary requirement;
- replace Agent 365 governance, Entra authorization, Defender security operations, or Purview compliance;
- assign a generic trust score to an agent or Microsoft service;
- make preview APIs equivalent to stable production contracts.

## Program-level success condition

Agent 365 becomes a successful ETS reference integration when ETS can demonstrate, with independently reproducible artifacts, that:

> a specific governed agent identity operated under a retained authority/configuration state, Microsoft observed a bounded execution, a target Microsoft resource transitioned to a separately observed resulting state, ETS preserved the attributable observations without collapsing their provenance, and an independent verifier can later reproduce the evidence relationship and expose agreement, contradiction, absence, or uncertainty.
