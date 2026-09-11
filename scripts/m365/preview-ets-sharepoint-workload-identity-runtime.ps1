[CmdletBinding()]
param(
    [string]$DestinationAzureTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2',
    [string]$DestinationSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d',
    [string]$ResourceGroup = 'rg-ets-prod-eastus',
    [string]$ContainerAppName = 'ets-oif5r5ydprrou-gw',
    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d'
$approvedResourceGroup = 'rg-ets-prod-eastus'
$approvedContainerAppName = 'ets-oif5r5ydprrou-gw'
$approvedManagedIdentityName = 'ets-oif5r5ydprrou-gw-id'

function Assert-Exact {
    param(
        [Parameter(Mandatory = $true)][string]$Actual,
        [Parameter(Mandatory = $true)][string]$Expected,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($Actual -cne $Expected) {
        throw "$Name must match the approved Gate 2 value exactly."
    }
}

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Get-RevisionValue {
    param(
        [Parameter(Mandatory = $true)][object]$Revision,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $topLevel = $Revision.PSObject.Properties[$Name]
    if ($null -ne $topLevel) {
        return $topLevel.Value
    }
    $properties = $Revision.PSObject.Properties['properties']
    if ($null -ne $properties -and $null -ne $properties.Value) {
        $nested = $properties.Value.PSObject.Properties[$Name]
        if ($null -ne $nested) {
            return $nested.Value
        }
    }
    return $null
}

Assert-Exact $DestinationAzureTenantId $approvedTenantId 'DestinationAzureTenantId'
Assert-Exact $DestinationSubscriptionId $approvedSubscriptionId 'DestinationSubscriptionId'
Assert-Exact $ResourceGroup $approvedResourceGroup 'ResourceGroup'
Assert-Exact $ContainerAppName $approvedContainerAppName 'ContainerAppName'
Assert-Exact $ManagedIdentityName $approvedManagedIdentityName 'ManagedIdentityName'
Assert-Command -Name 'az'

$account = az account show --output json | ConvertFrom-Json
if (-not $account.tenantId -or $account.tenantId -cne $approvedTenantId) {
    throw 'Azure CLI is not authenticated to the approved destination tenant.'
}
if (-not $account.id -or $account.id -cne $approvedSubscriptionId) {
    throw 'Azure CLI is not using the approved destination subscription.'
}

$identity = az identity show `
    --resource-group $approvedResourceGroup `
    --name $approvedManagedIdentityName `
    --output json | ConvertFrom-Json
if (-not $identity.id -or -not $identity.clientId -or -not $identity.principalId) {
    throw 'Approved Gateway UAMI response is incomplete.'
}

$app = az containerapp show `
    --resource-group $approvedResourceGroup `
    --name $approvedContainerAppName `
    --output json | ConvertFrom-Json
if (-not $app.id -or -not $app.identity) {
    throw 'Approved Gateway Container App could not be read completely.'
}

$userAssigned = $app.identity.PSObject.Properties['userAssignedIdentities']
if ($null -eq $userAssigned -or $null -eq $userAssigned.Value) {
    throw 'Gateway Container App has no user-assigned identities.'
}
$attachedIdentity = @($userAssigned.Value.PSObject.Properties | Where-Object {
    $_.Name -ieq [string]$identity.id
})
if ($attachedIdentity.Count -ne 1) {
    throw 'Approved Gateway UAMI is not attached exactly once to the Container App.'
}

$revisions = @(
    az containerapp revision list `
        --resource-group $approvedResourceGroup `
        --name $approvedContainerAppName `
        --output json | ConvertFrom-Json
)
$activeRevisions = @($revisions | Where-Object {
    (Get-RevisionValue -Revision $_ -Name 'active') -eq $true
})
$activeReplicaCount = 0
foreach ($revision in $activeRevisions) {
    $replicas = Get-RevisionValue -Revision $revision -Name 'replicas'
    if ($null -ne $replicas) {
        $activeReplicaCount += [int]$replicas
    }
}

$runtimeReady = $activeReplicaCount -gt 0
$stage = if ($runtimeReady) {
    'gateway_workload_identity_runtime_read'
}
else {
    'gateway_runtime_activation_boundary'
}

[pscustomobject]@{
    mode = 'preview_only'
    stage = $stage
    mutationPerformed = $false
    destinationAzureTenantVerified = $true
    destinationSubscriptionVerified = $true
    gatewayContainerAppVerified = $true
    gatewayManagedIdentityVerified = $true
    gatewayManagedIdentityAttached = $true
    activeRevisionCount = $activeRevisions.Count
    activeReplicaCount = $activeReplicaCount
    runtimeReadReady = $runtimeReady
    runtimeActivationRequired = (-not $runtimeReady)
    reusableCredentialRetained = $false
    sourcePayloadRetained = $false
} | ConvertTo-Json -Depth 4
