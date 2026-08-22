[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$SharePointManagedIdentityName,

    [Parameter(Mandatory = $true)]
    [string]$DirectoryManagedIdentityName,

    [Parameter(Mandatory = $true)]
    [string]$PurviewManagedIdentityName,

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$microsoftGraphApplicationId = '00000003-0000-0000-c000-000000000000'
$officeManagementApplicationId = 'c5393580-f805-4401-95e8-94b7a6ef2fc2'
$directoryRoleValues = @('User.Read.All', 'Group.Read.All')
$purviewRoleValues = @('ActivityFeed.Read')
$requiredScopes = [System.Collections.Generic.List[string]]::new()
$requiredScopes.Add('User.Read')
$requiredScopes.Add('Application.Read.All')
if ($Apply) {
    $requiredScopes.Add('AppRoleAssignment.ReadWrite.All')
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

function Invoke-GraphCollection {
    param([Parameter(Mandatory = $true)][string]$Uri)

    $items = [System.Collections.Generic.List[object]]::new()
    $next = $Uri
    for ($page = 1; $page -le 20; $page++) {
        $response = Invoke-GraphGet -Uri $next
        foreach ($item in @($response.value)) {
            $items.Add($item)
        }
        $nextLinkProperty = $response.PSObject.Properties['@odata.nextLink']
        if ($null -eq $nextLinkProperty) {
            return $items.ToArray()
        }
        $next = [string]$nextLinkProperty.Value
        if ([string]::IsNullOrWhiteSpace($next)) {
            return $items.ToArray()
        }
    }
    throw 'Microsoft Graph collection exceeded the bounded pagination limit.'
}

function Get-ServicePrincipalByAppId {
    param([Parameter(Mandatory = $true)][string]$AppId)

    $filter = [uri]::EscapeDataString("appId eq '$AppId'")
    $uri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter&" +
        "`$select=id,appId,displayName,servicePrincipalType,accountEnabled,appRoles"
    )
    $matches = @(Invoke-GraphCollection -Uri $uri)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one service principal for appId '$AppId'."
    }
    if ($matches[0].accountEnabled -ne $true) {
        throw "Service principal for appId '$AppId' is disabled."
    }
    return $matches[0]
}

