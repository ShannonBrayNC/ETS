# Support page — owner draft, not published

Product: ETS Desktop Developer (Preview)
Support owner: [OWNER]
Public support URL or monitored email: [OWNER]
Supported Windows builds: [OWNER: exact qualified versions]
Response commitment: [OWNER: optional; do not promise an unstaffed SLA]

## What to include in a report

- App/package version and whether installed from Store or a preview package.
- Windows build, architecture and WebView2 version.
- The operation, exact error text and a minimal synthetic reproduction.
- Whether the issue repeats after restart; whether a fresh local output path helps.
- A redacted screenshot only if useful. Do not send account names, customer data,
  secrets, tokens, private keys or real evidence bundles.

## Common questions

**It will not start.** Confirm the full application is installed and the approved
WebView2 prerequisite is present. If signing or organizational policy blocks it,
contact the administrator/support owner; do not bypass security or install unknown
certificates.

**Missing trust says indeterminate.** That is intentional. For the built-in
synthetic sample, choose its sample trust explicitly. For real bundles obtain
trusted public keys independently from a source you trust.

**A verified checkpoint is not a current-standing or compliance certificate.**
It reports integrity/signature checks under selected inputs, not real-world truth,
completeness, legal sufficiency, or the separate artifact's bytes.

**Export refuses an existing file.** Choose a new filename in a writable local
folder. Existing files are protected. Check the SDK archive hash after a failed
write; retry using a new filename if it is partial.

**Do I need Python, .NET or Node?** Not for the built-in workflow. The GUI needs
WebView2. Running exported SDK source projects separately needs their documented
toolchains; dependencies are not all vendored and restore may need internet.

[OWNER: add privacy-notice link, support intake/retention terms and escalation
instructions. Publish only after approval and verify the actual destination.]
