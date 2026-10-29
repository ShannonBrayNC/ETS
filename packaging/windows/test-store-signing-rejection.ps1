# Verify the actual unsigned Store-identity artifact cannot enter development signing.
# Mock the certificate reader and signing tool; never inspect a certificate or sign bytes.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Package,
    [Parameter(Mandatory)][string]$OutputFile
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item $root -ItemType Directory | Out-Null
function Get-Item { throw 'Certificate access must not occur for Store candidates.' }
try {
    $fakeTool = Join-Path $root 'must-not-sign.ps1'
    Set-Content $fakeTool "throw 'Signing tool must not be invoked for Store candidates.'"
    $before = (Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash
    foreach ($edition in @('verifier', 'developer')) {
        $output = Join-Path $root $edition
        $rejected = $false
        try {
            & (Join-Path $PSScriptRoot 'sign-development-msix.ps1') -Package $Package -ExpectedSha256 $before -CertificateThumbprint ('0' * 40) -OutputDirectory $output -SignToolPath $fakeTool -Edition $edition
        } catch {
            if ($_.Exception.Message -notlike 'Only the x64 * identity and exact development publisher may be signed*') { throw }
            $rejected = $true
        }
        if (-not $rejected -or (Test-Path $output)) { throw 'Store candidate entered development signing.' }
        if ((Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash -cne $before) { throw 'Source package changed.' }
    }
    [ordered]@{
        package = [IO.Path]::GetFileName($Package)
        sha256 = $before.ToLowerInvariant()
        rejectedByBothDevelopmentAllowlists = $true
        certificateAccessed = $false
        signingToolInvoked = $false
        sourceUnchanged = $true
    } | ConvertTo-Json | Set-Content -LiteralPath $OutputFile -Encoding utf8
} finally { Remove-Item -LiteralPath $root -Recurse -Force }
