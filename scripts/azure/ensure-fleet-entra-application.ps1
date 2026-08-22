[CmdletBinding()]
param(
    [string]$DisplayName = 'ETS Fleet Control Plane',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [string[]]$RequiredTags = @(
        'ets:component=fleet',
        'ets:environment=live',
        'ets:owner=lantern-protocol'
    ),

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$requiredScopes = @('User.Read', 'Application.Read.All')
if ($Apply) {
    $requiredScopes = @('User.Read', 'Application.ReadWrite.All')
}

$expectedRoles = @(
    [ordered]@{
        id = '19292461-7726-5197-acd4-6da5cf9d5440'
        allowedMemberTypes = @('User')
        description = 'Read authorized Fleet control-plane objects.'
        displayName = 'Fleet Viewer'
        isEnabled = $true
        value = 'Fleet.Viewer'
    },
    [ordered]@{
        id = 'b1c406fc-6d94-5397-a37d-7b23192f052f'
        allowedMemberTypes = @('User')
        description = 'Perform bounded Fleet operational mutations.'
        displayName = 'Fleet Operator'
        isEnabled = $true
        value = 'Fleet.Operator'
    },
    [ordered]@{
        id = 'cd7b83d7-7fbe-5b30-811d-5b6b8fa79fb4'
        allowedMemberTypes = @('User')
        description = 'Perform step-up protected Fleet trust mutations.'
        displayName = 'Fleet Security Administrator'
        isEnabled = $true
        value = 'Fleet.SecurityAdmin'
    }
)

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or available on PATH."
    }
}

function Invoke-GraphGet {
    param([Parameter(Mandatory = $true)][string]$Uri)

    return Invoke-MgGraphRequest -Method GET -Uri $Uri -OutputType PSObject
}

function Get-FleetApplications {
    param([Parameter(Mandatory = $true)][string]$Name)

    $escapedName = $Name.Replace("'", "''")
    $filter = [uri]::EscapeDataString("displayName eq '$escapedName'")
    $uri = (
        "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&" +
        "`$select=id,appId,displayName,signInAudience,tags,appRoles,api,web," +
        "passwordCredentials,keyCredentials"
    )
    $response = Invoke-GraphGet -Uri $uri
    return @($response.value)
}

function Get-FleetServicePrincipals {
    param([Parameter(Mandatory = $true)][string]$ApplicationId)

    $filter = [uri]::EscapeDataString("appId eq '$ApplicationId'")
    $uri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter&" +
        "`$select=id,appId,displayName,servicePrincipalType,accountEnabled,passwordCredentials,keyCredentials"
    )
    $response = Invoke-GraphGet -Uri $uri
    return @($response.value)
}

function Get-NormalizedRoleContract {
    param([Parameter(Mandatory = $true)][object[]]$Roles)

    return @(
        $Roles |
            ForEach-Object {
                $memberTypes = @($_.allowedMemberTypes | ForEach-Object { [string]$_ })
                [pscustomobject]@{
                    id = ([string]$_.id).ToLowerInvariant()
                    allowedMemberTypes = @($memberTypes | Sort-Object)
                    description = [string]$_.description
                    displayName = [string]$_.displayName
                    isEnabled = [bool]$_.isEnabled
                    value = [string]$_.value
                }
            } |
            Sort-Object value
    )
}

function Test-RoleContractEqual {
    param(
        [Parameter(Mandatory = $true)][object[]]$Actual,
        [Parameter(Mandatory = $true)][object[]]$Expected
    )

    $actualJson = Get-NormalizedRoleContract -Roles $Actual | ConvertTo-Json -Depth 8 -Compress
    $expectedJson = Get-NormalizedRoleContract -Roles $Expected | ConvertTo-Json -Depth 8 -Compress
    return $actualJson -ceq $expectedJson
}

function Assert-NoReusableCredentials {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$ObjectType
    )

    if (@($Object.passwordCredentials).Count -ne 0) {
        throw "$ObjectType must not retain password credentials."
    }
    if (@($Object.keyCredentials).Count -ne 0) {
        throw "$ObjectType must not retain key credentials."
    }
}

