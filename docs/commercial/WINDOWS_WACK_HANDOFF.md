# Windows App Certification Kit handoff

Status: NOT RUN. A successful WACK run is required evidence, not Store approval.
The Lenovo manual test results are recorded in
[Lenovo qualification](LENOVO_WINDOWS_QUALIFICATION.md).

This page's Lenovo commands target **Verifier only**. Do not change only the display
name or reuse its results for Developer. Developer has a distinct identity and a
separate [exact signed-package installation and WACK handoff](WINDOWS_DEVELOPER_QUALIFICATION.md).
Each edition needs its own package digest, installed-package identity and reports.

## Run Verifier on the Lenovo

Use the current Windows SDK's App Certification Kit. If it is absent, install the
App Certification Kit component through the Windows SDK installer. Record this
preparation; it changes the test-machine tool inventory. Close ETS before testing.
Run in an active signed-in desktop session; do not use a background Session 0.

From Start, open **Windows App Cert Kit**, choose **Validate a Windows app**,
select **ETS Verifier (Development)** version **0.1.1.0**, and run all applicable
tests. Save both HTML and XML results to a new directory. Do not deselect failing
tests or treat skipped/inapplicable checks as passed without reviewing why.

For command-line execution, open elevated PowerShell under the same account that
installed ETS. This elevation is for the certification tool, not an assertion
that normal app operation requires administrator privileges. The block below
resets only WACK's prior test state and starts its installed-package validation:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $kit = "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe"
    if (-not (Test-Path -LiteralPath $kit)) { throw 'Install Windows App Certification Kit first.' }
    $packages = @(Get-AppxPackage -Name ETSVerifier.Development)
    if ($packages.Count -ne 1 -or $packages[0].Version -ne [version]'0.1.1.0') {
        throw 'Expected exactly one installed ETSVerifier.Development 0.1.1.0 package.'
    }
    $out = Join-Path $HOME ('Documents\ETS-WACK-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
    $packages[0] | Select-Object Name, Version, Publisher, PackageFullName, Status |
        ConvertTo-Json | Set-Content (Join-Path $out 'installed-package.json')
    Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture |
        ConvertTo-Json | Set-Content (Join-Path $out 'windows.json')
    (Get-Item $kit).VersionInfo | Select-Object FileVersion, ProductVersion |
        ConvertTo-Json | Set-Content (Join-Path $out 'kit-version.json')
    & $kit reset
    if ($LASTEXITCODE -ne 0) { throw 'WACK reset failed.' }
    & $kit test -packagefullname $packages[0].PackageFullName -reportoutputpath (Join-Path $out 'wack.xml')
    Write-Host "WACK exit code: $LASTEXITCODE; inspect the report in $out"
}
```

Retain the complete HTML/XML report, not only a screenshot or exit code. Attach
signing.json for the transferred candidate, the read-only client-preflight report
(if available), kit version and OS observations. Review each failure by exact test
name and affected file. A missing report is NOT RUN, never PASS. Re-run after
fixes against the exact new package and retain both results.

## Submission boundary

This candidate still uses the engineering publisher and software test certificate.
After Partner Center provides the exact production package identity, rebuild and
repeat applicable packaging/client/certification checks. Do not submit the
ETSVerifier.Development or ETSDeveloper.Development identity as a production product.

Required external inputs: verified publisher/account owner, reserved product
identity, final branding/screenshots, privacy and support URLs, age ratings and
markets, runtime dependency/license sign-off, and runFullTrust capability rationale.
No production identity, public URL or legal approval should be invented.

Reference (checked 2026-10-28):
https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit
