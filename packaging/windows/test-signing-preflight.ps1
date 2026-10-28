# Negative-path tests use synthetic ZIPs, never credentials or certificate-store writes.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script = Join-Path $PSScriptRoot 'sign-development-msix.ps1'
$tokens = $null
$parseErrors = $null
[void][Management.Automation.Language.Parser]::ParseFile($script, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$root = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item $root -ItemType Directory | Out-Null
try {
    $fakeTool = Join-Path $root 'must-not-run.ps1'
    Set-Content $fakeTool "throw 'Signing tool unexpectedly invoked'"
    $cases = @(
        @{ name = 'wrong-identity'; identity = 'Wrong'; version = '0.1.0.0'; error = 'Only the x64' },
        @{ name = 'unsafe-version'; identity = 'ETSVerifier.Development'; version = '../outside'; error = 'Invalid development package version' },
        @{ name = 'overflow-version'; identity = 'ETSVerifier.Development'; version = '65536.1.0.0'; error = 'Invalid development package version' },
        @{ name = 'already-signed'; identity = 'ETSVerifier.Development'; version = '0.1.0.0'; error = 'Expected an unsigned'; signed = $true },
        @{ name = 'missing-manifest'; identity = 'ETSVerifier.Development'; version = '0.1.0.0'; error = 'Expected exactly one'; missing = $true }
    )
    foreach ($case in $cases) {
        $package = Join-Path $root ($case.name + '.msix')
        $zip = [IO.Compression.ZipFile]::Open($package, [IO.Compression.ZipArchiveMode]::Create)
        try {
            if (-not $case.ContainsKey('missing')) {
                $entry = $zip.CreateEntry('AppxManifest.xml')
                $writer = [IO.StreamWriter]::new($entry.Open())
                try { $writer.Write('<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"><Identity Name="' + $case.identity + '" Publisher="CN=ETSVerifier.Development" ProcessorArchitecture="x64" Version="' + $case.version + '" /></Package>') }
                finally { $writer.Dispose() }
            }
            if ($case.ContainsKey('signed')) { [void]$zip.CreateEntry('AppxSignature.p7x') }
        } finally { $zip.Dispose() }
        $before = (Get-FileHash $package).Hash
        $output = Join-Path $root ($case.name + '-output')
        $failed = $false
        try { & $script -Package $package -CertificateThumbprint ('0' * 40) -OutputDirectory $output -SignToolPath $fakeTool }
        catch {
            if ($_.Exception.Message -notlike ('*' + $case.error + '*')) { throw }
            $failed = $true
        }
        if (-not $failed) { throw "Expected rejection: $($case.name)" }
        if (Test-Path $output) { throw 'Rejected input created output.' }
        if ((Get-FileHash $package).Hash -ne $before) { throw 'Rejected input changed source.' }
    }
    Write-Output "Passed $($cases.Count) signing preflight rejection cases."
} finally { Remove-Item $root -Recurse -Force }