function Assert-GovernedFleetApplication {
    param(
        [Parameter(Mandatory = $true)][object]$Application,
        [Parameter(Mandatory = $true)][string]$ExpectedDisplayName,
        [Parameter(Mandatory = $true)][string[]]$ExpectedTags
    )

    if ([string]$Application.displayName -ne $ExpectedDisplayName) {
        throw 'Resolved Fleet application display name changed during provisioning.'
    }
    if ([string]$Application.signInAudience -ne 'AzureADMyOrg') {
        throw 'Fleet application must remain single-tenant (AzureADMyOrg).'
    }

    Assert-NoReusableCredentials -Object $Application -ObjectType 'Fleet application'

    if ($null -ne $Application.api) {
        if (@($Application.api.oauth2PermissionScopes).Count -ne 0) {
            throw 'Fleet application must not expose delegated OAuth permission scopes.'
        }
        if (@($Application.api.preAuthorizedApplications).Count -ne 0) {
            throw 'Fleet application must not contain pre-authorized delegated clients.'
        }
        if (@($Application.api.knownClientApplications).Count -ne 0) {
            throw 'Fleet application must not contain known client applications.'
        }
    }

    $actualRoles = @($Application.appRoles)
    if ($actualRoles.Count -ne 0 -and -not (Test-RoleContractEqual -Actual $actualRoles -Expected $expectedRoles)) {
        throw 'Existing Fleet app roles differ from the governed role contract. Refusing implicit role migration.'
    }

    $actualTags = @($Application.tags | ForEach-Object { [string]$_ })
    $unexpectedTags = @($actualTags | Where-Object { $_ -like 'ets:*' -and $ExpectedTags -notcontains $_ })
    if ($unexpectedTags.Count -ne 0) {
        throw 'Existing Fleet application contains unexpected ETS governance tags.'
    }
}

function Test-FleetApplicationReady {
    param(
        [Parameter(Mandatory = $true)][object]$Application,
        [Parameter(Mandatory = $true)][string[]]$ExpectedTags
    )

    $actualTags = @($Application.tags | ForEach-Object { [string]$_ })
    foreach ($tag in $ExpectedTags) {
        if ($actualTags -notcontains $tag) {
            return $false
        }
    }
    if (-not (Test-RoleContractEqual -Actual @($Application.appRoles) -Expected $expectedRoles)) {
        return $false
    }
    if ($null -eq $Application.web) {
        return $false
    }
    if (
        $null -eq $Application.web.implicitGrantSettings -or
        $Application.web.implicitGrantSettings.enableIdTokenIssuance -ne $true
    ) {
        return $false
    }
    if ($Application.web.implicitGrantSettings.enableAccessTokenIssuance -eq $true) {
        return $false
    }
    return $true
}

function Assert-FleetServicePrincipal {
    param(
        [Parameter(Mandatory = $true)][object]$ServicePrincipal,
        [Parameter(Mandatory = $true)][string]$ExpectedApplicationId
    )

    if ([string]$ServicePrincipal.appId -ne $ExpectedApplicationId) {
        throw 'Fleet service principal appId does not match the governed application.'
    }
    if ([string]$ServicePrincipal.servicePrincipalType -ne 'Application') {
        throw 'Fleet service principal must use servicePrincipalType Application.'
    }
    if ($ServicePrincipal.accountEnabled -ne $true) {
        throw 'Fleet service principal is disabled.'
    }
    Assert-NoReusableCredentials -Object $ServicePrincipal -ObjectType 'Fleet service principal'
}

