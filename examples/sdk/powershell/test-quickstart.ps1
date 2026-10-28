#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Fixture,
    [Parameter(Mandatory)][string]$TrustStore,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$PythonExecutable = 'python'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Expected native child exits are checked explicitly below, including 1/2/3.
$PSNativeCommandUseErrorActionPreference = $false
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Use a new test output directory' }
$root = (New-Item -ItemType Directory -Path $OutputDirectory).FullName
$script = Join-Path $PSScriptRoot 'quickstart.ps1'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$fixturePath = (Resolve-Path -LiteralPath $Fixture).Path
$trustPath = (Resolve-Path -LiteralPath $TrustStore).Path

function Run-Case([string]$Name, [int]$ExpectedExit, [string]$Fault = 'None', [bool]$WithTrust = $true) {
    $args = @('-NoProfile', '-File', $script, '-Smoke', '-Fixture', $fixturePath,
              '-OutputDirectory', (Join-Path $root $Name), '-ExpectedLogId', 'ets-cli-golden-fixture',
              '-PythonExecutable', $PythonExecutable, '-SmokeFault', $Fault)
    if ($WithTrust) { $args += @('-TrustStore', $trustPath) }
    & $pwsh @args
    if ($LASTEXITCODE -ne $ExpectedExit) { throw "$Name expected $ExpectedExit, got $LASTEXITCODE" }
}

$preparedPath = Join-Path $root 'prepared-event.json'
& $pwsh -NoProfile -File (Join-Path $PSScriptRoot 'new-synthetic-event.ps1') `
    -EventId evt_powershell_smoke -CreatedAtUtc '2026-10-28T12:00:00Z' `
    -TenantId synthetic-tenant -WorkspaceId sample -OutputPath $preparedPath
if ($LASTEXITCODE -ne 0) { throw 'Synthetic event preparation failed' }
$prepared = [Text.Json.JsonDocument]::Parse([IO.File]::ReadAllText($preparedPath))
try {
    if ($prepared.RootElement.GetProperty('event_id').GetString() -cne 'evt_powershell_smoke' -or
        $prepared.RootElement.GetProperty('created_at_utc').GetString() -cne '2026-10-28T12:00:00Z' -or
        $prepared.RootElement.GetProperty('content_hash').GetString() -cne '38d38f9443a7aadbd82d0a0ac048e2a5d44ad8e07b8a60d996d144e7961a1d0e') {
        throw 'Synthetic event identity/time/content digest mismatch'
    }
} finally { $prepared.Dispose() }

Run-Case 'valid' 0
Run-Case 'tampered' 1 'Tampered'
Run-Case 'missing-trust' 2 'None' $false
Run-Case 'forbidden' 3 'Forbidden'
Run-Case 'malformed' 3 'Malformed'
$before = (Get-FileHash -LiteralPath (Join-Path $root 'valid/bundle.json') -Algorithm SHA256).Hash
Run-Case 'valid' 3
$after = (Get-FileHash -LiteralPath (Join-Path $root 'valid/bundle.json') -Algorithm SHA256).Hash
if ($before -cne $after) { throw 'Existing output was modified' }
foreach ($entry in @(@('valid', 'valid'), @('tampered', 'invalid'), @('missing-trust', 'indeterminate'))) {
    $report = [Text.Json.JsonDocument]::Parse([IO.File]::ReadAllText((Join-Path $root "$($entry[0])/verification.json")))
    try {
        if ($report.RootElement.GetProperty('outcome').GetProperty('status').GetString() -cne $entry[1]) {
            throw 'Unexpected report status'
        }
    } finally { $report.Dispose() }
}
Write-Host 'PowerShell smoke passed: capture/read/proof/export, strict valid/invalid/missing-trust, 403/malformed, no-overwrite.'

# Every expected native exit and report assertion passed. Do not leak the last
# intentionally failing child exit through the GitHub Actions PowerShell wrapper.
exit 0
