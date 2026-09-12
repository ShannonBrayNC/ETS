[CmdletBinding()]
param(
    [string]$DestinationAzureTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2',
    [string]$DestinationSubscriptionId = '5729a82b-8850-4868-b96c-96c3805cbb9d',
    [string]$ResourceGroup = 'rg-ets-prod-eastus',
    [string]$ContainerAppName = 'ets-oif5r5ydprrou-gw',
    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id',
    [string]$QualificationImage = '',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$corePath = Join-Path $PSScriptRoot 'invoke-ets-sharepoint-workload-identity-isolated-job.core.ps1'
if (-not (Test-Path $corePath -PathType Leaf)) {
    throw 'Gate 2 isolated-job core script is unavailable.'
}

function Replace-ExactlyOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$OldValue,
        [Parameter(Mandatory = $true)][string]$NewValue,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $first = $Source.IndexOf($OldValue, [System.StringComparison]::Ordinal)
    if ($first -lt 0) {
        throw "Gate 2 isolated-job hotfix target '$Name' was not found."
    }
    if ($Source.IndexOf($OldValue, $first + $OldValue.Length, [System.StringComparison]::Ordinal) -ge 0) {
        throw "Gate 2 isolated-job hotfix target '$Name' is ambiguous."
    }
    return $Source.Replace($OldValue, $NewValue)
}

$source = Get-Content $corePath -Raw -Encoding UTF8

