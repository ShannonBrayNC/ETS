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

    [Parameter(Mandatory = $true)]
    [string]$ExpectedTenantId,

    [ValidateSet('read')]
    [string]$ExpectedSiteRole = 'read',

    [string]$ExpectedVerifiedDomain,

    [string]$ExpectedOperatorAccount
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$graphAppId = '00000003-0000-0000-c000-000000000000'
$requiredScopes = @(
    'Application.Read.All',
    'Organization.Read.All',
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
    $uri = "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter&`$select=id,appId,displayName,appRoles"
    $response = Invoke-GraphGet -Uri $uri
    $matches = @($response.value)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one service principal for appId '$AppId'."
    }
    return $matches[0]
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
if ($azureAccount.tenantId -ne $ExpectedTenantId) {
    throw (
        "Active Azure tenant '$($azureAccount.tenantId)' does not match expected tenant " +
        "'$ExpectedTenantId'."
    )
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
        -TenantId $ExpectedTenantId `
        -Scopes $requiredScopes `
        -ContextScope Process `
        -NoWelcome
    $connected = $true

    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -ne $ExpectedTenantId) {
        throw 'Microsoft Graph tenant does not match the expected destination tenant.'
    }
    if ($ExpectedOperatorAccount) {
        if (-not $context.Account -or $context.Account -ine $ExpectedOperatorAccount) {
            throw (
                "Microsoft Graph operator '$($context.Account)' does not match expected operator " +
                "'$ExpectedOperatorAccount'."
            )
        }
    }

    $organization = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/organization?`$select=id,displayName,verifiedDomains"
    )
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1) {
        throw 'Expected exactly one Microsoft Entra organization in the authenticated tenant.'
    }
    $tenant = $organizations[0]
    if ($tenant.id -ne $ExpectedTenantId) {
        throw 'Microsoft Graph organization id does not match the expected destination tenant.'
    }

    if ($ExpectedVerifiedDomain) {
        $domain = @($tenant.verifiedDomains | Where-Object {
            $_.name -ieq $ExpectedVerifiedDomain
        })
        if ($domain.Count -ne 1) {
            throw (
                "Authenticated tenant does not contain required verified domain " +
                "'$ExpectedVerifiedDomain'."
            )
        }
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

    $managedIdentitySp = Get-ServicePrincipalByAppId -AppId $identity.clientId
    $assignmentsUri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$($managedIdentitySp.id)/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    $assignments = Invoke-GraphGet -Uri $assignmentsUri
    $existingRole = @($assignments.value | Where-Object {
        $_.resourceId -eq $graphSp.id -and $_.appRoleId -eq $sitesSelectedRole.id
    })
    if ($existingRole.Count -ne 1) {
        throw (
            "Expected exactly one Sites.Selected app-role assignment for managed identity " +
            "'$ManagedIdentityName'; found $($existingRole.Count)."
        )
    }

    $siteUri = (
        "https://graph.microsoft.com/v1.0/sites/${SharePointHostname}:${SitePath}?" +
        "`$select=id,displayName,webUrl"
    )
    $site = Invoke-GraphGet -Uri $siteUri
    if (-not $site.id -or -not $site.webUrl) {
        throw 'SharePoint site could not be resolved from the supplied hostname and site path.'
    }

    $permissions = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$($site.id)/permissions?" +
        "`$select=id,roles,grantedToIdentities,grantedToIdentitiesV2"
    )
    $siteGrants = @($permissions.value | Where-Object {
        @(Get-PermissionApplicationIds -Permission $_) -contains $identity.clientId
    })
    if ($siteGrants.Count -ne 1) {
        throw (
            "Expected exactly one site-level permission for managed identity '$ManagedIdentityName'; " +
            "found $($siteGrants.Count)."
        )
    }

    $roles = @($siteGrants[0].roles)
    if ($roles.Count -ne 1 -or $roles[0] -ne $ExpectedSiteRole) {
        throw (
            "Managed identity site grant role(s) '$($roles -join ',')' do not match expected " +
            "role '$ExpectedSiteRole'."
        )
    }

    [pscustomobject]@{
        qualification = 'pass'
        mutationPerformed = $false
        tenantId = $context.TenantId
        tenantDisplayName = $tenant.displayName
        verifiedDomain = $ExpectedVerifiedDomain
        operatorAccount = $context.Account
        managedIdentityName = $ManagedIdentityName
        managedIdentityResourceId = $identity.id
        managedIdentityClientId = $identity.clientId
        managedIdentityPrincipalId = $identity.principalId
        sitesSelectedAppRoleId = $sitesSelectedRole.id
        sitesSelectedAssignmentCount = $existingRole.Count
        sharePointSiteId = $site.id
        sharePointSiteUrl = $site.webUrl
        sharePointSiteRole = $roles[0]
        sharePointPermissionCount = $siteGrants.Count
    } | ConvertTo-Json -Depth 4
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
