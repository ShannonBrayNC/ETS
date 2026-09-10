[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationAzureTenantId,

    [string]$ApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Get-ApplicationMatches {
    param([Parameter(Mandatory = $true)][string]$DisplayName)

    $escapedName = $DisplayName.Replace("'", "''")
    $filter = [uri]::EscapeDataString("displayName eq '$escapedName'")
    $uri = (
        "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&" +
        "`$select=id,appId,displayName,signInAudience,passwordCredentials,keyCredentials," +
        "requiredResourceAccess,identifierUris,web,spa,publicClient"
    )
    $response = az rest --method get --url $uri --output json | ConvertFrom-Json
    return @($response.value)
}

function Assert-ApplicationShape {
    param([Parameter(Mandatory = $true)][object]$Application)

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
    if (@($Application.identifierUris).Count -ne 0) {
        throw 'Destination application unexpectedly contains identifier URIs.'
    }
    if (@($Application.web.redirectUris).Count -ne 0) {
        throw 'Destination application unexpectedly contains web redirect URIs.'
    }
    if (@($Application.spa.redirectUris).Count -ne 0) {
        throw 'Destination application unexpectedly contains SPA redirect URIs.'
    }
    if (@($Application.publicClient.redirectUris).Count -ne 0) {
        throw 'Destination application unexpectedly contains public-client redirect URIs.'
    }
}

function Write-StageResult {
    param(
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [Parameter(Mandatory = $true)][bool]$MutationPerformed,
        [string]$ApplicationId = ''
    )

    [pscustomobject]@{
        mode = if ($Apply) { 'apply' } else { 'preview_only' }
        stage = 'destination_multitenant_application'
        mutationRequired = $MutationRequired
        mutationPerformed = $MutationPerformed
        destinationAzureTenantVerified = $true
        applicationDisplayName = $approvedApplicationDisplayName
        applicationId = $ApplicationId
        signInAudience = 'AzureADMultipleOrgs'
        passwordCredentials = 0
        certificateCredentials = 0
        requestedApiPermissions = 0
        redirectUris = 0
        federatedIdentityCredentialCreated = $false
        resourceTenantServicePrincipalCreated = $false
        graphPermissionAssigned = $false
        sharePointPermissionAssigned = $false
    } | ConvertTo-Json -Depth 4
}

Assert-Command -Name 'az'

if ($DestinationAzureTenantId -cne $approvedDestinationTenantId) {
    throw 'DestinationAzureTenantId must match the approved migration destination tenant exactly.'
}
if ($ApplicationDisplayName -cne $approvedApplicationDisplayName) {
    throw 'ApplicationDisplayName must match the approved Gate 2 application name exactly.'
}

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId -or $azureAccount.tenantId -cne $DestinationAzureTenantId) {
    throw 'Active Azure tenant does not match the approved destination tenant.'
}

$matches = Get-ApplicationMatches -DisplayName $ApplicationDisplayName
if ($matches.Count -gt 1) {
    throw 'Destination application display name resolved to multiple application objects.'
}
if ($matches.Count -eq 1) {
    Assert-ApplicationShape -Application $matches[0]
    Write-StageResult `
        -MutationRequired $false `
        -MutationPerformed $false `
        -ApplicationId ([string]$matches[0].appId)
    return
}

if (-not $Apply) {
    Write-StageResult -MutationRequired $true -MutationPerformed $false
    return
}

az ad app create `
    --display-name $approvedApplicationDisplayName `
    --sign-in-audience AzureADMultipleOrgs `
    --output none

$postMatches = Get-ApplicationMatches -DisplayName $ApplicationDisplayName
if ($postMatches.Count -ne 1) {
    throw 'Post-create verification did not resolve exactly one destination application.'
}
Assert-ApplicationShape -Application $postMatches[0]

Write-StageResult `
    -MutationRequired $false `
    -MutationPerformed $true `
    -ApplicationId ([string]$postMatches[0].appId)
