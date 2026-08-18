[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$CoreApplicationId,

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$RoleId = '062e20df-6571-4fa3-ab90-e1f30cd360bd',

    [string]$RoleValue = 'evidence_producer',

    [string]$RoleDisplayName = 'ETS Evidence Producer',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$requiredScopes = @(
    'User.Read',
    'Application.ReadWrite.All'
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

function Get-CoreApplication {
    param([Parameter(Mandatory = $true)][string]$ApplicationId)

    $filter = [uri]::EscapeDataString("appId eq '$ApplicationId'")
    $uri = (
        "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&" +
        "`$select=id,appId,displayName,appRoles"
    )
    $response = Invoke-GraphGet -Uri $uri
    $matches = @($response.value)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one Core application for appId '$ApplicationId'."
    }
    return $matches[0]
}

function Assert-EvidenceProducerRole {
    param(
        [Parameter(Mandatory = $true)][object]$Application,
        [Parameter(Mandatory = $true)][string]$ExpectedRoleId,
        [Parameter(Mandatory = $true)][string]$ExpectedRoleValue
    )

    $matches = @($Application.appRoles | Where-Object {
        $_.value -eq $ExpectedRoleValue
    })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one '$ExpectedRoleValue' app role on the Core application."
    }

    $role = $matches[0]
    if ([string]$role.id -ne $ExpectedRoleId) {
        throw (
            "Core '$ExpectedRoleValue' role id '$($role.id)' differs from the governed " +
            "role id '$ExpectedRoleId'. Refusing implicit role-id migration."
        )
    }
    if ($role.isEnabled -ne $true) {
        throw "Core '$ExpectedRoleValue' app role is disabled."
    }
    if (@($role.allowedMemberTypes) -notcontains 'Application') {
        throw "Core '$ExpectedRoleValue' app role does not allow application principals."
    }
    return $role
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
            "'$ExpectedVerifiedDomain'. Refusing to modify the Core application."
        )
    }

    $application = Get-CoreApplication -ApplicationId $CoreApplicationId
    $existing = @($application.appRoles | Where-Object {
        $_.value -eq $RoleValue
    })

    $created = $false
    if ($existing.Count -eq 0) {
        if ($Apply) {
            $appRoles = [System.Collections.Generic.List[object]]::new()
            foreach ($role in @($application.appRoles)) {
                $appRoles.Add(@{
                    allowedMemberTypes = @($role.allowedMemberTypes)
                    description = [string]$role.description
                    displayName = [string]$role.displayName
                    id = [string]$role.id
                    isEnabled = [bool]$role.isEnabled
                    value = [string]$role.value
                })
            }
            $appRoles.Add(@{
                allowedMemberTypes = @('Application')
                description = 'Create and relay ETS evidence within server-authorized scope.'
                displayName = $RoleDisplayName
                id = $RoleId
                isEnabled = $true
                value = $RoleValue
            })

            $body = @{
                appRoles = $appRoles.ToArray()
            } | ConvertTo-Json -Depth 8
            Invoke-MgGraphRequest `
                -Method PATCH `
                -Uri "https://graph.microsoft.com/v1.0/applications/$($application.id)" `
                -Body $body `
                -ContentType 'application/json' `
                -OutputType PSObject | Out-Null
            $created = $true
            $application = Get-CoreApplication -ApplicationId $CoreApplicationId
            $role = Assert-EvidenceProducerRole `
                -Application $application `
                -ExpectedRoleId $RoleId `
                -ExpectedRoleValue $RoleValue
        }
        else {
            [pscustomobject]@{
                verifiedDomain = $ExpectedVerifiedDomain
                coreApplicationId = $CoreApplicationId
                roleValue = $RoleValue
                roleId = $RoleId
                roleReady = $false
                mutationRequired = $true
                applyRequested = $false
                reusableCredentialRetained = $false
            } | ConvertTo-Json -Depth 4
            return
        }
    }
    elseif ($existing.Count -eq 1) {
        $role = Assert-EvidenceProducerRole `
            -Application $application `
            -ExpectedRoleId $RoleId `
            -ExpectedRoleValue $RoleValue
    }
    else {
        throw "Duplicate '$RoleValue' app roles were found on the Core application."
    }

    [pscustomobject]@{
        verifiedDomain = $ExpectedVerifiedDomain
        coreApplicationId = $CoreApplicationId
        roleValue = $RoleValue
        roleId = [string]$role.id
        roleReady = $true
        roleCreated = $created
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
