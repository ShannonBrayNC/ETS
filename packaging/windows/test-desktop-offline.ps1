# Run only on a disposable Windows test machine with enabled Windows Firewall.
[CmdletBinding()]
param(
    [string]$DesktopDirectory = 'dist/ets-desktop',
    [string]$Bundle = 'tests/fixtures/verifier/native-signed.json',
    [string]$Trust = 'tests/fixtures/verifier/native-trust.json',
    [string]$OutputDirectory = 'test-results/offline-desktop'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Windows Firewall qualification requires Windows.' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a fresh output directory.' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Firewall test setup requires an elevated disposable test session.'
}
$profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore)
if ($profiles.Count -ne 3 -or @($profiles | Where-Object { $_.Enabled -ne 'True' -or $_.AllowLocalFirewallRules -eq 'False' }).Count) {
    throw 'All firewall profiles must be enabled and permit local test rules.'
}
$root = (Resolve-Path -LiteralPath $DesktopDirectory).Path
$desktop = Join-Path $root 'ets-desktop.exe'
$verifier = Join-Path $root 'verifier/ets-verify.exe'
foreach ($required in @($desktop, $verifier)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing executable: $required" }
}
$fixture = (Resolve-Path -LiteralPath $Bundle).Path
$trustedKeys = (Resolve-Path -LiteralPath $Trust).Path
$runtimeRoots = @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA) |
    Where-Object { $_ } | ForEach-Object { Join-Path $_ 'Microsoft/EdgeWebView/Application' } |
    Where-Object { Test-Path -LiteralPath $_ }
$runtimeExecutables = @($runtimeRoots | ForEach-Object { Get-ChildItem -LiteralPath $_ -Recurse -File -Filter '*.exe' })
if (-not @($runtimeExecutables | Where-Object Name -eq 'msedgewebview2.exe').Count) {
    throw 'No installed WebView2 runtime executable found; cannot qualify network blocking.'
}
$programs = @(@(Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.exe') + $runtimeExecutables |
    ForEach-Object FullName | Sort-Object -Unique)
New-Item $OutputDirectory -ItemType Directory | Out-Null
$out = (Resolve-Path -LiteralPath $OutputDirectory).Path
$result = Join-Path $out 'smoke.json'
$group = 'ETS-offline-test-' + [guid]::NewGuid().ToString()
$rules = [Collections.Generic.List[string]]::new()
$observed = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$process = $null
$passed = $false
try {
    foreach ($program in $programs) {
        foreach ($direction in @('Inbound', 'Outbound')) {
            $name = $group + '-' + $rules.Count
            $rules.Add($name)
            New-NetFirewallRule -Name $name -DisplayName $name -Group $group -Program $program `
                -Direction $direction -Action Block -Enabled True -Profile Any | Out-Null
            $effective = Get-NetFirewallRule -PolicyStore ActiveStore -Name $name
            if ($effective.Enabled -ne 'True' -or $effective.Action -ne 'Block') {
                throw 'Firewall rule is not active.'
            }
            $filter = $effective | Get-NetFirewallApplicationFilter
            if ($filter.Program -ne $program) { throw 'Firewall executable filter mismatch.' }
        }
    }
    $start = [Diagnostics.ProcessStartInfo]::new($desktop)
    $start.UseShellExecute = $false
    foreach ($argument in @('--smoke-test', '--smoke-result', $result, '--smoke-bundle', $fixture, '--smoke-trust', $trustedKeys)) {
        $start.ArgumentList.Add($argument)
    }
    $process = [Diagnostics.Process]::Start($start)
    $deadline = [DateTime]::UtcNow.AddMinutes(5)
    while (-not $process.HasExited) {
        foreach ($runtime in @(Get-Process -Name msedgewebview2 -ErrorAction SilentlyContinue)) {
            if ($runtime.Path) {
                if ($runtime.Path -notin $programs) { throw 'An observed WebView2 executable was not blocked.' }
                [void]$observed.Add($runtime.Path)
            }
        }
        if ([DateTime]::UtcNow -gt $deadline) { throw 'Offline desktop smoke timed out.' }
        Start-Sleep -Milliseconds 100
        $process.Refresh()
    }
    if ($process.ExitCode -ne 0) { Get-Content $result -ErrorAction SilentlyContinue; throw 'Offline desktop smoke failed.' }
    if ($observed.Count -eq 0) { throw 'No running WebView2 executable was observed; coverage is unproven.' }
    $smoke = Get-Content -LiteralPath $result -Raw | ConvertFrom-Json
    if ($smoke.status -ne 0) { throw 'Smoke result did not report success.' }
    $passed = $true
} finally {
    try {
        if ($process -and -not $process.HasExited) { $process.Kill($true); $process.WaitForExit() }
    } catch {
        $passed = $false
        Write-Warning "Process cleanup failed: $_"
    }
    foreach ($name in $rules) { Remove-NetFirewallRule -Name $name -ErrorAction SilentlyContinue }
    $remaining = @(Get-NetFirewallRule -Group $group -ErrorAction SilentlyContinue)
    [ordered]@{
        passed = $passed -and $remaining.Count -eq 0
        scope = 'Program-scoped Windows Firewall rules on engineering runner; not physical network isolation'
        osVersion = [Environment]::OSVersion.VersionString
        elevatedTestSession = $true
        blockedExecutables = $programs
        observedWebViewExecutables = @($observed)
        rulesRemoved = $remaining.Count -eq 0
        cleanWindows11Qualified = $false
        createdAtUtc = [DateTime]::UtcNow.ToString('o')
    } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'network-qualification.json') -Encoding utf8
    if ($remaining.Count) { throw "Test firewall rules remain in group $group" }
}
