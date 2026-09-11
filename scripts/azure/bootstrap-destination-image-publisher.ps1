[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$expectedTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$expectedSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d'
$sharedResourceGroup = 'rg-ets-shared-eastus'
$registryName = 'etsprod7c8ab70380'
$identityName = 'ets-gh-dst-image-publisher'
$federatedCredentialName = 'github-ets-destination-image-publish'
$githubEnvironment = 'ets-azure-migration-destination-image-publish'
$githubSubject = 'repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-image-publish'
$configurationReaderRole = 'Container Registry Configuration Reader and Data Access Configuration Reader'
$writerRole = 'AcrPush'

function Assert-AzSuccess {
    param([Parameter(Mandatory = $true)][string]$Message)
    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

function Get-ExactRoleAssignmentCount {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalId,
        [Parameter(Mandatory = $true)][string]$RoleName,
        [Parameter(Mandatory = $true)][string]$Scope
    )

    $count = az role assignment list `
        --scope $Scope `
        --assignee-object-id $PrincipalId `
        --query "[?roleDefinitionName=='$RoleName'] | length(@)" `
        --output tsv
    Assert-AzSuccess -Message "Unable to inspect '$RoleName' at the approved ACR scope."
    return [int]$count
}

function Ensure-ExactRoleAssignment {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalId,
        [Parameter(Mandatory = $true)][string]$RoleName,
        [Parameter(Mandatory = $true)][string]$Scope
    )

    $count = Get-ExactRoleAssignmentCount -PrincipalId $PrincipalId -RoleName $RoleName -Scope $Scope
    if ($count -gt 1) {
        throw "Publisher has duplicate '$RoleName' assignments at the approved ACR scope."
    }
    if ($count -eq 1) {
        return $false
    }
    if (-not $Apply) {
        return $true
    }

    az role assignment create `
        --assignee-object-id $PrincipalId `
        --assignee-principal-type ServicePrincipal `
        --role $RoleName `
        --scope $Scope `
        --output none
    Assert-AzSuccess -Message "Azure rejected the bounded '$RoleName' assignment."
    return $true
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Required command 'az' is not installed or available on PATH."
}

$account = az account show --output json | ConvertFrom-Json
Assert-AzSuccess -Message 'Azure CLI is not logged into a usable account.'
if ([string]$account.tenantId -ine $expectedTenantId) {
    throw "Destination tenant mismatch. Expected '$expectedTenantId', observed '$($account.tenantId)'."
}
if ([string]$account.id -ine $expectedSubscriptionId) {
    throw "Destination subscription mismatch. Expected '$expectedSubscriptionId', observed '$($account.id)'."
}

$registry = az acr show `
    --name $registryName `
    --resource-group $sharedResourceGroup `
    --query '{id:id,loginServer:loginServer,adminUserEnabled:adminUserEnabled,roleAssignmentMode:roleAssignmentMode}' `
    --output json | ConvertFrom-Json
Assert-AzSuccess -Message 'Unable to resolve the approved destination ACR.'
if ([string]$registry.loginServer -ine "$registryName.azurecr.io") {
    throw 'Destination ACR login server changed unexpectedly.'
}
if ($registry.adminUserEnabled -ne $false) {
    throw 'Refusing publisher bootstrap while the destination ACR admin user is enabled.'
}
if ([string]$registry.roleAssignmentMode -cne 'LegacyRegistryPermissions') {
    throw (
        "Destination ACR roleAssignmentMode is '$($registry.roleAssignmentMode)'. " +
        'This bootstrap intentionally supports only LegacyRegistryPermissions; ' +
        'ABAC mode requires a separately reviewed repository-scoped condition.'
    )
}

$identity = $null
$identityExists = $true
try {
    $identity = az identity show `
        --resource-group $sharedResourceGroup `
        --name $identityName `
        --output json 2>$null | ConvertFrom-Json
    Assert-AzSuccess -Message 'Unable to inspect the destination image publisher identity.'
}
catch {
    $identityExists = $false
}

$mutationRequired = -not $identityExists
$ficRequired = $false
$readerRoleRequired = $false
$writerRoleRequired = $false

