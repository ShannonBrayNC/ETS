[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationAzureTenantId,

    [string]$ResourceGroup = 'rg-ets-prod-eastus',

    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id',

    [string]$ApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a',

    [string]$FederatedCredentialName = 'ets-gateway-sharepoint-uami',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedResourceGroup = 'rg-ets-prod-eastus'
$approvedManagedIdentityName = 'ets-oif5r5ydprrou-gw-id'
$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'
$approvedApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant'
$approvedFederatedCredentialName = 'ets-gateway-sharepoint-uami'
$tokenExchangeAudience = 'api://AzureADTokenExchange'

function Assert-NativeSuccess {
    param([Parameter(Mandatory = $true)][string]$Operation)

    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with Azure CLI exit code $LASTEXITCODE."
    }
}

function Get-FederatedCredentials {
    param([Parameter(Mandatory = $true)][string]$AppId)

    $raw = az ad app federated-credential list --id $AppId --output json
    Assert-NativeSuccess -Operation 'Federated credential lookup'
    if (-not $raw) {
        return @()
    }
    $parsed = $raw | ConvertFrom-Json
    return @($parsed)
}

function Assert-ApplicationShape {
    param([Parameter(Mandatory = $true)][object]$Application)

    if ($Application.appId -cne $approvedApplicationId) {
        throw 'Destination application ID does not match the approved Stage 1 result.'
    }
    if ($Application.displayName -cne $approvedApplicationDisplayName) {
        throw 'Destination application display name does not match the approved value.'
    }
    if ($Application.signInAudience -cne 'AzureADMultipleOrgs') {
        throw 'Destination application is not configured as AzureADMultipleOrgs.'
    }
    if (@($Application.passwordCredentials).Count -ne 0) {
        throw 'Destination application unexpectedly contains password credentials.'
    }
    if (@($Application.keyCredentials).Count -ne 0) {
        throw 'Destination application unexpectedly contains certificate credentials.'
    }
    if (@($Application.requiredResourceAccess).Count -ne 0) {
        throw 'Destination application unexpectedly requests API permissions.'
    }
}

function Assert-FederatedCredentialShape {
    param(
        [Parameter(Mandatory = $true)][object]$Credential,
        [Parameter(Mandatory = $true)][string]$ExpectedIssuer,
        [Parameter(Mandatory = $true)][string]$ExpectedSubject
    )

    $audiences = @($Credential.audiences)
    if ($Credential.name -cne $approvedFederatedCredentialName) {
        throw 'Federated credential name does not match the approved value.'
    }
    if ($Credential.issuer -cne $ExpectedIssuer) {
        throw 'Federated credential issuer does not match the destination tenant.'
    }
    if ($Credential.subject -cne $ExpectedSubject) {
        throw 'Federated credential subject does not match the approved Gateway UAMI principal ID.'
    }
    if ($audiences.Count -ne 1 -or $audiences[0] -cne $tokenExchangeAudience) {
        throw 'Federated credential audience does not match Azure AD token exchange exactly.'
    }
}

function Write-StageResult {
    param(
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [Parameter(Mandatory = $true)][bool]$MutationPerformed
    )

    [pscustomobject]@{
        mode = if ($Apply) { 'apply' } else { 'preview_only' }
        stage = 'destination_federated_identity_credential'
        mutationRequired = $MutationRequired
        mutationPerformed = $MutationPerformed
        destinationAzureTenantVerified = $true
        destinationManagedIdentityVerified = $true
        managedIdentityName = $approvedManagedIdentityName
        microsoftApplicationId = $approvedApplicationId
        federatedCredentialName = $approvedFederatedCredentialName
        issuer = "https://login.microsoftonline.com/$approvedDestinationTenantId/v2.0"
        audience = $tokenExchangeAudience
        resourceTenantServicePrincipalCreated = $false
        graphPermissionAssigned = $false
        sharePointPermissionAssigned = $false
    } | ConvertTo-Json -Depth 4
}

