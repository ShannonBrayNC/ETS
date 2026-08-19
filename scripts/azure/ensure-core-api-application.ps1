[CmdletBinding()]
param(
    [string]$DisplayName = 'ETS Core Live API',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [string[]]$RequiredTags = @(
        'ets:component=core',
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

function Get-CoreApplicationCandidates {
    param([Parameter(Mandatory = $true)][string]$Name)

    $escapedName = $Name.Replace("'", "''")
    $filter = [uri]::EscapeDataString("displayName eq '$escapedName'")
    $uri = (
        "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&" +
        "`$select=id,appId,displayName,signInAudience,identifierUris,tags,appRoles,api," +
        "optionalClaims,passwordCredentials,keyCredentials"
    )
    $response = Invoke-GraphGet -Uri $uri
    return @($response.value)
}

function Get-CoreServicePrincipals {
    param([Parameter(Mandatory = $true)][string]$ApplicationId)

    $filter = [uri]::EscapeDataString("appId eq '$ApplicationId'")
    $uri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter&" +
        "`$select=id,appId,displayName,servicePrincipalType,accountEnabled"
    )
    $response = Invoke-GraphGet -Uri $uri
    return @($response.value)
}

function Get-CoreIdtypOptionalClaimState {
    param([Parameter(Mandatory = $true)][object]$Application)

    if (
        $Application.PSObject.Properties.Name -notcontains 'optionalClaims' -or
        $null -eq $Application.optionalClaims
    ) {
        return 'missing'
    }

    $optionalClaims = $Application.optionalClaims
    $idTokenClaims = @()
    $accessTokenClaims = @()
    $saml2TokenClaims = @()

    if ($optionalClaims.PSObject.Properties.Name -contains 'idToken') {
        $idTokenClaims = @($optionalClaims.idToken)
    }
    if ($optionalClaims.PSObject.Properties.Name -contains 'accessToken') {
        $accessTokenClaims = @($optionalClaims.accessToken)
    }
    if ($optionalClaims.PSObject.Properties.Name -contains 'saml2Token') {
        $saml2TokenClaims = @($optionalClaims.saml2Token)
    }

    if ($idTokenClaims.Count -ne 0 -or $saml2TokenClaims.Count -ne 0) {
        return 'unexpected'
    }
    if ($accessTokenClaims.Count -eq 0) {
        return 'missing'
    }
    if ($accessTokenClaims.Count -ne 1) {
        return 'unexpected'
    }

    $claim = $accessTokenClaims[0]
    if (
        $claim.PSObject.Properties.Name -notcontains 'name' -or
        [string]$claim.name -ne 'idtyp'
    ) {
        return 'unexpected'
    }
    if (
        $claim.PSObject.Properties.Name -contains 'source' -and
        $null -ne $claim.source -and
        [string]$claim.source
    ) {
        return 'unexpected'
    }
    if (
        $claim.PSObject.Properties.Name -contains 'essential' -and
        $claim.essential -eq $true
    ) {
        return 'unexpected'
    }
    if (
        $claim.PSObject.Properties.Name -contains 'additionalProperties' -and
        @($claim.additionalProperties).Count -ne 0
    ) {
        return 'unexpected'
    }

    return 'ready'
}

function Assert-GovernedCoreApplication {
    param(
        [Parameter(Mandatory = $true)][object]$Application,
        [Parameter(Mandatory = $true)][string]$ExpectedDisplayName,
        [Parameter(Mandatory = $true)][string[]]$ExpectedTags
    )

    if ([string]$Application.displayName -ne $ExpectedDisplayName) {
        throw 'Resolved Core application display name changed during provisioning.'
    }
    if ([string]$Application.signInAudience -ne 'AzureADMyOrg') {
        throw 'Core application must be single-tenant (AzureADMyOrg). Refusing implicit migration.'
    }

    $actualTags = @($Application.tags)
    foreach ($tag in $ExpectedTags) {
        if ($actualTags -notcontains $tag) {
            throw (
                "Existing Core application is missing governed tag '$tag'. " +
                'Refusing to adopt an unowned application implicitly.'
            )
        }
    }

    if (@($Application.passwordCredentials).Count -ne 0) {
        throw 'Core application must not retain password credentials.'
    }
    if (@($Application.keyCredentials).Count -ne 0) {
        throw 'Core application must not retain application key credentials.'
    }

    if ($null -ne $Application.api) {
        if (@($Application.api.oauth2PermissionScopes).Count -ne 0) {
            throw 'Core application must not expose delegated OAuth permission scopes.'
        }
        if (@($Application.api.preAuthorizedApplications).Count -ne 0) {
            throw 'Core application must not contain pre-authorized delegated clients.'
        }
        if (@($Application.api.knownClientApplications).Count -ne 0) {
            throw 'Core application must not contain known delegated client applications.'
        }
    }
}

function Assert-CoreApplicationReady {
    param([Parameter(Mandatory = $true)][object]$Application)

    $expectedIdentifierUri = "api://$($Application.appId)"
    $identifierUris = @($Application.identifierUris)
    if ($identifierUris.Count -ne 1 -or [string]$identifierUris[0] -ne $expectedIdentifierUri) {
        throw 'Core application identifier URI did not converge to api://<appId>.'
    }
    if ($null -eq $Application.api -or $Application.api.requestedAccessTokenVersion -ne 2) {
        throw 'Core application did not converge to requested access token version 2.'
    }
    if ((Get-CoreIdtypOptionalClaimState -Application $Application) -ne 'ready') {
        throw 'Core application did not converge to the governed idtyp access-token optional claim.'
    }
}

function Assert-CoreServicePrincipal {
    param(
        [Parameter(Mandatory = $true)][object]$ServicePrincipal,
        [Parameter(Mandatory = $true)][string]$ExpectedApplicationId
    )

    if ([string]$ServicePrincipal.appId -ne $ExpectedApplicationId) {
        throw 'Core service principal appId did not match the application registration.'
    }
    if ([string]$ServicePrincipal.servicePrincipalType -ne 'Application') {
        throw 'Core service principal must use servicePrincipalType Application.'
    }
    if ($ServicePrincipal.accountEnabled -ne $true) {
        throw 'Core service principal is disabled.'
    }
}

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId) {
    throw 'Azure CLI is not signed in to an Entra tenant.'
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
            "'$ExpectedVerifiedDomain'. Refusing to provision the ETS Core API application."
        )
    }

    $applications = @(Get-CoreApplicationCandidates -Name $DisplayName)
    if ($applications.Count -gt 1) {
        throw 'Multiple applications use the governed ETS Core display name. Refusing ambiguity.'
    }

    $applicationCreated = $false
    if ($applications.Count -eq 0) {
        if (-not $Apply) {
            [pscustomobject]@{
                verifiedDomain = $ExpectedVerifiedDomain
                displayName = $DisplayName
                applicationReady = $false
                servicePrincipalReady = $false
                mutationRequired = $true
                applyRequested = $false
                reusableCredentialRetained = $false
            } | ConvertTo-Json -Depth 4
            return
        }

        $createBody = @{
            displayName = $DisplayName
            signInAudience = 'AzureADMyOrg'
            tags = @($RequiredTags)
        } | ConvertTo-Json -Depth 6
        Invoke-MgGraphRequest `
            -Method POST `
            -Uri 'https://graph.microsoft.com/v1.0/applications' `
            -Body $createBody `
            -ContentType 'application/json' `
            -OutputType PSObject | Out-Null
        $applicationCreated = $true
        $applications = @(Get-CoreApplicationCandidates -Name $DisplayName)
        if ($applications.Count -ne 1) {
            throw 'Core application creation did not converge to exactly one governed application.'
        }
    }

    $application = $applications[0]
    Assert-GovernedCoreApplication `
        -Application $application `
        -ExpectedDisplayName $DisplayName `
        -ExpectedTags $RequiredTags

    $expectedIdentifierUri = "api://$($application.appId)"
    $identifierUris = @($application.identifierUris)
    $needsApiUpdate = $false
    if ($identifierUris.Count -eq 0) {
        $needsApiUpdate = $true
    }
    elseif ($identifierUris.Count -ne 1 -or [string]$identifierUris[0] -ne $expectedIdentifierUri) {
        throw 'Existing Core application has an unexpected identifier URI. Refusing implicit migration.'
    }
    if ($null -eq $application.api -or $application.api.requestedAccessTokenVersion -ne 2) {
        $needsApiUpdate = $true
    }

    $idtypClaimState = Get-CoreIdtypOptionalClaimState -Application $application
    if ($idtypClaimState -eq 'unexpected') {
        throw 'Existing Core application has unexpected optional token claims. Refusing implicit migration.'
    }
    if ($idtypClaimState -eq 'missing') {
        $needsApiUpdate = $true
    }

    if ($needsApiUpdate) {
        if (-not $Apply) {
            [pscustomobject]@{
                verifiedDomain = $ExpectedVerifiedDomain
                displayName = $DisplayName
                coreApplicationId = [string]$application.appId
                expectedIdentifierUri = $expectedIdentifierUri
                applicationReady = $false
                servicePrincipalReady = $false
                appOnlyTokenTypeClaimReady = $false
                mutationRequired = $true
                applyRequested = $false
                reusableCredentialRetained = $false
            } | ConvertTo-Json -Depth 4
            return
        }

        $updateBody = @{
            identifierUris = @($expectedIdentifierUri)
            api = @{
                requestedAccessTokenVersion = 2
            }
            optionalClaims = @{
                idToken = @()
                accessToken = @(
                    @{
                        name = 'idtyp'
                        source = $null
                        essential = $false
                        additionalProperties = @()
                    }
                )
                saml2Token = @()
            }
        } | ConvertTo-Json -Depth 8
        Invoke-MgGraphRequest `
            -Method PATCH `
            -Uri "https://graph.microsoft.com/v1.0/applications/$($application.id)" `
            -Body $updateBody `
            -ContentType 'application/json' `
            -OutputType PSObject | Out-Null

        $applications = @(Get-CoreApplicationCandidates -Name $DisplayName)
        if ($applications.Count -ne 1) {
            throw 'Core application update could not be re-read uniquely.'
        }
        $application = $applications[0]
        Assert-GovernedCoreApplication `
            -Application $application `
            -ExpectedDisplayName $DisplayName `
            -ExpectedTags $RequiredTags
        Assert-CoreApplicationReady -Application $application
    }
    else {
        Assert-CoreApplicationReady -Application $application
    }

    $servicePrincipals = @(Get-CoreServicePrincipals -ApplicationId $application.appId)
    if ($servicePrincipals.Count -gt 1) {
        throw 'Multiple service principals resolve to the ETS Core application ID.'
    }

    $servicePrincipalCreated = $false
    if ($servicePrincipals.Count -eq 0) {
        if (-not $Apply) {
            [pscustomobject]@{
                verifiedDomain = $ExpectedVerifiedDomain
                displayName = $DisplayName
                coreApplicationId = [string]$application.appId
                coreIdentifierUri = "api://$($application.appId)"
                coreScope = "api://$($application.appId)/.default"
                applicationReady = $true
                servicePrincipalReady = $false
                appOnlyTokenTypeClaimReady = $true
                mutationRequired = $true
                applyRequested = $false
                reusableCredentialRetained = $false
            } | ConvertTo-Json -Depth 4
            return
        }

        $spBody = @{
            appId = [string]$application.appId
        } | ConvertTo-Json -Depth 4
        Invoke-MgGraphRequest `
            -Method POST `
            -Uri 'https://graph.microsoft.com/v1.0/servicePrincipals' `
            -Body $spBody `
            -ContentType 'application/json' `
            -OutputType PSObject | Out-Null
        $servicePrincipalCreated = $true

        for ($attempt = 1; $attempt -le 10; $attempt++) {
            $servicePrincipals = @(Get-CoreServicePrincipals -ApplicationId $application.appId)
            if ($servicePrincipals.Count -eq 1) {
                break
            }
            if ($servicePrincipals.Count -gt 1) {
                throw 'Core service principal creation converged to duplicate principals.'
            }
            if ($attempt -lt 10) {
                Start-Sleep -Seconds 2
            }
        }
    }

    if ($servicePrincipals.Count -ne 1) {
        throw 'Core service principal creation did not converge to exactly one principal.'
    }
    $servicePrincipal = $servicePrincipals[0]
    Assert-CoreServicePrincipal `
        -ServicePrincipal $servicePrincipal `
        -ExpectedApplicationId $application.appId

    $identifierUri = "api://$($application.appId)"
    [pscustomobject]@{
        tenantId = $context.TenantId
        verifiedDomain = $ExpectedVerifiedDomain
        displayName = $DisplayName
        coreApplicationObjectId = [string]$application.id
        coreApplicationId = [string]$application.appId
        coreServicePrincipalObjectId = [string]$servicePrincipal.id
        coreIdentifierUri = $identifierUri
        coreScope = "$identifierUri/.default"
        authAudience = $identifierUri
        authIssuer = "https://login.microsoftonline.com/$($context.TenantId)/v2.0"
        authJwksUrl = "https://login.microsoftonline.com/$($context.TenantId)/discovery/v2.0/keys"
        requestedAccessTokenVersion = 2
        appOnlyTokenTypeClaim = 'idtyp'
        appOnlyTokenTypeClaimReady = $true
        applicationReady = $true
        servicePrincipalReady = $true
        applicationCreated = $applicationCreated
        servicePrincipalCreated = $servicePrincipalCreated
        mutationRequired = $false
        applyRequested = [bool]$Apply
        reusableCredentialRetained = $false
    } | ConvertTo-Json -Depth 4
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
