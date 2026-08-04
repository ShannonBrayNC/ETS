# Research Certificate Generator

## Status

Research/specification draft for `ETS-RESEARCH-001`.

This document defines a proposed ETS Research Certificate Generator. It is not an
implementation contract yet. Follow-on implementation issues should be created
only after the schema, lifecycle, and review semantics are accepted.

## Objective

An ETS research certificate is a verifiable envelope around a research result. It
records the research question, generated conclusion, source/evidence references,
claim mappings, source quality indicators, review state, and ETS proof material.

The certificate is designed to answer a narrow question:

> Given this research output, what evidence was submitted, what was hashed, what
> was linked, what was reviewed, and what can an independent verifier check?

It does **not** prove that the conclusion is true in the real world. It proves
only that the submitted evidence records, hashes, links, and review metadata are
consistent with the published ETS evidence and proof material.

## Design constraints

ETS alpha already separates evidence metadata from raw evidence bytes. The
Research Certificate Generator must preserve that boundary.

Required constraints:

- Store and verify metadata, identifiers, content hashes, and proof references.
- Do not require raw sensitive source content to be stored inside ETS.
- Use canonical JSON for hashable certificate payloads.
- Support public and private certificate profiles.
- Make review state explicit instead of implying that an AI-generated answer is
  self-validating.
- Treat source quality, contradiction status, and reviewer approval as certificate
  fields, not hidden assumptions.

## Reference standards and patterns

The certificate model should borrow from existing standards without claiming that
ETS is a full implementation of any one of them.

| Reference | Pattern useful to ETS | Application in research certificates |
| --- | --- | --- |
| W3C PROV | Entities, activities, agents, attribution, derivation, bundles, and provenance interchange | Model research question, source capture, extraction, synthesis, certificate generation, and reviewer action as auditable provenance |
| RFC 9162 Certificate Transparency | Append-only log, Merkle inclusion proofs, consistency proofs | Bind certificate and evidence references to ETS log entries and verifiable tree heads |
| NIST AI RMF | Governed AI lifecycle, test/evaluate/verify/validate concepts, risk management | Require review state, limitation disclosure, and high-stakes workflow gates |
| C2PA | Provenance manifest, assertions, ingredients, signed claim concepts | Inform public verification UX and artifact provenance blocks without limiting ETS to media files |

Reference URLs:

- https://www.w3.org/TR/prov-overview/
- https://www.w3.org/TR/prov-dm/
- https://www.rfc-editor.org/rfc/rfc9162
- https://www.nist.gov/itl/ai-risk-management-framework
- https://spec.c2pa.org/specifications/specifications/2.1/index.html

## Lifecycle

```text
Research Question
  -> Research Run Created
  -> Source Discovery
  -> Source Capture
  -> Evidence Events Appended
  -> Claim Extraction
  -> Citation / Evidence Linking
  -> Source Quality Assessment
  -> Contradiction / Dispute Check
  -> Human Review
  -> Certificate Generation
  -> Export / Publication
  -> Public or Private Verification
```

### 1. Research run created

A research run begins with a scoped question, tenant/workspace context, purpose,
expected output profile, and privacy profile.

Example purposes:

- VA claim support memo
- legal filing support research
- policy paper research
- technical architecture decision record
- incident/audit report
- vendor due diligence

### 2. Source discovery

Source discovery produces candidate source references. A candidate source is not
yet evidence until ETS captures enough metadata and hash material to reference it
reliably.

Candidate metadata:

- source URL or local source identifier
- source title
- source type
- discovered timestamp
- retrieval timestamp when available
- source date / published date when available
- access profile: public, private, restricted, redacted
- discovery query or user-supplied source context

### 3. Source capture

Source capture records the metadata and content hash for an evidence object.
Capture profiles should be explicit:

- `metadata_only`: source metadata and external reference only
- `hash_only`: content hash and metadata without retained source bytes
- `snapshot_ref`: source hash plus reference to an external snapshot package
- `private_attachment_ref`: private source reference with hash and access policy
- `public_snapshot`: public source snapshot intended for verification

