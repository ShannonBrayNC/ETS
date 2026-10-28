#requires -Version 7.0
<# Create one explicitly identified synthetic event file; no HTTP calls or signing. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$EventId,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$CreatedAtUtc,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$TenantId,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$WorkspaceId,
    [Parameter(Mandatory)][string]$OutputPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($CreatedAtUtc -notmatch '(Z|[+]00:00)$') { throw 'Use an explicit stable UTC timestamp' }
$instant = [DateTimeOffset]::Parse($CreatedAtUtc, [Globalization.CultureInfo]::InvariantCulture)
if ($instant.Offset -ne [TimeSpan]::Zero) { throw 'Use UTC' }
foreach ($value in @($EventId, $TenantId, $WorkspaceId)) {
    if ($value.Length -gt 128 -or [string]::IsNullOrWhiteSpace($value)) { throw 'Invalid identifier' }
}
if ($EventId.Length -gt 118) { throw 'Event ID must fit the prefixed synthetic evidence ID' }
$content = [Text.Encoding]::UTF8.GetBytes("Synthetic SDK integration example`n")
$sha = [Security.Cryptography.SHA256]::Create()
try { $hash = ([BitConverter]::ToString($sha.ComputeHash($content))).Replace('-', '').ToLowerInvariant() }
finally { $sha.Dispose() }
$event = [ordered]@{
    schema_version = 'ets.event.v1'
    event_id = $EventId
    tenant_id = $TenantId
    workspace_id = $WorkspaceId
    evidence_id = "synthetic:$EventId"
    event_type = 'sdk.synthetic.observation'
    subject_ref = 'synthetic:integration-example'
    content_hash = $hash
    content_hash_alg = 'sha256'
    metadata = @{ synthetic = $true; description = 'Example observation, not a real-world claim' }
    created_at_utc = $CreatedAtUtc
    source_system = 'ets-sdk-powershell-example'
}
$bytes = [Text.UTF8Encoding]::new($false).GetBytes(($event | ConvertTo-Json -Depth 8) + "`n")
$stream = [IO.File]::Open([IO.Path]::GetFullPath($OutputPath), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
Write-Host 'Synthetic event saved. Preserve these exact bytes/ID/time before any capture; no network request performed.'
