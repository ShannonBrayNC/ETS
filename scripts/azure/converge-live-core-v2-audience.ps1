[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [guid]$CoreApplicationId,

    [string]$ResourceGroup = 'rg-ets-live-eastus',

    [string]$Repository = 'ShannonBrayNC/ETS',

    [string]$EnvironmentName = 'ets-azure-q1',

    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or available on PATH."
    }
}

function Get-ContainerEnvironmentMap {
    param([Parameter(Mandatory = $true)][object]$Container)

    $map = @{}
    foreach ($entry in @($Container.env)) {
        if ($null -eq $entry -or -not $entry.name) {
            continue
        }
        $map[[string]$entry.name] = [string]$entry.value
    }
    return $map
}

function Get-LiveCoreContainerApp {
    $apps = @(
        az containerapp list `
            --resource-group $ResourceGroup `
            --output json |
        ConvertFrom-Json
    )
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to list live Container Apps.'
    }

    $matches = [System.Collections.Generic.List[object]]::new()
    foreach ($app in $apps) {
        $containers = @($app.properties.template.containers)
        if ($containers.Count -ne 1) {
            continue
        }
        $envMap = Get-ContainerEnvironmentMap -Container $containers[0]
        if ($envMap['ETS_STORAGE_PROVIDER'] -eq 'azure_table') {
            $matches.Add($app)
        }
    }

    if ($matches.Count -ne 1) {
        throw "Expected exactly one live ETS Core Container App; found $($matches.Count)."
    }
    return $matches[0]
}

function Write-BoundedStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][bool]$RuntimeAudienceReady,
        [Parameter(Mandatory = $true)][bool]$ProtectedSecretWritten,
        [Parameter(Mandatory = $true)][bool]$MutationRequired
    )

    [pscustomobject]@{
        stage = $Stage
        resourceGroup = $ResourceGroup
        environment = $EnvironmentName
        runtimeAudienceReady = $RuntimeAudienceReady
        protectedAudienceSecretWritten = $ProtectedSecretWritten
        mutationRequired = $MutationRequired
        applyRequested = [bool]$Apply
        requestedAccessTokenVersion = 2
        audienceShape = 'application_id_guid'
        scopeShape = 'api://<application-id>/.default'
        reusableCredentialRetained = $false
        customerIdentifiersRetained = $false
        publicEvidenceSafe = $true
    } | ConvertTo-Json -Depth 5
}

Assert-Command -Name 'az'
Assert-Command -Name 'gh'

$coreApplicationId = $CoreApplicationId.Guid.ToLowerInvariant()
$core = Get-LiveCoreContainerApp
$coreName = [string]$core.name
if (-not $coreName) {
    throw 'Resolved live ETS Core Container App has no name.'
}

$containers = @($core.properties.template.containers)
if ($containers.Count -ne 1) {
    throw 'Resolved live ETS Core must have exactly one container.'
}
$envMap = Get-ContainerEnvironmentMap -Container $containers[0]
$currentAudience = [string]$envMap['ETS_AUTH_AUDIENCE']
if (-not $currentAudience) {
    throw 'Live ETS Core does not expose ETS_AUTH_AUDIENCE.'
}

$legacyAudience = "api://$coreApplicationId"
if (
    $currentAudience -ine $coreApplicationId -and
    $currentAudience -ine $legacyAudience
) {
    throw 'Live ETS Core audience does not match either the governed v2 GUID or the legacy api:// identifier.'
}

$runtimeAudienceReady = $currentAudience -ieq $coreApplicationId
if (-not $Apply) {
    Write-BoundedStatus `
        -Stage 'ready_to_converge_v2_audience' `
        -RuntimeAudienceReady $runtimeAudienceReady `
        -ProtectedSecretWritten $false `
        -MutationRequired $true
    return
}

gh auth status --active --hostname github.com *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'GitHub CLI is not authenticated to github.com.'
}

$resolvedRepository = (gh repo view $Repository --json nameWithOwner --jq '.nameWithOwner').Trim()
if ($LASTEXITCODE -ne 0 -or $resolvedRepository -cne $Repository) {
    throw "GitHub CLI repository resolution did not match '$Repository'."
}

$coreApplicationId | gh secret set ETS_LIVE_AUTH_AUDIENCE `
    --env $EnvironmentName `
    --repo $Repository `
    --body $coreApplicationId
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to write ETS_LIVE_AUTH_AUDIENCE to the protected GitHub environment.'
}

az containerapp update `
    --name $coreName `
    --resource-group $ResourceGroup `
    --set-env-vars "ETS_AUTH_AUDIENCE=$coreApplicationId" `
    --only-show-errors `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to update the live ETS Core v2 audience.'
}

$core = Get-LiveCoreContainerApp
$containers = @($core.properties.template.containers)
$envMap = Get-ContainerEnvironmentMap -Container $containers[0]
$updatedAudience = [string]$envMap['ETS_AUTH_AUDIENCE']
if ($updatedAudience -ine $coreApplicationId) {
    throw 'Live ETS Core audience did not converge to the v2 application ID GUID.'
}

$latestRevisionName = [string]$core.properties.latestRevisionName
if (-not $latestRevisionName) {
    throw 'Live ETS Core did not report a latest revision after audience convergence.'
}

Write-BoundedStatus `
    -Stage 'live_core_v2_audience_ready' `
    -RuntimeAudienceReady $true `
    -ProtectedSecretWritten $true `
    -MutationRequired $false
