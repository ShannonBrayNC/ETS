[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationAzureTenantId,

    [Parameter(Mandatory = $true)]
    [string]$MicrosoftResourceTenantId,

    [string]$ResourceGroup = 'rg-ets-prod-eastus',

    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id',

    [string]$MicrosoftApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant',

    [string]$SharePointHostname = 'echomediaai.sharepoint.com',

    [ValidatePattern('^/(sites|teams)/[^/]+')]
    [string]$SitePath = '/sites/ETS',

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
$approvedSharePointHostname = 'echomediaai.sharepoint.com'
$approvedSitePath = '/sites/ETS'
$destinationScopes = @('Application.Read.All')
$resourceScopes = @(
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

function ConvertTo-ODataLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)

    return $Value.Replace("'", "''")
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

function Write-PreviewStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [string]$MicrosoftApplicationId = ''
    )

    [pscustomobject]@{
        mode = 'preview_only'
        stage = $Stage
        mutationRequired = $MutationRequired
        mutationPerformed = $false
        destinationAzureTenantVerified = $true
        destinationManagedIdentityVerified = $true
        managedIdentityName = $ManagedIdentityName
        microsoftApplicationId = $MicrosoftApplicationId
        sharePointHostname = $SharePointHostname
        sitePath = $SitePath
        expectedSiteRole = $ExpectedSiteRole
        reusableCredentialRetained = $false
        publicEvidenceSafe = $false
    } | ConvertTo-Json -Depth 5
}

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

if ($DestinationAzureTenantId -eq $MicrosoftResourceTenantId) {
    throw 'Cross-tenant preview requires distinct Azure and Microsoft resource tenants.'
}
if ($SharePointHostname -cne $approvedSharePointHostname) {
    throw 'SharePointHostname must match the approved EchoMedia SharePoint hostname exactly.'
}
if ($SitePath -cne $approvedSitePath) {
    throw 'SitePath must match the approved ETS SharePoint site path exactly.'
}

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId -or $azureAccount.tenantId -ne $DestinationAzureTenantId) {
    throw 'Active Azure tenant does not match the expected destination tenant.'
}

