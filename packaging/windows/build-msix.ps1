[CmdletBinding()]
param(
    [string]$Source = 'dist/ets-desktop',
    [string]$OutputDirectory = 'dist/msix',
    [string]$PackageVersion = '0.1.0.0',
    [string]$MakeAppxPath
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'MakeAppx packaging requires Windows and the Windows SDK.' }
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
$package = Join-Path $out "ETSVerifier.Development_${PackageVersion}_x64_unsigned.msix"
python (Join-Path $PSScriptRoot 'msix_layout.py') --source $Source --layout $layout --inventory $inventory --version $PackageVersion
if ($LASTEXITCODE -ne 0) { throw 'MSIX layout generation failed.' }
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
    identity = 'ETSVerifier.Development'
    publisher = 'CN=ETSVerifier.Development'
    version = $PackageVersion
    signed = $false
    installationTested = $false
    manifestValidated = $true
    payloadHashesVerified = $true
    filesVerified = $expected.Count
    makeAppx = $MakeAppxPath
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json | Set-Content (Join-Path $out 'qualification.json') -Encoding utf8
Write-Output "Unsigned development MSIX: $package"
