[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateLength(1, 128)]
    [string]$EtsTenantId,

    [Parameter(Mandatory = $true)]
    [ValidateLength(1, 128)]
    [string]$EtsWorkspaceId,

    [Parameter(Mandatory = $true)]
    [ValidateLength(1, 512)]
    [string]$SharePointDriveId,

    [string]$Repository = 'ShannonBrayNC/ETS',

    [string]$EnvironmentName = 'ets-azure-q1',

    [string]$ResourceGroup = 'rg-ets-live-eastus',

    [string]$ManagedIdentityName = 'ets-o23bf2d6oq44s-gw-id',

    [string]$CoreDisplayName = 'ETS Core Live API',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [switch]$Apply,

    [switch]$DispatchDeployment
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or available on PATH."
    }
}

function Invoke-IdentityOrchestration {
    param([Parameter(Mandatory = $true)][string]$Path)

    $parameters = @{
        EtsTenantId = $EtsTenantId.Trim()
        EtsWorkspaceId = $EtsWorkspaceId.Trim()
        ResourceGroup = $ResourceGroup
        ManagedIdentityName = $ManagedIdentityName
        CoreDisplayName = $CoreDisplayName
        ExpectedVerifiedDomain = $ExpectedVerifiedDomain
    }
    if ($Apply) {
        $parameters.Apply = $true
    }

    $raw = (& $Path @parameters | Out-String).Trim()
    if (-not $raw) {
        throw 'Live Core/Gateway identity orchestration returned no JSON.'
    }
    try {
        return $raw | ConvertFrom-Json -Depth 16
    }
    catch {
        throw 'Live Core/Gateway identity orchestration returned invalid JSON.'
    }
}

function Set-ProtectedEnvironmentSecret {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if (-not $Value) {
        throw "Refusing to write empty protected environment secret '$Name'."
    }

    $Value | gh secret set $Name `
        --env $EnvironmentName `
        --repo $Repository | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set protected environment secret '$Name'."
    }
}

function Write-BoundedStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][bool]$MutationRequired,
        [Parameter(Mandatory = $true)][bool]$SecretsReady,
        [Parameter(Mandatory = $true)][bool]$DeploymentDispatched
    )

    [pscustomobject]@{
        stage = $Stage
        repository = $Repository
        environment = $EnvironmentName
        resourceGroup = $ResourceGroup
        gatewayManagedIdentityName = $ManagedIdentityName
        verifiedDomain = $ExpectedVerifiedDomain
        identityAuthorizationReady = ($Stage -ne 'identity_authorization_incomplete')
        protectedDeploymentSecretsReady = $SecretsReady
        deploymentDispatched = $DeploymentDispatched
        mutationRequired = $MutationRequired
        applyRequested = [bool]$Apply
        reusableCredentialRetained = $false
        customerIdentifiersRetained = $false
        publicEvidenceSafe = $true
    } | ConvertTo-Json -Depth 5
}

Assert-Command -Name 'az'
Assert-Command -Name 'gh'

$etsTenant = $EtsTenantId.Trim()
$etsWorkspace = $EtsWorkspaceId.Trim()
$sharePointDrive = $SharePointDriveId.Trim()
if (-not $etsTenant -or -not $etsWorkspace -or -not $sharePointDrive) {
    throw 'ETS tenant, workspace, and SharePoint drive values must be non-empty after trimming.'
}
if ($DispatchDeployment -and -not $Apply) {
    throw '-DispatchDeployment requires -Apply.'
}

$activeTenant = (az account show --query tenantId -o tsv).Trim()
if ($LASTEXITCODE -ne 0 -or -not $activeTenant) {
    throw 'Azure CLI is not signed in to the target Azure tenant.'
}

gh auth status --active --hostname github.com *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'GitHub CLI is not authenticated to github.com.'
}

$resolvedRepository = (gh repo view $Repository --json nameWithOwner --jq '.nameWithOwner').Trim()
if ($LASTEXITCODE -ne 0 -or $resolvedRepository -cne $Repository) {
    throw "GitHub CLI repository resolution did not match '$Repository'."
}

