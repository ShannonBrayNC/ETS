# Evidence matrix and blockers

Snapshot: 2026-10-28. **Engineering evidence exists; release gates remain open.**

| Gate | Evidence retained | Status / next evidence |
| --- | --- | --- |
| Source correctness | #952 head `d3b4b7ce`; 27 successful checks; clean CI Python 3,508 passed / 12 skipped | Engineering pass at exact head, not final release |
| Windows Developer package | Run `40777778220`, source `2606424f`; frozen CLI/native WebView2, sample/report/SDK export, toolchains absent from PATH | Engineering pass on Windows Server runner; not installed Windows 11 |
| Offline engineering smoke | Program-specific network rules; cleanup retained | Not a physically disconnected end-user network test; not zero-network guarantee for Windows/WebView2 |
| Package structure | MakeAppx pack/unpack, 357 payload hashes; 12 review-file records independently checked | Unsigned development identity only |
| SDK pin | Source `a6eb2c70`; ZIP SHA-256 `c12ab50a808b5266593ef731951a875dd5276a89fd7b963c82eabffbc44d03a7` | Alpha kit, 2,034,146 bytes; no production release-provenance attestation |
| Synthetic reviewer fixture | Four local CLI outcomes retained under `evidence/`; six sample hashes checked | Source-level check; no Windows client result inferred |
| Formal models | Five model passes; three allowed 180-second timeouts | Configured bounded gate passed, not exhaustive model exploration |
| Signed Developer install/lifecycle | No exact-candidate retained client evidence | BLOCKED: approved signed candidate, standard-user install/Start launch/uninstall/reinstall/upgrade/downgrade/coexistence |
| WebView2 lifecycle | Existing runtime on CI | BLOCKED: absent/present/update/offline provisioning on intended client |
| Native controls/accessibility | Browser regressions and native smoke | BLOCKED: real dialogs, cancellation, keyboard, Narrator, 200% scaling, narrow screens, non-ASCII/unwritable paths on final client |
| WACK | Current qualification record says `wackPassed=false` | NOT RUN for Developer final candidate; retain full report with exact digest |
| Runtime/SDK licensing | Build/dependency evidence collected | BLOCKED: shipped-payload+kit reconciliation, licenses/notices, vulnerability disposition and legal/IP owner sign-off |
| Production identity/version | Development-only manifest | BLOCKED: Partner Center identities + reviewed production build |
| Privacy/support | Draft text only | BLOCKED: owner/contact/content approval; published and verified privacy URL |
| Listing/assets/rating/markets/price | Draft copy/constraints and shot list | BLOCKED: owner choices, real final screenshots, approved branding, IARC completion |
| Microsoft review/release | None | NOT SUBMITTED / NOT CERTIFIED / NOT RELEASE APPROVED |

## Immutable preview artifact references

[Developer candidate run](https://github.com/ShannonBrayNC/ETS/actions/runs/40777778220)

- [Portable artifact 12855742839](https://github.com/ShannonBrayNC/ETS/actions/runs/40777778220/artifacts/12855742839):
  45,993,944 bytes; SHA-256 `6a941c17a53ff3e85dccfe3fe2966c5a3aace91f3e5fcad87d429ecfb91484cc`.
- [Review artifact 12855023592](https://github.com/ShannonBrayNC/ETS/actions/runs/40777778220/artifacts/12855023592):
  45,598,679 bytes; SHA-256 `d742876585ce1a13f30994668503f9cfe3fc3c242fa7017ecc12dbb47ad79530`.
- Inner `ETSDeveloper.Development_0.1.0.0_x64_unsigned.msix`: 47,617,168 bytes;
  SHA-256 `c98817347e37864a062ada4bb223ca99348e020401b0afdc5b5cc3ca7e52b376`.

The copied [candidate record](evidence/preview-candidate.json) and
[qualification record](evidence/preview-qualification.json) are original
engineering metadata, not new approvals. Their file paths describe the original
review archive; that archive/MSIX is not embedded in this preparation ZIP.
CI artifacts can expire and may require GitHub access. Do not silently substitute
“latest”; rebuild from reviewed pins and requalify if the original bytes are gone.

## WACK handoff for Developer, not the existing Verifier

Use the repository's `docs/commercial/WINDOWS_WACK_HANDOFF.md` procedure with the
**authorized Developer package and its exact signed digest**, adapting product
selection carefully. Do not claim the Lenovo standalone Verifier's results for
this product. Record WACK/Windows/WebView2 versions, report paths/hashes, tested
identity/version, failures and dispositions. Any production rebuild changes the
candidate and needs evidence review; a clean old report is not transferable.

This task does not install WACK, sign/trust software, use the user's computer or
change the Store account. The final release owner must authorize those actions.
