[CmdletBinding()]
param(
    [string]$ResourceGroup = 'rg-ets-prod-eastus',
    [string]$ContainerAppName = 'ets-oif5r5ydprrou-gw'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedResourceGroup = 'rg-ets-prod-eastus'
$approvedContainerAppName = 'ets-oif5r5ydprrou-gw'

if ($ResourceGroup -cne $approvedResourceGroup) {
    throw 'ResourceGroup must match the approved Gate 2 destination exactly.'
}
if ($ContainerAppName -cne $approvedContainerAppName) {
    throw 'ContainerAppName must match the approved Gateway exactly.'
}

$previewPath = Join-Path $PSScriptRoot 'preview-ets-sharepoint-workload-identity-runtime.ps1'
$harnessPath = Join-Path $PSScriptRoot 'qualify_ets_sharepoint_workload_identity.py'
if (-not (Test-Path $previewPath -PathType Leaf)) {
    throw 'Gateway runtime preview script is unavailable.'
}
if (-not (Test-Path $harnessPath -PathType Leaf)) {
    throw 'Gateway workload-identity qualification harness is unavailable.'
}

$previewJson = & $previewPath `
    -ResourceGroup $approvedResourceGroup `
    -ContainerAppName $approvedContainerAppName
$preview = $previewJson | ConvertFrom-Json
if ($preview.mutationPerformed -ne $false) {
    throw 'Gateway runtime preview unexpectedly reported a mutation.'
}
if ($preview.runtimeReadReady -ne $true -or [int]$preview.activeReplicaCount -lt 1) {
    throw (
        'Gateway runtime qualification is blocked because no active replica exists. ' +
        'This command will not activate a revision or change replica settings.'
    )
}

$harness = Get-Content $harnessPath -Raw -Encoding UTF8
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($harness))
$remoteCommand = (
    'python -c "import base64;' +
    "exec(compile(base64.b64decode('$payload')," +
    "'<ets-gate2-runtime-qualification>','exec'))\""
)

az containerapp exec `
    --resource-group $approvedResourceGroup `
    --name $approvedContainerAppName `
    --command $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Gateway runtime qualification command failed with exit code $LASTEXITCODE."
}
