# Reviewer instructions — draft for the final MSIX

**Do not submit these notes with the current engineering package.** Replace the
candidate record after production identity/version and qualification are approved.
No reviewer credentials, account, activation key or paid service are required for
the implemented built-in workflow. Runtime prerequisite: WebView2; see the
qualified provisioning procedure that the release owner must provide.

## Primary path: generate the example in the installed application

1. On the intended Windows 11 x64 standard-user client, install the authorized
   final package and open **ETS Desktop Developer** from Start. Record package
   identity, version, SHA-256, Windows build and WebView2 version. Do not use an
   unsigned preview to stand in for installed-package qualification.
2. Select **Create synthetic sample…** and choose an empty local writable parent
   folder (no network share or linked/reparse-point path). A new `ETS-synthetic-*`
   child is created. `sample-summary.json` is the completion marker; its six hashes
   cover `README.txt`, `synthetic-artifact.txt`, `event.json`, `bundle.json`,
   `sample-trust.json`, and `tampered-bundle.json`. No private key is saved.
3. With `bundle.json` selected and no trust selected, click **Verify offline**.
   Expected UI: **Indeterminate — trust material missing**; JSON status
   `indeterminate`, `valid=false`, reason code `missing_trust_material`.
4. Click **Use this sample’s trust**, read the synthetic-only warning, and verify
   again with expected log ID `ets-desktop-synthetic`. Expected UI: **Verified at
   checkpoint**; status `valid`, `signature_verified=true`,
   `continuity_verified=false`, `standing_status=checkpoint_only`.
5. Export JSON, Markdown and HTML to three fresh filenames. JSON has schema
   `ets.offline_report.v1` and strict signature policy. Reuse one filename and
   confirm overwrite is refused; original bytes must remain unchanged.
6. Choose `tampered-bundle.json` from that child folder. Selection must clear
   previous sample trust/result. Choose `sample-trust.json` explicitly; set the
   expected log ID to `ets-desktop-synthetic`; verify. Expected UI:
   **Verification failed**, status `invalid`, `valid=false`.
7. Select the original `bundle.json` and its public trust, then use expected log
   `not-the-sample-log`. Expect `invalid`; do not present wrong-log acceptance as
   successful verification. Restore the correct log to recover.
8. Cancel a bundle/folder/export picker and confirm previous state is preserved.
   Selecting new material or editing expected log clears the old exportable
   result. Repeat clicks must not launch duplicate operations.
9. Select **Export SDK test kit…**, choose a fresh ZIP name, and compare SHA-256
   to `c12ab50a808b5266593ef731951a875dd5276a89fd7b963c82eabffbc44d03a7`
   (2,034,146 bytes for this preview's exact pinned kit). Existing filenames are
   protected. Export does not execute, extract, download or install the kit.
10. Repeat built-in creation/verification/report/kit export while disconnected
    using the authorized test environment. No language toolchain is required for
    these built-in steps. Running the exported source examples is optional and
    separate; language tools and dependency restore may be required.

## Supplied fallback fixture (no private/customer data)

The preparation ZIP includes `fixtures/synthetic-sample/`. Select its `bundle.json`
and deliberately select its `sample-trust.json` in the app; expected log is
`ets-desktop-synthetic`. Missing trust, selected trust, tampering and wrong-log
outcomes are the same as above. This fixture was freshly generated from the
candidate's exact `sandbox.py` blob `3ef2e5b3fbed573a3818ee6ccb44085dec87489e`
and locally checked with the shared CLI. It is test trust, **not a trusted real
publisher**. Evidence JSON files under `evidence/fixture-*.json` retain those
source-level results, not installed Windows qualification.

## Important limits and recovery

- Checkpoint-only success does not establish current standing, real-world truth,
  completeness, regulatory compliance, or the separate artifact's bytes.
- Interrupted creation may leave a new incomplete folder without the completion
  marker. Retry creates a different child. Do not import or execute partial data.
- A failed SDK write may leave a new partial ZIP; use a fresh name and hash-check.
- User-selected output folders remain after uninstall. The app does not scan
  customer folders, run a collector, install a service/driver, or install trust.
- If WebView2, signing or trust policy blocks startup, stop and use the authorized
  release process. These instructions do not authorize bypassing security.

The release owner must attach the final test environment and WACK results, final
SDK pin if changed, and an accessible reviewer-fixture delivery path approved for
Microsoft's reviewers. This repository ZIP is not automatically attached to a
Partner Center submission.
