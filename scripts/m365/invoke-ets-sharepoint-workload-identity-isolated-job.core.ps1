[CmdletBinding()]
param(
    [string]$DestinationAzureTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2',
    [string]$DestinationSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d',
    [string]$ResourceGroup = 'rg-ets-prod-eastus',
    [string]$ContainerAppName = 'ets-oif5r5ydprrou-gw',
    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvedTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
$approvedSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d'
$approvedResourceGroup = 'rg-ets-prod-eastus'
$approvedContainerAppName = 'ets-oif5r5ydprrou-gw'
$approvedManagedIdentityName = 'ets-oif5r5ydprrou-gw-id'
$approvedContainerName = 'ets-gateway'
$qualificationContainerName = 'ets-gate2-qualification'
$jobApiVersion = '2026-01-01'

function Assert-Exact {
    param(
        [Parameter(Mandatory = $true)][string]$Actual,
        [Parameter(Mandatory = $true)][string]$Expected,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($Actual -cne $Expected) {
        throw "$Name must match the approved Gate 2 value exactly."
    }
}

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Get-ResourceProperty {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $topLevel = $Object.PSObject.Properties[$Name]
    if ($null -ne $topLevel) {
        return $topLevel.Value
    }
    $properties = $Object.PSObject.Properties['properties']
    if ($null -ne $properties -and $null -ne $properties.Value) {
        $nested = $properties.Value.PSObject.Properties[$Name]
        if ($null -ne $nested) {
            return $nested.Value
        }
    }
    return $null
}

Assert-Exact $DestinationAzureTenantId $approvedTenantId 'DestinationAzureTenantId'
Assert-Exact $DestinationSubscriptionId $approvedSubscriptionId 'DestinationSubscriptionId'
Assert-Exact $ResourceGroup $approvedResourceGroup 'ResourceGroup'
Assert-Exact $ContainerAppName $approvedContainerAppName 'ContainerAppName'
Assert-Exact $ManagedIdentityName $approvedManagedIdentityName 'ManagedIdentityName'
Assert-Command -Name 'az'

$previewPath = Join-Path $PSScriptRoot 'preview-ets-sharepoint-workload-identity-runtime.ps1'
$harnessPath = Join-Path $PSScriptRoot 'qualify_ets_sharepoint_workload_identity.py'
if (-not (Test-Path $previewPath -PathType Leaf)) {
    throw 'Gate 2 runtime preview script is unavailable.'
}
if (-not (Test-Path $harnessPath -PathType Leaf)) {
    throw 'Gate 2 workload-identity qualification harness is unavailable.'
}

$account = az account show --output json | ConvertFrom-Json
if (-not $account.tenantId -or $account.tenantId -cne $approvedTenantId) {
    throw 'Azure CLI is not authenticated to the approved destination tenant.'
}
if (-not $account.id -or $account.id -cne $approvedSubscriptionId) {
    throw 'Azure CLI is not using the approved destination subscription.'
}

$baselineJson = & $previewPath `
    -DestinationAzureTenantId $approvedTenantId `
    -DestinationSubscriptionId $approvedSubscriptionId `
    -ResourceGroup $approvedResourceGroup `
    -ContainerAppName $approvedContainerAppName `
    -ManagedIdentityName $approvedManagedIdentityName
$baseline = $baselineJson | ConvertFrom-Json
if ($baseline.mutationPerformed -ne $false) {
    throw 'Gate 2 runtime preview unexpectedly reported a mutation.'
}
if ([int]$baseline.activeRevisionCount -ne 0 -or [int]$baseline.activeReplicaCount -ne 0) {
    throw 'Isolated qualification requires the production Gateway to remain at zero runtime.'
}
if ($baseline.runtimeActivationRequired -ne $true) {
    throw 'Isolated qualification expected the runtime activation boundary.'
}

$gatewayIdentity = az identity show `
    --resource-group $approvedResourceGroup `
    --name $approvedManagedIdentityName `
    --output json | ConvertFrom-Json
if (-not $gatewayIdentity.id -or -not $gatewayIdentity.clientId -or -not $gatewayIdentity.principalId) {
    throw 'Approved Gateway UAMI response is incomplete.'
}

$app = az containerapp show `
    --resource-group $approvedResourceGroup `
    --name $approvedContainerAppName `
    --output json | ConvertFrom-Json
if (-not $app.id -or -not $app.identity) {
    throw 'Approved Gateway Container App could not be read completely.'
}

$environmentId = [string](Get-ResourceProperty -Object $app -Name 'environmentId')
$configuration = Get-ResourceProperty -Object $app -Name 'configuration'
$template = Get-ResourceProperty -Object $app -Name 'template'
if (-not $environmentId -or $null -eq $configuration -or $null -eq $template) {
    throw 'Gateway Container App runtime configuration is incomplete.'
}
if (-not $app.location) {
    throw 'Gateway Container App location is unavailable.'
}

$containers = @($template.containers)
$gatewayContainers = @($containers | Where-Object { $_.name -ceq $approvedContainerName })
if ($gatewayContainers.Count -ne 1) {
    throw 'Gateway Container App must contain exactly one approved Gateway container.'
}
$gatewayContainer = $gatewayContainers[0]
$image = [string]$gatewayContainer.image
if ($image -notmatch '@sha256:[0-9a-fA-F]{64}$') {
    throw 'Gateway image is not pinned by immutable sha256 digest.'
}
$cpu = $gatewayContainer.resources.cpu
$memory = [string]$gatewayContainer.resources.memory
if ($null -eq $cpu -or -not $memory) {
    throw 'Gateway container resource bounds are unavailable.'
}

$registries = @($configuration.registries)
if ($registries.Count -ne 1) {
    throw 'Gateway must expose exactly one approved ACR registry configuration.'
}
$registryServer = [string]$registries[0].server
$pullIdentityId = [string]$registries[0].identity
if (-not $registryServer -or -not $pullIdentityId) {
    throw 'Gateway ACR registry configuration is incomplete.'
}
if ($pullIdentityId -ieq 'system' -or $pullIdentityId -ieq 'system-environment') {
    throw 'Gate 2 requires the existing dedicated user-assigned ACR pull identity.'
}
if ($pullIdentityId -ieq [string]$gatewayIdentity.id) {
    throw 'Gateway runtime and ACR pull identities must remain distinct.'
}
if (-not $image.StartsWith("$registryServer/", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Gateway image registry does not match the configured ACR server.'
}

$pullIdentity = az identity show --ids $pullIdentityId --output json | ConvertFrom-Json
if (-not $pullIdentity.id -or -not $pullIdentity.clientId -or -not $pullIdentity.principalId) {
    throw 'Gateway ACR pull identity response is incomplete.'
}

$userAssigned = $app.identity.PSObject.Properties['userAssignedIdentities']
if ($null -eq $userAssigned -or $null -eq $userAssigned.Value) {
    throw 'Gateway Container App has no user-assigned identities.'
}
$attachedIds = @($userAssigned.Value.PSObject.Properties | ForEach-Object { $_.Name })
if (@($attachedIds | Where-Object { $_ -ieq [string]$gatewayIdentity.id }).Count -ne 1) {
    throw 'Approved Gateway UAMI is not attached exactly once to the Container App.'
}
if (@($attachedIds | Where-Object { $_ -ieq $pullIdentityId }).Count -ne 1) {
    throw 'Approved ACR pull identity is not attached exactly once to the Container App.'
}

$harness = Get-Content $harnessPath -Raw -Encoding UTF8
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($harness))
$bootstrap = (
    "import base64;exec(compile(base64.b64decode('$payload')," +
    "'<ets-gate2-isolated-job>','exec'))"
)

if (-not $Apply) {
    [pscustomobject]@{
        mode = 'preview_only'
        stage = 'gateway_isolated_workload_identity_execution'
        mutationRequired = $true
        mutationPerformed = $false
        destinationAzureTenantVerified = $true
        destinationSubscriptionVerified = $true
        productionGatewayZeroRuntimeVerified = $true
        gatewayManagedIdentityVerified = $true
        gatewayManagedIdentityAttached = $true
        registryPullIdentityVerified = $true
        immutableGatewayImageVerified = $true
        temporaryJobRequired = $true
        gatewayContainerAppMutationPlanned = $false
        azureRbacMutationPlanned = $false
        gatewayStateMountPlanned = $false
        gatewayEntrypointPlanned = $false
        reusableCredentialRetained = $false
        sourcePayloadRetained = $false
    } | ConvertTo-Json -Depth 4
    return
}

$jobName = 'ets-g2q-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$jobResourceId = (
    "/subscriptions/$approvedSubscriptionId/resourceGroups/$approvedResourceGroup" +
    "/providers/Microsoft.App/jobs/$jobName"
)
$jobUri = "https://management.azure.com$jobResourceId?api-version=$jobApiVersion"

$jobIdentities = [ordered]@{}
$jobIdentities[[string]$gatewayIdentity.id] = @{}
$jobIdentities[$pullIdentityId] = @{}

$jobBody = [ordered]@{
    location = [string]$app.location
    tags = [ordered]@{
        'ets-purpose' = 'gate2-workload-identity-qualification'
        'ets-temporary' = 'true'
    }
    identity = [ordered]@{
        type = 'UserAssigned'
        userAssignedIdentities = $jobIdentities
    }
    properties = [ordered]@{
        environmentId = $environmentId
        configuration = [ordered]@{
            triggerType = 'Manual'
            replicaTimeout = 180
            replicaRetryLimit = 0
            manualTriggerConfig = [ordered]@{
                parallelism = 1
                replicaCompletionCount = 1
            }
            registries = @(
                [ordered]@{
                    server = $registryServer
                    identity = $pullIdentityId
                }
            )
            identitySettings = @(
                [ordered]@{
                    identity = [string]$gatewayIdentity.id
                    lifecycle = 'Main'
                },
                [ordered]@{
                    identity = $pullIdentityId
                    lifecycle = 'None'
                }
            )
        }
        template = [ordered]@{
            containers = @(
                [ordered]@{
                    name = $qualificationContainerName
                    image = $image
                    command = @('python')
                    args = @('-c', $bootstrap)
                    env = @(
                        [ordered]@{
                            name = 'ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID'
                            value = [string]$gatewayIdentity.clientId
                        }
                    )
                    probes = @()
                    resources = [ordered]@{
                        cpu = $cpu
                        memory = $memory
                    }
                    volumeMounts = @()
                }
            )
            initContainers = @()
            volumes = @()
        }
    }
}
$jobBodyJson = $jobBody | ConvertTo-Json -Depth 30 -Compress

$jobCreated = $false
$executionName = $null
$executionStatus = $null
$qualificationObserved = $false
try {
    $createdJson = az rest `
        --method put `
        --uri $jobUri `
        --headers 'Content-Type=application/json' `
        --body $jobBodyJson `
        --output json
    if ($LASTEXITCODE -ne 0) {
        throw "Temporary Gate 2 qualification job creation failed with exit code $LASTEXITCODE."
    }
    $created = $createdJson | ConvertFrom-Json
    $jobCreated = $true

    $createdEnvironmentId = [string](Get-ResourceProperty -Object $created -Name 'environmentId')
    if ($createdEnvironmentId -cne $environmentId) {
        throw 'Temporary qualification job was created in an unexpected managed environment.'
    }
    $createdTemplate = Get-ResourceProperty -Object $created -Name 'template'
    $createdContainers = @($createdTemplate.containers)
    if ($createdContainers.Count -ne 1) {
        throw 'Temporary qualification job container count is unexpected.'
    }
    if ([string]$createdContainers[0].image -cne $image) {
        throw 'Temporary qualification job image does not match the immutable Gateway image.'
    }

    $startJson = az containerapp job start `
        --resource-group $approvedResourceGroup `
        --name $jobName `
        --output json
    if ($LASTEXITCODE -ne 0) {
        throw "Temporary Gate 2 qualification job start failed with exit code $LASTEXITCODE."
    }
    if ($startJson) {
        $start = $startJson | ConvertFrom-Json
        if ($start.name) {
            $executionName = [string]$start.name
        }
    }

    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $executions = @(
            az containerapp job execution list `
                --resource-group $approvedResourceGroup `
                --name $jobName `
                --output json | ConvertFrom-Json
        )
        if ($LASTEXITCODE -ne 0) {
            throw 'Unable to read temporary Gate 2 job execution state.'
        }
        if ($executions.Count -gt 0) {
            if (-not $executionName) {
                $latest = $executions | Sort-Object {
                    [datetime]$_.properties.startTime
                } -Descending | Select-Object -First 1
                $executionName = [string]$latest.name
            }
            $selected = @($executions | Where-Object { $_.name -ceq $executionName })
            if ($selected.Count -eq 1) {
                $executionStatus = [string]$selected[0].properties.status
                if ($executionStatus -ceq 'Succeeded') {
                    break
                }
                if ($executionStatus -in @('Failed', 'Stopped', 'Degraded')) {
                    throw "Temporary Gate 2 job execution ended with status $executionStatus."
                }
            }
        }
        Start-Sleep -Seconds 3
    }
    if ($executionStatus -cne 'Succeeded' -or -not $executionName) {
        throw 'Temporary Gate 2 job execution did not succeed within the bounded wait period.'
    }

    $logText = $null
    for ($attempt = 0; $attempt -lt 6; $attempt++) {
        $logText = az containerapp job logs show `
            --resource-group $approvedResourceGroup `
            --name $jobName `
            --execution $executionName `
            --container $qualificationContainerName `
            --format text `
            --tail 30 2>$null | Out-String
        if ($LASTEXITCODE -eq 0 -and $logText) {
            if ($logText -match '"qualification"\s*:\s*"pass"') {
                break
            }
        }
        Start-Sleep -Seconds 2
    }
    if (-not $logText -or $logText -notmatch '"qualification"\s*:\s*"pass"') {
        throw 'Temporary Gate 2 job succeeded but sanitized qualification evidence was not found.'
    }
    foreach ($requiredMarker in @(
        '"federatedCredentialProviderVerified"\s*:\s*true',
        '"sitesSelectedRoleClaimVerified"\s*:\s*true',
        '"exactSharePointSiteVerified"\s*:\s*true',
        '"defaultDriveRootReadVerified"\s*:\s*true',
        '"reusableCredentialRetained"\s*:\s*false',
        '"sharePointPayloadRetained"\s*:\s*false'
    )) {
        if ($logText -notmatch $requiredMarker) {
            throw 'Temporary Gate 2 job output is missing required sanitized proof markers.'
        }
    }
    $qualificationObserved = $true
}
finally {
    if ($jobCreated) {
        az rest --method delete --uri $jobUri --output none
        if ($LASTEXITCODE -ne 0) {
            throw 'CRITICAL: temporary Gate 2 qualification job cleanup failed.'
        }
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            az resource show `
                --resource-group $approvedResourceGroup `
                --resource-type 'Microsoft.App/jobs' `
                --name $jobName `
                --output none 2>$null
            if ($LASTEXITCODE -ne 0) {
                break
            }
            Start-Sleep -Seconds 2
        }
        if ($LASTEXITCODE -eq 0) {
            throw 'CRITICAL: temporary Gate 2 qualification job still exists after cleanup.'
        }
    }
}

