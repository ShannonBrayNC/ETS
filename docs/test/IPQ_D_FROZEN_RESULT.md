# IPQ-D Frozen Baseline Result

Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`  
Qualification sprint: #343  
Harness PR: #344

## Result summary

The detached qualification harness executed the frozen connector platform and Dark Pro Console without modifying the frozen SUT.

| Area | Result | Evidence |
|---|---|---|
| Selected frozen connector/Console Python suite | **PASS** | 56/56 selected baseline-native tests passed after the harness was corrected to execute from the frozen repository root. |
| Frozen Dark Pro locked production build and static trust-boundary checks | **PASS** | Frozen npm lock installed and the production build/static boundary job completed successfully. |
| IPQ-D10 guided connector workflow | **PASS** | Detached Chromium reached Connection → Scope → Evidence Policy → Collection → Test → Activate without raw configuration-file editing under controlled auth/G2C fixtures. |
| IPQ-D13 status/theme semantics | **PASS** | Frozen browser showed text/symbol status meaning, visible focus styling, dark default, and light-mode switching. |
| IPQ-D13 deterministic modal focus/Escape return | **FAIL** | After keyboard activation of Add connector, the frozen modal did not move focus to the Close connector wizard control as required by the bounded browser qualification. |
| IPQ-D13 narrow responsive authorization visibility | **FAIL** | At 390×844 the `Server authorized` indicator existed in the DOM but was hidden by the frozen responsive CSS. |
| Overall frozen D13 browser/accessibility row | **FAIL** | Two required D13 browser behaviors failed; a passing theme/status subtest does not override those failures. |

## Retained evidence

Initial detached browser evidence run: `31858256730`  
Browser evidence job: `94946909473`  
Browser artifact: `ipq-d-frozen-browser`  
Artifact ID: `9239723989`  
Artifact ZIP SHA-256: `2ad0bd815b38a7844860a22da8746e4a5d8c3fb88d0877257cf27bdb3e1925fe`

The same run also completed the frozen connector-platform and frozen Dark Pro build jobs successfully as evidence collectors. A previous Python harness attempt produced six path-related failures because tests were launched outside the frozen repository root; those were classified as harness defects. After changing only the harness working directory to `sut/`, the selected baseline-native suite passed 56/56. The frozen SUT was never patched.

## Claim treatment

The frozen baseline **does not pass IPQ-D in full** because mandatory D13 browser qualification fails on deterministic modal focus/return and responsive authorization-state visibility. The valid D10 and other reproduced PASS results remain retained evidence and are not discarded because D13 failed.

Merged #342 is **post-baseline repair evidence only**. It added production overlay focus management and kept the server-authorized scope state visible responsively, and its repaired head passed controlled Chromium qualification. Those later repairs align with the two frozen D13 failures, but they cannot retroactively change the result of `75927c5...`.

Later #338 and #340 are likewise post-baseline hardening for read-only auditor UX and bounded connector diagnostics. They must not be represented as capabilities proven on the frozen SUT unless separately reproduced there.

## Nonclaims

This result does not establish source truth or completeness, legal admissibility, regulatory compliance, production GA, hardware attestation, high availability, or third-party/full-product WCAG certification.

## Final synchronization rule

After this result record was created, the harness branch is synchronized to the then-current `main` and the detached qualification workflow is rerun. That rerun validates the final harness revision and is expected to reproduce the frozen SUT outcome; it does not alter the frozen result if the product behavior is unchanged. Final run identifiers may be attached to #343/#321 without rewriting the frozen SUT or substituting later product code.
