[CmdletBinding()]
param(
    [string]$Source = 'dist/ets-desktop',
    [string]$OutputDirectory = 'dist/msix',
    [string]$PackageVersion,
    [ValidateSet('development', 'store')][string]$Profile = 'development',
    [ValidateSet('verifier', 'developer')][string]$Edition = 'verifier',
    [string]$MakeAppxPath
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'MakeAppx packaging requires Windows and the Windows SDK.' }
$Profile = $Profile.ToLowerInvariant()
$Edition = $Edition.ToLowerInvariant()
if (-not $PackageVersion) { $PackageVersion = if ($Profile -eq 'store') { '1.0.0.0' } else { '0.1.0.0' } }
if (Test-Path $OutputDirectory) { throw 'Choose a new output directory; existing output is protected.' }
if (-not $MakeAppxPath) {
    $sdkBin = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/bin'
    $tool = Get-ChildItem $sdkBin -Directory |
        Where-Object { $_.Name -match '^10\.0\.\d+\.\d+$' } |
        Sort-Object { [version]$_.Name } -Descending |
        ForEach-Object { Join-Path $_.FullName 'x64/MakeAppx.exe' } |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $tool) { throw 'MakeAppx.exe was not found. Install the Windows SDK.' }
    $MakeAppxPath = $tool
}
New-Item $OutputDirectory -ItemType Directory | Out-Null
$out = (Resolve-Path $OutputDirectory).Path
$layout = Join-Path $out 'layout'
$inventory = Join-Path $out 'layout-sha256.json'
python (Join-Path $PSScriptRoot 'msix_layout.py') --source $Source --layout $layout --inventory $inventory --version $PackageVersion --edition $Edition --profile $Profile
if ($LASTEXITCODE -ne 0) { throw 'MSIX layout generation failed.' }
# Derive filename/record from the validated staged manifest, never duplicate publisher inputs.
[xml]$manifest = Get-Content (Join-Path $layout 'AppxManifest.xml') -Raw
$identity = [string]$manifest.Package.Identity.Name
$publisher = [string]$manifest.Package.Identity.Publisher
$package = Join-Path $out "${identity}_${PackageVersion}_x64_unsigned.msix"
# Do not use /nv: MakeAppx must perform its manifest and package validation.
& $MakeAppxPath pack /d $layout /p $package /v
if ($LASTEXITCODE -ne 0) { throw 'MakeAppx pack validation failed.' }
$unpacked = Join-Path $out 'unpacked'
& $MakeAppxPath unpack /p $package /d $unpacked
if ($LASTEXITCODE -ne 0) { throw 'MakeAppx unpack failed.' }
$expected = Get-Content $inventory -Raw | ConvertFrom-Json -AsHashtable
foreach ($relative in $expected.Keys) {
    $file = Join-Path $unpacked $relative
    if (-not (Test-Path $file -PathType Leaf)) { throw "Packaged file missing: $relative" }
    if ((Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected[$relative]) {
        throw "Packaged file mismatch: $relative"
    }
}
[ordered]@{
    package = [IO.Path]::GetFileName($package)
    sha256 = (Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant()
    identity = $identity
    publisher = $publisher
    profile = $Profile
    publisherDisplayName = [string]$manifest.Package.Properties.PublisherDisplayName
    displayName = [string]$manifest.Package.Properties.DisplayName
    edition = $Edition
    version = $PackageVersion
    signed = $false
    installationTested = $false
    cleanWindows11Qualified = $false
    wackPassed = $false
    licensesApproved = $false
    releaseApproved = $false
    storeSubmissionApproved = $false
    storeSubmitted = $false
    storeArtworkFinal = $false
    runtimePrerequisitesQualified = $false
    manifestValidated = $true
    payloadHashesVerified = $true
    filesVerified = $expected.Count
    makeAppx = $MakeAppxPath
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json | Set-Content (Join-Path $out 'qualification.json') -Encoding utf8
Write-Output "Unsigned $Profile identity MSIX candidate: $package"
