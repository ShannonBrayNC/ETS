# Developer development signing, Windows client and WACK handoff

Status: **NOT RUN** for signed Developer installation, lifecycle and WACK.
This is an operator procedure, not authorization to sign, create/export keys,
install/trust certificates, change security/network settings, install software or
run WACK on a user device. Obtain the owner's authorization for those actions
first. No production identity, Store submission, approval or merge is implied.

Verifier and Developer are separate candidates. The Lenovo Verifier `0.1.1.0`
results do not qualify Developer. The current Developer build recipe emits
`ETSDeveloper.Development_0.1.0.0_x64_unsigned.msix`; always use the version in the
actual reviewed candidate and signed record, never copy the Verifier version.

## 1. Review the exact unsigned candidate before any Windows changes

On an engineering/review machine, retain the complete
`ets-developer-review-<source>` artifact from the selected successful Windows
Developer candidate run. Record the artifact ID, repository, workflow/run URL,
exact `candidate.json` `sourceSha`, package entry SHA-256 and byte count. A PR
workflow's source can be its synthetic merge commit, not the PR head. A new build
from merged `main` is a different candidate and requires its own complete record.
Do not substitute the latest run or claim that an earlier PR artifact is a merged
main build.

```powershell
python packaging/windows/candidate_record.py verify '<fresh review artifact extraction>'
if ($LASTEXITCODE -ne 0) { throw 'Candidate integrity verification failed.' }
```

Review `candidate.json`, `package/qualification.json`, the payload inventory and
retained engineering results. Confirm the exact source/run against GitHub, the
Developer identity/publisher, x64 architecture and approved test version. Copy
the reviewed package digest into the signing invocation from that retained record,
not by hashing an unreviewed replacement. Unsigned hash records check integrity,
not authenticated origin or release approval. Keep this review bundle unchanged.

## 2. Authorized signing owner: Developer only

Use PowerShell 7 on the approved Windows signing workstation, an already-approved
certificate in `CurrentUser/My` with exact subject `CN=ETSDeveloper.Development`,
accessible private key, explicit code-signing EKU and current validity. The
Verifier certificate is intentionally rejected. If the Developer certificate or
approved trust is absent, stop and obtain owner action; do not create/export a
key, send a password/private key in chat, or bypass signature enforcement.

```powershell
./packaging/windows/sign-development-msix.ps1 -Edition developer `
  -Package '<review extraction>/package/ETSDeveloper.Development_0.1.0.0_x64_unsigned.msix' `
  -ExpectedSha256 '<reviewed Developer unsigned package SHA-256>' `
  -CertificateThumbprint '<approved Developer certificate thumbprint>' `
  -OutputDirectory '<new Developer signing output directory>' `
  -SignToolPath '<Windows SDK x64 directory>/signtool.exe'
