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

function Invoke-AzRestGetJson {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Operation
    )

    $rawOutput = & az rest --method get --url $Uri --output json
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Operation failed through Azure CLI with exit code $exitCode."
    }

    $jsonText = (@($rawOutput) -join [Environment]::NewLine).Trim()
    if (-not $jsonText) {
        throw "$Operation returned no JSON payload."
    }

    try {
        return $jsonText | ConvertFrom-Json
    }
    catch {
        throw "$Operation returned invalid JSON."
    }
}

function Get-ApplicationMatches {
    param([Parameter(Mandatory = $true)][string]$DisplayName)

    $escapedName = $DisplayName.Replace("'", "''")
    $filter = [uri]::EscapeDataString("displayName eq '$escapedName'")

    # Keep each Graph URL to one query parameter. On Windows, az.cmd can otherwise
    # let cmd.exe interpret '&' as a command separator when a URI contains both
    # $filter and $select parameters.
    $listUri = "https://graph.microsoft.com/v1.0/applications?`$filter=$filter"
    $listResponse = Invoke-AzRestGetJson `
        -Uri $listUri `
        -Operation 'Destination application lookup'

    $exactCandidates = @(
        @($listResponse.value) |
            Where-Object { $_.displayName -ceq $DisplayName }
    )

    $hydratedMatches = @()
    foreach ($candidate in $exactCandidates) {
        if (-not $candidate.id) {
            throw 'Destination application lookup returned an object without an id.'
        }

        $detailUri = (
            "https://graph.microsoft.com/v1.0/applications/$($candidate.id)?" +
            "`$select=id,appId,displayName,signInAudience,passwordCredentials," +
            "keyCredentials,requiredResourceAccess,identifierUris,web,spa,publicClient"
        )
        $hydratedMatches += Invoke-AzRestGetJson `
            -Uri $detailUri `
            -Operation 'Destination application detail read'
    }

    return $hydratedMatches
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
    if ($null -ne $Application.web -and @($Application.web.redirectUris).Count -ne 0) {
        throw 'Destination application unexpectedly contains web redirect URIs.'
    }
    if ($null -ne $Application.spa -and @($Application.spa.redirectUris).Count -ne 0) {
        throw 'Destination application unexpectedly contains SPA redirect URIs.'
    }
    if (
        $null -ne $Application.publicClient -and
        @($Application.publicClient.redirectUris).Count -ne 0
    ) {
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

$accountRaw = & az account show --output json
$accountExitCode = $LASTEXITCODE
if ($accountExitCode -ne 0) {
    throw "Azure account read failed with exit code $accountExitCode."
}
$accountJson = (@($accountRaw) -join [Environment]::NewLine).Trim()
if (-not $accountJson) {
    throw 'Azure account read returned no JSON payload.'
}
$azureAccount = $accountJson | ConvertFrom-Json
if (-not $azureAccount.tenantId -or $azureAccount.tenantId -cne $DestinationAzureTenantId) {
    throw 'Active Azure tenant does not match the approved destination tenant.'
}

$matches = @(Get-ApplicationMatches -DisplayName $ApplicationDisplayName)
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

& az ad app create `
    --display-name $approvedApplicationDisplayName `
    --sign-in-audience AzureADMultipleOrgs `
    --output none
$createExitCode = $LASTEXITCODE
if ($createExitCode -ne 0) {
    throw "Destination application creation failed with exit code $createExitCode."
}

$postMatches = @(Get-ApplicationMatches -DisplayName $ApplicationDisplayName)
if ($postMatches.Count -ne 1) {
    throw 'Post-create verification did not resolve exactly one destination application.'
}
Assert-ApplicationShape -Application $postMatches[0]

Write-StageResult `
    -MutationRequired $false `
    -MutationPerformed $true `
    -ApplicationId ([string]$postMatches[0].appId)
