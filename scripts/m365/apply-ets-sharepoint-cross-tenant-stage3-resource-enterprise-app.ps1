[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$MicrosoftResourceTenantId,

    [string]$ApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [string]$ExpectedOperatorAccount = 'shannon.bray@echomedia.ai',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'
$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'
$approvedApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant'
$approvedVerifiedDomain = 'echomedia.ai'
$approvedOperatorAccount = 'shannon.bray@echomedia.ai'

function Assert-NativeSuccess {
    param([Parameter(Mandatory = $true)][string]$Operation)

    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with Azure CLI exit code $LASTEXITCODE."
    }
}

function Get-ResourceTenantServicePrincipals {
    $raw = az ad sp list `
        --filter "appId eq '$approvedApplicationId'" `
        --output json
    Assert-NativeSuccess -Operation 'Resource enterprise application lookup'
    if (-not $raw) {
        return @()
    }
    return @($raw | ConvertFrom-Json)
}

function Assert-ServicePrincipalShape {
    param([Parameter(Mandatory = $true)][object]$ServicePrincipal)

    if ($ServicePrincipal.appId -cne $approvedApplicationId) {
        throw 'Resource enterprise application appId does not match the approved application.'
    }
    if ($ServicePrincipal.displayName -cne $approvedApplicationDisplayName) {
        throw 'Resource enterprise application display name does not match the approved application.'
    }
    if ($ServicePrincipal.servicePrincipalType -cne 'Application') {
        throw 'Resource enterprise application is not an Application service principal.'
    }
    if ($ServicePrincipal.accountEnabled -ne $true) {
        throw 'Resource enterprise application is not enabled.'
    }
    if ($ServicePrincipal.appOwnerOrganizationId -cne $approvedDestinationTenantId) {
        throw 'Resource enterprise application is not owned by the approved destination tenant.'
    }
}

function Write-StageResult {
    param(
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [Parameter(Mandatory = $true)][bool]$MutationPerformed,
        [string]$ServicePrincipalId = ''
    )

    [pscustomobject]@{
        mode = if ($Apply) { 'apply' } else { 'preview_only' }
        stage = 'resource_enterprise_application'
        mutationRequired = $MutationRequired
        mutationPerformed = $MutationPerformed
        microsoftResourceTenantVerified = $true
        verifiedDomain = $approvedVerifiedDomain
        operatorAccountVerified = $true
        microsoftApplicationId = $approvedApplicationId
        servicePrincipalId = $ServicePrincipalId
        resourceTenantServicePrincipalCreated = $MutationPerformed
        graphPermissionAssigned = $false
        sharePointPermissionAssigned = $false
        publicEvidenceSafe = $false
    } | ConvertTo-Json -Depth 4
}

if ($MicrosoftResourceTenantId -cne $approvedResourceTenantId) {
    throw 'MicrosoftResourceTenantId must match the approved EchoMedia resource tenant exactly.'
}
if ($ApplicationId -cne $approvedApplicationId) {
    throw 'ApplicationId must match the approved Stage 1 application exactly.'
}
if ($ExpectedVerifiedDomain -cne $approvedVerifiedDomain) {
    throw 'ExpectedVerifiedDomain must match the approved EchoMedia domain exactly.'
}
if ($ExpectedOperatorAccount -cne $approvedOperatorAccount) {
    throw 'ExpectedOperatorAccount must match the approved EchoMedia operator exactly.'
}

$accountRaw = az account show --output json
Assert-NativeSuccess -Operation 'Azure account context lookup'
$account = $accountRaw | ConvertFrom-Json
if (-not $account.tenantId -or $account.tenantId -cne $approvedResourceTenantId) {
    throw 'Active Azure CLI tenant does not match the approved EchoMedia resource tenant.'
}
if (-not $account.user.name -or $account.user.name -ine $approvedOperatorAccount) {
    throw 'Active Azure CLI operator does not match the approved EchoMedia operator account.'
}

$organizationRaw = az rest `
    --method get `
    --url 'https://graph.microsoft.com/v1.0/organization?$select=id,verifiedDomains' `
    --output json
Assert-NativeSuccess -Operation 'EchoMedia organization lookup'
$organizationResponse = $organizationRaw | ConvertFrom-Json
$organizations = @($organizationResponse.value)
if ($organizations.Count -ne 1 -or $organizations[0].id -cne $approvedResourceTenantId) {
    throw 'Authenticated Microsoft resource tenant organization could not be verified exactly.'
}
$domains = @($organizations[0].verifiedDomains | Where-Object {
    $_.name -ieq $approvedVerifiedDomain
})
if ($domains.Count -ne 1) {
    throw 'Authenticated Microsoft resource tenant does not contain the approved verified domain.'
}

$matches = @(Get-ResourceTenantServicePrincipals)
if ($matches.Count -gt 1) {
    throw 'Multiple EchoMedia enterprise applications exist for the approved application ID.'
}
if ($matches.Count -eq 1) {
    Assert-ServicePrincipalShape -ServicePrincipal $matches[0]
    Write-StageResult `
        -MutationRequired $false `
        -MutationPerformed $false `
        -ServicePrincipalId ([string]$matches[0].id)
    return
}

if (-not $Apply) {
    Write-StageResult -MutationRequired $true -MutationPerformed $false
    return
}

az ad sp create --id $approvedApplicationId --output none
Assert-NativeSuccess -Operation 'EchoMedia enterprise application creation'

$postMatches = @(Get-ResourceTenantServicePrincipals)
if ($postMatches.Count -ne 1) {
    throw 'Post-create verification did not resolve exactly one EchoMedia enterprise application.'
}
Assert-ServicePrincipalShape -ServicePrincipal $postMatches[0]

Write-StageResult `
    -MutationRequired $false `
    -MutationPerformed $true `
    -ServicePrincipalId ([string]$postMatches[0].id)