if ($DestinationAzureTenantId -cne $approvedDestinationTenantId) {
    throw 'DestinationAzureTenantId must match the approved migration destination tenant exactly.'
}
if ($ResourceGroup -cne $approvedResourceGroup) {
    throw 'ResourceGroup must match the approved migration destination resource group exactly.'
}
if ($ManagedIdentityName -cne $approvedManagedIdentityName) {
    throw 'ManagedIdentityName must match the approved Gateway UAMI exactly.'
}
if ($ApplicationId -cne $approvedApplicationId) {
    throw 'ApplicationId must match the application created by Gate 2 Stage 1 exactly.'
}
if ($FederatedCredentialName -cne $approvedFederatedCredentialName) {
    throw 'FederatedCredentialName must match the approved Gate 2 Stage 2 value exactly.'
}

$azureAccountRaw = az account show --output json
Assert-NativeSuccess -Operation 'Azure account context lookup'
$azureAccount = $azureAccountRaw | ConvertFrom-Json
if (-not $azureAccount.tenantId -or $azureAccount.tenantId -cne $approvedDestinationTenantId) {
    throw 'Active Azure tenant does not match the approved destination tenant.'
}

$identityRaw = az identity show `
    --resource-group $approvedResourceGroup `
    --name $approvedManagedIdentityName `
    --output json
Assert-NativeSuccess -Operation 'Gateway managed identity lookup'
$identity = $identityRaw | ConvertFrom-Json
if (-not $identity.principalId -or -not $identity.clientId -or -not $identity.id) {
    throw 'Destination managed identity did not return the required identity fields.'
}

$applicationRaw = az ad app show --id $approvedApplicationId --output json
Assert-NativeSuccess -Operation 'Destination application lookup'
$application = $applicationRaw | ConvertFrom-Json
Assert-ApplicationShape -Application $application

$expectedIssuer = "https://login.microsoftonline.com/$approvedDestinationTenantId/v2.0"
$expectedSubject = [string]$identity.principalId
$credentials = @(Get-FederatedCredentials -AppId $approvedApplicationId)

if ($credentials.Count -gt 1) {
    throw 'Destination application contains multiple federated identity credentials.'
}
if ($credentials.Count -eq 1) {
    Assert-FederatedCredentialShape `
        -Credential $credentials[0] `
        -ExpectedIssuer $expectedIssuer `
        -ExpectedSubject $expectedSubject
    Write-StageResult -MutationRequired $false -MutationPerformed $false
    return
}

if (-not $Apply) {
    Write-StageResult -MutationRequired $true -MutationPerformed $false
    return
}

$tempPath = Join-Path ([System.IO.Path]::GetTempPath()) (
    'ets-stage2-fic-' + [guid]::NewGuid().ToString('N') + '.json'
)
try {
    [pscustomobject]@{
        name = $approvedFederatedCredentialName
        issuer = $expectedIssuer
        subject = $expectedSubject
        audiences = @($tokenExchangeAudience)
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $tempPath -Encoding utf8NoBOM

    az ad app federated-credential create `
        --id $approvedApplicationId `
        --parameters $tempPath `
        --output none
    Assert-NativeSuccess -Operation 'Federated credential creation'
}
finally {
    if (Test-Path -LiteralPath $tempPath) {
        Remove-Item -LiteralPath $tempPath -Force
    }
}

$postCredentials = @(Get-FederatedCredentials -AppId $approvedApplicationId)
if ($postCredentials.Count -ne 1) {
    throw 'Post-create verification did not resolve exactly one federated identity credential.'
}
Assert-FederatedCredentialShape `
    -Credential $postCredentials[0] `
    -ExpectedIssuer $expectedIssuer `
    -ExpectedSubject $expectedSubject

Write-StageResult -MutationRequired $false -MutationPerformed $true