```

If the reviewed version changes, replace the example filename with that exact
package. Never rename a Verifier package to make it look like Developer. Retain
`signing.json` and the signed package together, separately from the immutable
unsigned review bundle. The record binds the reviewed unsigned digest to the
signed digest, selected edition, identity, publisher and version. Signature
verification on the signing workstation is not client trust or installation
qualification. These engineering signatures are not timestamped; test before
certificate expiry. Failure output is diagnostic only, never a qualified package.

## 3. Authorized Windows 11 x64 standard-user installation

Use a disposable clean Windows 11 x64 snapshot without Python/Git/language SDKs.
Record machine/snapshot, OS build, WebView2 version, account/elevation, operator,
date and any approved administrator preparation. The bundled synthetic workflow
must work without external language toolchains. Exported SDK samples still have
their separately documented runtime/dependency requirements.

Before installation, review `signing.json` against the retained signing-owner
handoff and original source/run. Run the read-only `client-preflight.ps1` in
PowerShell 7 with that signed package, the reviewed signed digest and a new report
filename; stop if automatic prerequisites fail. Retain the report and separately
record clean-snapshot/manual conditions; preflight is not qualification.

In **Windows PowerShell 5.1** as the **standard user**, fill these two paths and
run the guarded check/install only after authorization:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run fresh-install qualification as the standard user, without elevation.'
    }
    $signedPackage = '<exact transferred Developer signed MSIX path>'
    $signingRecord = '<matching Developer signing.json path>'
    $record = Get-Content -LiteralPath $signingRecord -Raw | ConvertFrom-Json
    if ($record.edition -cne 'developer' -or $record.identity -cne 'ETSDeveloper.Development' -or
        $record.publisher -cne 'CN=ETSDeveloper.Development' -or $record.architecture -cne 'x64' -or
        $record.signed -ne $true -or $record.signatureVerifiedOnSigningMachine -ne $true -or
        $record.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
        $record.reviewedUnsignedSha256 -cnotmatch '^[0-9a-f]{64}$' -or
        $record.unsignedSha256 -cne $record.reviewedUnsignedSha256) {
        throw 'Not a completed, reviewed Developer development signing record.'
    }
    $expectedName = "ETSDeveloper.Development_$($record.version)_x64_signed.msix"
    if ([IO.Path]::GetFileName($signedPackage) -cne $expectedName -or $record.package -cne $expectedName -or
        (Get-FileHash -LiteralPath $signedPackage -Algorithm SHA256).Hash.ToLowerInvariant() -cne $record.sha256) {
        throw 'Transferred package does not match the reviewed signed Developer candidate.'
    }
    if ((Get-AuthenticodeSignature -LiteralPath $signedPackage).Status -ne 'Valid') {
        throw 'Developer package is not trusted here. Stop; do not change trust automatically.'
    }
    if (@(Get-AppxPackage -Name ETSDeveloper.Development).Count -ne 0) {
        throw 'Fresh-install qualification requires a clean snapshot, not an existing Developer package.'
    }
    Add-AppxPackage -Path $signedPackage
    $installed = @(Get-AppxPackage -Name ETSDeveloper.Development)
    if ($installed.Count -ne 1 -or $installed[0].Name -cne $record.identity -or
        $installed[0].Publisher -cne $record.publisher -or
        $installed[0].Version -ne [version]$record.version -or
        [string]$installed[0].Architecture -ine 'X64' -or [string]$installed[0].Status -ne 'Ok') {
        throw 'Installed Developer identity/version/publisher/architecture/status mismatch.'
    }
    $installed[0] | Select-Object Name, Version, Publisher, Architecture, PackageFullName, Status
}
```

Retain the installation transcript and exact package full name. Launch **ETS
Desktop Developer (Preview)** from Start, not the portable EXE.
Do not run WACK until the guarded installation and manual startup are evidenced.

## 4. Keep Developer lifecycle and coexistence evidence separate

Use PASS / FAIL / NOT RUN for each row, with evidence location. A FAIL or NOT RUN
is an open gate, not an implied pass from Verifier or Windows Server CI.

| Test | Required Developer evidence |
| --- | --- |
| Native startup and dialogs | Start-menu package launch without elevation or external language tools; real selection/export/cancel dialogs; repeated/cancelled operations leave no stale result |
| Synthetic workflow | Build and verify the bundled synthetic example; retain expected strict verification result and exported report hashes; no signing of real evidence is claimed |
| Strict verifier | Valid, tampered, malformed and missing-trust fixtures produce expected statuses; no false valid result |
| Offline | Under separately authorized disconnected VM conditions, built-in workflow and report/kit export work without login/network; record actual conditions, not merely blocked process traffic |
| SDK kit export | Export into a new user directory, retain archive and pin digests; refuse overwrite; kit remains alpha, with external sample prerequisites and no release provenance attestation |
| Accessibility/runtime | Keyboard, Narrator, scaling and real dialogs; separately evidence WebView2 missing/present/update behavior without silently installing prerequisites |
| Coexistence | Install separately reviewed Verifier and Developer packages with their own approved certs; record both full names, Start entries, launch and expected version/publisher; neither replaces the other |
| Upgrade/downgrade | Requires two separately reviewed signed Developer versions with the same Developer identity/publisher and authorized certificate continuity. Do not use Verifier `0.1.1.0` as a Developer upgrade. Record NOT RUN until a newer Developer candidate exists; ordinary downgrade must reject without force switches |
| Remove/reinstall | Remove only the exact Developer full name after approval; confirm Verifier remains installed and launches; reinstall the exact reviewed Developer signed digest and repeat startup/workflow |
| External file preservation | Hash dedicated input/trust/export directories outside package private data before and after lifecycle operations; require unchanged user-owned files, not survival of private app data |

## 5. Authorized WACK: bind to this Developer package, not a fixed version

