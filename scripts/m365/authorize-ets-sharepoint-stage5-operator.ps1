[CmdletBinding()]
param(
    [string]$MicrosoftResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe',
    [string]$ApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a',
    [string]$ExpectedOperatorAccount = 'shannon.bray@echomedia.ai',
    [string]$ExpectedVerifiedDomain = 'echomedia.ai',
    [string]$SharePointHostname = 'echomediaai.sharepoint.com',
    [string]$SitePath = '/sites/ETS'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'
$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'
$approvedOperatorAccount = 'shannon.bray@echomedia.ai'
$approvedVerifiedDomain = 'echomedia.ai'
$approvedSharePointHostname = 'echomediaai.sharepoint.com'
$approvedSitePath = '/sites/ETS'
$approvedSiteId = 'echomediaai.sharepoint.com,2604ea4c-3b40-4195-b1a8-e3d7327b7c41,9ddf1ece-7f81-4258-af25-91e06afaa682'
$approvedSiteWebUrl = 'https://echomediaai.sharepoint.com/sites/ets'
$requiredScopes = @(
    'Application.Read.All',
    'Organization.Read.All',
    'Sites.Read.All',
    'Sites.FullControl.All'
)

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Invoke-GraphGet {
    param([Parameter(Mandatory = $true)][string]$Uri)

    return Invoke-MgGraphRequest -Method GET -Uri $Uri -OutputType PSObject
}

function Get-PermissionApplicationIds {
    param([Parameter(Mandatory = $true)][object]$Permission)

    $ids = [System.Collections.Generic.List[string]]::new()
    foreach ($propertyName in @('grantedToIdentities', 'grantedToIdentitiesV2')) {
        $property = $Permission.PSObject.Properties[$propertyName]
        if ($null -eq $property -or $null -eq $property.Value) {
            continue
        }
        foreach ($identitySet in @($property.Value)) {
            if ($null -ne $identitySet.application -and $identitySet.application.id) {
                $ids.Add([string]$identitySet.application.id)
            }
        }
    }
    return $ids.ToArray()
}

function Write-AuthorizationResult {
    param(
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][bool]$OperatorAuthorizationVerified,
        [Parameter(Mandatory = $true)][bool]$SiteGrantPresent
    )

    [pscustomobject]@{
        mode = 'operator_authorization'
        stage = $Stage
        operatorAuthorizationVerified = $OperatorAuthorizationVerified
        microsoftResourceTenantVerified = $true
        operatorAccountVerified = $true
        verifiedDomain = $approvedVerifiedDomain
        microsoftApplicationId = $approvedApplicationId
        sharePointHostname = $approvedSharePointHostname
        sitePath = $approvedSitePath
        canonicalSiteId = $approvedSiteId
        siteGrantPresent = $SiteGrantPresent
        graphResourceMutationPerformed = $false
        oauthConsentMayHaveChanged = $true
        publicEvidenceSafe = $false
    } | ConvertTo-Json -Depth 5
}

Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

if ($MicrosoftResourceTenantId -cne $approvedResourceTenantId) {
    throw 'MicrosoftResourceTenantId must match the approved EchoMedia resource tenant exactly.'
}
if ($ApplicationId -cne $approvedApplicationId) {
    throw 'ApplicationId must match the approved ETS connector application exactly.'
}
if ($ExpectedOperatorAccount -ine $approvedOperatorAccount) {
    throw 'ExpectedOperatorAccount must match the approved EchoMedia operator exactly.'
}
if ($ExpectedVerifiedDomain -cne $approvedVerifiedDomain) {
    throw 'ExpectedVerifiedDomain must match the approved EchoMedia domain exactly.'
}
if ($SharePointHostname -cne $approvedSharePointHostname) {
    throw 'SharePointHostname must match the approved EchoMedia SharePoint hostname exactly.'
}
if ($SitePath -cne $approvedSitePath) {
    throw 'SitePath must match the approved ETS site path exactly.'
}

$connected = $false
try {
    Connect-MgGraph `
        -TenantId $approvedResourceTenantId `
        -Scopes $requiredScopes `
        -ContextScope Process `
        -NoWelcome
    $connected = $true

    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -cne $approvedResourceTenantId) {
        throw 'Microsoft Graph tenant does not match the approved EchoMedia resource tenant.'
    }
    if (-not $context.Account -or $context.Account -ine $approvedOperatorAccount) {
        throw 'Microsoft Graph operator does not match the approved EchoMedia operator.'
    }

    $effectiveScopes = @($context.Scopes)
    $missingScopes = @($requiredScopes | Where-Object { $effectiveScopes -notcontains $_ })
    if ($missingScopes.Count -gt 0) {
        throw ('Microsoft Graph operator token is missing required delegated scopes: ' + ($missingScopes -join ', '))
    }

    $organization = Invoke-GraphGet -Uri 'https://graph.microsoft.com/v1.0/organization?$select=id,verifiedDomains'
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1 -or $organizations[0].id -cne $approvedResourceTenantId) {
        throw 'Authenticated Microsoft resource tenant organization could not be verified exactly.'
    }
    $domains = @($organizations[0].verifiedDomains | Where-Object {
        $_.name -ieq $approvedVerifiedDomain
    })
    if ($domains.Count -ne 1) {
        throw 'Authenticated Microsoft resource tenant does not contain the approved verified domain.'
    }

    $site = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/${approvedSharePointHostname}:${approvedSitePath}?" +
        "`$select=id,webUrl"
    )
    if (-not $site.id -or [string]$site.id -cne $approvedSiteId) {
        throw 'Resolved SharePoint site ID does not match the approved ETS site identity.'
    }
    if (-not $site.webUrl -or ([string]$site.webUrl).TrimEnd('/') -ine $approvedSiteWebUrl) {
        throw 'Resolved SharePoint site URL does not match the approved ETS site URL.'
    }

    $permissions = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$approvedSiteId/permissions?" +
        "`$select=id,roles,grantedToIdentities,grantedToIdentitiesV2"
    )
    $permissionSet = @($permissions.value)
    $connectorGrants = @($permissionSet | Where-Object {
        @(Get-PermissionApplicationIds -Permission $_) -contains $approvedApplicationId
    })

    if ($connectorGrants.Count -eq 0) {
        Write-AuthorizationResult `
            -Stage 'sharepoint_site_read_grant' `
            -OperatorAuthorizationVerified $true `
            -SiteGrantPresent $false
        return
    }
    if ($connectorGrants.Count -ne 1) {
        throw 'ETS connector has multiple grants on the approved SharePoint site.'
    }

    $roles = @($connectorGrants[0].roles)
    if ($roles.Count -ne 1 -or $roles[0] -cne 'read') {
        throw 'Existing ETS SharePoint site grant is not exactly read-only.'
    }

    Write-AuthorizationResult `
        -Stage 'ready_for_read_only_qualification' `
        -OperatorAuthorizationVerified $true `
        -SiteGrantPresent $true
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
