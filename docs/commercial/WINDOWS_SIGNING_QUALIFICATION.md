# Development signing and Windows 11 qualification

This procedure advances the development MSIX toward client qualification. It does
not approve production distribution or establish Store readiness. Store submission
uses the verified Partner Center identity and Store signing; the engineering
identities below must not be submitted as production identities.

## Sign a development candidate

`-Edition verifier` is the backward-compatible default. Developer must be selected
explicitly with `-Edition developer`; the helper never guesses from the package.

| Edition | Only accepted x64 package identity | Exact certificate subject / publisher |
| --- | --- | --- |
| `verifier` (default) | `ETSVerifier.Development` | `CN=ETSVerifier.Development` |
| `developer` (explicit) | `ETSDeveloper.Development` | `CN=ETSDeveloper.Development` |

These are a fixed engineering allowlist, not parameters for arbitrary publishers
or production signing. A Verifier certificate cannot sign the Developer candidate.
For Developer, use the separate [exact-candidate client and WACK handoff](WINDOWS_DEVELOPER_QUALIFICATION.md).
The Verifier commands and lifecycle version examples below remain Verifier-only.

A signing owner must supply an already-approved certificate in `CurrentUser/My`
on the Windows signing workstation. It must have an accessible private key,
explicit code-signing EKU, current validity, and exact subject
`CN=ETSVerifier.Development` for Verifier or `CN=ETSDeveloper.Development` for
Developer. The certificate chain must already be trusted there.
The helper does not create/export keys, import certificates, modify trust, accept
PFX passwords, or install packages. Do not upload private keys as CI artifacts.

Build using [the MSIX recipe](WINDOWS_MSIX_CANDIDATE.md), retain its qualification
JSON and source SHA, then run PowerShell 7 with the Windows SDK:

```powershell
./packaging/windows/sign-development-msix.ps1 `
  -Package ./dist/msix/ETSVerifier.Development_0.1.0.0_x64_unsigned.msix `
  -ExpectedSha256 '<reviewed unsigned package SHA-256>' `
  -CertificateThumbprint '<approved certificate thumbprint>' `
  -OutputDirectory ./dist/signed-development `
  -SignToolPath '<Windows SDK x64 directory>/signtool.exe'
```

Obtain `-ExpectedSha256` from the retained review candidate's package entry or its
packaging qualification record after reviewing the expected repository/run and
source. Do not compute the expected value from an unreviewed replacement package
at signing time: that would defeat the handoff check. The unsigned review record
itself does not authenticate build origin; its provenance must be reviewed separately.

The helper compares the input digest before inspecting the package or accessing the
certificate store, then checks the copied package again before invoking SignTool.
A mismatch leaves no successful signing record. `signing.json` records both the
reviewed unsigned digest and final signed digest. This digest binding is not a
substitute for certificate authorization, source review or client qualification.

The helper rejects other identities, architectures, existing signatures, invalid
versions and existing output directories. It signs a copy with SHA-256, verifies
with SignTool's Authenticode policy, checks the source remained unchanged, and
writes `signing.json` only after success, including the selected edition, identity,
architecture and manifest version. Failed output directories are diagnostic
artifacts, not qualified candidates; retry into a new directory. Signature trust
on this machine does not prove trust on a client. These short-lived development
signatures have **no timestamp**; qualification must occur before expiry. Production
signing and timestamp policy require a separate reviewed release process.

Both Windows candidate workflows run syntax and negative-path tests with synthetic
packages and mocked certificate objects. They cover cross-edition identity/publisher
and certificate rejection, reviewed digest mismatch, unknown edition, key/validity/EKU
checks, unchanged input, no preflight output, and no success record on tool failure.
No actual signing or certificate-store access occurs in these tests. They do not
test successful signing, chain trust, or certificate-provider access.

## Clean Verifier client qualification

Use a disposable Windows 11 x64 VM with a standard-user account, no Python/Git/SDK,
and an OS snapshot. Retain the exact OS build, WebView2 version, package/source
hashes, test operator/date, and result/evidence for each row. An administrator may
provision the approved development certificate trust and WebView2 before testing;
record that preparation. Run the app tests without elevation. Do not disable
signature enforcement or treat a developer workstation as a clean client.

| Step | Procedure | Required evidence |
| --- | --- | --- |
| Preflight | Verify signed package SHA-256 against `signing.json`; run `signtool verify /pa /v` on a separate verification workstation if the client has no SDK | Exact digest and successful trust verification; client trust separately confirmed by installation |
| Install | As standard user, use `Add-AppxPackage -Path <signed package>` | Successful per-user registration; `Get-AppxPackage -Name ETSVerifier.Development` shows expected version and publisher |
| Launch | Launch from Start, not the unpacked EXE | Correct desktop under package identity, WebView2 readiness, no Python or admin requirement |
| Offline | Disable network using VM controls; select known valid, tampered, missing-trust and malformed fixtures through native dialogs | Expected strict statuses; no account/network requirement; no false valid result |
| Reports | Export JSON, Markdown and HTML to a user document directory; cancel dialogs; attempt an existing output name | Fresh snapshot reports, safe cancellation and no overwrite; retain report digests |
| Access | Complete selection, verification and export using keyboard and Narrator, then test 200% scaling | Focus/order/labels readable and no blocked controls; screenshots and observations |
| Upgrade | Build and sign `0.1.1.0` with the same identity and certificate; install over `0.1.0.0`, then launch and repeat verification | Version advances, single app entry, external source/trust/report files unchanged |
| Downgrade | Attempt ordinary installation of the older package without force switches | Rejection recorded; newer installed version still launches |
| Remove | Close app, remove the exact development package with `Remove-AppxPackage`, then inspect registration and user documents | Registration removed; externally selected inputs and exported reports preserved byte-for-byte |
| Reinstall | Install the newer package again and verify the same fixtures | Clean startup and correct results without stale state |

Before lifecycle tests, hash a dedicated fixture/report directory outside the
package's private data directory. Compare after upgrade and removal. Do not assume
MSIX private application data survives uninstall; preserving external user-owned
files is the requirement. Keep sensitive real evidence out of CI/test artifacts.
Record each row as PASS, FAIL or NOT RUN with evidence location. Any FAIL or NOT
RUN leaves client qualification incomplete. WACK, licensing, production identity,
WebView2 provisioning and Store review remain separate release gates.

## References

- [Microsoft MSIX signing guide](https://learn.microsoft.com/en-us/windows/msix/package/sign-msix-package-guide)
- [SignTool package signing](https://learn.microsoft.com/en-us/windows/msix/package/sign-app-package-using-signtool)
- [Certificate publisher matching](https://learn.microsoft.com/en-us/windows/msix/package/create-certificate-package-signing)

### PowerShell EKU representation

`EnhancedKeyUsageList` exposes `ObjectId` as an OID string in PowerShell's
certificate provider. The signing helper compares that string directly with the
code-signing OID. Accessing `ObjectId.Value` fails under strict mode before the
package is copied or signed. This was observed during operator qualification;
a corrected Windows signing run is still required to establish successful signing.
