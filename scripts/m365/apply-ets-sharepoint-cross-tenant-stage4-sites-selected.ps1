[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$MicrosoftResourceTenantId,

    [string]$ApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [string]$ExpectedOperatorAccount = 'shannon.bray@echomedia.ai',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'
$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'
$approvedApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant'
$approvedVerifiedDomain = 'echomedia.ai'
$approvedOperatorAccount = 'shannon.bray@echomedia.ai'
$graphApplicationId = '00000003-0000-0000-c000-000000000000'
$sitesSelectedRoleValue = 'Sites.Selected'
$requiredScopes = @(
    'Application.Read.All',
    'AppRoleAssignment.ReadWrite.All',
    'Organization.Read.All'
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
    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -cne $approvedResourceTenantId) {
        throw 'Microsoft Graph tenant does not match the approved EchoMedia resource tenant.'
    }
    if (-not $context.Account -or $context.Account -ine $approvedOperatorAccount) {
        throw 'Microsoft Graph operator does not match the approved EchoMedia operator.'
    }
    return $context
}

function Get-ServicePrincipalsByAppId {
    param([Parameter(Mandatory = $true)][string]$AppId)

    $filter = [uri]::EscapeDataString("appId eq '$AppId'")
    $response = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter&" +
        "`$select=id,appId,displayName,appRoles,accountEnabled,servicePrincipalType," +
        "appOwnerOrganizationId"
    )
    return @($response.value)
}

function Assert-ConnectorServicePrincipalShape {
    param([Parameter(Mandatory = $true)][object]$ServicePrincipal)

    if ($ServicePrincipal.appId -cne $approvedApplicationId) {
        throw 'Connector service principal appId does not match the approved application.'
    }
    if ($ServicePrincipal.displayName -cne $approvedApplicationDisplayName) {
        throw 'Connector service principal display name does not match the approved application.'
    }
    if ($ServicePrincipal.servicePrincipalType -cne 'Application') {
        throw 'Connector service principal is not an Application service principal.'
    }
    if ($ServicePrincipal.accountEnabled -ne $true) {
        throw 'Connector service principal is not enabled.'
    }
    if ($ServicePrincipal.appOwnerOrganizationId -cne $approvedDestinationTenantId) {
        throw 'Connector service principal is not owned by the approved destination tenant.'
    }
}

function Get-ConnectorAssignments {
    param([Parameter(Mandatory = $true)][string]$ServicePrincipalId)

    $response = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/servicePrincipals/$ServicePrincipalId/" +
        "appRoleAssignments?`$select=id,appRoleId,resourceId,principalId"
    )
    return @($response.value)
}

function Write-StageResult {
    param(
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [Parameter(Mandatory = $true)][bool]$MutationPerformed
    )

    [pscustomobject]@{
        mode = if ($Apply) { 'apply' } else { 'preview_only' }
        stage = 'resource_sites_selected_assignment'
        mutationRequired = $MutationRequired
        mutationPerformed = $MutationPerformed
        microsoftResourceTenantVerified = $true
        verifiedDomain = $approvedVerifiedDomain
        operatorAccountVerified = $true
        microsoftApplicationId = $approvedApplicationId
        graphApplicationId = $graphApplicationId
        graphRole = $sitesSelectedRoleValue
        graphPermissionAssigned = $MutationPerformed
        sharePointPermissionAssigned = $false
        publicEvidenceSafe = $false
    } | ConvertTo-Json -Depth 4
}

Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

if ($MicrosoftResourceTenantId -cne $approvedResourceTenantId) {
    throw 'MicrosoftResourceTenantId must match the approved EchoMedia resource tenant exactly.'
}
if ($ApplicationId -cne $approvedApplicationId) {
    throw 'ApplicationId must match the approved Stage 1 application exactly.'
}
if ($ExpectedVerifiedDomain -cne $approvedVerifiedDomain) {
    throw 'ExpectedVerifiedDomain must match the approved EchoMedia domain exactly.'
}
if ($ExpectedOperatorAccount -cne $approvedOperatorAccount) {
    throw 'ExpectedOperatorAccount must match the approved EchoMedia operator exactly.'
}

$connected = $false
try {
    Connect-MgGraph `
        -TenantId $approvedResourceTenantId `
        -Scopes $requiredScopes `
        -ContextScope Process `
        -NoWelcome
    $connected = $true
    Assert-GraphContext | Out-Null

    $organization = Invoke-GraphGet -Uri (
        'https://graph.microsoft.com/v1.0/organization?$select=id,verifiedDomains'
    )
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

    $connectorMatches = @(Get-ServicePrincipalsByAppId -AppId $approvedApplicationId)
    if ($connectorMatches.Count -ne 1) {
        throw 'EchoMedia enterprise application did not resolve uniquely.'
    }
    $connectorSp = $connectorMatches[0]
    Assert-ConnectorServicePrincipalShape -ServicePrincipal $connectorSp

    $graphMatches = @(Get-ServicePrincipalsByAppId -AppId $graphApplicationId)
    if ($graphMatches.Count -ne 1) {
        throw 'Microsoft Graph service principal did not resolve uniquely.'
    }
    $graphSp = $graphMatches[0]

    $sitesSelectedRoles = @($graphSp.appRoles | Where-Object {
        $_.value -ceq $sitesSelectedRoleValue -and
        $_.isEnabled -eq $true -and
        @($_.allowedMemberTypes) -contains 'Application'
    })
    if ($sitesSelectedRoles.Count -ne 1) {
        throw 'Microsoft Graph Sites.Selected application role did not resolve uniquely.'
    }
    $sitesSelectedRole = $sitesSelectedRoles[0]

    $assignments = @(Get-ConnectorAssignments -ServicePrincipalId ([string]$connectorSp.id))
    $selectedAssignments = @($assignments | Where-Object {
        $_.principalId -eq $connectorSp.id -and
        $_.resourceId -eq $graphSp.id -and
        $_.appRoleId -eq $sitesSelectedRole.id
    })

    if ($assignments.Count -gt 0) {
        if ($assignments.Count -ne 1 -or $selectedAssignments.Count -ne 1) {
            throw 'Connector enterprise application has an unexpected Graph permission set.'
        }
        Write-StageResult -MutationRequired $false -MutationPerformed $false
        return
    }

    if (-not $Apply) {
        Write-StageResult -MutationRequired $true -MutationPerformed $false
        return
    }

    $assignmentBody = @{
        principalId = $connectorSp.id
        resourceId = $graphSp.id
        appRoleId = $sitesSelectedRole.id
    } | ConvertTo-Json -Depth 4

    Invoke-MgGraphRequest `
        -Method POST `
        -Uri "https://graph.microsoft.com/v1.0/servicePrincipals/$($graphSp.id)/appRoleAssignedTo" `
        -Body $assignmentBody `
        -ContentType 'application/json' `
        -OutputType PSObject | Out-Null

    $postAssignments = @(Get-ConnectorAssignments -ServicePrincipalId ([string]$connectorSp.id))
    $postSelectedAssignments = @($postAssignments | Where-Object {
        $_.principalId -eq $connectorSp.id -and
        $_.resourceId -eq $graphSp.id -and
        $_.appRoleId -eq $sitesSelectedRole.id
    })
    if ($postAssignments.Count -ne 1 -or $postSelectedAssignments.Count -ne 1) {
        throw 'Post-create verification did not resolve exactly the approved Sites.Selected assignment.'
    }

    Write-StageResult -MutationRequired $false -MutationPerformed $true
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
