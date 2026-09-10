[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$ManagedIdentityName,

    [Parameter(Mandatory = $true)]
    [string]$DestinationAzureTenantId,

    [Parameter(Mandatory = $true)]
    [string]$MicrosoftResourceTenantId,

    [Parameter(Mandatory = $true)]
    [string]$MicrosoftApplicationId,

    [Parameter(Mandatory = $true)]
    [string]$SharePointHostname,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^/(sites|teams)/[^/]+')]
    [string]$SitePath,

    [ValidateSet('read')]
    [string]$ExpectedSiteRole = 'read',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [string]$ExpectedDestinationOperatorAccount,

    [string]$ExpectedResourceOperatorAccount
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$graphAppId = '00000003-0000-0000-c000-000000000000'
$tokenExchangeAudience = 'api://AzureADTokenExchange'
$destinationScopes = @('Application.Read.All')
$resourceScopes = @(
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
    $matches = @($response.value)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one service principal for appId '$AppId'."
    }
    return $matches[0]
}

function Get-ApplicationByAppId {
    param([Parameter(Mandatory = $true)][string]$AppId)

    $filter = [uri]::EscapeDataString("appId eq '$AppId'")
    $uri = (
        "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&" +
        "`$select=id,appId,displayName,signInAudience"
    )
    $response = Invoke-GraphGet -Uri $uri
    $matches = @($response.value)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one application registration for appId '$AppId'."
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

function Assert-GraphContext {
    param(
        [Parameter(Mandatory = $true)][string]$TenantId,
        [string]$ExpectedAccount
    )

    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -ne $TenantId) {
        throw "Microsoft Graph tenant does not match expected tenant '$TenantId'."
    }
    if ($ExpectedAccount) {
        if (-not $context.Account -or $context.Account -ine $ExpectedAccount) {
            throw (
                "Microsoft Graph operator '$($context.Account)' does not match expected operator " +
                "'$ExpectedAccount'."
            )
        }
    }
    return $context
}

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

if ($SharePointHostname -notmatch '\.sharepoint\.com$') {
    throw 'SharePointHostname must be a SharePoint Online hostname ending in .sharepoint.com.'
}
if ($DestinationAzureTenantId -eq $MicrosoftResourceTenantId) {
    throw 'Cross-tenant qualification requires distinct Azure and Microsoft resource tenants.'
}

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId) {
    throw 'Azure CLI is not signed in to an Entra tenant.'
}
if ($azureAccount.tenantId -ne $DestinationAzureTenantId) {
    throw (
        "Active Azure tenant '$($azureAccount.tenantId)' does not match expected destination " +
        "tenant '$DestinationAzureTenantId'."
    )
}

$identity = az identity show `
    --resource-group $ResourceGroup `
    --name $ManagedIdentityName `
    --output json | ConvertFrom-Json
if (-not $identity.clientId -or -not $identity.principalId -or -not $identity.id) {
    throw 'Managed identity response did not include clientId, principalId, and resource id.'
}

$destinationConnected = $false
try {
    Connect-MgGraph `
        -TenantId $DestinationAzureTenantId `
        -Scopes $destinationScopes `
        -ContextScope Process `
        -NoWelcome
    $destinationConnected = $true
    $destinationContext = Assert-GraphContext `
        -TenantId $DestinationAzureTenantId `
        -ExpectedAccount $ExpectedDestinationOperatorAccount

    $application = Get-ApplicationByAppId -AppId $MicrosoftApplicationId
    if ($application.signInAudience -ne 'AzureADMultipleOrgs') {
        throw 'Destination Microsoft application is not configured as a multitenant application.'
    }

    $credentials = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/applications/$($application.id)/" +
        "federatedIdentityCredentials?`$select=id,name,issuer,subject,audiences"
    )
    $federatedCredentials = @($credentials.value)
    if ($federatedCredentials.Count -ne 1) {
        throw (
            "Expected exactly one federated identity credential for the SharePoint application; " +
            "found $($federatedCredentials.Count)."
        )
    }

    $credential = $federatedCredentials[0]
    $expectedIssuer = "https://login.microsoftonline.com/$DestinationAzureTenantId/v2.0"
    $audiences = @($credential.audiences)
    if ($credential.issuer -cne $expectedIssuer) {
        throw 'Federated identity credential issuer does not match the destination tenant issuer.'
    }
    if ($credential.subject -cne $identity.principalId) {
        throw 'Federated identity credential subject does not match the destination UAMI principal ID.'
    }
    if ($audiences.Count -ne 1 -or $audiences[0] -cne $tokenExchangeAudience) {
        throw 'Federated identity credential audience is not the exact Azure AD token exchange audience.'
    }
}
finally {
    if ($destinationConnected) {
        Disconnect-MgGraph | Out-Null
    }
}

