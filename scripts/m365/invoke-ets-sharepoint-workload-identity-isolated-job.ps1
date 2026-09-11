[CmdletBinding()]
param(
    [string]$DestinationAzureTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2',
    [string]$DestinationSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d',
    [string]$ResourceGroup = 'rg-ets-prod-eastus',
    [string]$ContainerAppName = 'ets-oif5r5ydprrou-gw',
    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$corePath = Join-Path $PSScriptRoot 'invoke-ets-sharepoint-workload-identity-isolated-job.core.ps1'
if (-not (Test-Path $corePath -PathType Leaf)) {
    throw 'Gate 2 isolated-job core script is unavailable.'
}

$source = Get-Content $corePath -Raw -Encoding UTF8
$oldLine = (
    '$jobUri = "https://management.azure.com' +
    '$jobResourceId' +
    '?api-version=' +
    '$jobApiVersion"'
)
$newLine = '$jobUri = "https://management.azure.com${jobResourceId}?api-version=${jobApiVersion}"'

$first = $source.IndexOf($oldLine, [System.StringComparison]::Ordinal)
if ($first -lt 0) {
    throw 'Gate 2 isolated-job URI hotfix target was not found.'
}
if ($source.IndexOf($oldLine, $first + $oldLine.Length, [System.StringComparison]::Ordinal) -ge 0) {
    throw 'Gate 2 isolated-job URI hotfix target is ambiguous.'
}
$patched = $source.Replace($oldLine, $newLine)

$escapedRoot = $PSScriptRoot.Replace("'", "''")
$scriptRootLiteral = "'$escapedRoot'"
$patched = $patched.Replace('$PSScriptRoot', $scriptRootLiteral)

$scriptBlock = [scriptblock]::Create($patched)
& $scriptBlock @PSBoundParameters
