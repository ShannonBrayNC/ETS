# IPQ-D Frozen Baseline Execution

Parent: #321  
Execution sprint: #343  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Rule

The frozen SUT is immutable. Qualification tooling may evolve on a separate harness branch, but the workflow must check out the exact SUT SHA into a separate path and execute the product/tests there without applying patches to that tree.

Every retained evidence artifact must identify both:

- `sut_sha` — the exact frozen product revision under test;
- `harness_sha` — the qualification tooling revision that executed the test.

A later product revision cannot retroactively make a frozen-baseline row pass. If the frozen behavior is missing or defective, the row is `FAIL`, `BLOCKED`, or `EXCLUDED` with rationale and a defect/candidate link as appropriate.

## Executable coverage

The detached pass deliberately reuses tests that already exist inside the frozen SUT and adds an external browser probe without copying later product code into that tree:

| IPQ-D area | Frozen evidence source |
|---|---|
| D01 schema/model validation | `test_connector_models.py`, `test_connector_schemas.py`, `test_connector_registry.py` |
| D02 compatibility/conformance | `test_connector_conformance.py` |
| D03/D04 credential-reference behavior | `test_connector_credentials.py` |
| D05 management operations | `test_connector_management_api.py` |
| D06/D07 runtime persistence/conflicts | `test_connector_runtime.py` |
| D08 native catalog/model ownership | `test_native_connectors.py` |
| D09 auth-context boundary | frozen `test_console_production_boundary.py` + Console build |
| D10 guided workflow | detached Chromium probe against the frozen Console with controlled G2C fixtures |
| D11 pre-commit preview | frozen architecture test + browser workflow evidence |
| D12 health/verification separation | frozen architecture test + browser workflow evidence |
| D13 browser/accessibility | detached Chromium focus, theme/status and narrow-viewport probes |

Static focus/theme/status source checks remain supporting evidence only; D13 browser status comes from the detached Chromium probe.

## Workflow

`.github/workflows/ipq-d-frozen.yml` checks out:

1. the qualification harness into `harness/`;
2. the frozen SUT into `sut/` using exact SHA `75927c5...` with persisted credentials disabled.

Each job asserts `git -C sut rev-parse HEAD` equals the frozen SHA before running any qualification step.

### Frozen connector platform

The Python job installs `sut[dev]` and executes the selected frozen tests from the frozen repository root. It retains:

- identity record;
- JUnit XML;
- pytest text output;
- qualification manifest naming the covered IPQ-D areas and claim boundary.

### Frozen Dark Pro build

The Console job uses the frozen npm lock, runs the frozen production build, and records bounded source assertions for auth context, pre-commit preview, source-health/verification separation, focus styling, theme support, and status semantics. It retains:

- identity record;
- build log;
- qualification manifest explicitly stating that static/build evidence is not browser qualification.

### Detached frozen browser evidence

The browser job installs only the frozen Console's own locked dependencies into `sut/` and the qualification harness's locked Playwright dependencies into `harness/`. It launches the unmodified frozen Vite source and intercepts the auth/G2C transport with controlled fixtures.

D10 and D13 execute separately and produce independent status values:

- `d10_guided_workflow=PASS|FAIL`
- `d13_browser_accessibility=PASS|FAIL`

A product assertion failure does not cause the harness job to patch or mutate the SUT. The runner captures Playwright exit codes, logs and failure artifacts, writes the result manifest, and completes as evidence collection. A `FAIL` therefore remains a frozen-product qualification result, not a harness instruction to repair `75927c5...`.

The D13 probe covers deterministic modal focus entry/Escape return, visible keyboard focus, dark/light state semantics, non-color status text, and responsive visibility of server-authorized scope. These are bounded browser observations, not third-party WCAG certification.

## Post-baseline hardening

#338, #340 and #342 are useful candidate evidence for later revisions, but they are not evidence that the frozen baseline possessed those later behaviors. In particular, read-only auditor UX, bounded diagnostic categories, overlay focus management and responsive authorization-state fixes must remain explicitly post-baseline unless independently reproduced on `75927c5...`.

If the detached frozen browser evidence reports the same focus or responsive defects later corrected by #342, the frozen row remains failed and #342 may be linked only as post-baseline repair evidence.

## Claim boundary

This execution work qualifies only rows actually reproduced against the exact frozen SUT. It does not establish source truth/completeness, compliance, legal admissibility, production GA, hardware attestation, full WCAG certification, or the correctness of later ETS revisions.