$resourceConnected = $false
try {
    Connect-MgGraph `
        -TenantId $MicrosoftResourceTenantId `
        -Scopes $resourceScopes `
        -ContextScope Process `
        -NoWelcome
    $resourceConnected = $true
    $resourceContext = Assert-GraphContext `
        -TenantId $MicrosoftResourceTenantId `
        -ExpectedAccount $ExpectedResourceOperatorAccount

    $organization = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/organization?`$select=id,displayName,verifiedDomains"
    )
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1) {
        throw 'Expected exactly one Microsoft Entra organization in the resource tenant.'
    }
    $tenant = $organizations[0]
    if ($tenant.id -ne $MicrosoftResourceTenantId) {
        throw 'Microsoft Graph organization id does not match the expected resource tenant.'
    }

    $domain = @($tenant.verifiedDomains | Where-Object {
        $_.name -ieq $ExpectedVerifiedDomain
    })
    if ($domain.Count -ne 1) {
        throw (
            "Authenticated Microsoft resource tenant does not contain required verified domain " +
            "'$ExpectedVerifiedDomain'."
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

    $connectorSp = Get-ServicePrincipalByAppId -AppId $MicrosoftApplicationId
    if ($connectorSp.servicePrincipalType -ne 'Application') {
        throw 'EchoMedia connector enterprise application has an unexpected service-principal type.'
    }
    if ($connectorSp.accountEnabled -ne $true) {
        throw 'EchoMedia connector enterprise application is disabled.'
    }
    if ($connectorSp.appOwnerOrganizationId -ne $DestinationAzureTenantId) {
        throw 'EchoMedia enterprise application is not owned by the destination Azure tenant.'
    }

    $assignments = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$($connectorSp.id)/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    $assignmentSet = @($assignments.value)
    $sitesSelectedAssignments = @($assignmentSet | Where-Object {
        $_.resourceId -eq $graphSp.id -and $_.appRoleId -eq $sitesSelectedRole.id
    })
    if ($sitesSelectedAssignments.Count -ne 1) {
        throw (
            "Expected exactly one Sites.Selected app-role assignment for the federated " +
            "SharePoint application; found $($sitesSelectedAssignments.Count)."
        )
    }
    if ($assignmentSet.Count -ne 1) {
        throw 'Federated SharePoint application has unexpected additional application permissions.'
    }

    $site = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/${SharePointHostname}:${SitePath}?" +
        "`$select=id,displayName,webUrl"
    )
    if (-not $site.id -or -not $site.webUrl) {
        throw 'SharePoint site could not be resolved from the supplied hostname and site path.'
    }

    $permissions = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$($site.id)/permissions?" +
        "`$select=id,roles,grantedToIdentities,grantedToIdentitiesV2"
    )
    $siteGrants = @($permissions.value | Where-Object {
        @(Get-PermissionApplicationIds -Permission $_) -contains $MicrosoftApplicationId
    })
    if ($siteGrants.Count -ne 1) {
        throw (
            "Expected exactly one site-level permission for the federated SharePoint " +
            "application; found $($siteGrants.Count)."
        )
    }

    $roles = @($siteGrants[0].roles)
    if ($roles.Count -ne 1 -or $roles[0] -ne $ExpectedSiteRole) {
        throw (
            "Federated SharePoint application site grant role(s) '$($roles -join ',')' do not " +
            "match expected role '$ExpectedSiteRole'."
        )
    }

    [pscustomobject]@{
        qualification = 'pass'
        mutationPerformed = $false
        destinationAzureTenantVerified = $true
        destinationManagedIdentityVerified = $true
        multitenantApplicationVerified = $true
        federatedIdentityCredentialVerified = $true
        microsoftResourceTenantVerified = $true
        enterpriseApplicationVerified = $true
        sitesSelectedVerified = $true
        exactSharePointSiteVerified = $true
        siteReadGrantVerified = $true
        destinationOperatorVerified = [bool]$ExpectedDestinationOperatorAccount
        resourceOperatorVerified = [bool]$ExpectedResourceOperatorAccount
        reusableCredentialRetained = $false
        sourcePayloadRetained = $false
    } | ConvertTo-Json -Depth 4
}
finally {
    if ($resourceConnected) {
        Disconnect-MgGraph | Out-Null
    }
}