$qualificationImage = $QualificationImage.Trim()
if ($qualificationImage -and $qualificationImage -notmatch '^etsprod7c8ab70380\.azurecr\.io/ets/hosted-q1@sha256:[0-9a-f]{64}$') {
    throw 'QualificationImage must be an immutable sha256 reference in the approved destination ACR ets/hosted-q1 repository.'
}
$qualificationImageLiteral = $qualificationImage.Replace("'", "''")
$oldImageLine = '$image = [string]$gatewayContainer.image'
$newImageBlock = @"
`$gatewayConfiguredImage = [string]`$gatewayContainer.image
if (`$gatewayConfiguredImage -notmatch '@sha256:[0-9a-fA-F]{64}$') {
    throw 'Gateway image is not pinned by immutable sha256 digest.'
}
`$image = '$qualificationImageLiteral'
`$qualificationImageOverrideUsed = -not [string]::IsNullOrWhiteSpace(`$image)
if (-not `$qualificationImageOverrideUsed) {
    `$image = `$gatewayConfiguredImage
}
"@
$source = Replace-ExactlyOnce `
    -Source $source `
    -OldValue $oldImageLine `
    -NewValue $newImageBlock `
    -Name 'qualification image selection'

$oldPreviewLine = '        immutableGatewayImageVerified = $true'
$newPreviewBlock = @'
        immutableGatewayImageVerified = $true
        immutableQualificationImageVerified = $true
        qualificationImageOverrideUsed = $qualificationImageOverrideUsed
        productionGatewayImageMutationPlanned = $false
'@
$source = Replace-ExactlyOnce `
    -Source $source `
    -OldValue $oldPreviewLine `
    -NewValue $newPreviewBlock `
    -Name 'qualification image preview evidence'

$oldUriLine = (
    '$jobUri = "https://management.azure.com' +
    '$jobResourceId' +
    '?api-version=' +
    '$jobApiVersion"'
)
$newUriLine = '$jobUri = "https://management.azure.com${jobResourceId}?api-version=${jobApiVersion}"'
$source = Replace-ExactlyOnce -Source $source -OldValue $oldUriLine -NewValue $newUriLine -Name 'ARM URI'

$oldBodyJsonLine = '$jobBodyJson = $jobBody | ConvertTo-Json -Depth 30 -Compress'
$newBodyJsonBlock = @'
$jobBodyJson = $jobBody | ConvertTo-Json -Depth 30 -Compress
$jobBodyPath = Join-Path ([System.IO.Path]::GetTempPath()) (
    'ets-g2q-body-' + [Guid]::NewGuid().ToString('N') + '.json'
)
[System.IO.File]::WriteAllText(
    $jobBodyPath,
    $jobBodyJson,
    [System.Text.UTF8Encoding]::new($false)
)
$jobBodyReference = "@$jobBodyPath"
'@
$source = Replace-ExactlyOnce `
    -Source $source `
    -OldValue $oldBodyJsonLine `
    -NewValue $newBodyJsonBlock `
    -Name 'ARM request body file staging'

$executionMarker = '$jobCreated = $false'
$executionIndex = $source.IndexOf($executionMarker, [System.StringComparison]::Ordinal)
if ($executionIndex -lt 0) {
    throw 'Gate 2 isolated-job execution-tail hotfix target was not found.'
}
if ($source.IndexOf($executionMarker, $executionIndex + $executionMarker.Length, [System.StringComparison]::Ordinal) -ge 0) {
    throw 'Gate 2 isolated-job execution-tail hotfix target is ambiguous.'
}

$newExecutionTail = @'
$jobCreated = $false
$executionName = $null
$executionStatus = $null
$qualificationObserved = $false
$qualificationFailure = $null
$sanitizedFailureReason = $null
$cleanupFailure = $null
$cleanupVerified = $false
$productionGatewayZeroRuntimeRestored = $false
$logText = $null

function Get-SanitizedGate2FailureReason {
    param([string]$Text)

    if (-not $Text) {
        return 'no_sanitized_runtime_log'
    }
    $patterns = [ordered]@{
        'managed_identity_client_id_missing' = 'ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID is required'
        'managed_identity_endpoint_unavailable' = 'Azure managed identity runtime endpoint is unavailable'
        'unexpected_credential_provider' = 'Unexpected Gateway credential provider'
        'graph_token_invalid_jwt' = 'Microsoft Graph access token is not a JWT'
        'graph_token_claims_decode_failed' = 'Microsoft Graph access token claims could not be decoded'
        'graph_token_tenant_mismatch' = 'Microsoft Graph token tenant does not match EchoMedia'
        'graph_token_application_mismatch' = 'Microsoft Graph token application does not match ETS Gateway'
        'graph_token_delegated_scopes_present' = 'Microsoft Graph token unexpectedly contains delegated scopes'
        'graph_token_role_mismatch' = 'Microsoft Graph token role set is not exactly Sites.Selected'
        'graph_token_audience_unexpected' = 'Microsoft Graph token audience is unexpected'
        'graph_http_401' = 'Microsoft Graph GET returned HTTP 401'
        'graph_http_403' = 'Microsoft Graph GET returned HTTP 403'
        'graph_http_404' = 'Microsoft Graph GET returned HTTP 404'
        'graph_service_unreachable' = 'Microsoft Graph GET could not reach the service'
        'site_id_mismatch' = 'Resolved SharePoint site ID is not the approved ETS site'
        'site_url_mismatch' = 'Resolved SharePoint site URL is not the approved ETS site'
        'drive_root_incomplete' = 'SharePoint default drive root metadata is incomplete'
        'drive_root_host_unexpected' = 'SharePoint default drive root host is unexpected'
        'module_not_found' = 'ModuleNotFoundError'
        'import_error' = 'ImportError'
        'azure_identity_authentication_error' = 'ClientAuthenticationError'
        'python_traceback' = 'Traceback \(most recent call last\)'
    }
    foreach ($entry in $patterns.GetEnumerator()) {
        if ($Text -match [regex]::Escape([string]$entry.Value)) {
            return [string]$entry.Key
        }
    }
    return 'unclassified_sanitized_runtime_failure'
}

try {
    $createdJson = $null
    $jobCreateExitCode = $null
    try {
        $createdJson = az rest `
            --method put `
            --uri $jobUri `
            --headers 'Content-Type=application/json' `
            --body $jobBodyReference `
            --output json
        $jobCreateExitCode = $LASTEXITCODE
    }
    finally {
        Remove-Item -LiteralPath $jobBodyPath -Force -ErrorAction SilentlyContinue
    }
    if ($jobCreateExitCode -ne 0) {
        throw "Temporary Gate 2 qualification job creation failed with exit code $jobCreateExitCode."
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
        throw 'Temporary qualification job image does not match the immutable qualification image.'
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
                if ($executionStatus -in @('Succeeded', 'Failed', 'Stopped', 'Degraded')) {
                    break
                }
            }
        }
        Start-Sleep -Seconds 3
    }

    if (-not $executionName) {
        $qualificationFailure = 'execution_name_unavailable'
    }
    elseif ($executionStatus -notin @('Succeeded', 'Failed', 'Stopped', 'Degraded')) {
        $qualificationFailure = 'execution_did_not_reach_terminal_state'
    }

    if ($executionName) {
        for ($attempt = 0; $attempt -lt 6; $attempt++) {
            $logText = az containerapp job logs show `
                --resource-group $approvedResourceGroup `
                --name $jobName `
                --execution $executionName `
                --container $qualificationContainerName `
                --format text `
                --tail 30 2>$null | Out-String
            if ($LASTEXITCODE -eq 0 -and $logText) {
                if ($logText -match '"qualification"\s*:\s*"pass"' -or $executionStatus -ne 'Succeeded') {
                    break
                }
            }
            Start-Sleep -Seconds 2
        }
    }

    if ($executionStatus -ceq 'Succeeded') {
        if (-not $logText -or $logText -notmatch '"qualification"\s*:\s*"pass"') {
            $qualificationFailure = 'sanitized_pass_evidence_missing'
        }
        else {
            foreach ($requiredMarker in @(
                '"federatedCredentialProviderVerified"\s*:\s*true',
                '"sitesSelectedRoleClaimVerified"\s*:\s*true',
                '"exactSharePointSiteVerified"\s*:\s*true',
                '"defaultDriveRootReadVerified"\s*:\s*true',
                '"reusableCredentialRetained"\s*:\s*false',
                '"sharePointPayloadRetained"\s*:\s*false'
            )) {
                if ($logText -notmatch $requiredMarker) {
                    $qualificationFailure = 'required_sanitized_proof_marker_missing'
                    break
                }
            }
            if (-not $qualificationFailure) {
                $qualificationObserved = $true
            }
        }
    }
    elseif ($executionStatus -in @('Failed', 'Stopped', 'Degraded')) {
        $sanitizedFailureReason = Get-SanitizedGate2FailureReason -Text $logText
        $qualificationFailure = 'terminal_' + $executionStatus.ToLowerInvariant()
    }
}
catch {
    if (-not $qualificationFailure) {
        $qualificationFailure = 'wrapper_exception'
    }
    if (-not $sanitizedFailureReason) {
        $sanitizedFailureReason = Get-SanitizedGate2FailureReason -Text ([string]$_.Exception.Message)
    }
}
finally {
    $logText = $null
    if ($jobCreated) {
        az rest --method delete --uri $jobUri --output none
        if ($LASTEXITCODE -ne 0) {
            $cleanupFailure = 'temporary_job_delete_failed'
        }
        else {
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                az resource show `
                    --resource-group $approvedResourceGroup `
                    --resource-type 'Microsoft.App/jobs' `
                    --name $jobName `
                    --output none 2>$null
                if ($LASTEXITCODE -ne 0) {
                    $cleanupVerified = $true
                    break
                }
                Start-Sleep -Seconds 2
            }
            if (-not $cleanupVerified) {
                $cleanupFailure = 'temporary_job_still_exists_after_cleanup'
            }
        }
    }
    else {
        $cleanupVerified = $true
    }
}

