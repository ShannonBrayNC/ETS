[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$ManagedIdentityName,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$CoreApplicationId,

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$ExpectedRoleId = '062e20df-6571-4fa3-ab90-e1f30cd360bd',

    [string]$ExpectedRoleValue = 'evidence_producer',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$requiredScopes = @(
    'User.Read',
    'Application.Read.All',
    'AppRoleAssignment.ReadWrite.All'
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
        "`$select=id,appId,displayName,appRoles"
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

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

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
            "'$ExpectedVerifiedDomain'. Refusing to assign Core producer authority."
        )
    }

    $coreSp = Get-ServicePrincipalByAppId -AppId $CoreApplicationId
    $roles = @($coreSp.appRoles | Where-Object {
        $_.value -eq $ExpectedRoleValue -and
        [string]$_.id -eq $ExpectedRoleId -and
        $_.isEnabled -eq $true -and
        @($_.allowedMemberTypes) -contains 'Application'
    })
    if ($roles.Count -ne 1) {
        throw (
            "Core service principal does not expose exactly one enabled application role " +
            "'$ExpectedRoleValue' with governed id '$ExpectedRoleId'."
        )
    }
    $role = $roles[0]

    $gatewaySp = Get-ManagedIdentityServicePrincipal -ClientId $identity.clientId
    if ([string]$gatewaySp.id -ne [string]$identity.principalId) {
        throw (
            "Managed identity service-principal object id '$($gatewaySp.id)' differs from " +
            "Azure principalId '$($identity.principalId)'."
        )
    }

    $assignmentsUri = (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$($gatewaySp.id)/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    $assignments = Invoke-GraphGet -Uri $assignmentsUri
    $coreAssignments = @($assignments.value | Where-Object {
        $_.resourceId -eq $coreSp.id
    })
    $unexpected = @($coreAssignments | Where-Object {
        [string]$_.appRoleId -ne $ExpectedRoleId
    })
    if ($unexpected.Count -gt 0) {
        throw (
            'Gateway managed identity already has unexpected app-role authority on the ' +
            'Core service principal. Refusing to broaden or normalize permissions implicitly.'
        )
    }

    $existing = @($coreAssignments | Where-Object {
        [string]$_.appRoleId -eq $ExpectedRoleId
    })
    if ($existing.Count -gt 1) {
        throw 'Duplicate Core evidence_producer app-role assignments were found.'
    }

    $created = $false
    if ($existing.Count -eq 0) {
        if ($Apply) {
            $body = @{
                principalId = $gatewaySp.id
                resourceId = $coreSp.id
                appRoleId = $role.id
            } | ConvertTo-Json -Depth 4
            Invoke-MgGraphRequest `
                -Method POST `
                -Uri "https://graph.microsoft.com/v1.0/servicePrincipals/$($coreSp.id)/appRoleAssignedTo" `
                -Body $body `
                -ContentType 'application/json' `
                -OutputType PSObject | Out-Null
            $created = $true

            $assignments = Invoke-GraphGet -Uri $assignmentsUri
            $existing = @($assignments.value | Where-Object {
                $_.resourceId -eq $coreSp.id -and
                [string]$_.appRoleId -eq $ExpectedRoleId
            })
            if ($existing.Count -ne 1) {
                throw 'Core evidence_producer assignment did not converge to exactly one grant.'
            }
        }
        else {
            [pscustomobject]@{
                verifiedDomain = $ExpectedVerifiedDomain
                managedIdentityResourceId = $identity.id
                managedIdentityClientId = $identity.clientId
                coreApplicationId = $CoreApplicationId
                roleValue = $ExpectedRoleValue
                roleId = $ExpectedRoleId
                assignmentReady = $false
                mutationRequired = $true
                applyRequested = $false
                reusableCredentialRetained = $false
            } | ConvertTo-Json -Depth 4
            return
        }
    }

    [pscustomobject]@{
        verifiedDomain = $ExpectedVerifiedDomain
        managedIdentityResourceId = $identity.id
        managedIdentityClientId = $identity.clientId
        coreApplicationId = $CoreApplicationId
        roleValue = $ExpectedRoleValue
        roleId = $ExpectedRoleId
        assignmentReady = $true
        assignmentCreated = $created
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
