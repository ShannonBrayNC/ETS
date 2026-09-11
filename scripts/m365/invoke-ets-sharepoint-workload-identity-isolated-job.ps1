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

function Replace-ExactlyOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$OldValue,
        [Parameter(Mandatory = $true)][string]$NewValue,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $first = $Source.IndexOf($OldValue, [System.StringComparison]::Ordinal)
    if ($first -lt 0) {
        throw "Gate 2 isolated-job hotfix target '$Name' was not found."
    }
    if ($Source.IndexOf($OldValue, $first + $OldValue.Length, [System.StringComparison]::Ordinal) -ge 0) {
        throw "Gate 2 isolated-job hotfix target '$Name' is ambiguous."
    }
    return $Source.Replace($OldValue, $NewValue)
}

$source = Get-Content $corePath -Raw -Encoding UTF8

$oldUriLine = (
    '$jobUri = "https://management.azure.com' +
    '$jobResourceId' +
    '?api-version=' +
    '$jobApiVersion"'
)
$newUriLine = '$jobUri = "https://management.azure.com${jobResourceId}?api-version=${jobApiVersion}"'
$source = Replace-ExactlyOnce -Source $source -OldValue $oldUriLine -NewValue $newUriLine -Name 'ARM URI'

$oldBodyJsonLine = '$jobBodyJson = $jobBody | ConvertTo-Json -Depth 30 -Compress'
$newBodyJsonBlock = @'
$jobBodyJson = $jobBody | ConvertTo-Json -Depth 30 -Compress
$jobBodyPath = Join-Path ([System.IO.Path]::GetTempPath()) (
    'ets-g2q-body-' + [Guid]::NewGuid().ToString('N') + '.json'
)
[System.IO.File]::WriteAllText(
    $jobBodyPath,
    $jobBodyJson,
    [System.Text.UTF8Encoding]::new($false)
)
$jobBodyReference = "@$jobBodyPath"
'@
$source = Replace-ExactlyOnce `
    -Source $source `
    -OldValue $oldBodyJsonLine `
    -NewValue $newBodyJsonBlock `
    -Name 'ARM request body file staging'

$oldCreateBlock = @'
    $createdJson = az rest `
        --method put `
        --uri $jobUri `
        --headers 'Content-Type=application/json' `
        --body $jobBodyJson `
        --output json
    if ($LASTEXITCODE -ne 0) {
        throw "Temporary Gate 2 qualification job creation failed with exit code $LASTEXITCODE."
    }
'@
$newCreateBlock = @'
    $createdJson = $null
    $jobCreateExitCode = $null
    try {
        $createdJson = az rest `
            --method put `
            --uri $jobUri `
            --headers 'Content-Type=application/json' `
            --body $jobBodyReference `
            --output json
        $jobCreateExitCode = $LASTEXITCODE
    }
    finally {
        Remove-Item -LiteralPath $jobBodyPath -Force -ErrorAction SilentlyContinue
    }
    if ($jobCreateExitCode -ne 0) {
        throw "Temporary Gate 2 qualification job creation failed with exit code $jobCreateExitCode."
    }
'@
$source = Replace-ExactlyOnce `
    -Source $source `
    -OldValue $oldCreateBlock `
    -NewValue $newCreateBlock `
    -Name 'Windows-safe ARM request submission'

$escapedRoot = $PSScriptRoot.Replace("'", "''")
$scriptRootLiteral = "'$escapedRoot'"
$source = $source.Replace('$PSScriptRoot', $scriptRootLiteral)

$scriptBlock = [scriptblock]::Create($source)
& $scriptBlock @PSBoundParameters