$postJson = & $previewPath `
    -DestinationAzureTenantId $approvedTenantId `
    -DestinationSubscriptionId $approvedSubscriptionId `
    -ResourceGroup $approvedResourceGroup `
    -ContainerAppName $approvedContainerAppName `
    -ManagedIdentityName $approvedManagedIdentityName
$post = $postJson | ConvertFrom-Json
if ([int]$post.activeRevisionCount -eq 0 -and [int]$post.activeReplicaCount -eq 0) {
    $productionGatewayZeroRuntimeRestored = $true
}

if ($cleanupFailure) {
    throw "CRITICAL: Gate 2 cleanup verification failed; reason=$cleanupFailure; productionGatewayZeroRuntimeRestored=$($productionGatewayZeroRuntimeRestored.ToString().ToLowerInvariant())."
}
if (-not $productionGatewayZeroRuntimeRestored) {
    throw 'CRITICAL: production Gateway runtime is not at the required zero-runtime state after isolated qualification.'
}
if (-not $qualificationObserved) {
    if (-not $sanitizedFailureReason) {
        $sanitizedFailureReason = 'none'
    }
    throw "Gate 2 workload-identity qualification failed; executionStatus=$executionStatus; failure=$qualificationFailure; sanitizedReason=$sanitizedFailureReason; temporaryJobDeleted=$cleanupVerified; productionGatewayZeroRuntimeRestored=$productionGatewayZeroRuntimeRestored."
}

[pscustomobject]@{
    qualification = 'pass'
    mode = 'gateway_uami_isolated_container_apps_job'
    stage = 'gateway_workload_identity_runtime_read'
    temporaryAzureMutationPerformed = $true
    temporaryJobCreated = $true
    temporaryJobDeleted = $cleanupVerified
    productionGatewayMutationPerformed = $false
    productionGatewayImageMutationPerformed = $false
    productionGatewayZeroRuntimeRestored = $productionGatewayZeroRuntimeRestored
    immutableQualificationImageVerified = $true
    qualificationImageOverrideUsed = $qualificationImageOverrideUsed
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
'@

$source = $source.Substring(0, $executionIndex) + $newExecutionTail

$escapedRoot = $PSScriptRoot.Replace("'", "''")
$scriptRootLiteral = "'$escapedRoot'"
$source = $source.Replace('$PSScriptRoot', $scriptRootLiteral)

$forwardParameters = @{}
foreach ($entry in $PSBoundParameters.GetEnumerator()) {
    if ($entry.Key -cne 'QualificationImage') {
        $forwardParameters[$entry.Key] = $entry.Value
    }
}

$scriptBlock = [scriptblock]::Create($source)
& $scriptBlock @forwardParameters
