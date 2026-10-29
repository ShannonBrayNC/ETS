# Synthetic ZIPs and mocked certificate reads only: no credentials, key/trust writes, or signing.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$signingScript = Join-Path $PSScriptRoot 'sign-development-msix.ps1'
$tokens = $null
$parseErrors = $null
[void][Management.Automation.Language.Parser]::ParseFile($signingScript, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
# Parse operator examples without executing installation, trust or certification actions.
$docs = Join-Path $PSScriptRoot '../../docs/commercial'
foreach ($name in @('WINDOWS_SIGNING_QUALIFICATION.md', 'WINDOWS_DEVELOPER_QUALIFICATION.md', 'WINDOWS_WACK_HANDOFF.md')) {
    $content = Get-Content -LiteralPath (Join-Path $docs $name) -Raw
    foreach ($block in [regex]::Matches($content, '(?ms)^```powershell\r?\n(.*?)^```')) {
        [void][Management.Automation.Language.Parser]::ParseInput($block.Groups[1].Value, [ref]$tokens, [ref]$parseErrors)
        if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
    }
}
if (-not $IsWindows) { throw 'Run this preflight suite with PowerShell 7 on Windows.' }
$root = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item $root -ItemType Directory | Out-Null
# Shadow only the helper's certificate read; never access an actual certificate store.
$testState = [pscustomobject]@{ CertificateReads = 0; MockCertificate = $null }
function Get-Item {
    param([string]$LiteralPath)
    if ($LiteralPath -cne ('Cert:\CurrentUser\My\' + ('0' * 40))) {
        throw "Unexpected certificate lookup: $LiteralPath"
    }
    $testState.CertificateReads++
    return $testState.MockCertificate
}
try {
    $fakeTool = Join-Path $root 'must-not-sign.ps1'
    Set-Content $fakeTool @'
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ToolArguments)
Set-Content (Join-Path $PSScriptRoot 'tool-invoked.txt') ($ToolArguments -join '|')
throw 'Synthetic signing tool failure; no signing performed.'
'@
    $toolMarker = Join-Path $root 'tool-invoked.txt'
    $cases = @()
    foreach ($edition in @('verifier', 'developer')) {
        $name = if ($edition -eq 'verifier') { 'ETSVerifier.Development' } else { 'ETSDeveloper.Development' }
        $other = if ($edition -eq 'verifier') { 'ETSDeveloper.Development' } else { 'ETSVerifier.Development' }
        $variants = @(
            @{ name = 'wrong-reviewed-hash'; error = 'does not match the reviewed candidate'; wrongHash = $true },
            @{ name = 'other-edition-identity'; identity = $other; error = 'Only the x64' },
            @{ name = 'other-edition-publisher'; publisher = "CN=$other"; error = 'Only the x64' },
            @{ name = 'production-identity'; identity = 'ETS.Production'; error = 'Only the x64' },
            @{ name = 'production-publisher'; publisher = 'CN=Production'; error = 'Only the x64' },
            @{ name = 'wrong-architecture'; architecture = 'arm64'; error = 'Only the x64' },
            @{ name = 'unsafe-version'; version = '../outside'; error = 'Invalid development package version' },
            @{ name = 'overflow-version'; version = '65536.1.0.0'; error = 'Invalid development package version' },
            @{ name = 'nonzero-revision'; version = '0.1.0.1'; error = 'Invalid development package version' },
            @{ name = 'already-signed'; error = 'Expected an unsigned'; signed = $true },
            @{ name = 'missing-manifest'; error = 'Expected exactly one'; missing = $true },
            @{ name = 'duplicate-manifest'; error = 'Expected exactly one'; duplicate = $true },
            @{ name = 'wrong-certificate'; certificateSubject = "CN=$other"; error = 'Certificate subject must exactly match'; certificateRead = $true },
            @{ name = 'certificate-without-key'; noKey = $true; error = 'Certificate has no accessible private key'; certificateRead = $true },
            @{ name = 'expired-certificate'; expired = $true; error = 'Certificate is outside its validity'; certificateRead = $true },
            @{ name = 'future-certificate'; future = $true; error = 'Certificate is outside its validity'; certificateRead = $true },
            @{ name = 'certificate-without-code-signing-eku'; noEku = $true; error = 'Certificate must explicitly permit code signing'; certificateRead = $true },
            @{ name = 'sign-tool-failure'; copyExpected = $true; error = 'Synthetic signing tool failure'; certificateRead = $true }
        )
        foreach ($variant in $variants) {
            $case = @{ edition = $edition; identity = $name; publisher = "CN=$name"; architecture = 'x64'; version = '0.1.0.0' }
            foreach ($key in $variant.Keys) { $case[$key] = $variant[$key] }
            $case.name = "$edition-$($variant.name)"
            $cases += $case
        }
    }
    # Omission is deliberately Verifier, not autodetection from an untrusted package.
    $cases += @{ name = 'default-rejects-developer'; identity = 'ETSDeveloper.Development'; publisher = 'CN=ETSDeveloper.Development'; architecture = 'x64'; version = '0.1.0.0'; error = 'Only the x64 ETSVerifier.Development' }
    $cases += @{ name = 'default-accepts-verifier-preflight'; identity = 'ETSVerifier.Development'; publisher = 'CN=ETSVerifier.Development'; architecture = 'x64'; version = '0.1.0.0'; copyExpected = $true; certificateRead = $true; error = 'Synthetic signing tool failure' }
    $cases += @{ name = 'unknown-edition'; edition = 'production'; identity = 'ETSVerifier.Development'; publisher = 'CN=ETSVerifier.Development'; architecture = 'x64'; version = '0.1.0.0'; error = 'does not belong to the set' }
    foreach ($case in $cases) {
        $package = Join-Path $root ($case.name + '.msix')
        $zip = [IO.Compression.ZipFile]::Open($package, [IO.Compression.ZipArchiveMode]::Create)
        try {
            if (-not $case.ContainsKey('missing')) {
                $entry = $zip.CreateEntry('AppxManifest.xml')
                $writer = [IO.StreamWriter]::new($entry.Open())
                try { $writer.Write('<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"><Identity Name="' + $case.identity + '" Publisher="' + $case.publisher + '" ProcessorArchitecture="' + $case.architecture + '" Version="' + $case.version + '" /></Package>') }
                finally { $writer.Dispose() }
            }
            if ($case.ContainsKey('duplicate')) { [void]$zip.CreateEntry('AppxManifest.xml') }
            if ($case.ContainsKey('signed')) { [void]$zip.CreateEntry('AppxSignature.p7x') }
        } finally { $zip.Dispose() }
        $before = (Get-FileHash $package).Hash
        $expectedHash = if ($case.ContainsKey('wrongHash')) { '0' * 64 } else { $before }
        $output = Join-Path $root ($case.name + '-output')
        $testState.CertificateReads = 0
        $testState.MockCertificate = [pscustomobject]@{
            Subject = if ($case.ContainsKey('certificateSubject')) { $case.certificateSubject } else { $case.publisher }
            HasPrivateKey = -not $case.ContainsKey('noKey')
            NotBefore = if ($case.ContainsKey('future')) { (Get-Date).AddDays(1) } else { (Get-Date).AddDays(-2) }
            NotAfter = if ($case.ContainsKey('expired')) { (Get-Date).AddDays(-1) } else { (Get-Date).AddDays(2) }
            EnhancedKeyUsageList = if ($case.ContainsKey('noEku')) { @([pscustomobject]@{ ObjectId = '1.3.6.1.5.5.7.3.1' }) } else { @([pscustomobject]@{ ObjectId = '1.3.6.1.5.5.7.3.3' }) }
        }
        if (Test-Path $toolMarker) { Remove-Item $toolMarker }
        $parameters = @{ Package = $package; ExpectedSha256 = $expectedHash; CertificateThumbprint = '0' * 40; OutputDirectory = $output; SignToolPath = $fakeTool }
        if ($case.ContainsKey('edition')) { $parameters.Edition = $case.edition }
        $failed = $false
        try { & $signingScript @parameters }
        catch {
            if ($_.Exception.Message -notlike ('*' + $case.error + '*')) { throw }
            $failed = $true
        }
        if (-not $failed) { throw "Expected rejection: $($case.name)" }
        $expectedReads = if ($case.ContainsKey('certificateRead')) { 1 } else { 0 }
        if ($testState.CertificateReads -ne $expectedReads) { throw "Unexpected certificate access: $($case.name)" }
        if ($case.ContainsKey('copyExpected')) {
            $copy = Join-Path $output "$($case.identity)_$($case.version)_x64_signed.msix"
            if (-not (Test-Path $copy) -or (Get-FileHash $copy).Hash -ne $before) { throw 'Wrong edition output or changed synthetic copy.' }
            if (-not (Test-Path $toolMarker)) { throw 'Synthetic failure tool was not reached.' }
        } else {
            if (Test-Path $output) { throw 'Rejected preflight input created output.' }
            if (Test-Path $toolMarker) { throw 'Rejected preflight input invoked signing tool.' }
        }
        if (Test-Path (Join-Path $output 'signing.json')) { throw 'Rejected candidate created a successful signing record.' }
        if ((Get-FileHash $package).Hash -ne $before) { throw 'Rejected input changed source.' }
    }
    Write-Output "Passed $($cases.Count) signing rejection cases; no signing or certificate-store access performed."
} finally { Remove-Item $root -Recurse -Force }
