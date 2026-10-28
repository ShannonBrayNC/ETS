[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Package,
    [Parameter(Mandatory)][ValidatePattern('^[0-9A-Fa-f]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [Parameter(Mandatory)][string]$SignToolPath
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Signing requires Windows and the Windows SDK.' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output directory; existing output is protected.' }
$source = (Resolve-Path -LiteralPath $Package).Path
$tool = (Resolve-Path -LiteralPath $SignToolPath).Path
if ([IO.Path]::GetExtension($source) -ne '.msix') { throw 'Expected an MSIX package.' }

# Inspect without extraction or modifying the source. Only the development identity is allowed.
$archive = [IO.Compression.ZipFile]::OpenRead($source)
try {
    $entries = @($archive.Entries | Where-Object { $_.FullName -eq 'AppxManifest.xml' })
    if ($entries.Count -ne 1) { throw 'Expected exactly one package manifest.' }
    if ($archive.GetEntry('AppxSignature.p7x')) { throw 'Expected an unsigned development package.' }
    $settings = [Xml.XmlReaderSettings]::new()
    $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    $settings.XmlResolver = $null
    $settings.MaxCharactersInDocument = 1048576
    $stream = $entries[0].Open()
    $reader = [Xml.XmlReader]::Create($stream, $settings)
    try {
        $manifest = [Xml.XmlDocument]::new()
        $manifest.XmlResolver = $null
        $manifest.Load($reader)
    } finally { $reader.Dispose(); $stream.Dispose() }
    $ns = [Xml.XmlNamespaceManager]::new($manifest.NameTable)
    $ns.AddNamespace('p', 'http://schemas.microsoft.com/appx/manifest/foundation/windows10')
    $identity = $manifest.SelectSingleNode('/p:Package/p:Identity', $ns)
    if (-not $identity -or $identity.GetAttribute('Name') -cne 'ETSVerifier.Development' -or
        $identity.GetAttribute('Publisher') -cne 'CN=ETSVerifier.Development' -or
        $identity.GetAttribute('ProcessorArchitecture') -cne 'x64') {
        throw 'Only the x64 ETSVerifier.Development identity may be signed by this helper.'
    }
    $version = $identity.GetAttribute('Version')
    if ($version -notmatch '^(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\.0$' -or
        @($version.Split('.') | Where-Object { [int]$_ -gt 65535 }).Count -gt 0) {
        throw 'Invalid development package version.'
    }
} finally { $archive.Dispose() }

$cert = Get-Item -LiteralPath "Cert:\CurrentUser\My\$CertificateThumbprint"
if ($cert.Subject -cne 'CN=ETSVerifier.Development') { throw 'Certificate subject must exactly match the development publisher.' }
if (-not $cert.HasPrivateKey) { throw 'Certificate has no accessible private key.' }
$now = Get-Date
if ($cert.NotBefore -gt $now -or $cert.NotAfter -le $now) { throw 'Certificate is outside its validity period.' }
$eku = @($cert.EnhancedKeyUsageList | ForEach-Object { $_.ObjectId.Value })
if ('1.3.6.1.5.5.7.3.3' -notin $eku) { throw 'Certificate must explicitly permit code signing.' }

New-Item -Path $OutputDirectory -ItemType Directory | Out-Null
$out = (Resolve-Path -LiteralPath $OutputDirectory).Path
$destination = Join-Path $out "ETSVerifier.Development_${version}_x64_signed.msix"
$sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
Copy-Item -LiteralPath $source -Destination $destination
# Select only the explicitly supplied CurrentUser/My certificate. No PFX/password arguments.
& $tool sign /fd SHA256 /s My /sha1 $CertificateThumbprint $destination
if ($LASTEXITCODE -ne 0) { throw 'SignTool signing failed; output is not qualified.' }
& $tool verify /pa /v $destination
if ($LASTEXITCODE -ne 0) { throw 'SignTool trust verification failed; output is not qualified.' }
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sourceHash) {
    throw 'Source package changed during signing; output is not qualified.'
}
[ordered]@{
    package = [IO.Path]::GetFileName($destination)
    sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    unsignedSha256 = $sourceHash
    certificateThumbprint = $cert.Thumbprint
    certificateExpiresAtUtc = $cert.NotAfter.ToUniversalTime().ToString('o')
    publisher = $cert.Subject
    identity = 'ETSVerifier.Development'
    version = $version
    signed = $true
    signatureVerifiedOnSigningMachine = $true
    timestamped = $false
    installationTested = $false
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json | Set-Content (Join-Path $out 'signing.json') -Encoding utf8
Write-Output "Signed development candidate: $destination"
