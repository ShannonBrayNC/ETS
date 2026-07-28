[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Connect', 'Plan', 'Deploy', 'Upgrade', 'Validate')]
    [string]$Mode = 'Plan',

    [ValidateSet('free', 'standard')]
    [string]$Tier = 'free',

    [string]$TenantId,
    [string]$SubscriptionId,
    [string]$DeploymentName = 'ets',
    [string]$Location = 'eastus2',
    [switch]$UseDeviceCode,
    [switch]$SkipApi,
    [switch]$NonInteractive,
    [string]$OutputPath = './artifacts/azure-configurator-result.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Command {
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found. Install the Azure CLI and retry."
    }
}

function Invoke-AzJson {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $raw = & az @Arguments --only-show-errors --output json
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI failed: az $($Arguments -join ' ')"
    }
    if ([string]::IsNullOrWhiteSpace(($raw -join "`n"))) { return $null }
    return (($raw -join "`n") | ConvertFrom-Json -Depth 100)
}

function Connect-EtsAzure {
    $loginArgs = @('login')
    if ($TenantId) { $loginArgs += @('--tenant', $TenantId) }
    if ($UseDeviceCode) { $loginArgs += '--use-device-code' }
    if ($NonInteractive) {
        $existing = Invoke-AzJson -Arguments @('account', 'show')
        if (-not $existing) { throw 'No existing Azure CLI session is available for non-interactive execution.' }
    }
    else {
        & az @loginArgs --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Azure sign-in failed.' }
    }

    $subscriptions = @(Invoke-AzJson -Arguments @('account', 'list'))
    if ($subscriptions.Count -eq 0) { throw 'No accessible Azure subscriptions were found.' }

    $selected = $null
    if ($SubscriptionId) {
        $selected = $subscriptions | Where-Object { $_.id -eq $SubscriptionId } | Select-Object -First 1
        if (-not $selected) { throw "Subscription '$SubscriptionId' is not accessible in the current session." }
    }
    elseif ($subscriptions.Count -eq 1 -or $NonInteractive) {
        $selected = $subscriptions | Where-Object { $_.isDefault } | Select-Object -First 1
        if (-not $selected) { $selected = $subscriptions | Select-Object -First 1 }
    }
    else {
        Write-Host 'Accessible subscriptions:'
        for ($i = 0; $i -lt $subscriptions.Count; $i++) {
            Write-Host "[$($i + 1)] $($subscriptions[$i].name) ($($subscriptions[$i].id))"
        }
        $choice = Read-Host 'Select subscription number'
        if ($choice -notmatch '^\d+$' -or [int]$choice -lt 1 -or [int]$choice -gt $subscriptions.Count) {
            throw 'Invalid subscription selection.'
        }
        $selected = $subscriptions[[int]$choice - 1]
    }

    & az account set --subscription $selected.id
    if ($LASTEXITCODE -ne 0) { throw 'Unable to set the active subscription.' }
    return Invoke-AzJson -Arguments @('account', 'show')
}

function Get-DeploymentArguments {
    param([Parameter(Mandatory)][string]$Command)
    $template = Join-Path $PSScriptRoot '../../infra/azure/configurator/main.bicep'
    $deployApi = (-not $SkipApi).ToString().ToLowerInvariant()
    return @(
        'deployment', 'sub', $Command,
        '--name', "ets-config-$DeploymentName",
        '--location', $Location,
        '--template-file', $template,
        '--parameters', "deploymentName=$DeploymentName", "location=$Location", "tier=$Tier", "deployApi=$deployApi"
    )
}

function Write-Result {
    param([Parameter(Mandatory)]$Account, $Deployment)
    $result = [ordered]@{
        generatedAtUtc = [DateTime]::UtcNow.ToString('o')
        mode = $Mode
        tier = $Tier
        tenantId = $Account.tenantId
        subscriptionId = $Account.id
        subscriptionName = $Account.name
        deploymentName = $DeploymentName
        location = $Location
        apiEnabled = -not $SkipApi
        deployment = $Deployment
        upgradeCommand = "pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 -Mode Upgrade -Tier standard -TenantId $($Account.tenantId) -SubscriptionId $($Account.id) -DeploymentName $DeploymentName -Location $Location"
    }
    $directory = Split-Path -Parent $OutputPath
    if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
    $result | ConvertTo-Json -Depth 100 | Set-Content -Path $OutputPath -Encoding utf8
    return [pscustomobject]$result
}

Assert-Command -Name 'az'
$version = Invoke-AzJson -Arguments @('version')
if (-not $version.'azure-cli') { throw 'Unable to determine the Azure CLI version.' }

$account = Connect-EtsAzure
Write-Host "Connected to tenant $($account.tenantId), subscription $($account.name)."

if ($Mode -eq 'Connect') {
    Write-Result -Account $account -Deployment $null | Format-List
    exit 0
}

$providers = @('Microsoft.Web', 'Microsoft.Storage', 'Microsoft.Resources')
foreach ($provider in $providers) {
    & az provider register --namespace $provider --wait --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to register resource provider $provider." }
}

if ($Mode -eq 'Validate') {
    $deployment = Invoke-AzJson -Arguments (Get-DeploymentArguments -Command 'validate')
    Write-Result -Account $account -Deployment $deployment | Format-List
    exit 0
}

if ($Mode -eq 'Plan') {
    $deployment = Invoke-AzJson -Arguments ((Get-DeploymentArguments -Command 'what-if') + @('--result-format', 'ResourceIdOnly'))
    Write-Result -Account $account -Deployment $deployment | Format-List
    exit 0
}

if ($Mode -eq 'Upgrade' -and $Tier -ne 'standard') {
    throw 'Upgrade mode requires -Tier standard.'
}

$action = if ($Mode -eq 'Upgrade') { 'upgrade' } else { 'deploy' }
if ($PSCmdlet.ShouldProcess("subscription $($account.id)", "$action ETS tier '$Tier'")) {
    $deployment = Invoke-AzJson -Arguments (Get-DeploymentArguments -Command 'create')
    $result = Write-Result -Account $account -Deployment $deployment
    Write-Host "ETS Azure configuration completed. Result: $OutputPath"
    $result | Format-List
}