function Get-ManagedIdentityBinding {
    param([Parameter(Mandatory = $true)][string]$Name)

    $identity = az identity show `
        --resource-group $ResourceGroup `
        --name $Name `
        --output json | ConvertFrom-Json
    if (-not $identity.clientId -or -not $identity.principalId -or -not $identity.id) {
        throw "Managed identity '$Name' omitted required identity metadata."
    }

    $servicePrincipal = $null
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            $servicePrincipal = Get-ServicePrincipalByAppId -AppId $identity.clientId
            break
        }
        catch {
            if ($attempt -eq 10) {
                throw
            }
            Start-Sleep -Seconds 3
        }
    }
    if ($null -eq $servicePrincipal) {
        throw "Managed identity '$Name' service principal is unavailable."
    }
    if ([string]$servicePrincipal.id -ne [string]$identity.principalId) {
        throw (
            "Managed identity '$Name' service-principal object id differs from its Azure " +
            'principalId.'
        )
    }
    if ([string]$servicePrincipal.servicePrincipalType -ne 'ManagedIdentity') {
        throw "Managed identity '$Name' did not resolve to servicePrincipalType ManagedIdentity."
    }
    return [pscustomobject]@{
        resourceId = [string]$identity.id
        clientId = [string]$identity.clientId
        principalId = [string]$identity.principalId
        servicePrincipal = $servicePrincipal
    }
}

function Get-RequiredAppRole {
    param(
        [Parameter(Mandatory = $true)][object]$ResourceServicePrincipal,
        [Parameter(Mandatory = $true)][string]$RoleValue
    )

    $roles = @($ResourceServicePrincipal.appRoles | Where-Object {
        [string]$_.value -ceq $RoleValue -and
        $_.isEnabled -eq $true -and
        @($_.allowedMemberTypes) -contains 'Application'
    })
    if ($roles.Count -ne 1) {
        throw (
            "Resource app '$($ResourceServicePrincipal.appId)' does not expose exactly one " +
            "enabled application role '$RoleValue'."
        )
    }
    if (-not $roles[0].id) {
        throw "Resource app role '$RoleValue' omitted its immutable role id."
    }
    return [pscustomobject]@{
        resourceId = [string]$ResourceServicePrincipal.id
        resourceAppId = [string]$ResourceServicePrincipal.appId
        appRoleId = [string]$roles[0].id
        roleValue = $RoleValue
    }
}

function Get-PrincipalAssignments {
    param([Parameter(Mandatory = $true)][string]$PrincipalId)

    $uri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$PrincipalId/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    return @(Invoke-GraphCollection -Uri $uri)
}

function Assert-ExactAssignmentBoundary {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalId,
        [Parameter(Mandatory = $true)][object[]]$Expected
    )

    $assignments = @(Get-PrincipalAssignments -PrincipalId $PrincipalId)
    foreach ($assignment in $assignments) {
        $matches = @($Expected | Where-Object {
            [string]$_.resourceId -eq [string]$assignment.resourceId -and
            [string]$_.appRoleId -eq [string]$assignment.appRoleId
        })
        if ($matches.Count -ne 1) {
            throw (
                "Managed identity '$PrincipalId' has an unexpected application permission. " +
                'Refusing implicit permission broadening or normalization.'
            )
        }
    }

    $missing = [System.Collections.Generic.List[object]]::new()
    foreach ($expectedRole in $Expected) {
        $matches = @($assignments | Where-Object {
            [string]$_.resourceId -eq [string]$expectedRole.resourceId -and
            [string]$_.appRoleId -eq [string]$expectedRole.appRoleId
        })
        if ($matches.Count -gt 1) {
            throw (
                "Managed identity '$PrincipalId' has a duplicate " +
                "'$($expectedRole.roleValue)' assignment."
            )
        }
        if ($matches.Count -eq 0) {
            $missing.Add($expectedRole)
        }
    }
    return $missing.ToArray()
}

function Add-AppRoleAssignment {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalId,
        [Parameter(Mandatory = $true)][object]$Role
    )

    $body = @{
        principalId = $PrincipalId
        resourceId = $Role.resourceId
        appRoleId = $Role.appRoleId
    } | ConvertTo-Json -Depth 4
    Invoke-MgGraphRequest `
        -Method POST `
        -Uri "https://graph.microsoft.com/v1.0/servicePrincipals/$($Role.resourceId)/appRoleAssignedTo" `
        -Body $body `
        -ContentType 'application/json' `
        -OutputType PSObject | Out-Null
}