$identityScript = Join-Path $PSScriptRoot 'provision-live-core-gateway-identity.ps1'
if (-not (Test-Path -LiteralPath $identityScript -PathType Leaf)) {
    throw "Required identity orchestration script was not found: $identityScript"
}

$identity = Invoke-IdentityOrchestration -Path $identityScript
if ([string]$identity.stage -ne 'ready_for_protected_deployment') {
    Write-BoundedStatus `
        -Stage 'identity_authorization_incomplete' `
        -MutationRequired ([bool]$identity.mutationRequired) `
        -SecretsReady $false `
        -DeploymentDispatched $false
    return
}

if ([string]$identity.resourceGroup -ne $ResourceGroup) {
    throw 'Identity orchestration returned an unexpected Azure resource group.'
}
if ([string]$identity.gatewayManagedIdentityName -ne $ManagedIdentityName) {
    throw 'Identity orchestration returned an unexpected Gateway managed identity.'
}
if ([string]$identity.verifiedDomain -ine $ExpectedVerifiedDomain) {
    throw 'Identity orchestration returned an unexpected verified domain.'
}
if ([string]$identity.etsTenantId -ne $etsTenant) {
    throw 'Identity orchestration returned a different ETS tenant scope.'
}
if ([string]$identity.etsWorkspaceId -ne $etsWorkspace) {
    throw 'Identity orchestration returned a different ETS workspace scope.'
}
if ([string]$identity.authTenantId -ine $activeTenant) {
    throw 'Identity auth tenant does not match the active Azure tenant.'
}
if (-not [bool]$identity.authorizationReady -or -not [bool]$identity.scopeMapReady) {
    throw 'Identity orchestration did not converge authorization and scope-map readiness.'
}
if ([bool]$identity.reusableCredentialRetained) {
    throw 'Identity orchestration unexpectedly reported reusable credential retention.'
}

$audience = ([string]$identity.authAudience).TrimEnd('/')
$coreScope = [string]$identity.coreScope
if (-not $audience.StartsWith('api://', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Core authentication audience must use the governed api:// identifier.'
}
if ($coreScope -ne "$audience/.default") {
    throw 'Core managed-identity scope must equal <audience>/.default.'
}

if (-not $Apply) {
    Write-BoundedStatus `
        -Stage 'ready_to_write_protected_secrets' `
        -MutationRequired $true `
        -SecretsReady $false `
        -DeploymentDispatched $false
    return
}

$secretValues = [ordered]@{
    ETS_LIVE_CORE_SCOPE = $coreScope
    ETS_LIVE_AUTH_AUDIENCE = [string]$identity.authAudience
    ETS_LIVE_AUTH_ISSUER = [string]$identity.authIssuer
    ETS_LIVE_AUTH_JWKS_URL = [string]$identity.authJwksUrl
    ETS_LIVE_AUTH_TENANT_ID = [string]$identity.authTenantId
    ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON = [string]$identity.authAppScopeMapJson
    ETS_LIVE_TENANT_ID = $etsTenant
    ETS_LIVE_WORKSPACE_ID = $etsWorkspace
    ETS_LIVE_MICROSOFT_TENANT_ID = $activeTenant
    ETS_LIVE_SHAREPOINT_DRIVE_ID = $sharePointDrive
}

foreach ($entry in $secretValues.GetEnumerator()) {
    Set-ProtectedEnvironmentSecret -Name $entry.Key -Value ([string]$entry.Value)
}

$requiredSecretNames = @($secretValues.Keys | Sort-Object)
$listedNames = @(
    gh secret list `
        --env $EnvironmentName `
        --repo $Repository `
        --json name `
        --jq '.[].name'
)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to verify protected deployment secret names after write.'
}
foreach ($name in $requiredSecretNames) {
    if ($listedNames -notcontains $name) {
        throw "Protected deployment environment is missing expected secret '$name'."
    }
}

$dispatched = $false
if ($DispatchDeployment) {
    gh workflow run live-core-gateway-deployment.yml `
        --repo $Repository `
        --ref main | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to dispatch the protected persistent Core/Gateway deployment workflow.'
    }
    $dispatched = $true
}

Write-BoundedStatus `
    -Stage 'protected_deployment_secrets_ready' `
    -MutationRequired $false `
    -SecretsReady $true `
    -DeploymentDispatched $dispatched
