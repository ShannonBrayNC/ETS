[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RegistryName,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [string]$PublisherClientId = $env:AZURE_CLIENT_ID,

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$acrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Get-DirectRegistryAssignments {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalObjectId,
        [Parameter(Mandatory = $true)][string]$RegistryResourceId
    )

    $json = az role assignment list `
        --assignee $PrincipalObjectId `
        --scope $RegistryResourceId `
        --include-inherited false `
        --all `
        --output json
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to enumerate Azure role assignments for the Q0 publisher.'
    }
    return @($json | ConvertFrom-Json)
}

function Get-AcrPushAssignments {
    param([Parameter(Mandatory = $true)][object[]]$Assignments)

    return @($Assignments | Where-Object {
        $roleDefinitionId = [string]$_.roleDefinitionId
        $roleDefinitionLeaf = if ($roleDefinitionId) {
            ($roleDefinitionId.TrimEnd('/') -split '/')[-1]
        }
        else {
            ''
        }
        $roleDefinitionLeaf -ieq $acrPushRoleId -or
            [string]$_.roleDefinitionName -ieq 'AcrPush'
    })
}

Assert-Command -Name 'az'

if ([string]::IsNullOrWhiteSpace($PublisherClientId)) {
    throw (
        'PublisherClientId is required. Pass -PublisherClientId explicitly or set ' +
        'AZURE_CLIENT_ID in the authorized operator shell.'
    )
}

$account = az account show --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $account.id -or -not $account.tenantId) {
    throw 'Azure CLI is not logged into a usable subscription/tenant context.'
}

$registry = az acr show `
    --name $RegistryName `
    --resource-group $ResourceGroup `
    --query '{id:id,loginServer:loginServer,adminUserEnabled:adminUserEnabled,roleAssignmentMode:roleAssignmentMode}' `
    --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "Unable to resolve ACR '$RegistryName' in resource group '$ResourceGroup'."
}
if (-not $registry.id -or -not $registry.loginServer) {
    throw 'ACR lookup omitted required registry metadata.'
}
if ($registry.adminUserEnabled -ne $false) {
    throw 'Refusing Q0 publisher bootstrap while the ACR admin user is enabled.'
}
if ([string]$registry.roleAssignmentMode -cne 'LegacyRegistryPermissions') {
    throw (
        "This bootstrap is only valid for LegacyRegistryPermissions. Observed '$($registry.roleAssignmentMode)'. " +
        'ABAC registries require Container Registry Repository Writer instead of AcrPush.'
    )
}

$registrySubscriptionId = ([string]$registry.id -split '/')[2]
if ($registrySubscriptionId -ine [string]$account.id) {
    throw 'The selected ACR is not in the active Azure subscription.'
}

$publisher = az ad sp show `
    --id $PublisherClientId `
    --query '{id:id,appId:appId,displayName:displayName}' `
    --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $publisher.id -or -not $publisher.appId) {
    throw 'Unable to resolve the GitHub OIDC publisher service principal from PublisherClientId.'
}
if ([string]$publisher.appId -ine $PublisherClientId) {
    throw 'Resolved service-principal appId does not match PublisherClientId.'
}

$assignments = @(Get-DirectRegistryAssignments `
    -PrincipalObjectId ([string]$publisher.id) `
    -RegistryResourceId ([string]$registry.id))
$acrPushAssignments = @(Get-AcrPushAssignments -Assignments $assignments)
if ($acrPushAssignments.Count -gt 1) {
    throw 'Q0 publisher has duplicate AcrPush assignments at the approved ACR scope.'
}

Write-Host 'Q0 ACR publisher bootstrap boundary:'
Write-Host "  active_subscription=$($account.id)"
Write-Host "  registry=$($registry.loginServer)"
Write-Host '  role_assignment_mode=LegacyRegistryPermissions'
Write-Host "  publisher_app_id=$($publisher.appId)"
Write-Host "  target_role=AcrPush ($acrPushRoleId)"
Write-Host '  target_scope=approved ACR resource only'
Write-Host '  registry_admin_user=false'

if ($acrPushAssignments.Count -eq 1) {
    Write-Host 'AcrPush assignment already exists at the approved ACR scope; no mutation required.'
    exit 0
}

if (-not $Apply) {
    Write-Host 'Preview only. Re-run with -Apply after reviewing the active tenant, subscription, publisher, role, and scope.'
    exit 0
}

az role assignment create `
    --assignee-object-id $publisher.id `
    --assignee-principal-type ServicePrincipal `
    --role $acrPushRoleId `
    --scope $registry.id `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw 'Azure rejected the bounded AcrPush role assignment.'
}

for ($attempt = 1; $attempt -le 10; $attempt++) {
    $assignments = @(Get-DirectRegistryAssignments `
        -PrincipalObjectId ([string]$publisher.id) `
        -RegistryResourceId ([string]$registry.id))
    $acrPushAssignments = @(Get-AcrPushAssignments -Assignments $assignments)
    if ($acrPushAssignments.Count -eq 1) {
        Write-Host 'AcrPush assignment is present at the approved ACR scope.'
        Write-Host 'Allow Azure RBAC data-plane propagation before retrying the protected Q0 publication workflow.'
        exit 0
    }
    if ($acrPushAssignments.Count -gt 1) {
        throw 'Q0 publisher converged to duplicate AcrPush assignments.'
    }
    if ($attempt -lt 10) {
        Start-Sleep -Seconds 3
    }
}

throw 'AcrPush role assignment did not become visible within the bounded verification window.'
