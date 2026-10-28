# Microsoft Store release gaps

Updated: 2026-10-28. Status: engineering candidate; **not Store-ready**.

## Highest recommendation: qualify the installed client

Run the signed development candidate on a disposable Windows 11 x64 VM using a
non-elevated account. Finish the [qualification record](WINDOWS_RELEASE_QUALIFICATION_RECORD.md)
and [lifecycle procedure](WINDOWS_SIGNING_QUALIFICATION.md). This is the critical
path: Server CI launches unpacked executables and cannot prove installed-client
behavior. Do not purchase a commercial certificate merely for Store submission;
Microsoft re-signs MSIX submissions after certification. Local sideload testing
still needs an approved signing certificate and trust setup.

Start with the read-only preflight from PowerShell 7 on the test client:

```powershell
./packaging/windows/client-preflight.ps1 `
  -Package '<signed development MSIX>' `
  -ExpectedSha256 '<retained signed MSIX SHA-256>' `
  -OutputFile './client-preflight.json'
```

Use the **signed** digest from `signing.json`, not the unsigned review digest.
Preflight records OS/client type, architecture, elevation, package digest/signature,
and Evergreen WebView2 registry versions. Exit 0 means automatic prerequisites
passed; exit 2 means at least one failed. Neither means client qualification passed.
The tool only reads system state and writes a fresh report. It does not install,
launch, trust a certificate, change network settings, or collect machine/user names.
An unsigned package on the Server CI runner must fail this preflight; CI checks that
negative case and retains its report in the review bundle.

## Remaining gaps and required tests

| Priority | Gap | Completion evidence / required input |
| --- | --- | --- |
| P0 | Signing and clean test client | Approved development signing owner/certificate; signed candidate digest; clean Windows 11 VM snapshot and non-elevated test account |
| P0 | Installed lifecycle | Install, Start-menu launch under package identity, upgrade, downgrade rejection, uninstall/reinstall, preserved external input/report hashes |
| P0 | WebView2 delivery | Recommend Evergreen Runtime; verify detection, missing-runtime recovery and startup on clean client. For disconnected preparation use Microsoft's standalone installer; no silent network install during verification. Store delivery/provisioning path still needs qualification |
| P0 | End-user offline behavior | Real file dialogs; valid/tampered/unsupported/missing-trust/malformed/oversized fixtures; expected-log mismatch; network disabled at VM level; JSON/Markdown/HTML export, cancellation and overwrite protection |
| P0 | Accessibility and compatibility | Keyboard-only flow, Narrator, 200% scaling, small screens, non-ASCII paths, read-only inputs and unwritable export destination; record exact Windows builds/hardware supported |
| P0 | Runtime distribution review | Exact shipped Python/native components, runtime SBOM, dependency/license obligations, approved customer notices and vulnerability dispositions. Build-environment inventory is not sufficient |
| P0 | Partner Center identity | Verified developer account, reserved product name, exact package name/publisher/publisher display name. Current development identity must be replaced through a reviewed production build change |
| P0 | Store assets and listing | Final icons/screenshots, accurate offline/trust claims, description/category, age ratings, markets, privacy-policy and support URLs/contact; pricing decision remains free local verifier |
| P0 | Certification | WACK on intended client/package, restricted `runFullTrust` capability explanation, submission notes and test instructions, Partner Center validation and Store certification |
| P1 | Release operations | Retained source/build/evidence hashes, support owner, update/rollback plan, runtime update regression coverage and incident handling |

## Engineering evidence already available

Frozen CLI and native WebView2 tests cover signed verification, tampering, missing
trust, malformed input and strict report snapshots. Browser tests cover keyboard
focus and failure recovery. Program-specific firewall tests pass on Server CI.
MSIX manifest/packing/unpacking, payload hashes, linked-path rejection, signing
negative paths, dependency evidence and reviewer-bundle checks pass in CI. None of
these substitutes for the open gates above. See [current readiness](WINDOWS_VERIFIER_READINESS.md).

## Inputs that cannot be inferred from the repository

- Exact Partner Center identity and authorized publisher/account owner.
- Approved test-signing certificate access; never send a private key or password in chat.
- Windows 11 VM/test session and completed observations from its tester.
- Final branding, public support/privacy destinations and named release/license reviewers.

## Microsoft references

Reviewed 2026-10-28; recheck at submission:

- [MSIX Store package requirements and Store signing](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements)
- [WebView2 detection and distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
