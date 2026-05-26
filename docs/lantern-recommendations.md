# ETS Lantern Recommendation Export

## Purpose

Christina reviews Lantern product-family recommendations on a fixed operating loop. ETS exposes its open work in a stable shape so Christina and SignalForge can route software changes, process changes, documentation work, and investigations without creating duplicate issues.

## Query pattern

Use:

```text
GET /api/v1/lantern/recommendations
```

The response contains:

- `recommendations`: the full ETS recommendation list,
- `sprintCandidates`: actionable items suitable for sprint intake,
- `duplicateKey`: a deterministic key derived from owner repo, item type, and title,
- `trackingIssueUrl`: the existing GitHub issue when one already exists.

SignalForge should search for the `duplicateKey` or `trackingIssueUrl` before creating a new issue. If either exists, update the existing item instead of creating another.

## Update pattern

Use:

```text
POST /api/v1/lantern/recommendations/{recommendationId}
```

Request body:

```json
{
  "status": "in-review",
  "trackingIssueUrl": "https://github.com/ShannonBrayNC/ETS/issues/34",
  "note": "Christina selected this for hosted-readiness sprint review.",
  "author": "christina"
}
```

The update appends a review note and returns the refreshed export. ETS does not auto-close issues or perform customer-facing actions through this route.

## Item classes

| Type | Use |
| --- | --- |
| `software-change` | Code, API, UI, test, or deployment work. |
| `process-change` | Workflow, governance, or operator behavior change. |
| `documentation-change` | Architecture, release, research, runbook, or user-facing docs. |
| `investigation` | Research, scoping, risk review, or future phase planning. |

## Approval boundary

Recommendation export is safe for routing and sprint planning. Customer-facing actions remain approval-gated through the Lantern consent flow and must still pass ETS proof verification before use.
