# ETS EvidenceEvent Schema v0.1 Skeleton

Status: Draft
Scope: Public protocol schema skeleton
Patent notice: ETS - Evidence Transparency System is patent pending. This public schema material does not include USPTO receipts, application numbers, claim charts, prior-art matrices, assignment records, attorney-review notes, private drafts, customer evidence, secrets, or private Lantern-IP materials.

## 1. Purpose

The EvidenceEvent schema defines the submitted-event contract for ETS. It describes the metadata, content-hash references, source context, sensitivity labels, claim boundaries, and routing context used by ETS to canonicalize, hash, append, prove, verify, certify, route, and replay evidence events.

## 2. Design goals

An EvidenceEvent should be:

- deterministic enough to hash reproducibly;
- expressive enough to describe cross-application evidence;
- safe enough to avoid raw evidence disclosure by default;
- bounded enough to prevent overclaiming;
- versioned enough to survive protocol evolution; and
- testable enough for conformance vectors.

## 3. Non-goals

An EvidenceEvent is not required to store raw evidence bytes. It may reference external evidence through content hashes, URIs, repository references, ticket IDs, or other external references.

An EvidenceEvent does not prove the real-world truth of the referenced evidence. It records submitted-event metadata and allows ETS to verify protocol-level consistency.

## 4. Candidate JSON object

```json
{
  "schema_version": "ets.event.v0.1",
  "event_id": "evt-example-0001",
  "tenant_id": "example-tenant",
  "workspace_id": "example-workspace",
  "evidence_id": "evd-example-0001",
  "event_type": "example_event",
  "subject_ref": "human-readable subject or external reference",
  "content_hash_alg": "sha256",
  "content_hash": "sha256:example-content-hash-placeholder",
  "source_system": "example-source-system",
  "actor_id": "example-actor-or-system",
  "correlation_id": "example-correlation-id",
  "created_at_utc": "2026-01-01T00:00:00Z",
  "metadata": {},
  "external_refs": [],
  "sensitivity": [],
  "claim_boundary": [],
  "redaction_profile": "default"
}
```

## 5. Candidate field catalog

| Field | Candidate requirement | Description |
| --- | --- | --- |
| schema_version | required | Version of the EvidenceEvent schema. |
| event_id | required | Unique event identifier in the submitter or ETS namespace. |
| tenant_id | required | Tenant, organization, project, or deployment namespace. |
| workspace_id | required | Workspace, repository, program, mission, or operating boundary. |
| evidence_id | required | Evidence item identifier or logical evidence handle. |
| event_type | required | Event category, such as architecture_snapshot, workflow_approval, sensor_evidence, or audit_record. |
| subject_ref | recommended | Human-readable reference to the subject of the event. |
| content_hash_alg | required | Hash algorithm used for the referenced evidence content. |
| content_hash | required | Hash of the referenced evidence content or evidence packet. |
| source_system | required | System, process, integration, or human workflow that submitted or originated the event. |
| actor_id | recommended | Human, system, agent, or workflow identity associated with submission. |
| correlation_id | recommended | Trace identifier linking the event to a workflow, case, release, incident, or review. |
| created_at_utc | required | UTC timestamp supplied for event creation or submission. |
| metadata | required | JSON object containing event-specific metadata. |
| external_refs | optional | Array of references to external systems or records. |
| sensitivity | optional | Array of sensitivity labels. |
| claim_boundary | recommended | Array of statements limiting what the event and certificate claim. |
| redaction_profile | optional | Named redaction or evidence-disclosure profile. |

## 6. External references

An external reference object should be explicit about reference type and value:

```json
{
  "type": "repo",
  "ref": "owner/repository/path-or-commit",
  "label": "optional human label"
}
```

Candidate external reference types:

- repo;
- issue;
- pull_request;
- document;
- ticket;
- sensor_record;
- incident_record;
- certificate;
- receipt;
- package;
- artifact;
- other.

## 7. Sensitivity labels

Candidate sensitivity labels:

- public;
- internal;
- confidential;
- restricted;
- privacy_sensitive;
- security_sensitive;
- public_release_restricted;
- human_review_required;
- potential_civic_impact;
- emergency_context;
- synthetic_test_data.

## 8. Claim-boundary examples

Candidate claim-boundary strings:

- Verifies submitted-event metadata and proof material only.
- Does not prove real-world truth without external observation.
- Does not prove legal sufficiency.
- Does not prove official chain of custody unless separately designated.
- Does not prove completeness of all expected events without an expected-event policy.
- Does not prove election correctness, vote totals, ballot validity, or voter eligibility.

## 9. Hashable-payload candidate

The hashable payload should include stable submitted fields and exclude future server-generated proof fields.

Candidate included fields:

- schema_version;
- event_id;
- tenant_id;
- workspace_id;
- evidence_id;
- event_type;
- subject_ref;
- content_hash_alg;
- content_hash;
- source_system;
- actor_id;
- correlation_id;
- created_at_utc;
- metadata;
- external_refs;
- sensitivity;
- claim_boundary;
- redaction_profile.

Candidate excluded fields:

- append_index;
- event_hash;
- leaf_hash;
- tree_head;
- inclusion_proof;
- verification_certificate;
- server_received_at_utc;
- policy_route;
- replay_report.

## 10. Validation rules placeholder

Future normative validation should address:

- required field presence;
- field type checks;
- timestamp format;
- hash algorithm vocabulary;
- hash prefix and digest format;
- external reference shape;
- metadata JSON restrictions;
- maximum object size;
- allowed Unicode normalization profile;
- claim-boundary requirement for public or civic/election-adjacent evidence; and
- rejection behavior.

## 11. Example event types

Candidate event_type values:

- architecture_snapshot;
- workflow_approval;
- ai_agent_recommendation;
- policy_decision;
- release_gate_evidence;
- github_issue_or_pr_evidence;
- emergency_report;
- outage_record;
- rf_anomaly;
- sensor_telemetry;
- weather_impact;
- civic_evidence_packet;
- audit_replay_request;
- certificate_generation;
- formal_traceability_record.

## 12. Test-vector requirements

Each EvidenceEvent test vector should include:

- input event JSON;
- canonical payload or canonical bytes representation;
- expected event_hash;
- expected leaf_hash;
- expected validation status;
- expected rejection reason for invalid vectors; and
- expected policy-route hint when applicable.

## 13. Open issues

- Decide whether tenant_id and workspace_id are mandatory for single-tenant deployments.
- Decide whether actor_id is required or optional.
- Decide whether content_hash is always required or may be deferred for metadata-only events.
- Decide maximum metadata size.
- Decide exact canonicalization profile.
- Decide whether claim_boundary is required for all certificates or only public-facing certificates.