$identity = az identity show `
    --resource-group $ResourceGroup `
    --name $ManagedIdentityName `
    --output json | ConvertFrom-Json
if (-not $identity.principalId -or -not $identity.clientId -or -not $identity.id) {
    throw 'Destination managed identity did not return the required identity fields.'
}

$destinationConnected = $false
$applicationId = ''
try {
    Connect-MgGraph `
        -TenantId $DestinationAzureTenantId `
        -Scopes $destinationScopes `
        -ContextScope Process `
        -NoWelcome
    $destinationConnected = $true
    Assert-GraphContext `
        -TenantId $DestinationAzureTenantId `
        -ExpectedAccount $ExpectedDestinationOperatorAccount | Out-Null

    $displayNameLiteral = ConvertTo-ODataLiteral -Value $MicrosoftApplicationDisplayName
    $filter = [uri]::EscapeDataString("displayName eq '$displayNameLiteral'")
    $apps = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&" +
        "`$select=id,appId,displayName,signInAudience"
    )
    $matches = @($apps.value)
    if ($matches.Count -eq 0) {
        Write-PreviewStatus -Stage 'destination_multitenant_application' -MutationRequired $true
        return
    }
    if ($matches.Count -ne 1) {
        throw 'Destination application display name did not resolve uniquely.'
    }

    $application = $matches[0]
    $applicationId = [string]$application.appId
    if ($application.signInAudience -ne 'AzureADMultipleOrgs') {
        Write-PreviewStatus `
            -Stage 'destination_multitenant_application_configuration' `
            -MutationRequired $true `
            -MicrosoftApplicationId $applicationId
        return
    }

    $credentials = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/applications/$($application.id)/" +
        "federatedIdentityCredentials?`$select=id,name,issuer,subject,audiences"
    )
    $allCredentials = @($credentials.value)
    $expectedIssuer = "https://login.microsoftonline.com/$DestinationAzureTenantId/v2.0"
    $matchingCredentials = @($allCredentials | Where-Object {
        $audiences = @($_.audiences)
        $_.issuer -ceq $expectedIssuer -and
        $_.subject -ceq $identity.principalId -and
        $audiences.Count -eq 1 -and
        $audiences[0] -ceq $tokenExchangeAudience
    })
    if ($matchingCredentials.Count -eq 0 -and $allCredentials.Count -eq 0) {
        Write-PreviewStatus `
            -Stage 'destination_federated_identity_credential' `
            -MutationRequired $true `
            -MicrosoftApplicationId $applicationId
        return
    }
    if ($matchingCredentials.Count -ne 1 -or $allCredentials.Count -ne 1) {
        throw 'Destination SharePoint application has an unexpected federated credential set.'
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
    Assert-GraphContext `
        -TenantId $MicrosoftResourceTenantId `
        -ExpectedAccount $ExpectedResourceOperatorAccount | Out-Null

    $organization = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/organization?`$select=id,verifiedDomains"
    )
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1 -or $organizations[0].id -ne $MicrosoftResourceTenantId) {
        throw 'Microsoft resource tenant organization could not be verified exactly.'
    }
    $domain = @($organizations[0].verifiedDomains | Where-Object {
        $_.name -ieq $ExpectedVerifiedDomain
    })
    if ($domain.Count -ne 1) {
        throw 'Microsoft resource tenant does not contain the expected verified domain.'
    }

    $connectorMatches = Get-ServicePrincipalByAppId -AppId $applicationId
    if ($connectorMatches.Count -eq 0) {
        Write-PreviewStatus `
            -Stage 'resource_enterprise_application' `
            -MutationRequired $true `
            -MicrosoftApplicationId $applicationId
        return
    }
    if ($connectorMatches.Count -ne 1) {
        throw 'EchoMedia enterprise application did not resolve uniquely.'
    }
    $connectorSp = $connectorMatches[0]
    if ($connectorSp.servicePrincipalType -ne 'Application' -or $connectorSp.accountEnabled -ne $true) {
        throw 'EchoMedia enterprise application is not an enabled application service principal.'
    }
    if ($connectorSp.appOwnerOrganizationId -ne $DestinationAzureTenantId) {
        throw 'EchoMedia enterprise application is not owned by the destination Azure tenant.'
    }

    $graphMatches = Get-ServicePrincipalByAppId -AppId $graphAppId
    if ($graphMatches.Count -ne 1) {
        throw 'Microsoft Graph service principal could not be resolved uniquely.'
    }
    $graphSp = $graphMatches[0]
    $sitesSelectedRoles = @($graphSp.appRoles | Where-Object {
        $_.value -eq 'Sites.Selected' -and
        $_.isEnabled -eq $true -and
        @($_.allowedMemberTypes) -contains 'Application'
    })
    if ($sitesSelectedRoles.Count -ne 1) {
        throw 'Microsoft Graph Sites.Selected role could not be resolved uniquely.'
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
    if ($selectedAssignments.Count -eq 0 -and $assignmentSet.Count -eq 0) {
        Write-PreviewStatus `
            -Stage 'resource_sites_selected_assignment' `
            -MutationRequired $true `
            -MicrosoftApplicationId $applicationId
        return
    }
    if ($selectedAssignments.Count -ne 1 -or $assignmentSet.Count -ne 1) {
        throw 'Federated SharePoint application has an unexpected Graph permission set.'
    }

    $site = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/${SharePointHostname}:${SitePath}?" +
        "`$select=id,webUrl"
    )
    if (-not $site.id -or -not $site.webUrl) {
        throw 'Approved SharePoint site could not be resolved.'
    }

    $permissions = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$($site.id)/permissions?" +
        "`$select=id,roles,grantedToIdentities,grantedToIdentitiesV2"
    )
    $siteGrants = @($permissions.value | Where-Object {
        @(Get-PermissionApplicationIds -Permission $_) -contains $applicationId
    })
    if ($siteGrants.Count -eq 0) {
        Write-PreviewStatus `
            -Stage 'sharepoint_site_read_grant' `
            -MutationRequired $true `
            -MicrosoftApplicationId $applicationId
        return
    }
    if ($siteGrants.Count -ne 1) {
        throw 'Federated SharePoint application has multiple site grants on the approved site.'
    }
    $roles = @($siteGrants[0].roles)
    if ($roles.Count -ne 1 -or $roles[0] -ne $ExpectedSiteRole) {
        throw 'Existing SharePoint site grant does not match the required read-only role.'
    }

    Write-PreviewStatus `
        -Stage 'ready_for_read_only_qualification' `
        -MutationRequired $false `
        -MicrosoftApplicationId $applicationId
}
finally {
    if ($resourceConnected) {
        Disconnect-MgGraph | Out-Null
    }
}
