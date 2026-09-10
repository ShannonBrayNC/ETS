[CmdletBinding()]
param(
    [string]$MicrosoftResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe',
    [string]$ApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a',
    [string]$ExpectedOperatorAccount = 'shannon.bray@echomedia.ai',
    [string]$ExpectedVerifiedDomain = 'echomedia.ai',
    [string]$SharePointHostname = 'echomediaai.sharepoint.com',
    [string]$SitePath = '/sites/ETS',
    [ValidateSet('read')]
    [string]$SiteRole = 'read',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'
$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'
$approvedApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant'
$approvedOperatorAccount = 'shannon.bray@echomedia.ai'
$approvedVerifiedDomain = 'echomedia.ai'
$approvedSharePointHostname = 'echomediaai.sharepoint.com'
$approvedSitePath = '/sites/ETS'
$approvedSiteId = 'echomediaai.sharepoint.com,2604ea4c-3b40-4195-b1a8-e3d7327b7c41,9ddf1ece-7f81-4258-af25-91e06afaa682'
$approvedSiteWebUrl = 'https://echomediaai.sharepoint.com/sites/ets'
$graphAppId = '00000003-0000-0000-c000-000000000000'
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

function Get-ServicePrincipalByAppId {
    param([Parameter(Mandatory = $true)][string]$AppId)

    $filter = [uri]::EscapeDataString("appId eq '$AppId'")
    $uri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter&" +
        "`$select=id,appId,displayName,appRoles,accountEnabled,servicePrincipalType," +
        "appOwnerOrganizationId"
    )
    $response = Invoke-GraphGet -Uri $uri
    return @($response.value)
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

function Get-ConnectorSiteGrants {
    param([Parameter(Mandatory = $true)][object[]]$Permissions)

    return @($Permissions | Where-Object {
        @(Get-PermissionApplicationIds -Permission $_) -contains $approvedApplicationId
    })
}

function Assert-ExactReadGrant {
    param([Parameter(Mandatory = $true)][object[]]$Grants)

    if ($Grants.Count -ne 1) {
        throw 'Expected exactly one ETS connector grant on the approved SharePoint site.'
    }
    $roles = @($Grants[0].roles)
    if ($roles.Count -ne 1 -or $roles[0] -cne 'read') {
        throw 'ETS connector SharePoint site grant is not exactly read-only.'
    }
    if (-not $Grants[0].id) {
        throw 'ETS connector SharePoint site grant did not return a permission id.'
    }
}

function Write-StageResult {
    param(
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [Parameter(Mandatory = $true)][bool]$MutationPerformed,
        [string]$PermissionId = ''
    )

    [pscustomobject]@{
        mode = if ($Apply) { 'apply' } else { 'preview_only' }
        stage = 'sharepoint_site_read_grant'
        mutationRequired = $MutationRequired
        mutationPerformed = $MutationPerformed
        microsoftResourceTenantVerified = $true
        operatorAccountVerified = $true
        verifiedDomain = $approvedVerifiedDomain
        microsoftApplicationId = $approvedApplicationId
        graphPermissionAssigned = $true
        sharePointHostname = $approvedSharePointHostname
        sitePath = $approvedSitePath
        canonicalSiteId = $approvedSiteId
        sharePointSiteRole = 'read'
        sharePointPermissionId = $PermissionId
        sharePointPermissionAssigned = -not $MutationRequired
        broaderSiteRoleAssigned = $false
        reusableCredentialRetained = $false
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
if ($SiteRole -cne 'read') {
    throw 'Only the read SharePoint site role is permitted in Stage 5.'
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

    $connectorMatches = @(Get-ServicePrincipalByAppId -AppId $approvedApplicationId)
    if ($connectorMatches.Count -ne 1) {
        throw 'EchoMedia connector enterprise application did not resolve uniquely.'
    }
    $connectorSp = $connectorMatches[0]
    if ($connectorSp.displayName -cne $approvedApplicationDisplayName) {
        throw 'EchoMedia connector enterprise application display name does not match the approved value.'
    }
    if ($connectorSp.servicePrincipalType -ne 'Application' -or $connectorSp.accountEnabled -ne $true) {
        throw 'EchoMedia connector enterprise application is not an enabled application service principal.'
    }
    if ($connectorSp.appOwnerOrganizationId -cne $approvedDestinationTenantId) {
        throw 'EchoMedia connector enterprise application is not owned by the approved destination tenant.'
    }

    $graphMatches = @(Get-ServicePrincipalByAppId -AppId $graphAppId)
    if ($graphMatches.Count -ne 1) {
        throw 'Microsoft Graph service principal did not resolve uniquely.'
    }
    $graphSp = $graphMatches[0]
    $sitesSelectedRoles = @($graphSp.appRoles | Where-Object {
        $_.value -eq 'Sites.Selected' -and
        $_.isEnabled -eq $true -and
        @($_.allowedMemberTypes) -contains 'Application'
    })
    if ($sitesSelectedRoles.Count -ne 1) {
        throw 'Microsoft Graph Sites.Selected application role did not resolve uniquely.'
    }
    $sitesSelectedRole = $sitesSelectedRoles[0]

    $assignments = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$($connectorSp.id)/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    $assignmentSet = @($assignments.value)
    $selectedAssignments = @($assignmentSet | Where-Object {
        $_.resourceId -eq $graphSp.id -and $_.appRoleId -eq $sitesSelectedRole.id
    })
    if ($selectedAssignments.Count -ne 1 -or $assignmentSet.Count -ne 1) {
        throw 'ETS connector does not have exactly one Sites.Selected Graph app-role assignment.'
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

    $permissionsUri = (
        "https://graph.microsoft.com/v1.0/sites/$approvedSiteId/permissions?" +
        "`$select=id,roles,grantedToIdentities,grantedToIdentitiesV2"
    )
    $permissions = Invoke-GraphGet -Uri $permissionsUri
    $permissionSet = @($permissions.value)
    $connectorGrants = @(Get-ConnectorSiteGrants -Permissions $permissionSet)

    if ($connectorGrants.Count -gt 0) {
        Assert-ExactReadGrant -Grants $connectorGrants
        Write-StageResult `
            -MutationRequired $false `
            -MutationPerformed $false `
            -PermissionId ([string]$connectorGrants[0].id)
        return
    }

    if (-not $Apply) {
        Write-StageResult -MutationRequired $true -MutationPerformed $false
        return
    }

    $permissionBody = @{
        roles = @('read')
        grantedToIdentities = @(
            @{
                application = @{
                    id = $approvedApplicationId
                    displayName = $approvedApplicationDisplayName
                }
            }
        )
    } | ConvertTo-Json -Depth 6

    Invoke-MgGraphRequest `
        -Method POST `
        -Uri "https://graph.microsoft.com/v1.0/sites/$approvedSiteId/permissions" `
        -Body $permissionBody `
        -ContentType 'application/json' `
        -OutputType PSObject | Out-Null

    $afterPermissions = Invoke-GraphGet -Uri $permissionsUri
    $afterPermissionSet = @($afterPermissions.value)
    $afterConnectorGrants = @(Get-ConnectorSiteGrants -Permissions $afterPermissionSet)
    Assert-ExactReadGrant -Grants $afterConnectorGrants

    Write-StageResult `
        -MutationRequired $false `
        -MutationPerformed $true `
        -PermissionId ([string]$afterConnectorGrants[0].id)
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
