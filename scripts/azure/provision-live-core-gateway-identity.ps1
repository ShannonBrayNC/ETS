[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateLength(1, 128)]
    [string]$EtsTenantId,

    [Parameter(Mandatory = $true)]
    [ValidateLength(1, 128)]
    [string]$EtsWorkspaceId,

    [string]$ResourceGroup = 'rg-ets-live-eastus',

    [string]$ManagedIdentityName = 'ets-o23bf2d6oq44s-gw-id',

    [string]$CoreDisplayName = 'ETS Core Live API',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-JsonProvisioningScript {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][hashtable]$Parameters
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required provisioning script was not found: $Path"
    }

    $raw = (& $Path @Parameters | Out-String).Trim()
    if (-not $raw) {
        throw "Provisioning script returned no JSON: $Path"
    }

    try {
        return $raw | ConvertFrom-Json -Depth 16
    }
    catch {
        throw "Provisioning script returned invalid JSON: $Path"
    }
}

function Write-BoundedStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [string]$CoreApplicationId = ''
    )

    [pscustomobject]@{
        stage = $Stage
        verifiedDomain = $ExpectedVerifiedDomain
        resourceGroup = $ResourceGroup
        gatewayManagedIdentityName = $ManagedIdentityName
        etsTenantId = $EtsTenantId.Trim()
        etsWorkspaceId = $EtsWorkspaceId.Trim()
        coreApplicationId = $CoreApplicationId
        authorizationReady = $false
        scopeMapReady = $false
        mutationRequired = $MutationRequired
        applyRequested = [bool]$Apply
        reusableCredentialRetained = $false
        publicEvidenceSafe = $false
    } | ConvertTo-Json -Depth 5
}

$etsTenant = $EtsTenantId.Trim()
$etsWorkspace = $EtsWorkspaceId.Trim()
if (-not $etsTenant -or -not $etsWorkspace) {
    throw 'ETS tenant and workspace scope values must be non-empty after trimming.'
}

$coreAppScript = Join-Path $PSScriptRoot 'ensure-core-api-application.ps1'
$coreRoleScript = Join-Path $PSScriptRoot 'ensure-core-evidence-producer-app-role.ps1'
$assignmentScript = Join-Path $PSScriptRoot 'provision-gateway-core-evidence-producer.ps1'

$appParameters = @{
    DisplayName = $CoreDisplayName
    ExpectedVerifiedDomain = $ExpectedVerifiedDomain
}
if ($Apply) {
    $appParameters.Apply = $true
}
$app = Invoke-JsonProvisioningScript -Path $coreAppScript -Parameters $appParameters

if (-not $app.applicationReady -or -not $app.servicePrincipalReady) {
    Write-BoundedStatus `
        -Stage 'core_api_registration' `
        -MutationRequired ([bool]$app.mutationRequired) `
        -CoreApplicationId ([string]($app.coreApplicationId ?? ''))
    return
}

$coreApplicationId = [string]$app.coreApplicationId
if (-not $coreApplicationId) {
    throw 'Ready Core API registration did not return coreApplicationId.'
}

$roleParameters = @{
    CoreApplicationId = $coreApplicationId
    ExpectedVerifiedDomain = $ExpectedVerifiedDomain
}
if ($Apply) {
    $roleParameters.Apply = $true
}
$role = Invoke-JsonProvisioningScript -Path $coreRoleScript -Parameters $roleParameters

if ([string]$role.coreApplicationId -ne $coreApplicationId) {
    throw 'Core role provisioning returned a different application ID.'
}
if (-not $role.roleReady) {
    Write-BoundedStatus `
        -Stage 'core_evidence_producer_role' `
        -MutationRequired ([bool]$role.mutationRequired) `
        -CoreApplicationId $coreApplicationId
    return
}

$assignmentParameters = @{
    ResourceGroup = $ResourceGroup
    ManagedIdentityName = $ManagedIdentityName
    CoreApplicationId = $coreApplicationId
    ExpectedVerifiedDomain = $ExpectedVerifiedDomain
}
if ($Apply) {
    $assignmentParameters.Apply = $true
}
$assignment = Invoke-JsonProvisioningScript -Path $assignmentScript -Parameters $assignmentParameters

if ([string]$assignment.coreApplicationId -ne $coreApplicationId) {
    throw 'Gateway role assignment returned a different Core application ID.'
}
if (-not $assignment.assignmentReady) {
    Write-BoundedStatus `
        -Stage 'gateway_evidence_producer_assignment' `
        -MutationRequired ([bool]$assignment.mutationRequired) `
        -CoreApplicationId $coreApplicationId
    return
}

$gatewayClientId = [string]$assignment.managedIdentityClientId
if (-not $gatewayClientId) {
    throw 'Ready Gateway assignment did not return the managed identity client ID.'
}

$scopeMap = [ordered]@{}
$scopeMap[$gatewayClientId] = [ordered]@{
    tenant_id = $etsTenant
    workspace_id = $etsWorkspace
}
$scopeMapJson = $scopeMap | ConvertTo-Json -Depth 5 -Compress

if (-not $app.coreScope -or -not $app.authAudience -or -not $app.authIssuer -or -not $app.authJwksUrl) {
    throw 'Ready Core API registration did not return the complete hosted authentication contract.'
}

[pscustomobject]@{
    stage = 'ready_for_protected_deployment'
    verifiedDomain = $ExpectedVerifiedDomain
    resourceGroup = $ResourceGroup
    gatewayManagedIdentityName = $ManagedIdentityName
    gatewayManagedIdentityClientId = $gatewayClientId
    coreApplicationId = $coreApplicationId
    coreIdentifierUri = [string]$app.coreIdentifierUri
    coreScope = [string]$app.coreScope
    authAudience = [string]$app.authAudience
    authIssuer = [string]$app.authIssuer
    authJwksUrl = [string]$app.authJwksUrl
    authTenantId = [string]$app.tenantId
    etsTenantId = $etsTenant
    etsWorkspaceId = $etsWorkspace
    authAppScopeMapJson = $scopeMapJson
    coreApplicationReady = $true
    coreProducerRoleReady = $true
    gatewayProducerAssignmentReady = $true
    authorizationReady = $true
    scopeMapReady = $true
    mutationRequired = $false
    applyRequested = [bool]$Apply
    reusableCredentialRetained = $false
    publicEvidenceSafe = $false
} | ConvertTo-Json -Depth 6
