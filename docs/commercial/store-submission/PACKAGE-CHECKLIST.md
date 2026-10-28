# Package identity, version and account checklist

**Current engineering evidence is not a production upload.** This preparation
makes no manifest, signing, account, trust or Store changes.

| Field | Current preview | Required final decision/evidence |
| --- | --- | --- |
| Product/SKU | Proposed separate Developer product | Owner reserves and confirms product name and Product ID |
| Package name | `ETSDeveloper.Development` | Exact Partner Center package identity name |
| Publisher | `CN=ETSDeveloper.Development` | Exact Partner Center publisher identity string |
| Publisher display name | `ETS Development` | Approved publisher display name |
| Package display name | `ETS Desktop Developer (Preview)` | Match approved listing and manifest |
| Executable / application ID | `ets-developer.exe` / `ETSDeveloper` | Retain or review final association; no execution alias is implemented |
| Architecture / family | x64 / Windows.Desktop | Do not claim ARM64, x86, Xbox, mobile or HoloLens support |
| Package version | `0.1.0.0` | Owner-approved production version and accepted upgrade path |
| OS manifest floor / tested marker | `10.0.22000.0` / `10.0.22000.0` | Actual qualified Windows builds and reviewed manifest values |
| Language | en-us | Match actual English UI and listing |
| Capability | `runFullTrust` | Final-manifest audit and certification rationale |
| Signature | Unsigned engineering review MSIX | Approved test-signing path; Store submission follows MSIX rules |

## Identity/version gates

- Copy identities from Partner Center's **View app identity details**, preserving
  case, spaces and punctuation. GitHub ownership is not publisher identity.
- The current builder deliberately emits development identities. Production
  support requires a separately reviewed implementation change; do not hand-edit
  a review MSIX or fabricate an apparently validated production manifest.
- Microsoft's Windows 10/11 package-version section states a nonzero first
  component, components bounded by 65535, and fourth component 0. Its paragraph
  labels this UWP; do not assume packaged-desktop `0.1.0.0` is accepted. Choose a
  conservative nonzero-major production version and validate in Partner Center.
  Version text here is not an approved release number.
- Distinct development identities are not proof of Developer/Verifier coexistence.
  Keep standalone Lenovo Verifier 0.1.1.0 evidence separate and preserve that install.
- Microsoft re-signs MSIX/AppX after certification. A purchased CA code-signing
  certificate is not a prerequisite for Store submission. Sideload qualification
  still requires authorized signing/trust; no certificate actions are included here.

[Microsoft package/identity/version requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements)

## Exact-candidate release record to retain

1. Approved source commit, build/run URL, all binary artifact identifiers, package
   filename, byte count and SHA-256. Keep PR head distinct from PR-merge build SHA.
2. Unpacked manifest; exact identity/version/architecture/capabilities; package
   block map and all payload hashes; exact SDK kit source/hash/manifest.
3. Shipped runtime and SDK SBOMs, licenses/notices, vulnerability disposition and
   redistribution/IP sign-off. Build-environment inventory alone is insufficient.
4. Windows client/build, standard-user/elevation status, WebView2 version and
   delivery strategy; exact signed test-package digest, preflight and lifecycle
   evidence. Never request private keys or passwords in a document or chat.
5. Native screenshot capture provenance and image validation. Current engineering
   tiles are not approved branding.
6. Full WACK result/report, not only an exit code; resolve failures and rerun after
   payload/manifest changes. WACK pass is not Store certification.
7. Owner approval, actual Partner Center package validation, capability review and
   certification. No production release until all applicable gates are closed.

## Submission settings needing deliberate owner choices

Complete the IARC questionnaire; no rating is preassigned. Confirm markets rather
than accepting the all-markets/future-markets default. Decide price/trial and
private/public audience before submission; a Public product cannot later switch
to Private. Choose publication timing explicitly. Preparation is not permission to
submit, publish immediately, accept legal terms, or purchase anything.
See [official sources](MICROSOFT-SOURCES.md).
