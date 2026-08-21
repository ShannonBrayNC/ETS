[CmdletBinding()]
param(
    [string]$Repository = "ShannonBrayNC/ETS",
    [string]$EnvironmentName = "edge-demo-azure",
    [string]$EvidenceRoot = (Join-Path $HOME "ETS-Evidence")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ApiVersion = "2026-03-10"
$ImageWorkflow = "edge-virtual-azure-q0-images.yml"
$DeployWorkflow = "deploy-edge-dark-azure.yml"

function Require-Command {
    param([Parameter(Mandatory)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or is not on PATH."
    }
}

function Invoke-NativeText {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments
    )

    $output = & $FilePath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath command failed. Review its local authentication and permissions."
    }
    return (($output | Out-String).Trim())
}

function Invoke-GhJson {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [hashtable]$Body
    )

    if ($null -eq $Body) {
        $raw = & gh @Arguments 2>&1
    } else {
        $payload = $Body | ConvertTo-Json -Depth 10 -Compress
        $raw = $payload | & gh @Arguments 2>&1
    }

    if ($LASTEXITCODE -ne 0) {
        throw "GitHub API command failed. No credential or token value was retained."
    }

    $text = ($raw | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "GitHub API returned an empty response where JSON was required."
    }
    return ($text | ConvertFrom-Json)
}

function Invoke-WorkflowDispatch {
    param(
        [Parameter(Mandatory)][string]$Workflow,
        [Parameter(Mandatory)][hashtable]$Inputs
    )

    $body = @{
        ref = "main"
        return_run_details = $true
        inputs = $Inputs
    }

    $response = Invoke-GhJson -Body $body -Arguments @(
        "api",
        "--method", "POST",
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: $ApiVersion",
        "repos/$Repository/actions/workflows/$Workflow/dispatches",
        "--input", "-"
    )

    if (-not $response.workflow_run_id) {
        throw "Workflow dispatch did not return an exact run ID."
    }
    return $response
}

function Wait-WorkflowSuccess {
    param(
        [Parameter(Mandatory)][long]$RunId,
        [Parameter(Mandatory)][string]$ExpectedSourceSha
    )

    & gh run watch $RunId --repo $Repository --exit-status --interval 10
    if ($LASTEXITCODE -ne 0) {
        throw "Workflow run $RunId failed."
    }

    $details = Invoke-NativeText -FilePath "gh" -Arguments @(
        "run", "view", [string]$RunId,
        "--repo", $Repository,
        "--json", "status,conclusion,headSha,event,url"
    ) | ConvertFrom-Json

    if ($details.status -ne "completed" -or $details.conclusion -ne "success") {
        throw "Workflow run $RunId did not complete successfully."
    }
    if ($details.event -ne "workflow_dispatch") {
        throw "Workflow run $RunId was not a workflow_dispatch run."
    }
    if ($details.headSha -ne $ExpectedSourceSha) {
        throw "Workflow run $RunId source SHA does not match the qualified source."
    }
    return $details
}

