# Unsigned Store-identity candidates

This implements the two public identities supplied by the owner from newly
created Partner Center apps on 2026-10-29. It does **not** upload, submit, sign,
install, approve, or publish either app. These remain **Store-identity candidates**,
not Store-ready releases. The Desktop Developer experience is still a partial
alpha/preview local sandbox and SDK test kit, not the complete production SDK.

| Edition | Package Identity Name | Display name |
| --- | --- | --- |
| `verifier` | `EchoMediaAILLC.ETSVerifier` | ETS Verifier |
| `developer` | `EchoMediaAILLC.ETSDesktopDeveloper` | ETS Desktop Developer |

Both use Publisher `CN=1FB1B754-89E5-418D-A454-50CADF768A9F` and
PublisherDisplayName `EchoMedia AI LLC`, exactly and case-sensitively.
No package SID, account secret, certificate, or credential is needed here.

## Explicit profile; safe development default

`build-msix.ps1` and `msix_layout.py` accept only `development` or `store`.
Omitting the profile retains development identities and the `0.1.0.0` script
default. Existing CI development candidates remain Verifier `0.1.2.0` and
Developer `0.1.1.0`; their identities, publishers, and signing guards are unchanged.
The opt-in Store profile defaults to `1.0.0.0`, requires a nonzero major version,
limits components to 65535, and reserves the final component as zero. This is a
first-candidate default for the new apps, not evidence of a successful Partner
Center package-history/collision check. Check current portal history before upload.

```powershell
# Start from the reviewed frozen payloads and use fresh output directories.
./packaging/windows/build-msix.ps1 -Source dist/ets-desktop -OutputDirectory dist/store-verifier-msix -Edition verifier -Profile store -PackageVersion '1.0.0.0'
./packaging/windows/build-msix.ps1 -Source dist/ets-developer -OutputDirectory dist/store-developer-msix -Edition developer -Profile store -PackageVersion '1.0.0.0'
```

There are no free-form identity or publisher flags. The independent post-packaging
checker has its own exact identity expectations. The actual Store candidate is
also passed to both development-signing allowlists with mocked certificate reads
and a non-signing stub: both must reject before credential access or output.
Never try to use a development certificate for the Store publisher.

Microsoft signs MSIX/AppX packages during Store publishing after certification;
a purchased CA certificate/PFX/token is not required for this Store route. Direct
sideloading is a different trust/distribution path and is not performed here.
See [Microsoft's package requirements and versioning](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/app-package-requirements?pivots=store-installer-msix).

## What CI establishes

The existing Windows jobs retain their development artifacts and produce separate
`ets-{verifier,developer}-store-identity-review-<source-sha>` bundles. They retain:

- A MakeAppx-validated **unsigned** MSIX; every staged payload hash checked after unpack.
- Independent exact package identity, display names, version, and frozen GUI manifest checks.
- The shared System-DPI-aware fix (`dpiAware=true`, `dpiAwareness=system`), not PMv2.
- Native smoke flow launched from the actual unpacked Store payload, without installation.
- Existing frozen verifier, offline/network-blocked, and Developer SDK export tests.
- Development-signing rejection evidence for the actual Store MSIX.
- Package and evidence hashes bound to the exact checkout commit and workflow run.

The same deterministic engineering PNG tiles remain in the package: 50×50 Store
logo, 44×44 and 150×150 app logos. They are valid package assets, **not final Store
artwork**. Dependency evidence is build-environment metadata, **not an exact
runtime/native/SDK SBOM or redistribution approval**. The pinned SDK archive is
hash-checked and every inventory member verified; it remains alpha-testing-only.

`stage_runtime_notices.py` also preserves three exact upstream notices under
`THIRD_PARTY_EVIDENCE/SUPPLEMENTAL_NOTICES`, with source URLs, archive/commit
provenance, and SHA-256 checks against the supplied notice and matching runtime
binaries (or exact installed `proxy_tools` source). Any hash/version mismatch
fails packaging before notices are copied. These are supplemental evidence, not
legal approval or a complete SBOM. The original environment inventory deliberately
still records the wheel's missing `proxy_tools` notice.

- CPython 3.12.10: unchanged aggregate notice from the official Windows embedded
  distribution, bound to both copies of the matching Python/OpenSSL/libffi/SQLite
  and MSVC DLLs. This does not prove coverage of every native component.
- Microsoft.Web.WebView2 SDK 1.0.3856.49: unchanged NuGet package notice, bound to
  the matching Core/WinForms assemblies and three architecture loader DLLs. This
  is not the separate WebView2 Runtime provisioning/license decision.
- `proxy_tools` 0.1.0: exact source-matched upstream BSD notice and copyright
  credits (Armin Ronacher 2013; Jonathan Tushman 2014). PyPI metadata says MIT,
  while source and notice say BSD; upstream placeholder/trailing text is retained
  byte-for-byte. **This discrepancy is not resolved by copying the notice.**
  The dependency is used by pywebview and no supported newer PyPI release exists;
  obtain rights-review clarification rather than deleting it or inventing MIT text.

Full native/runtime and SDK SBOM reconciliation remains open, including MSVC/UCRT,
cryptography's embedded native components, and exported SDK dependencies. The kit's
existing SPDX file lists only a root directory with `NOASSERTION`, not those
components. Retained package hashes from any earlier CI run are superseded by the
new notice-bearing candidates; never substitute one without updating review evidence.

## Still open before Store submission

- Final package icons, approved app screenshots, and truthful listing/restricted
  capability declarations; no final listing artwork is implied by these builds.
- Actual Windows 11 x64 client installation/launch/upgrade/uninstall, native dialogs,
  keyboard/Narrator and high-DPI/mixed-display checks, and final-candidate WACK.
  Hosted Windows Server CI is not Windows 11 client qualification.
- WebView2 missing/present/update and offline provisioning strategy; the payload
  currently requires a separately installed Edge WebView2 Runtime. Qualify .NET,
  Python/native loader and other bundled/runtime dependencies on clean clients.
- Reconcile frozen native/Python payload and exported SDK/runtime inventories;
  review Python, WebView2, native-library and SDK notices/licenses and sign off
  redistribution. Copied license metadata is not permission.
- Review source/PR dependency, fresh candidate hashes, portal version history,
  Partner Center package validation, certification, and owner's explicit final
  upload/submission/publication approval. A passing CI job closes none of these.

`qualification.json` keeps installation, Windows 11, WACK, licenses, runtime,
artwork, release, submission approval, and submission status false.
