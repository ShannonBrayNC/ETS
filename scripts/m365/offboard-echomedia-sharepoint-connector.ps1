[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$ManagedIdentityName,

    [Parameter(Mandatory = $true)]
    [string]$SharePointHostname,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^/(sites|teams)/[^/]+')]
    [string]$SitePath,

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [switch]$Apply,

    [switch]$RemoveSitesSelectedRole
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$graphAppId = '00000003-0000-0000-c000-000000000000'
$requiredScopes = @(
    'User.Read',
    'Application.Read.All',
    'AppRoleAssignment.ReadWrite.All',
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
        "https://graph.microsoft.com/v1.0/servicePrincipals?" +
        "`$filter=$filter&`$select=id,appId,displayName,appRoles"
    )
    $response = Invoke-GraphGet -Uri $uri
    $matches = @($response.value)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one service principal for appId '$AppId'."
    }
    return $matches[0]
}

function Get-ManagedIdentityServicePrincipal {
    param([Parameter(Mandatory = $true)][string]$ClientId)

    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            return Get-ServicePrincipalByAppId -AppId $ClientId
        }
        catch {
            if ($attempt -eq 10) {
                throw
            }
            Start-Sleep -Seconds 3
        }
    }
    throw 'Managed identity service principal lookup failed.'
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

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

if ($SharePointHostname -notmatch '\.sharepoint\.com$') {
    throw 'SharePointHostname must be a SharePoint Online hostname ending in .sharepoint.com.'
}

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId) {
    throw 'Azure CLI is not signed in to an Entra tenant.'
}