### 4. Evidence events appended

Each captured source should map to one or more ETS `EvidenceEvent` records. The
certificate should not replace the append-only log. It should reference log entries
and proof bundles.

Minimum references:

- `event_id`
- `evidence_id`
- `event_hash`
- `content_hash`
- `content_hash_alg`
- `tree_size`
- `leaf_index`
- `root_hash`
- optional inclusion proof reference
- optional consistency proof reference

### 5. Claim extraction

A claim is a discrete assertion that can be linked to one or more evidence
objects. The claim text may be stored directly in public profiles only when it is
safe to publish. Otherwise, the certificate should store a claim hash and a
redacted summary.

Claim statuses:

- `draft`
- `supported`
- `weakly_supported`
- `contradicted`
- `unverified`
- `out_of_scope`
- `needs_human_review`
- `approved`
- `rejected`
- `superseded`

### 6. Citation and evidence linking

Each claim should carry evidence links with a relationship type.

Relationship types:

- `supports`
- `refutes`
- `context`
- `primary_authority`
- `secondary_authority`
- `source_of_quote`
- `stale_authority`
- `duplicate_source`
- `unreachable_source`
- `private_reference`

### 7. Source quality assessment

The certificate should include source quality summaries without pretending that a
single score proves correctness.

Recommended initial tiers:

- `tier_1_primary_authority`: statutes, regulations, official agency guidance,
  court opinions, official product/security documentation
- `tier_2_authoritative_analysis`: peer-reviewed papers, government reports,
  standards bodies, authoritative datasets
- `tier_3_reputable_secondary`: reputable journalism, analyst reports, vendor docs
  outside direct authority, professional analysis
- `tier_4_low_authority`: blogs, forums, social posts, marketing pages,
  unreviewed commentary
- `tier_5_unverified_or_generated`: inaccessible, unknown, stale, unverifiable, or
  suspected AI-generated sources

### 8. Contradiction and dispute check

The certificate must preserve disagreement. It should not collapse conflicting
sources into a smooth answer.

Dispute statuses:

- `none_detected`
- `conflicting_sources`
- `jurisdiction_mismatch`
- `stale_source_conflict`
- `partial_support_only`
- `source_does_not_support_claim`
- `expert_review_required`

### 9. Human review

Human review should be modeled as an auditable activity. The certificate should
record who reviewed, what scope was reviewed, when review happened, and the final
review state.

Review states:

- `ai_draft`
- `source_captured`
- `needs_human_review`
- `human_reviewed`
- `approved`
- `approved_with_limitations`
- `disputed`
- `superseded`
- `deprecated`
- `published`

### 10. Certificate generation

The generator produces a hashable certificate payload and one or more renderings.
The hashable payload should be JSON-native and deterministic. Rendered Markdown,
HTML, PDF, or DOCX artifacts should include the certificate ID and verification
block.

## Proposed schema

