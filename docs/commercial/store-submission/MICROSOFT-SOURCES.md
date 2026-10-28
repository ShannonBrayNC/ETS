# Microsoft primary references

Checked 2026-10-28. Microsoft Store Policies 7.20 are effective October 22, 2026.
These are preparation constraints, not a guarantee of certification. Recheck live
Partner Center at submission; if fields differ, update the draft and validation.

| Topic | Practical constraint | Primary source |
| --- | --- | --- |
| Product name | Reserved/unique; up to 256 characters; unsubmitted reservation expires after three months | [Reserve name](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/reserve-your-apps-name) |
| Listing copy | Description ≤10,000 plain-text characters; short ≤1,000 (prefer <270); ≤20 features ×200; first submission What's new blank, otherwise ≤1,500 | [Listing fields](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/add-and-edit-store-listing-info) |
| Search | ≤7 phrases ×40 characters, ≤21 total words; relevant terms only | [Additional information](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/add-additional-information) |
| Desktop assets | PNG ≤50 MB; ≥1366×768; ≤10 screenshots; captions ≤200 characters; at least one screenshot | [Screenshots/images](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/screenshots-and-images) |
| Capability | Medium-integrity desktop host uses restricted `runFullTrust`; explain need, not administrator elevation | [Capabilities](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations) |
| Package | Exact account identity; Store signing; version and WACK requirements | [Package requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements) |
| Privacy/truthful claims | Policy 10.5.1 includes Win32/Desktop Bridge; privacy required even for local workflows. Actual functionality and limitations must match metadata | [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies) |
| Privacy/support fields | Provide an approved public privacy URL; support URL/email recommended | [Support info](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/support-info) |
| Category | Proposal: Developer tools / Development kits; owner confirms | [Categories](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/categories-and-subcategories?pivots=store-installer-msix) |
| Age | Complete IARC questionnaire; do not infer a rating | [Age ratings](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/age-ratings) |
| Regions | Explicit selection; default includes all and future markets | [Markets](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/market-selection) |
| Price | Owner selects tier/trial; standalone Verifier pricing does not decide Developer price | [Price/availability](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/price-and-availability) |
| Audience | Decide before submission; Public cannot later become Private | [Visibility](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/visibility-options) |
| Review/publish timing | Add repeatable notes/capability explanation; decide manual hold vs automatic publishing | [Submission options](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/faqs/notifications) |
| GUI prerequisite | Detect/provision WebView2 and qualify disconnected behavior | [WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |

## Documentation ambiguities retained as gates

- Screenshot guidance's main section allows package-icon fallback and calls
  uploaded Store logos optional; its FAQ says a Store logo is mandatory. Prepare
  approved package icons and a 300×300 listing icon, then verify actual fields.
  No logo waiver is assumed here.
- Support guidance offers direct privacy text, while policy 10.5.1 calls for a
  privacy URL. An approved, published, verified URL remains the conservative gate.
- Version-number wording specifies Windows 10/11 “(UWP)”. Do not assume the
  packaged desktop engineering version 0.1.0.0 will be accepted. Require reviewed
  production numbering and actual package validation.