$identity = az identity show `
    --resource-group $ResourceGroup `
    --name $ManagedIdentityName `
    --output json | ConvertFrom-Json
if (-not $identity.clientId -or -not $identity.principalId -or -not $identity.id) {
    throw 'Managed identity response did not include clientId, principalId, and resource id.'
}

$connected = $false
try {
    Connect-MgGraph `
        -TenantId $azureAccount.tenantId `
        -Scopes $requiredScopes `
        -ContextScope Process `
        -NoWelcome
    $connected = $true

    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -ne $azureAccount.tenantId) {
        throw 'Microsoft Graph tenant does not match the active Azure subscription tenant.'
    }

    $organization = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/organization?`$select=id,displayName,verifiedDomains"
    )
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1) {
        throw 'Expected exactly one Microsoft Entra organization in the authenticated tenant.'
    }
    $tenant = $organizations[0]
    $domain = @($tenant.verifiedDomains | Where-Object {
        $_.name -ieq $ExpectedVerifiedDomain
    })
    if ($domain.Count -ne 1) {
        throw (
            "Authenticated tenant does not contain required verified domain " +
            "'$ExpectedVerifiedDomain'. Refusing to offboard ETS M365 access."
        )
    }

    $graphSp = Get-ServicePrincipalByAppId -AppId $graphAppId
    $sitesSelectedRoles = @($graphSp.appRoles | Where-Object {
        $_.value -eq 'Sites.Selected' -and
        $_.isEnabled -eq $true -and
        @($_.allowedMemberTypes) -contains 'Application'
    })
    if ($sitesSelectedRoles.Count -ne 1) {
        throw 'Microsoft Graph Sites.Selected application role could not be resolved uniquely.'
    }
    $sitesSelectedRole = $sitesSelectedRoles[0]

    $managedIdentitySp = Get-ManagedIdentityServicePrincipal -ClientId $identity.clientId
    $assignmentsUri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$($managedIdentitySp.id)/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    $assignments = Invoke-GraphGet -Uri $assignmentsUri
    $existingRole = @($assignments.value | Where-Object {
        $_.resourceId -eq $graphSp.id -and $_.appRoleId -eq $sitesSelectedRole.id
    })
    if ($existingRole.Count -gt 1) {
        throw 'Duplicate Sites.Selected app-role assignments were found for the managed identity.'
    }

    $siteUri = (
        "https://graph.microsoft.com/v1.0/sites/$SharePointHostname`:$SitePath?" +
        "`$select=id,displayName,webUrl"
    )
    $site = Invoke-GraphGet -Uri $siteUri
    if (-not $site.id -or -not $site.webUrl) {
        throw 'SharePoint site could not be resolved from the supplied hostname and site path.'
    }

    $permissionsUri = (
        "https://graph.microsoft.com/v1.0/sites/$($site.id)/permissions?" +
        "`$select=id,roles,grantedToIdentities,grantedToIdentitiesV2"
    )
    $permissions = Invoke-GraphGet -Uri $permissionsUri
    $siteGrants = @($permissions.value | Where-Object {
        @(Get-PermissionApplicationIds -Permission $_) -contains $identity.clientId
    })
    if ($siteGrants.Count -gt 1) {
        throw 'Multiple SharePoint site grants were found for the managed identity.'
    }
    if ($siteGrants.Count -eq 1) {
        $grantApplicationIds = @(Get-PermissionApplicationIds -Permission $siteGrants[0])
        if ($grantApplicationIds.Count -ne 1 -or $grantApplicationIds[0] -ne $identity.clientId) {
            throw 'Target SharePoint permission also grants another application; refusing deletion.'
        }
    }

    $sitePermissionPresentBefore = $siteGrants.Count -eq 1
    $sitesSelectedAssignmentPresentBefore = $existingRole.Count -eq 1
    $sitePermissionRemoved = $false
    $sitesSelectedAssignmentRemoved = $false

    if ($Apply) {
        if ($sitePermissionPresentBefore) {
            Invoke-MgGraphRequest `
                -Method DELETE `
                -Uri "https://graph.microsoft.com/v1.0/sites/$($site.id)/permissions/$($siteGrants[0].id)" `
                -OutputType PSObject | Out-Null
            $sitePermissionRemoved = $true
        }

        $afterPermissions = Invoke-GraphGet -Uri $permissionsUri
        $remainingSiteGrants = @($afterPermissions.value | Where-Object {
            @(Get-PermissionApplicationIds -Permission $_) -contains $identity.clientId
        })
        if ($remainingSiteGrants.Count -ne 0) {
            throw 'SharePoint site permission remained after offboarding mutation.'
        }

        if ($RemoveSitesSelectedRole -and $sitesSelectedAssignmentPresentBefore) {
            Invoke-MgGraphRequest `
                -Method DELETE `
                -Uri (
                    "https://graph.microsoft.com/v1.0/servicePrincipals/$($managedIdentitySp.id)/" +
                    "appRoleAssignments/$($existingRole[0].id)"
                ) `
                -OutputType PSObject | Out-Null
            $sitesSelectedAssignmentRemoved = $true
        }

        if ($RemoveSitesSelectedRole) {
            $afterAssignments = Invoke-GraphGet -Uri $assignmentsUri
            $remainingRole = @($afterAssignments.value | Where-Object {
                $_.resourceId -eq $graphSp.id -and $_.appRoleId -eq $sitesSelectedRole.id
            })
            if ($remainingRole.Count -ne 0) {
                throw 'Sites.Selected app-role assignment remained after requested removal.'
            }
        }
    }

    [pscustomobject]@{
        mode = if ($Apply) { 'apply' } else { 'dry_run' }
        tenantId = $context.TenantId
        tenantDisplayName = $tenant.displayName
        verifiedDomain = $ExpectedVerifiedDomain
        managedIdentityResourceId = $identity.id
        managedIdentityClientId = $identity.clientId
        managedIdentityPrincipalId = $identity.principalId
        sharePointSiteId = $site.id
        sharePointSiteUrl = $site.webUrl
        sitePermissionPresentBefore = $sitePermissionPresentBefore
        sitePermissionRemoved = $sitePermissionRemoved
        sitesSelectedAssignmentPresentBefore = $sitesSelectedAssignmentPresentBefore
        removeSitesSelectedRoleRequested = [bool]$RemoveSitesSelectedRole
        sitesSelectedAssignmentRemoved = $sitesSelectedAssignmentRemoved
        managedIdentityDeleted = $false
        connectorHistoryDeleted = $false
        reusableCredentialRetained = $false
    } | ConvertTo-Json -Depth 4
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
