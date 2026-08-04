# Formal Evidence Capture Gate

## Status

Sprint artifact for issues `#70` and `#67`.

This gate protects the credibility of downstream ETS research, dissertation,
publication, and research-certificate work. It separates three different states
that must never be conflated:

1. A formal/specification file exists.
2. A workflow executed the formal target.
3. A retained evidence artifact proves what happened during execution.

Only the third state is strong enough for dissertation or publication citation.

## Scope

This sprint covers formal and reproducibility evidence capture for:

- TLC/TLA+ bounded PR validation.
- TLC/TLA+ full evidence capture outside the PR smoke gate.
- Lean mechanized proof validation.
- Apalache symbolic-safe model validation.
- Artifact retention for passing and failing formal targets.
- Evidence-report updates that distinguish passing validation, bounded validation,
  timeout/deferred validation, and failing model/proof commands.

## Non-goals

This sprint does not claim:

- universal theorem proof;
- universal liveness;
- Byzantine consensus;
- Internet-scale adversarial correctness;
- legal sufficiency;
- real-world evidence completeness;
- that a failed formal target is acceptable for publication.

A failed target is acceptable only as a captured engineering fact. Publication
claims must either exclude the failed claim or mark it pending.

## Evidence capture design

### PR smoke gate

The regular pull-request formal workflow remains bounded so it cannot hang
indefinitely during sprint handoff.

PR-gate TLC behavior:

- runs the configured TLC target set;
- records one log per model;
- records `summary.md` and `results.json`;
- uploads `tlc-evidence-artifacts` on success or failure;
- treats non-timeout TLC failures as workflow failures;
- treats timeouts as deferred to the full TLC evidence gate unless configured
  otherwise.

### Full TLC evidence gate

The full TLC evidence workflow is intentionally outside the pull-request smoke
gate and runs only through `workflow_dispatch`.

Full gate behavior:

- runs the same TLC target set with a configurable longer per-model timeout;
- defaults to `1800` seconds per model;
- defaults to treating timeouts as failures;
- uploads `full-tlc-evidence-artifacts` with per-model logs, Markdown summary,
  and JSON result metadata.

This is the sprint path for issue `#70`.

### Lean proof evidence

Lean proof validation now uses a wrapper that runs every configured proof file,
records one log per proof file, writes `summary.md`, writes `results.json`, and
fails the workflow at the end if any proof fails.

This prevents the first failing proof from hiding later proof status.

### Apalache symbolic evidence

Apalache validation now uses a wrapper that runs every symbolic-safe target,
records one log per target, writes `summary.md`, writes `results.json`, and fails
the workflow at the end if any symbolic target fails.

This prevents the first failing symbolic model from hiding later target status.

## Evidence artifact contract

Every formal evidence workflow should retain:

| Artifact | Required contents |
| --- | --- |
| `tlc-evidence-artifacts` | PR-gate TLC per-model logs, `summary.md`, `results.json` |
| `full-tlc-evidence-artifacts` | Full TLC per-model logs, `summary.md`, `results.json` |
| `lean-proof-artifacts` | Lean per-proof logs, `summary.md`, `results.json` |
| `symbolic-proof-artifacts` | Apalache per-target logs, `summary.md`, `results.json` |

## Claim-use policy

Evidence claims must follow this policy:

| Evidence result | Allowed claim language |
| --- | --- |
| Passed PR smoke gate only | `bounded CI validation passed` |
| Passed full TLC gate | `full configured TLC evidence capture passed under stated bounds` |
| Timeout in PR gate | `deferred to full TLC evidence gate` |
| Timeout in full gate | `not validated under configured full-gate bound` |
| Non-timeout failure | `formal target failed and is pending remediation` |
| Artifact missing | `not citable` |

## Ordered research runway after this gate

After `#70` and `#67`, the research stack should proceed in this dependency
order:

1. Research Certificate Generator.
2. Citation Chain and Evidence Linker.
3. Claim Matrix and Support Mapping.
4. Source Quality Scoring.
5. Contradiction and Dispute Detection.
6. Research Replay Log.
7. Deep Research Workflow.
8. Human Review Queue.

No downstream research certificate should cite formal proof status unless the
corresponding evidence artifact exists and the claim language matches the result.

## Completion criteria

Issues `#70` and `#67` can be considered complete when:

- regular formal workflows upload retained evidence artifacts;
- full TLC evidence workflow exists and can be run on demand;
- evidence reports identify exact workflow run IDs, commit SHAs, artifact names,
  and claim boundaries;
- publication/dissertation text distinguishes passed, bounded, timed-out,
  failed, and pending formal claims;
- the downstream research-stack issues reference this gate as their credibility
  baseline.
