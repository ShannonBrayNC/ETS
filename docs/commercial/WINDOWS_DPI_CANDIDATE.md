# Windows system-DPI repair candidate

This is an unsigned **development** candidate and WACK-retest handoff, not a
Store submission, production identity, signed installer, or qualification pass.

## Confirmed defect and narrow repair

The retained Verifier 0.1.1.0 executable tested by WACK had SHA-256
`9433a7df607f17d7746deab7aaea87492b46341889e8034a914ca4e34181dcc8`.
Its embedded Win32 manifest (`RT_MANIFEST`, ID 1) had no DPI declaration.
All 121 hashes listed by the supplied WACK report matched the retained package.
The report contained 24 tests: 22 passes, optional test 88 failure, and required
test 92 DPI warning. This is historical evidence, not this new candidate's result.

Both GUI hosts now share `packaging/windows/desktop.manifest`. It declares
`dpiAware=true` in the 2005 WindowsSettings namespace and `dpiAwareness=system`
in the 2016 namespace. System awareness matches the existing pywebview 6.2.1
WinForms `SetProcessDPIAware()` intent. This is **not** a PerMonitorV2 claim.
The five supported-OS declarations, Common-Controls v6, `longPathAware=true`,
`asInvoker`, and `uiAccess=false` are retained. The console verifier is unchanged.

The optional runtime/process warning is not hidden by removing legitimate
`shell=False` packaged-verifier subprocess execution or stripping stdlib data.
The observed mixed-case `CMd` literal was in compressed `pydoc_data.topics`, not
proof that ETS executes that command. The generic WACK failed-process cause has
not been established. The manifest repair alone is not promised to clear WACK.

## Candidate identity and version boundaries

| Candidate | MSIX identity / publisher | New MSIX version | Prior version |
| --- | --- | --- | --- |
| Verifier | `ETSVerifier.Development` / `CN=ETSVerifier.Development` | `0.1.2.0` | `0.1.1.0` |
| Developer preview | `ETSDeveloper.Development` / `CN=ETSDeveloper.Development` | `0.1.1.0` | `0.1.0.0` |

The version check reviewed current main, release/tag metadata, and prior candidate
PR records before allocating these versions. The two package identities have
independent version sequences. The Python source/application version remains
`0.1.0a1`; it is not the four-part MSIX version. Neither identity is a production
Partner Center identity. Each edition requires its own qualification evidence.

## Automated evidence and its limits

Both Windows workflows retain:

- Source XML regression tests, including namespace, duplication, wrong awareness,
  UAC/elevation, compatibility, and console-verifier boundary cases.
- `desktop-frozen-manifest.json`: native, non-executing extraction of the actual
  frozen GUI's embedded manifest with executable and manifest SHA-256.
- Native WebView2 smoke evidence with a read-only query of the actual GUI HWND's
  DPI-awareness context (system awareness), not the smoke worker thread.
- Existing strict-verifier, offline, UI, signing-preflight, SDK-kit (Developer),
  MakeAppx pack/unpack, payload-hash, and exact-source candidate-record gates.
- `desktop-msix-manifest.json`: the MakeAppx-unpacked GUI manifest plus exact
  development identity, version, x64 architecture, and GUI launch-target checks.

The records are included in the review bundle and bound by `candidate.json`.
CI uses Windows Server 2022, not a clean Windows 11 client. Manifest validation and
a native HWND query are not visual scaling, accessibility, installed-package, or
WACK certification. Browser tests do not replace native mixed-monitor testing.

## Exact-candidate signing and retest handoff

1. Use the successful PR run's edition-specific **review artifact**. Keep the full
   review bundle and portable artifact separate from prior candidates. Read its
   `candidate.json`, package `qualification.json`, source SHA/run URL,
   package version, and unsigned MSIX SHA-256. Verify with
   `python packaging/windows/candidate_record.py verify <review-directory>`.
   Do not select a package by `latest` or by filename alone.
2. Signing remains an explicitly authorized operator action on the original
   certificate workstation. Follow [development signing](WINDOWS_SIGNING_QUALIFICATION.md)
   using the reviewed new unsigned SHA-256 and the matching edition allowlist.
   Developer requires `-Edition developer`; Verifier keeps the default. Do not
   reuse the other edition's certificate or a previous candidate's digest.
   Preserve unsigned input and retain signed output, signed SHA-256, certificate
   subject/thumbprint, signing record, and source/run linkage. Never export a
   private key or treat unsigned-file integrity as publisher authentication.
3. After separate trust/install authorization, verify the exact signed package on
   the intended Windows 11 client and record OS/build, runtime, identity/version,
   package hash, installed path, standard-user context, and observed results.
   Use [Verifier client qualification](LENOVO_WINDOWS_QUALIFICATION.md)
   or [Developer candidate guidance](../../packaging/windows/DEVELOPER_CANDIDATE.md).
4. Repeat launch, native file dialogs, verification, report export, cancel/repeat,
   keyboard/Narrator, and layout at **100%, 150%, and 200%** scaling. Record moving
   between monitors with different scaling and reconnect/scaling-change behavior.
   System-aware apps may be bitmap-scaled after monitor changes; do not infer
   PerMonitorV2 support or clear this gate from CI's single-monitor result.
5. Run the full Windows App Certification Kit against the exact installed signed
   package for each edition, preserving original XML/full report and environment
   evidence. Compare test 92 and test 88, but investigate any remaining process
   failure rather than assuming the manifest fixed it. A missing or warning report
   is not a pass. Reconcile evidence without auto-approving release gates.

No step here authorizes certificate/trust changes, installation, merge, signing,
Store submission, registry publication, or production configuration changes.
Existing operator passes remain attached to their old package, not transferred to
these new bytes. Final production identity, client lifecycle/runtime/accessibility,
license/SBOM/IP review, production rebuild/retest, and Store review remain open.

## References

- [Microsoft: process-default DPI awareness](https://learn.microsoft.com/en-us/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process)
- [Microsoft: application manifests](https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests)
- [Microsoft: actual HWND DPI context](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowdpiawarenesscontext)
- [pywebview 6.2.1 WinForms implementation](https://github.com/r0x0r/pywebview/blob/6.2.1/webview/platforms/winforms.py)
