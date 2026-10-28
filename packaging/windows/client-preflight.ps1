# Read-only client observations; writes one new report, never installs or changes trust.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Package,
    [Parameter(Mandatory)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256,
    [Parameter(Mandatory)][string]$OutputFile
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Client preflight requires Windows and PowerShell 7.' }
if (Test-Path -LiteralPath $OutputFile) { throw 'Choose a new report filename.' }
$source = (Resolve-Path -LiteralPath $Package).Path
if ([IO.Path]::GetExtension($source) -ne '.msix') { throw 'Expected an MSIX file.' }
$hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
$signature = Get-AuthenticodeSignature -LiteralPath $source
$os = Get-CimInstance Win32_OperatingSystem
$architecture = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
$elevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$runtimeKey = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
$runtime = @()
foreach ($scope in @('LocalMachine', 'CurrentUser')) {
    $view = if ($scope -eq 'LocalMachine') { [Microsoft.Win32.RegistryView]::Registry32 } else { [Microsoft.Win32.RegistryView]::Registry64 }
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::$scope, $view)
    try {
        $key = $base.OpenSubKey($runtimeKey)
        if ($key) {
            try {
                $value = [string]$key.GetValue('pv', '')
                $version = $null
                if ([version]::TryParse($value, [ref]$version) -and $version -gt [version]'0.0.0.0') {
                    $runtime += [ordered]@{ scope = $scope; version = $value }
                }
            } finally { $key.Dispose() }
        }
    } finally { $base.Dispose() }
}
$toolsOnPath = @('python', 'python3', 'pip', 'git', 'makeappx', 'signtool' | Where-Object {
    $null -ne (Get-Command $_ -ErrorAction SilentlyContinue)
})
$checks = [ordered]@{
    reviewedHashMatches = $hash -ceq $ExpectedSha256.ToLowerInvariant()
    signatureTrustedOnThisMachine = $signature.Status -eq 'Valid'
    windows11Client = [int]$os.ProductType -eq 1 -and [int]$os.BuildNumber -ge 22000
    x64OperatingSystem = $architecture -eq 'X64'
    nonElevatedToken = -not $elevated
    evergreenWebView2Registered = $runtime.Count -gt 0
}
$passed = @($checks.Values | Where-Object { $_ -ne $true }).Count -eq 0
$record = [ordered]@{
    schemaVersion = 1
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
    package = [IO.Path]::GetFileName($source)
    sha256 = $hash
    expectedSha256 = $ExpectedSha256.ToLowerInvariant()
    signatureStatus = $signature.Status.ToString()
    signerThumbprint = if ($signature.SignerCertificate) { $signature.SignerCertificate.Thumbprint } else { $null }
    osVersion = $os.Version
    osBuild = $os.BuildNumber
    osProductType = [int]$os.ProductType
    osArchitecture = $architecture
    elevated = $elevated
    webView2Registrations = $runtime
    developerCommandsOnPath = $toolsOnPath
    checks = $checks
    automaticPrerequisitesPassed = $passed
    clientQualified = $false
    releaseApproved = $false
    manualChecksRequired = @('Clean OS snapshot and absence of developer tools',
        'Runtime provisioning and actual startup', 'Install and package-identity launch',
        'Real dialogs, network-disabled verification and report export',
        'Keyboard, Narrator and scaling', 'Upgrade, downgrade, uninstall and reinstall',
        'Licensing, WACK and Store review')
    limitations = @('Registry detection does not prove WebView2 can launch.',
        'Commands on PATH may be aliases; absence does not prove tools are not installed.',
        'Signature trust is observed only on this machine; no trust settings are changed.',
        'This is preflight evidence, never a completed client qualification.')
}
$json = $record | ConvertTo-Json -Depth 6
$stream = [IO.File]::Open([IO.Path]::GetFullPath($OutputFile), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
$writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($false))
try { $writer.WriteLine($json) } finally { $writer.Dispose() }
Write-Output "Preflight report: $OutputFile; automatic prerequisites passed: $passed; client qualification: NOT RUN"
if (-not $passed) { exit 2 }
