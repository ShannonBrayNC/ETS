# ETS Policy Routing v0.1 Skeleton

Status: Draft
Scope: Public protocol policy-routing skeleton
Patent notice: ETS - Evidence Transparency System is patent pending. This public policy-routing material does not include USPTO receipts, application numbers, claim charts, prior-art matrices, assignment records, attorney-review notes, private drafts, customer evidence, secrets, or private Lantern-IP materials.

## 1. Purpose

ETS policy routing defines how verified evidence states, proof status, source scope, sensitivity labels, requested actions, and claim boundaries are converted into routing outcomes.

Policy routing is intended to prevent unverified or overclaimed evidence from directly influencing downstream automation, governance, public release, or audit workflows.

## 2. Routing goals

An ETS policy route should:

- receive explicit evidence states;
- receive proof and certificate status;
- evaluate requested action;
- consider sensitivity and claim boundaries;
- return a deterministic route;
- explain why the route was selected;
- preserve human-review pathways; and
- avoid overclaiming real-world truth or legal/election correctness.

## 3. Candidate policy-route object

```json
{
  "schema_version": "ets.policy_route.v0.1",
  "route_id": "route-example-0001",
  "event_id": "evt-example-0001",
  "certificate_id": "cert-example-0001",
  "requested_action": "trigger_automation",
  "evidence_states": ["Schema Valid", "Hash Verified", "Inclusion Proof Verified"],
  "proof_status": "proof_verified",
  "certificate_status": "verified",
  "source_scope": "registered_internal_source",
  "sensitivity": ["internal"],
  "claim_boundaries": [
    "Verifies submitted-event metadata and proof material only."
  ],
  "route": "human_review",
  "reasons": [
    "requested_action requires human review under v0.1 policy profile"
  ],
  "generated_at_utc": "2026-01-01T00:00:00Z"
}
```

## 4. Candidate route outcomes

ETS v0.1 candidate route values:

- automation_allowed;
- human_review;
- quarantine;
- reject;
- archive;
- restrict_release;
- escalate;
- no_action.

## 5. Candidate inputs

Policy routing may evaluate:

- evidence_states;
- proof_status;
- certificate_status;
- source_system;
- source_scope;
- tenant_id;
- workspace_id;
- requested_action;
- sensitivity;
- claim_boundaries;
- event_type;
- redaction_profile;
- prior policy route;
- reviewer decision;
- replay result.

## 6. Candidate proof-status values

- not_evaluated;
- proof_verified;
- proof_invalid;
- proof_missing;
- root_mismatch;
- event_hash_mismatch;
- leaf_hash_mismatch;
- stale_tree_head;
- unsupported_profile;
- verifier_error.

## 7. Candidate requested actions

- record_only;
- generate_certificate;
- public_release;
- trigger_automation;
- create_issue;
- approve_release;
- modify_governance_record;
- escalate_incident;
- archive_record;
- replay_verification;
- export_report.

## 8. Candidate rule examples

### Rule: require human review before automation

```yaml
id: ets-policy-001
name: Require human review before downstream automation
when:
  requested_action:
    - trigger_automation
    - create_issue
    - approve_release
    - modify_governance_record
require:
  evidence_states:
    - Hash Verified
    - Included
    - Inclusion Proof Verified
outcome: human_review
```

### Rule: quarantine invalid proof material

```yaml
id: ets-policy-002
name: Quarantine invalid proof material
when:
  proof_status:
    - proof_invalid
    - proof_missing
    - root_mismatch
assign_states:
  - Quarantined
  - Requires Human Review
outcome: quarantine
```

### Rule: restrict civic or election-adjacent public release

```yaml
id: ets-policy-003
name: Restrict civic and election-adjacent public release
when:
  sensitivity:
    - potential_civic_impact
    - public_release_restricted
    - privacy_sensitive
assign_states:
  - Public Release Restricted
  - Requires Human Review
outcome: human_review
```

## 9. Routing profiles

Candidate v0.1 profiles:

- ets-policy-core-v0.1;
- ets-policy-devsecops-v0.1;
- ets-policy-ai-governance-v0.1;
- ets-policy-emergency-sensor-v0.1;
- ets-policy-civic-boundary-v0.1;
- ets-policy-public-release-v0.1.

## 10. Human review

A route to human_review should preserve enough context for a reviewer to understand:

- what event was submitted;
- what proof material was verified or rejected;
- what certificate was generated;
- what action was requested;
- what policy rule matched;
- what claim boundary applies;
- what safe next actions exist.

## 11. Quarantine and reject behavior

A route to quarantine should preserve the event and diagnostic metadata while blocking automated downstream actions.

A route to reject should produce a deterministic reason code. Rejected events may still be auditable as rejected submissions, depending on deployment policy.

Candidate reason codes:

- invalid_schema;
- unsupported_schema_version;
- missing_content_hash;
- unsupported_hash_algorithm;
- canonicalization_failed;
- proof_missing;
- proof_invalid;
- root_mismatch;
- source_not_authorized;
- sensitivity_requires_review;
- claim_boundary_missing;
- requested_action_forbidden.

## 12. Relationship to certificates

A certificate may include policy-routing results, but policy routing should not expand the certificate's claim boundary.

If a policy route allows automation, the certificate should still state exactly what was verified and what was not verified.

## 13. Relationship to audit replay

Audit replay should be able to reproduce or explain the policy route using:

- original EvidenceEvent metadata;
- proof status;
- certificate status;
- policy profile;
- policy version;
- input sensitivity labels;
- requested action;
- matched rule identifiers.

## 14. Test-vector requirements

Policy-routing test vectors should include:

- verified evidence routed to archive;
- verified evidence routed to human_review before automation;
- invalid proof routed to quarantine;
- missing claim boundary routed to human_review or restrict_release;
- civic/election-adjacent public release routed to human_review;
- emergency/sensor evidence routed to escalation;
- unsupported profile routed to reject or human_review;
- replay of same inputs producing same route.

## 15. Security considerations placeholder

The final policy-routing format must address:

- policy bypass;
- ambiguous source scope;
- hidden automated action;
- policy version drift;
- inconsistent human-readable and machine-readable outcomes;
- unsafe public release;
- overclaiming by downstream systems;
- prompt-injection or AI-agent misuse of certificate text;
- external system authorization; and
- audit replay of routing decisions.

## 16. Open issues

- Decide whether policy rules are normative or profile-specific in v0.1.
- Decide whether policy language is YAML, JSON, Rego-compatible, or implementation-defined.
- Decide whether route outcomes are mandatory vocabulary.
- Decide how human reviewer decisions are represented.
- Decide how policy versioning interacts with replay.