function Download-RunArtifact {
    param(
        [Parameter(Mandatory)][long]$RunId,
        [Parameter(Mandatory)][string]$ArtifactName,
        [Parameter(Mandatory)][string]$Destination
    )

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    & gh run download $RunId `
        --repo $Repository `
        --name $ArtifactName `
        --dir $Destination
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download required artifact '$ArtifactName' from run $RunId."
    }
}

function Require-ImmutableImage {
    param(
        [Parameter(Mandatory)][string]$Image,
        [Parameter(Mandatory)][string]$RepositoryPath
    )

    $escaped = [regex]::Escape($RepositoryPath)
    $pattern = "^[^/\s]+/$escaped@sha256:[0-9a-f]{64}$"
    if ($Image -notmatch $pattern) {
        throw "Qualified image reference for '$RepositoryPath' is not canonical and immutable."
    }
    if ($Image -match ":latest(?:@|$)") {
        throw "Mutable latest image references are forbidden."
    }
}

Require-Command -Name "gh"
Require-Command -Name "az"

Invoke-NativeText -FilePath "gh" -Arguments @(
    "auth", "status", "--hostname", "github.com"
) | Out-Null
Invoke-NativeText -FilePath "az" -Arguments @(
    "account", "show", "--only-show-errors", "--query", "id", "-o", "tsv"
) | Out-Null

$environment = Invoke-GhJson -Arguments @(
    "api",
    "-H", "Accept: application/vnd.github+json",
    "-H", "X-GitHub-Api-Version: $ApiVersion",
    "repos/$Repository/environments/$EnvironmentName"
)
if ($environment.name -ne $EnvironmentName) {
    throw "Protected GitHub environment '$EnvironmentName' was not found."
}

$environmentVariables = Invoke-GhJson -Arguments @(
    "api",
    "-H", "Accept: application/vnd.github+json",
    "-H", "X-GitHub-Api-Version: $ApiVersion",
    "repos/$Repository/environments/$EnvironmentName/variables?per_page=100"
)

$requiredVariables = @(
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    "ETS_EDGE_DEMO_ACR_NAME",
    "ETS_EDGE_DEMO_ACR_RESOURCE_GROUP",
    "ETS_EDGE_DEMO_RESOURCE_GROUP",
    "ETS_EDGE_DEMO_LOCATION"
)
$availableVariableNames = @($environmentVariables.variables | ForEach-Object { $_.name })
$missingVariables = @($requiredVariables | Where-Object {
    $_ -notin $availableVariableNames
})
if ($missingVariables.Count -gt 0) {
    throw "Missing required protected environment variable names: $($missingVariables -join ', ')."
}

$sourceSha = Invoke-NativeText -FilePath "gh" -Arguments @(
    "api", "repos/$Repository/commits/main", "--jq", ".sha"
)
if ($sourceSha -notmatch "^[0-9a-f]{40}$") {
    throw "Unable to resolve canonical main source SHA."
}

Write-Host "Dispatching qualified Edge Virtual image publication from main $sourceSha."
$publicationDispatch = Invoke-WorkflowDispatch -Workflow $ImageWorkflow -Inputs @{}
$publicationRunId = [long]$publicationDispatch.workflow_run_id
$publicationDetails = Wait-WorkflowSuccess `
    -RunId $publicationRunId `
    -ExpectedSourceSha $sourceSha

$publicationDirectory = Join-Path `
    (Join-Path (Join-Path $EvidenceRoot "edge-virtual-azure") $sourceSha) `
    "q0-$publicationRunId"
Download-RunArtifact `
    -RunId $publicationRunId `
    -ArtifactName "edge-virtual-azure-q0-$publicationRunId" `
    -Destination $publicationDirectory

$manifestFile = Get-ChildItem `
    -Path $publicationDirectory `
    -Filter "image-set-manifest.json" `
    -File `
    -Recurse |
    Select-Object -First 1
if (-not $manifestFile) {
    throw "Qualified image-set manifest was not present in the publication artifact."
}

$manifest = Get-Content -Raw -Path $manifestFile.FullName | ConvertFrom-Json
if ($manifest.schema_version -ne "ets.edge_virtual_azure.image_set.v1") {
    throw "Unexpected image-set manifest schema."
}
if ($manifest.source_sha -ne $sourceSha) {
    throw "Image-set manifest source SHA does not match qualified main."
}
if ([long]$manifest.workflow_run_id -ne $publicationRunId) {
    throw "Image-set manifest run ID does not match the dispatched publication run."
}
if ($manifest.platform -ne "linux/amd64") {
    throw "Image-set platform is outside the qualified Azure demo profile."
}
if ($manifest.vulnerability_gate -ne "PASS") {
    throw "Image-set vulnerability gate did not pass."
}
if ($manifest.registry_credentials_retained -ne $false) {
    throw "Image-set evidence claims registry credentials were retained."
}
if ($manifest.customer_identifiers_retained -ne $false) {
    throw "Image-set evidence claims customer identifiers were retained."
}

$images = $manifest.images
Require-ImmutableImage -Image $images.edge_api -RepositoryPath "ets/edge-demo/api"
Require-ImmutableImage -Image $images.edge_bff -RepositoryPath "ets/edge-demo/bff"
Require-ImmutableImage -Image $images.edge_upstream -RepositoryPath "ets/edge-demo/upstream"
Require-ImmutableImage -Image $images.edge_ui -RepositoryPath "ets/edge-demo/ui"

$mainBeforeOrigin = Invoke-NativeText -FilePath "gh" -Arguments @(
    "api", "repos/$Repository/commits/main", "--jq", ".sha"
)
if ($mainBeforeOrigin -ne $sourceSha) {
    throw "main advanced after image publication. Re-run to produce a single-source deployment."
}

Write-Host "Image set qualified. Dispatching private-origin deployment only."
$originDispatch = Invoke-WorkflowDispatch -Workflow $DeployWorkflow -Inputs @{
    phase = "origin"
    expected_source_sha = $sourceSha
    edge_api_image = [string]$images.edge_api
    edge_bff_image = [string]$images.edge_bff
    edge_upstream_image = [string]$images.edge_upstream
    edge_ui_image = [string]$images.edge_ui
}
$originRunId = [long]$originDispatch.workflow_run_id
$originDetails = Wait-WorkflowSuccess `
    -RunId $originRunId `
    -ExpectedSourceSha $sourceSha

$originDirectory = Join-Path `
    (Join-Path (Join-Path $EvidenceRoot "edge-virtual-azure") $sourceSha) `
    "origin-$originRunId"
Download-RunArtifact `
    -RunId $originRunId `
    -ArtifactName "edge-virtual-azure-origin-$originRunId" `
    -Destination $originDirectory

$originManifestFile = Get-ChildItem `
    -Path $originDirectory `
    -Filter "origin-manifest.json" `
    -File `
    -Recurse |
    Select-Object -First 1
if (-not $originManifestFile) {
    throw "Private-origin manifest was not present in the deployment artifact."
}

$originManifest = Get-Content -Raw -Path $originManifestFile.FullName | ConvertFrom-Json
if ($originManifest.schema_version -ne "ets.edge_virtual_azure.origin.v1") {
    throw "Unexpected private-origin manifest schema."
}
if ($originManifest.source_sha -ne $sourceSha) {
    throw "Private-origin manifest source SHA does not match the qualified image set."
}
if ([long]$originManifest.workflow_run_id -ne $originRunId) {
    throw "Private-origin manifest run ID does not match the deployment run."
}
if ($originManifest.public_network_access -ne "Disabled") {
    throw "Private-origin public network access is not disabled."
}
if ([int]$originManifest.runtime_identity_count -ne 0) {
    throw "Private-origin runtime identity count is not zero."
}
if ($originManifest.synthetic_only -ne $true) {
    throw "Private-origin manifest does not assert the synthetic-only boundary."
}
if ($originManifest.hardware_attested -ne $false) {
    throw "Hosted Edge Virtual must not claim hardware attestation."
}
if ($originManifest.public_activation -ne $false) {
    throw "Private-origin handoff must not activate the public edge."
}

if ($originManifest.images.edge_api -ne $images.edge_api -or
    $originManifest.images.edge_bff -ne $images.edge_bff -or
    $originManifest.images.edge_upstream -ne $images.edge_upstream -or
    $originManifest.images.edge_ui -ne $images.edge_ui) {
    throw "Private-origin image references do not match the qualified Q0 image set."
}

Write-Host ""
Write-Host "ETS Edge Virtual private-origin handoff completed."
Write-Host "Source SHA: $sourceSha"
Write-Host "Q0 publication run: $($publicationDetails.url)"
Write-Host "Origin deployment run: $($originDetails.url)"
Write-Host "Container App: $($originManifest.container_app_name)"
Write-Host "Managed environment: $($originManifest.managed_environment_name)"
Write-Host "Public network access: Disabled"
Write-Host "Hardware attested: false"
Write-Host ""
Write-Host "STOP BOUNDARY: public-edge was not dispatched."
Write-Host "No Private Link request was approved and no DNS record was changed."
