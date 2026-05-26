# ETS Lantern Adapter Contract

## Purpose

ETS exposes ticket intelligence, proof, consent, and verification services to Lantern without becoming the human approval layer. Lantern Core coordinates workflow state, Christina owns human-facing review and approvals, and ETS records tamper-evident evidence receipts plus machine-readable verification results.

## Exposed capabilities

| Capability | Lantern use | ETS responsibility |
| --- | --- | --- |
| Ticket ingestion | Register a ticket-analysis source event from OpsHelm or another vertical adapter. | Store metadata hashes, source IDs, custody metadata, and proof bundles. |
| Log and HAR analysis | Bind derived findings to raw artifact hashes without storing raw customer data. | Verify that findings correspond to registered artifact hashes. |
| Customer update drafting | Notarize a draft and mark it as approval-gated. | Return proof and consent status; never send customer-facing text. |
| Escalation recommendation | Record why a ticket or incident should move to another owner. | Preserve recommendation provenance and source hashes. |
| ROI and time-saved calculation | Capture operational metrics from adapter outputs. | Store metric evidence hashes and calculation metadata. |
| Report export | Produce verification packets for review, audit, or Content Engine reuse. | Generate proof bundles, certificates, and machine-readable reason codes. |

## Input payload from Lantern Core

Lantern Core should send a normalized support-intelligence request:

```json
{
  "lanternEventId": "lantern-support-001",
  "eventType": "lantern.support.analysis.requested",
  "sourceSystem": "opshelm",
  "workspaceId": "workspace-alpha",
  "ticketRef": "DEMO-1001",
  "artifactHashes": [
    {
      "artifactId": "ticket-body",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "kind": "ticket"
    },
    {
      "artifactId": "har-redacted",
      "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "kind": "har"
    }
  ],
  "requestedOutputs": [
    "customer_summary",
    "internal_summary",
    "technical_findings",
    "recommended_actions",
    "kb_candidates"
  ],
  "approvalState": "required",
  "consentId": "consent-support-001",
  "correlationId": "corr-support-001"
}
```

Raw tickets, logs, HAR files, customer messages, and credentials stay outside ETS. ETS receives references, normalized metadata, and hashes.

## Output artifacts to Lantern Core

ETS returns a support-intelligence verification envelope:

```json
{
  "lanternEventId": "lantern-support-001",
  "status": "hold-for-approval",
  "reasonCode": "approval-required",
  "proofBundleUrl": "/api/v1/bundles/artifact_registered:ticket-body",
  "outputs": {
    "customerSummary": {
      "artifactHash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "approvalRequired": true
    },
    "internalSummary": {
      "artifactHash": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "approvalRequired": false
    },
    "technicalFindings": [],
    "recommendedActions": [],
    "kbCandidates": []
  },
  "memoryObservations": [
    {
      "type": "recurring_support_pattern",
      "summary": "Multiple tickets reference the same redacted HAR failure signature.",
      "evidenceHash": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    }
  ]
}
```

## Lantern event mapping

| Lantern event type | ETS event type | Human approval required |
| --- | --- | --- |
| `lantern.support.ticket.ingested` | `evidence.registered` | No |
| `lantern.support.log.analyzed` | `evidence.registered` | No |
| `lantern.support.customer_update.drafted` | `evidence.registered` | Yes |
| `lantern.support.escalation.recommended` | `evidence.registered` | Yes when customer-facing or owner-changing |
| `lantern.support.kb_candidate.created` | `evidence.registered` | Yes before publishing externally |
| `lantern.support.report.exported` | `evidence.registered` | No for internal export; yes before customer delivery |

Approval-gated outputs must remain drafts until Christina or another configured approval authority records a granted consent event. ETS reports `hold-for-approval` or blocking reason codes; it does not override the approval decision.

## Content Engine handoff

Reusable knowledge or campaign material can flow to Content Engine only after ETS verification succeeds and approval-gated fields are either removed or approved. The handoff should include:

- artifact hash,
- proof bundle URL,
- consent ID,
- source ticket reference,
- allowed reuse scope,
- redaction profile,
- verification status and reason code.

Content Engine should treat unverified, quarantined, or blocked outputs as non-ingestable.

## Local sample workflow

1. Christina asks Lantern to review `DEMO-1001`.
2. Lantern Core asks OpsHelm for ticket and redacted log analysis.
3. OpsHelm returns hashes for the ticket body, redacted HAR, internal notes, and draft customer update.
4. Lantern Core calls `POST /api/v1/lantern/support/analyze` to receive the structured support-intelligence bundle.
5. ETS registers the hashes as `evidence.registered` events and emits proof bundles.
6. Lantern Core calls `POST /api/v1/lantern/verify` with the source event, proof bundle, consent event, and `action_type`.
7. ETS returns `passed`, `hold-for-approval`, `quarantined`, or `blocked` with a stable `reasonCode`.
8. Christina reviews any `hold-for-approval` customer-facing draft.
9. Approved reusable KB candidates are forwarded to Content Engine with proof and consent references.

## Boundary statement

ETS proves that registered metadata, hashes, proof bundles, and consent references are internally consistent and tamper-evident. ETS does not prove that a support diagnosis is factually complete, that raw ticket data was captured perfectly, or that a draft is safe to send. Those decisions remain with source systems, Christina, and the configured governance policy.