```json
{
  "schema_version": "ets.research_certificate.v0",
  "certificate_id": "ets-cert-2026-000001",
  "certificate_type": "research_result",
  "tenant_id": "tenant-local",
  "workspace_id": "workspace-default",
  "created_at_utc": "2026-06-24T20:00:00Z",
  "status": "ai_draft",
  "privacy_profile": "private",
  "research_run": {
    "run_id": "research-run-2026-000001",
    "question": "What features should ETS research adopt from cited answer engines?",
    "purpose": "technical_architecture_research",
    "started_at_utc": "2026-06-24T19:45:00Z",
    "completed_at_utc": "2026-06-24T20:00:00Z"
  },
  "output": {
    "title": "ETS Research Feature Recommendations",
    "summary_hash": "sha256:...",
    "artifact_refs": [
      {
        "artifact_id": "artifact-001",
        "artifact_type": "markdown_brief",
        "content_hash": "sha256:...",
        "uri": "private://artifacts/research-feature-recommendations.md"
      }
    ]
  },
  "claims": [
    {
      "claim_id": "claim-001",
      "claim_text": "Research certificates should include source hashes and review state.",
      "claim_hash": "sha256:...",
      "status": "supported",
      "evidence_links": [
        {
          "evidence_id": "evidence-001",
          "event_id": "event-001",
          "relationship": "supports",
          "source_quality_tier": "tier_1_primary_authority"
        }
      ]
    }
  ],
  "evidence_summary": {
    "evidence_count": 3,
    "public_source_count": 2,
    "private_source_count": 1,
    "source_quality_counts": {
      "tier_1_primary_authority": 1,
      "tier_2_authoritative_analysis": 1,
      "tier_3_reputable_secondary": 1
    }
  },
  "dispute_summary": {
    "status": "none_detected",
    "notes_hash": "sha256:..."
  },
  "review": {
    "review_state": "needs_human_review",
    "reviewer_agent_id": null,
    "reviewed_at_utc": null,
    "review_notes_hash": null
  },
  "verification": {
    "certificate_hash_alg": "sha256",
    "certificate_hash": "sha256:...",
    "ets_log_refs": [
      {
        "event_id": "event-001",
        "leaf_index": 42,
        "tree_size": 43,
        "root_hash": "...",
        "inclusion_proof_ref": "proof://event-001"
      }
    ],
    "tree_head_ref": "tree-head://2026-06-24T20:00:00Z"
  },
  "limitations": [
    "ETS verifies submitted evidence records and proof material, not real-world completeness.",
    "AI-generated summaries require human review before publication."
  ]
}
```

## ETS verification block

Every rendered artifact should include a compact verification block.

```text
ETS Verification
Certificate ID: ets-cert-2026-000001
Schema: ets.research_certificate.v0
Status: needs_human_review
Evidence Count: 3
Public Sources: 2
Private Sources: 1
Certificate Hash: sha256:...
Root Hash: ...
Generated UTC: 2026-06-24T20:00:00Z
Limitations: ETS verifies submitted evidence records and proof material, not real-world completeness.
```

## Public versus private certificate profiles

### Public profile

The public profile may expose:

- certificate ID
- certificate hash
- public source references
- source quality summary
- claim summaries safe for publication
- review state
- limitation statement
- inclusion/consistency proof references

The public profile must not expose:

- raw private evidence
- private medical/legal/campaign records
- protected personal data
- sealed or privileged material
- private prompt or reviewer notes unless explicitly approved

### Private profile

The private profile may expose richer internal references:

- private attachment identifiers
- internal artifact paths
- reviewer notes
- full claim text
- source excerpts when legally and ethically permitted
- access-control metadata

## Export formats

Recommended sequence:

1. JSON certificate payload for deterministic hashing and API verification.
2. Markdown rendering for review and repository documentation.
3. HTML rendering for local browser review.
4. PDF/DOCX rendering only after public/private redaction behavior is defined.

## Acceptance criteria for this research sprint

- The certificate lifecycle is defined from question to verification.
- The schema maps to ETS evidence objects and Merkle proof references.
- Review state, source quality, contradiction status, and limitations are explicit.
- The model supports public/private output profiles.
- Follow-on implementation work can be decomposed into core, API, verifier, reports,
  and explorer issues.

## Follow-on implementation candidates

After review, create implementation issues for:

1. `ets.core.research` certificate dataclasses / Pydantic models.
2. Canonical certificate hashing helper.
3. API route to generate a certificate from existing evidence events.
4. CLI command to verify a research certificate.
5. Markdown/HTML certificate renderer.
6. Explorer UI certificate detail view.
7. Public/private certificate redaction policy.
8. Tests for canonical payload stability and proof-reference validation.

## Open questions

1. Should the certificate be append-only as its own ETS evidence event, or should it
   remain an export artifact that references underlying evidence events?
2. Should reviewer notes be hash-only by default?
3. Should public certificates allow redacted claim text, or only claim hashes plus
   safe summaries?
4. Should source quality tiering be required for certificate generation or allowed
   to remain `unscored` in alpha?
5. Should certificate verification fail when a referenced source is stale, or only
   report staleness as a warning?