if (-not $identityExists -and $Apply) {
    az identity create `
        --resource-group $sharedResourceGroup `
        --name $identityName `
        --location eastus `
        --output none
    Assert-AzSuccess -Message 'Unable to create the destination image publisher identity.'
    $identity = az identity show `
        --resource-group $sharedResourceGroup `
        --name $identityName `
        --output json | ConvertFrom-Json
    Assert-AzSuccess -Message 'Unable to read back the destination image publisher identity.'
    $identityExists = $true
}

if ($identityExists) {
    $principalId = [string]$identity.principalId
    $clientId = [string]$identity.clientId
    if ([string]::IsNullOrWhiteSpace($principalId) -or [string]::IsNullOrWhiteSpace($clientId)) {
        throw 'Destination image publisher identity is missing clientId/principalId.'
    }

    $broadRoleCount = az role assignment list --all `
        --assignee-object-id $principalId `
        --query "[?contains(['Owner','Contributor','User Access Administrator','Role Based Access Control Administrator'], roleDefinitionName)] | length(@)" `
        --output tsv
    Assert-AzSuccess -Message 'Unable to inspect publisher role assignments.'
    if ([int]$broadRoleCount -ne 0) {
        throw 'Destination image publisher already has a broad administrative role; refusing to continue.'
    }

    $ficExists = $true
    try {
        $fic = az identity federated-credential show `
            --resource-group $sharedResourceGroup `
            --identity-name $identityName `
            --name $federatedCredentialName `
            --output json 2>$null | ConvertFrom-Json
        Assert-AzSuccess -Message 'Unable to inspect the destination image publisher federated credential.'
        if ([string]$fic.issuer -cne 'https://token.actions.githubusercontent.com') {
            throw 'Existing publisher federated credential issuer does not match GitHub Actions.'
        }
        if ([string]$fic.subject -cne $githubSubject) {
            throw 'Existing publisher federated credential subject does not match the protected GitHub environment.'
        }
        $audiences = @($fic.audiences)
        if ($audiences.Count -ne 1 -or [string]$audiences[0] -cne 'api://AzureADTokenExchange') {
            throw 'Existing publisher federated credential audience is not the required Azure AD token exchange audience.'
        }
    }
    catch {
        if ($_.Exception.Message -like 'Existing publisher*') {
            throw
        }
        $ficExists = $false
    }

    if (-not $ficExists) {
        $ficRequired = $true
        $mutationRequired = $true
        if ($Apply) {
            az identity federated-credential create `
                --resource-group $sharedResourceGroup `
                --identity-name $identityName `
                --name $federatedCredentialName `
                --issuer 'https://token.actions.githubusercontent.com' `
                --subject $githubSubject `
                --audiences 'api://AzureADTokenExchange' `
                --output none
            Assert-AzSuccess -Message 'Unable to create the destination image publisher federated credential.'
        }
    }

    $readerRoleRequired = Ensure-ExactRoleAssignment `
        -PrincipalId $principalId `
        -RoleName $configurationReaderRole `
        -Scope ([string]$registry.id)
    $writerRoleRequired = Ensure-ExactRoleAssignment `
        -PrincipalId $principalId `
        -RoleName $writerRole `
        -Scope ([string]$registry.id)
    $mutationRequired = $mutationRequired -or $readerRoleRequired -or $writerRoleRequired
}

$result = [ordered]@{
    mode = if ($Apply) { 'apply' } else { 'preview_only' }
    stage = 'destination_image_publisher_bootstrap'
    destinationTenantVerified = $true
    destinationSubscriptionVerified = $true
    registryVerified = $true
    registryName = $registryName
    registryResourceGroup = $sharedResourceGroup
    registryAdminUserEnabled = $false
    roleAssignmentMode = [string]$registry.roleAssignmentMode
    githubEnvironment = $githubEnvironment
    identityName = $identityName
    identityExists = $identityExists
    federatedCredentialRequired = $ficRequired
    configurationReaderRequired = $readerRoleRequired
    acrPushRequired = $writerRoleRequired
    mutationRequired = $mutationRequired
    mutationPerformed = [bool]($Apply -and $mutationRequired)
    clientSecretCreated = $false
    productionGatewayMutationPerformed = $false
}
if ($identityExists) {
    $result.azureClientId = [string]$identity.clientId
    $result.azureTenantId = $expectedTenantId
    $result.azureSubscriptionId = $expectedSubscriptionId
}

$result | ConvertTo-Json -Depth 4

if (-not $Apply -and $mutationRequired) {
    Write-Host 'Preview only. Re-run with -Apply only after reviewing the exact tenant, subscription, ACR, identity, FIC subject, and ACR-scoped roles.'
}
if ($Apply) {
    Write-Host "Configure GitHub environment '$githubEnvironment' with required reviewers and these environment secrets:"
    Write-Host "AZURE_CLIENT_ID=$([string]$identity.clientId)"
    Write-Host "AZURE_TENANT_ID=$expectedTenantId"
    Write-Host "AZURE_SUBSCRIPTION_ID=$expectedSubscriptionId"
    Write-Host 'These are identifiers, not reusable client secrets.'
}
