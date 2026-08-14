# Code scanning gate

ETS uses two distinct security signals for hardening work:

1. the repository `CodeQL` workflow, which performs source-code analysis for Python and JavaScript/TypeScript and uploads results to GitHub code scanning; and
2. the existing `Security Audit` workflow, which covers dependency auditing, full-history secret scanning, Explorer dependency/build checks, and Docker federation validation.

Both signals are part of the hardening evidence set. A successful `Security Audit` result is not a substitute for CodeQL source analysis, and a successful CodeQL run is not a substitute for dependency or secret scanning.

## SignalForge interpretation

SignalForge must distinguish code-scanning availability from a clean result:

- `available_and_green` — the exact-head `CodeQL` workflow completed successfully for every configured language.
- `available_and_failed` — CodeQL ran but at least one configured analysis failed or reported a blocking result under repository policy.
- `unavailable` — the workflow did not run, GitHub rejected SARIF upload/configuration, or the connected integration cannot query code-scanning status.

`unavailable` MUST NOT be represented as `clean`.

The connected repository integration currently receives HTTP 403 (`Resource not accessible by integration`) when directly querying the GitHub code-scanning alerts API. Therefore automation should use the exact-head `CodeQL` workflow result as the primary observable gate unless/until the connector receives the required code-scanning read permission. A 403 from the alerts API is an availability limitation, not evidence that there are zero alerts.

## Hardening completion rule

A security-sensitive or release-hardening sprint should not be marked complete unless:

- its exact-head `CodeQL` analysis has run successfully for the configured languages, or an explicitly approved replacement SAST gate is documented;
- the exact-head `Security Audit` workflow is green; and
- any blocking finding is resolved or recorded through an approved risk/exception process.

## Scope

The initial CodeQL configuration analyzes:

- Python (`python`)
- Explorer/frontend JavaScript and TypeScript (`javascript-typescript`)

The workflow uses GitHub's advanced CodeQL Actions setup with the `security-extended` query suite. Language coverage should be expanded when additional production language surfaces enter the repository.