function New-IdentityStatus {
    param(
        [Parameter(Mandatory = $true)][object]$Binding,
        [Parameter(Mandatory = $true)][object[]]$Roles,
        [Parameter(Mandatory = $true)][bool]$AssignmentReady,
        [Parameter(Mandatory = $true)][bool]$AssignmentCreated
    )

    return [pscustomobject]@{
        managedIdentityResourceId = $Binding.resourceId
        managedIdentityClientId = $Binding.clientId
        managedIdentityPrincipalId = $Binding.principalId
        resourceApplicationId = $Roles[0].resourceAppId
        roles = @($Roles | ForEach-Object {
            [pscustomobject]@{
                value = $_.roleValue
                id = $_.appRoleId
            }
        })
        assignmentReady = $AssignmentReady
        assignmentCreated = $AssignmentCreated
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
    $scopeArray = $requiredScopes.ToArray()
    Connect-MgGraph `
        -TenantId $azureAccount.tenantId `
        -Scopes $scopeArray `
        -ContextScope Process `
        -NoWelcome
    $connected = $true

    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -ne $azureAccount.tenantId) {
        throw 'Microsoft Graph tenant does not match the active Azure subscription tenant.'
    }

    $organization = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/organization?`$select=id,verifiedDomains"
    )
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1) {
        throw 'Expected exactly one Microsoft Entra organization in the authenticated tenant.'
    }
    $domain = @($organizations[0].verifiedDomains | Where-Object {
        $_.name -ieq $ExpectedVerifiedDomain
    })
    if ($domain.Count -ne 1) {
        throw (
            "Authenticated tenant does not contain required verified domain " +
            "'$ExpectedVerifiedDomain'. Refusing Microsoft connector permission mutation."
        )
    }

    $sharePoint = Get-ManagedIdentityBinding -Name $SharePointManagedIdentityName
    $directory = Get-ManagedIdentityBinding -Name $DirectoryManagedIdentityName
    $purview = Get-ManagedIdentityBinding -Name $PurviewManagedIdentityName
    if (
        $sharePoint.clientId -eq $directory.clientId -or
        $sharePoint.clientId -eq $purview.clientId -or
        $directory.clientId -eq $purview.clientId -or
        $sharePoint.principalId -eq $directory.principalId -or
        $sharePoint.principalId -eq $purview.principalId -or
        $directory.principalId -eq $purview.principalId -or
        $sharePoint.resourceId -eq $directory.resourceId -or
        $sharePoint.resourceId -eq $purview.resourceId -or
        $directory.resourceId -eq $purview.resourceId
    ) {
        throw 'SharePoint, directory, and Purview must use distinct user-assigned identities.'
    }

    $graphSp = Get-ServicePrincipalByAppId -AppId $microsoftGraphApplicationId
    $managementSp = Get-ServicePrincipalByAppId -AppId $officeManagementApplicationId
    $directoryRoles = @($directoryRoleValues | ForEach-Object {
        Get-RequiredAppRole -ResourceServicePrincipal $graphSp -RoleValue $_
    })
    $purviewRoles = @($purviewRoleValues | ForEach-Object {
        Get-RequiredAppRole -ResourceServicePrincipal $managementSp -RoleValue $_
    })

    $missingDirectory = @(Assert-ExactAssignmentBoundary `
        -PrincipalId $directory.principalId `
        -Expected $directoryRoles)
    $missingPurview = @(Assert-ExactAssignmentBoundary `
        -PrincipalId $purview.principalId `
        -Expected $purviewRoles)
    $mutationRequired = ($missingDirectory.Count + $missingPurview.Count) -gt 0

    if (-not $Apply -and $mutationRequired) {
        [pscustomobject]@{
            schemaVersion = 'ets.microsoft_p0_identity_bootstrap.preview.v1'
            verifiedDomain = $ExpectedVerifiedDomain
            sharePointManagedIdentityClientId = $sharePoint.clientId
            sharePointPermissionsChanged = $false
            directory = New-IdentityStatus `
                -Binding $directory `
                -Roles $directoryRoles `
                -AssignmentReady ($missingDirectory.Count -eq 0) `
                -AssignmentCreated $false
            purview = New-IdentityStatus `
                -Binding $purview `
                -Roles $purviewRoles `
                -AssignmentReady ($missingPurview.Count -eq 0) `
                -AssignmentCreated $false
            mutationRequired = $true
            applyRequested = $false
            reusableCredentialRetained = $false
            sourcePayloadRetained = $false
        } | ConvertTo-Json -Depth 6
        return
    }

    $directoryCreated = $false
    $purviewCreated = $false
    if ($Apply) {
        foreach ($role in $missingDirectory) {
            Add-AppRoleAssignment -PrincipalId $directory.principalId -Role $role
            $directoryCreated = $true
        }
        foreach ($role in $missingPurview) {
            Add-AppRoleAssignment -PrincipalId $purview.principalId -Role $role
            $purviewCreated = $true
        }
        $remainingDirectory = @(Assert-ExactAssignmentBoundary `
            -PrincipalId $directory.principalId `
            -Expected $directoryRoles)
        $remainingPurview = @(Assert-ExactAssignmentBoundary `
            -PrincipalId $purview.principalId `
            -Expected $purviewRoles)
        if ($remainingDirectory.Count -ne 0 -or $remainingPurview.Count -ne 0) {
            throw 'Microsoft connector application-permission assignments did not converge.'
        }
    }

    [pscustomobject]@{
        schemaVersion = 'ets.microsoft_p0_identity_bootstrap.result.v1'
        verifiedDomain = $ExpectedVerifiedDomain
        sharePointManagedIdentityClientId = $sharePoint.clientId
        sharePointPermissionsChanged = $false
        directory = New-IdentityStatus `
            -Binding $directory `
            -Roles $directoryRoles `
            -AssignmentReady $true `
            -AssignmentCreated $directoryCreated
        purview = New-IdentityStatus `
            -Binding $purview `
            -Roles $purviewRoles `
            -AssignmentReady $true `
            -AssignmentCreated $purviewCreated
        mutationRequired = $false
        applyRequested = [bool]$Apply
        reusableCredentialRetained = $false
        sourcePayloadRetained = $false
    } | ConvertTo-Json -Depth 8
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