if (-not $qualificationObserved) {
    throw 'Gate 2 workload-identity qualification did not produce a verified pass result.'
}

$postJson = & $previewPath `
    -DestinationAzureTenantId $approvedTenantId `
    -DestinationSubscriptionId $approvedSubscriptionId `
    -ResourceGroup $approvedResourceGroup `
    -ContainerAppName $approvedContainerAppName `
    -ManagedIdentityName $approvedManagedIdentityName
$post = $postJson | ConvertFrom-Json
if ([int]$post.activeRevisionCount -ne 0 -or [int]$post.activeReplicaCount -ne 0) {
    throw 'Production Gateway runtime changed during isolated qualification.'
}

[pscustomobject]@{
    qualification = 'pass'
    mode = 'gateway_uami_isolated_container_apps_job'
    stage = 'gateway_workload_identity_runtime_read'
    temporaryAzureMutationPerformed = $true
    temporaryJobCreated = $true
    temporaryJobDeleted = $true
    productionGatewayMutationPerformed = $false
    productionGatewayZeroRuntimeRestored = $true
    gatewayEntrypointStarted = $false
    gatewayStateMounted = $false
    azureRbacMutationPerformed = $false
    managedIdentityEndpointVerified = $true
    federatedCredentialProviderVerified = $true
    resourceTenantTokenVerified = $true
    applicationTokenVerified = $true
    sitesSelectedRoleClaimVerified = $true
    exactSharePointSiteVerified = $true
    defaultDriveRootReadVerified = $true
    reusableCredentialRetained = $false
    sharePointPayloadRetained = $false
} | ConvertTo-Json -Depth 4