function Write-FleetResult {
    param(
        [Parameter(Mandatory = $true)][string]$TenantId,
        [Parameter(Mandatory = $true)][bool]$ApplicationReady,
        [Parameter(Mandatory = $true)][bool]$ServicePrincipalReady,
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [string]$ApplicationObjectId = '',
        [string]$ApplicationId = '',
        [string]$ServicePrincipalObjectId = ''
    )

    [pscustomobject]@{
        schemaVersion = 'ets.fleet.c3e.entra_bootstrap.v1'
        tenantId = $TenantId
        verifiedDomain = $ExpectedVerifiedDomain
        displayName = $DisplayName
        fleetApplicationObjectId = $ApplicationObjectId
        fleetClientId = $ApplicationId
        fleetServicePrincipalObjectId = $ServicePrincipalObjectId
        authAudience = $ApplicationId
        authIssuer = if ($ApplicationId) { "https://login.microsoftonline.com/$TenantId/v2.0" } else { '' }
        roleIds = [ordered]@{
            'Fleet.Viewer' = '19292461-7726-5197-acd4-6da5cf9d5440'
            'Fleet.Operator' = 'b1c406fc-6d94-5397-a37d-7b23192f052f'
            'Fleet.SecurityAdmin' = 'cd7b83d7-7fbe-5b30-811d-5b6b8fa79fb4'
        }
        applicationReady = $ApplicationReady
        servicePrincipalReady = $ServicePrincipalReady
        mutationRequired = $MutationRequired
        applyRequested = [bool]$Apply
        reusableCredentialRetained = $false
        delegatedBootstrap = $true
        githubGraphWriteRequired = $false
    } | ConvertTo-Json -Depth 8
}

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId) {
    throw 'Azure CLI is not signed in to a Microsoft Entra tenant.'
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
    $domain = @($tenant.verifiedDomains | Where-Object { $_.name -ieq $ExpectedVerifiedDomain })
    if ($domain.Count -ne 1) {
        throw "Authenticated tenant does not contain required verified domain '$ExpectedVerifiedDomain'."
    }

    $applications = @(Get-FleetApplications -Name $DisplayName)
    if ($applications.Count -gt 1) {
        throw 'Multiple applications use the governed Fleet display name. Refusing ambiguity.'
    }

    if ($applications.Count -eq 0) {
        if (-not $Apply) {
            Write-FleetResult `
                -TenantId $context.TenantId `
                -ApplicationReady $false `
                -ServicePrincipalReady $false `
                -MutationRequired $true
            return
        }

        $createBody = [ordered]@{
            displayName = $DisplayName
            signInAudience = 'AzureADMyOrg'
            tags = @($RequiredTags)
            appRoles = @($expectedRoles)
            web = @{
                implicitGrantSettings = @{
                    enableIdTokenIssuance = $true
                    enableAccessTokenIssuance = $false
                }
            }
        } | ConvertTo-Json -Depth 10
        Invoke-MgGraphRequest `
            -Method POST `
            -Uri 'https://graph.microsoft.com/v1.0/applications' `
            -Body $createBody `
            -ContentType 'application/json' `
            -OutputType PSObject | Out-Null
        $applications = @(Get-FleetApplications -Name $DisplayName)
        if ($applications.Count -ne 1) {
            throw 'Fleet application creation did not converge to exactly one governed application.'
        }
    }

    $application = $applications[0]
    Assert-GovernedFleetApplication `
        -Application $application `
        -ExpectedDisplayName $DisplayName `
        -ExpectedTags $RequiredTags

    $applicationReady = Test-FleetApplicationReady -Application $application -ExpectedTags $RequiredTags
    if (-not $applicationReady) {
        if (-not $Apply) {
            Write-FleetResult `
                -TenantId $context.TenantId `
                -ApplicationReady $false `
                -ServicePrincipalReady $false `
                -MutationRequired $true `
                -ApplicationObjectId ([string]$application.id) `
                -ApplicationId ([string]$application.appId)
            return
        }

        $updateBody = [ordered]@{
            tags = @($RequiredTags)
            appRoles = @($expectedRoles)
            web = @{
                redirectUris = @($application.web.redirectUris)
                homePageUrl = $application.web.homePageUrl
                logoutUrl = $application.web.logoutUrl
                implicitGrantSettings = @{
                    enableIdTokenIssuance = $true
                    enableAccessTokenIssuance = $false
                }
            }
        } | ConvertTo-Json -Depth 10
        Invoke-MgGraphRequest `
            -Method PATCH `
            -Uri "https://graph.microsoft.com/v1.0/applications/$($application.id)" `
            -Body $updateBody `
            -ContentType 'application/json' `
            -OutputType PSObject | Out-Null

        $applications = @(Get-FleetApplications -Name $DisplayName)
        if ($applications.Count -ne 1) {
            throw 'Fleet application update could not be re-read uniquely.'
        }
        $application = $applications[0]
        Assert-GovernedFleetApplication `
            -Application $application `
            -ExpectedDisplayName $DisplayName `
            -ExpectedTags $RequiredTags
        if (-not (Test-FleetApplicationReady -Application $application -ExpectedTags $RequiredTags)) {
            throw 'Fleet application did not converge to the governed role and ID-token contract.'
        }
    }

    $servicePrincipals = @(Get-FleetServicePrincipals -ApplicationId $application.appId)
    if ($servicePrincipals.Count -gt 1) {
        throw 'Multiple service principals resolve to the governed Fleet application ID.'
    }
    if ($servicePrincipals.Count -eq 0) {
        if (-not $Apply) {
            Write-FleetResult `
                -TenantId $context.TenantId `
                -ApplicationReady $true `
                -ServicePrincipalReady $false `
                -MutationRequired $true `
                -ApplicationObjectId ([string]$application.id) `
                -ApplicationId ([string]$application.appId)
            return
        }

        $spBody = @{ appId = [string]$application.appId } | ConvertTo-Json -Depth 4
        Invoke-MgGraphRequest `
            -Method POST `
            -Uri 'https://graph.microsoft.com/v1.0/servicePrincipals' `
            -Body $spBody `
            -ContentType 'application/json' `
            -OutputType PSObject | Out-Null

        for ($attempt = 1; $attempt -le 10; $attempt++) {
            $servicePrincipals = @(Get-FleetServicePrincipals -ApplicationId $application.appId)
            if ($servicePrincipals.Count -eq 1) {
                break
            }
            if ($servicePrincipals.Count -gt 1) {
                throw 'Fleet service principal creation converged to duplicate principals.'
            }
            if ($attempt -lt 10) {
                Start-Sleep -Seconds 2
            }
        }
    }

    if ($servicePrincipals.Count -ne 1) {
        throw 'Fleet service principal creation did not converge to exactly one principal.'
    }
    $servicePrincipal = $servicePrincipals[0]
    Assert-FleetServicePrincipal `
        -ServicePrincipal $servicePrincipal `
        -ExpectedApplicationId ([string]$application.appId)

    Write-FleetResult `
        -TenantId $context.TenantId `
        -ApplicationReady $true `
        -ServicePrincipalReady $true `
        -MutationRequired $false `
        -ApplicationObjectId ([string]$application.id) `
        -ApplicationId ([string]$application.appId) `
        -ServicePrincipalObjectId ([string]$servicePrincipal.id)
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
