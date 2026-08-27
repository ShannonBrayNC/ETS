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
$acrConfigurationReaderRoleId = '69b07be0-09bf-439a-b9a6-e73de851bd59'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Get-DirectRegistryAssignments {
    param(
        [Parameter(Mandatory = $true)][string]$RegistryResourceId,
        [string]$PrincipalObjectId
    )

    $arguments = @(
        'role', 'assignment', 'list',
        '--scope', $RegistryResourceId,
        '--fill-principal-name', 'false',
        '--output', 'json'
    )
    if (-not [string]::IsNullOrWhiteSpace($PrincipalObjectId)) {
        $arguments += @('--assignee-object-id', $PrincipalObjectId)
    }

    $json = & az @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to enumerate Azure role assignments at the approved ACR scope.'
    }
    return @($json | ConvertFrom-Json)
}

function Get-RoleAssignmentsByDefinition {
    param(
        [Parameter(Mandatory = $true)][object[]]$Assignments,
        [Parameter(Mandatory = $true)][string]$RoleDefinitionId,
        [Parameter(Mandatory = $true)][string]$RoleDefinitionName
    )

    return @($Assignments | Where-Object {
        $definition = [string]$_.roleDefinitionId
        $leaf = if ($definition) {
            ($definition.TrimEnd('/') -split '/')[-1]
        }
        else {
            ''
        }
        $leaf -ieq $RoleDefinitionId -or
            [string]$_.roleDefinitionName -ieq $RoleDefinitionName
    })
}

function Get-AcrPushAssignments {
    param([Parameter(Mandatory = $true)][object[]]$Assignments)

    return @(Get-RoleAssignmentsByDefinition `
        -Assignments $Assignments `
        -RoleDefinitionId $acrPushRoleId `
        -RoleDefinitionName 'AcrPush')
}

function Resolve-PublisherFromReaderBoundary {
    param([Parameter(Mandatory = $true)][string]$RegistryResourceId)

    $assignments = @(Get-DirectRegistryAssignments -RegistryResourceId $RegistryResourceId)
    $readerAssignments = @(Get-RoleAssignmentsByDefinition `
        -Assignments $assignments `
        -RoleDefinitionId $acrConfigurationReaderRoleId `
        -RoleDefinitionName 'Container Registry Configuration Reader and Data Access Configuration Reader')

    $servicePrincipalReaders = @($readerAssignments | Where-Object {
        [string]$_.principalType -ieq 'ServicePrincipal' -and
        -not [string]::IsNullOrWhiteSpace([string]$_.principalId)
    })

    if ($servicePrincipalReaders.Count -eq 0) {
        throw (
            'PublisherClientId is not set and no direct service-principal assignment of the ' +
            'bounded ACR configuration-reader role exists at the approved registry scope. ' +
            'Pass -PublisherClientId explicitly or first establish the #374 read-only ' +
            'publisher boundary.'
        )
    }
    if ($servicePrincipalReaders.Count -gt 1) {
        throw (
            'PublisherClientId is not set and multiple service principals hold the bounded ' +
            'ACR configuration-reader role at the approved registry scope. Refusing ' +
            'ambiguous publisher discovery; pass -PublisherClientId explicitly.'
        )
    }

    $principalObjectId = [string]$servicePrincipalReaders[0].principalId
    $servicePrincipal = az ad sp show `
        --id $principalObjectId `
        --query '{id:id,appId:appId,displayName:displayName}' `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or -not $servicePrincipal.id -or -not $servicePrincipal.appId) {
        throw 'Unable to resolve the discovered Q0 publisher service principal.'
    }
    if ([string]$servicePrincipal.id -ine $principalObjectId) {
        throw 'Discovered Q0 publisher service-principal object id changed during resolution.'
    }

    Write-Host 'PublisherClientId was not provided; discovered the Q0 publisher from the exact direct ACR configuration-reader assignment.'
    return $servicePrincipal
}

function Assert-PublisherReaderBoundary {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalObjectId,
        [Parameter(Mandatory = $true)][string]$RegistryResourceId
    )

    $assignments = @(Get-DirectRegistryAssignments `
        -RegistryResourceId $RegistryResourceId `
        -PrincipalObjectId $PrincipalObjectId)
    $readerAssignments = @(Get-RoleAssignmentsByDefinition `
        -Assignments $assignments `
        -RoleDefinitionId $acrConfigurationReaderRoleId `
        -RoleDefinitionName 'Container Registry Configuration Reader and Data Access Configuration Reader')
    if ($readerAssignments.Count -ne 1) {
        throw (
            'Q0 publisher must have exactly one direct Container Registry Configuration Reader ' +
            'and Data Access Configuration Reader assignment at the approved ACR scope before ' +
            'the bounded AcrPush grant is applied.'
        )
    }
}

Assert-Command -Name 'az'

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

if ([string]::IsNullOrWhiteSpace($PublisherClientId)) {
    $publisher = Resolve-PublisherFromReaderBoundary -RegistryResourceId ([string]$registry.id)
    $PublisherClientId = [string]$publisher.appId
}
else {
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
}

Assert-PublisherReaderBoundary `
    -PrincipalObjectId ([string]$publisher.id) `
    -RegistryResourceId ([string]$registry.id)

$assignments = @(Get-DirectRegistryAssignments `
    -RegistryResourceId ([string]$registry.id) `
    -PrincipalObjectId ([string]$publisher.id))
$acrPushAssignments = @(Get-AcrPushAssignments -Assignments $assignments)
if ($acrPushAssignments.Count -gt 1) {
    throw 'Q0 publisher has duplicate AcrPush assignments at the approved ACR scope.'
}

Write-Host 'Q0 ACR publisher bootstrap boundary:'
Write-Host "  active_subscription=$($account.id)"
Write-Host "  registry=$($registry.loginServer)"
Write-Host '  role_assignment_mode=LegacyRegistryPermissions'
Write-Host "  publisher_app_id=$($publisher.appId)"
Write-Host '  publisher_reader_boundary=exact_direct_assignment'
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
        -RegistryResourceId ([string]$registry.id) `
        -PrincipalObjectId ([string]$publisher.id))
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