Use the current Windows SDK App Certification Kit in an active signed-in desktop
session under the same account that installed Developer. Obtain authorization
before installing/updating the SDK component or running WACK. Tool elevation is
not an app runtime requirement. Close both ETS editions; keep each edition's
reports in separate new directories.

The Appx installation/query cmdlets below use inbox Windows PowerShell 5.1;
PowerShell 7 is still required for the repository signing/preflight helpers.
Do not assume native Appx-module compatibility in PowerShell 7.

For the GUI, choose **Validate a Windows app**, then **ETS Desktop Developer
(Preview)** at the exact version recorded above. For CLI execution use elevated
**Windows PowerShell 5.1**. Fill the same reviewed record/package paths below. A package full
name does not prove installed bytes: use the fresh installation transcript above,
with no intervening reinstall or update, to bind this test to the signed digest.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest
    $signedPackage = '<same reviewed Developer signed MSIX path>'
    $signingRecord = '<matching Developer signing.json path>'
    $record = Get-Content -LiteralPath $signingRecord -Raw | ConvertFrom-Json
    if ($record.edition -cne 'developer' -or $record.identity -cne 'ETSDeveloper.Development' -or
        $record.publisher -cne 'CN=ETSDeveloper.Development' -or $record.architecture -cne 'x64' -or
        $record.signed -ne $true -or $record.signatureVerifiedOnSigningMachine -ne $true -or
        $record.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
        (Get-FileHash -LiteralPath $signedPackage -Algorithm SHA256).Hash.ToLowerInvariant() -cne $record.sha256) {
        throw 'WACK handoff does not match the reviewed signed Developer candidate.'
    }
    $kit = "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe"
    if (-not (Test-Path -LiteralPath $kit)) { throw 'App Certification Kit is not installed; obtain owner action.' }
    $packages = @(Get-AppxPackage -Name ETSDeveloper.Development)
    if ($packages.Count -ne 1 -or $packages[0].Name -cne $record.identity -or
        $packages[0].Publisher -cne $record.publisher -or
        $packages[0].Version -ne [version]$record.version -or
        [string]$packages[0].Architecture -ine 'X64' -or [string]$packages[0].Status -ne 'Ok') {
        throw 'Installed package is not the exact Developer identity/version/publisher/architecture.'
    }
    $out = Join-Path $HOME ('Documents\ETS-Developer-WACK-' + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
    Copy-Item -LiteralPath $signingRecord -Destination (Join-Path $out 'signing.json')
    $packages[0] | Select-Object Name, Version, Publisher, Architecture, PackageFullName, Status |
        ConvertTo-Json | Set-Content (Join-Path $out 'installed-package.json')
    Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture |
        ConvertTo-Json | Set-Content (Join-Path $out 'windows.json')
    (Get-Item $kit).VersionInfo | Select-Object FileVersion, ProductVersion |
        ConvertTo-Json | Set-Content (Join-Path $out 'kit-version.json')
    & $kit reset
    if ($LASTEXITCODE -ne 0) { throw 'WACK reset failed.' }
    & $kit test -packagefullname $packages[0].PackageFullName -reportoutputpath (Join-Path $out 'wack.xml')
    $wackExit = $LASTEXITCODE
    $wackExit | Set-Content (Join-Path $out 'wack-exit-code.txt')
    Write-Host "WACK exit code: $wackExit; review all reports in $out. This is not a PASS assertion."
}
```

Retain complete HTML/XML results, exact signed digest, original review source/run,
unsigned-to-signed record, installation transcript, client preflight, OS/kit and
WebView2 versions, operator/date and every applicable test result. A missing
report is NOT RUN. Do not deselect failing tests or count skipped checks as PASS.
Classify failures by exact test/file, fix, rebuild and repeat against the new
candidate; never attach an old report to a new digest.

Passing WACK is still not Store approval. Production Partner Center identity,
branding/privacy/support, restricted-capability rationale, licensing/SBOM review,
production signing policy and Store certification remain separate gates for each
edition. Do not submit either `.Development` identity as the production product.

Microsoft references (checked 2026-10-28):
- [Windows App Certification Kit](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [Sign an app package using SignTool](https://learn.microsoft.com/en-us/windows/msix/package/sign-app-package-using-signtool)
- [PowerShell Appx compatibility limitation](https://github.com/PowerShell/PowerShell/issues/19031)
