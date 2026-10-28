# Windows verifier and Edge operator validation — 2026-10-28

Status: development validation only; release approval remains false.

## Environment and evidence boundary

The operator tested Windows 11 using the unsigned desktop artifact from PR #944,
Actions run 40724269861, synthetic merge commit
`f0505efef508f530fbbd5cc62911771bd0f12979`. Edge ran through Docker Desktop Linux
containers at localhost:8400 after rebuilding a fresh ETS checkout. The exact
Edge checkout SHA and image digests were not captured. Existing persistent
volumes contained earlier demo records; this was not a clean installation.

Evidence consists of operator screenshots, three exported report formats, a
captured proof bundle, its public device identity, and explicit operator
confirmations in the testing conversation. Screenshots are not checked into the
repository. Results below distinguish observed outcomes from untested gates.

## Confirmed development results

- Desktop launches after the operator applied the downloaded-runtime unblock
  workaround. Initial launch failed resolving Python.Runtime.Loader.Initialize.
  The sequence supports downloaded DLL blocking as the cause; Zone.Identifier
  streams were not independently inspected.
- Signed fixture: valid with supplied trusted key; indeterminate without trust.
- Wrong expected log ID rejected; correct log ID restores valid verification.
- JSON, Markdown, and HTML exports contain identical report payloads and the
  original verification timestamp (2026-10-28T16:46:48.224499Z).
- Malformed trust and malformed evidence are rejected. Operator confirmed
  selection clears stale results/disables exports until verification and that
  returning to valid inputs recovers successfully.
- Edge synthetic capture, bundle export, and independent desktop verification
  passed. The repository CLI also independently verified all nine checks with
  the operator-supplied public key and expected log ID.
- Real captured event: `evt_webhook_3dbf3ac87d404fb88428433702d2855c`, log
  `ets-edge-virtual-demo`, leaf index 554, checkpoint tree size 555, root
  `ea6721258061afa9446783bc49b56f03e02b9b7547b54606c037e1bd96922fd7`.
  Public-key SHA-256 fingerprint:
  `45f6c7a52b443202fd94e2fd4697dd9e2bdd2a4586508468add0f1054f30190e`.
  Trust is relative to that local operator-supplied key, with software-volume
  custody and no hardware attestation. Continuity remained unverified.
- Online sync drained two pending events: synchronized 552 → 554, no pending,
  retryable, or terminal failures afterward.
- With demo upstream stopped, a new capture remained local and sync returned
  0/1, retryable 1, synchronized 554. Operator explicitly confirmed retryable
  state survived the webhook service restart.
- After upstream restart, safe sync returned 1/1, synchronized 555 and empty
  queue. Operator confirmed another run returned 0/0 with total unchanged.
  This demonstrates no reprocessing in this sequence, not exhaustive upstream
  duplicate/conflict qualification.

## Defects found and changes prepared

1. Local nginx stripped the port from Host on BFF requests; the browser sent
   Origin localhost:8400 and capture was rejected. Explicit allowed-origin
   configuration unblocked the operator. The repository fix preserves the
   incoming Host including port. Regression tests model nginx variable behavior
   and exercise the real ASGI capture guard, including wrong host/port rejection.
   Docker/nginx is unavailable in the agent environment; a rebuilt-container
   browser test without the workaround remains required.
2. Desktop startup errors incorrectly blamed only WebView2. The message now
   includes exception type/detail and explains runtime/extraction/download
   blocking possibilities. No files are unblocked automatically and no security
   setting is changed. Downloaded Windows artifact startup must be retested.
3. Older Edge instructions described a browser key field absent from Dark Pro.
   The Edge README now describes the current BFF flow.

## Remaining gates

- Download/extract/first-launch qualification on clean Windows 11, including
  blocked downloads and missing WebView2; no manual workaround as release proof.
- Actual Windows rendering of the updated startup dialog and diagnostics.
- Local proxy test through rebuilt nginx without explicit-origin workaround.
- Desktop export no-overwrite and cancellation confirmation; tampered bundle,
  unsupported schema and resource-limit manual checks; disconnected-network run.
- Keyboard/Narrator, scaling and resized-window checks. Earlier screenshots
  showed left-edge clipping; maximized screenshots were readable. Cause and
  reproduction remain unresolved.
- Signed MSIX clean-client install, launch, upgrade, downgrade rejection,
  uninstall/reinstall and preservation of external evidence files.
- Partner Center identity, listing/assets/privacy/support, dependency-license
  review, Windows App Certification Kit and Store submission/certification.
- Hosted Core/Gateway/fleet integration is separate from this simulated upstream.

Automated validation for this change: 33 targeted pytest tests passed covering
local-origin regression, desktop diagnostics/smoke/controller, BFF hosted-origin
policy and protected ingress. This does not replace Windows or Docker tests.

## Follow-up: proxy qualification in container CI

The Edge Dark Pro workflow now sends `Origin: http://localhost:8400` and
`Sec-Fetch-Site: same-origin` on capture and verification POSTs through the real
nginx container. Previously curl omitted Origin, bypassing the comparison that
failed in the operator's browser. Wrong-port and wrong-host capture requests
must return 403 even with the UI marker and same-origin fetch metadata present.
The job retains the receipt, proof, verification and bundle as CI artifacts.

This is a container HTTP integration test with browser-shaped headers, not a
real-browser UI automation test. The base Compose profile has no allowed-origin
override. A green run supplies proxy integration evidence; an operator browser
retest without the workaround remains the final UI confirmation.
