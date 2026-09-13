# Phase 10 CI Note — Workflow Parser Fix

During Phase 10 review, GitHub rejected `.github/workflows/lantern-tenant-exit-discovery.yml` before any job started because the workflow referenced `${{ runner.temp }}` from job-level `env`, where the `runner` context is unavailable.

The branch was corrected by moving the three ephemeral discovery paths to a runtime initialization step using the runner-provided `$RUNNER_TEMP` and exporting them through `$GITHUB_ENV`.

This change does not broaden Azure authority, add provider mutations, change migration resource scope, change identity selection, or alter the discovery-only evidence boundary. The artifact upload continues to use `${{ runner.temp }}` at step scope, where the `runner` context is valid.

The prior failure therefore represents a workflow-schema validation defect rather than a VRX curriculum, experiment, or physics failure.
