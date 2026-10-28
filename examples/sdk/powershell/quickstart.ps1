#requires -Version 7.0
<#
PowerShell REST + strict CLI integration; not a native PowerShell ETS SDK module.
-Smoke uses public synthetic fixture responses and never sends HTTP requests.
#>
[CmdletBinding()]
param(
    [switch]$Smoke,
    [string]$Fixture,
    [string]$EventPath,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$TrustStore,
    [Parameter(Mandatory)][string]$ExpectedLogId,
    [string]$PythonExecutable = 'python',
    [string]$VerifierExecutable,
    [switch]$AllowLocalDev,
    [ValidateSet('None', 'Forbidden', 'Malformed', 'Tampered')][string]$SmokeFault = 'None'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Limit = 4 * 1024 * 1024
$Utf8 = [Text.UTF8Encoding]::new($false, $true)
$script:CaptureCount = 0
$script:ReadCount = 0
$script:ProofCount = 0

function Read-BoundedText([string]$Path) {
    $stream = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).Path)
    try {
        $bytes = [byte[]]::new($Limit + 1)
        $count = 0
        while ($count -lt $bytes.Length) {
            $read = $stream.Read($bytes, $count, $bytes.Length - $count)
            if ($read -eq 0) { break }
            $count += $read
        }
        if ($count -gt $Limit) { throw 'Input exceeds 4 MiB sample limit' }
        return $Utf8.GetString($bytes, 0, $count)
    } finally { $stream.Dispose() }
}

function Write-NewText([string]$Path, [string]$Text) {
    $bytes = $Utf8.GetBytes($Text)
    if ($bytes.Length -gt $Limit) { throw 'Output exceeds sample limit' }
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
}

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Parse-Response([int]$Status, [string]$Content) {
    if ($Status -lt 200 -or $Status -ge 300) {
        # Do not print arbitrary server messages, response bodies or credentials.
        throw [InvalidOperationException]::new("ETS HTTP failure: $Status")
    }
    if ($Utf8.GetByteCount($Content) -gt $Limit) { throw 'Response exceeds sample limit' }
    return [Text.Json.JsonDocument]::Parse($Content)
}

function Invoke-EtsRequest([string]$Method, [string]$RelativePath, [string]$Body = '') {
    $uri = [Uri]::new($script:BaseUri, $RelativePath)
    $headers = @{
        Accept = 'application/json'
        'X-ETS-SDK-Contract' = 'ets.application.sdk.v1'
        'X-Correlation-ID' = 'powershell-synthetic-example'
    }
    if ($script:Bearer) { $headers.Authorization = "Bearer $script:Bearer" }
    if ($script:ApiKey) { $headers['X-ETS-API-Key'] = $script:ApiKey }
    if ($script:DevelopmentScope) {
        $headers['X-ETS-Tenant'] = $script:Event.GetProperty('tenant_id').GetString()
        $headers['X-ETS-Workspace'] = $script:Event.GetProperty('workspace_id').GetString()
    }
    if ($Smoke) {
        Require ($uri.Scheme -eq 'https' -and $uri.Host -eq 'ets.example') 'Unexpected synthetic origin'
        Require ($headers['X-ETS-SDK-Contract'] -eq 'ets.application.sdk.v1') 'Missing SDK contract'
        Require ($headers.Authorization -eq 'Bearer synthetic-not-a-secret') 'Missing synthetic auth'
        Require (-not $headers.ContainsKey('X-ETS-Tenant')) 'Bearer requests must not set scope headers'
        if ($SmokeFault -eq 'Forbidden') { return (Parse-Response 403 '{}') }
        if ($SmokeFault -eq 'Malformed') { return (Parse-Response 200 'not-json') }
        $eventIdJson = ConvertTo-Json -InputObject $script:EventId -Compress
        switch ("$Method $RelativePath") {
            'GET health' { return (Parse-Response 200 '{"status":"ok","version":"0.1.0a1"}') }
            'GET version' { return (Parse-Response 200 '{"name":"ETS","version":"0.1.0a1","api_version":"v1"}') }
            'POST api/v1/events' {
                $submitted = [Text.Json.JsonDocument]::Parse($Body)
                try {
                    Require ($submitted.RootElement.GetProperty('event_id').GetString() -ceq $script:EventId) 'Wrong event submitted'
                    Require ($submitted.RootElement.GetRawText() -ceq $script:Event.GetRawText()) 'Prepared event changed'
                } finally { $submitted.Dispose() }
                $script:CaptureCount++
                $head = $script:FixtureDocument.RootElement.GetProperty('tree_head').GetRawText()
                $hash = ConvertTo-Json -InputObject $script:FixtureDocument.RootElement.GetProperty('event_hash').GetString() -Compress
                $index = $script:FixtureDocument.RootElement.GetProperty('inclusion_proof').GetProperty('leaf_index').GetInt64()
                return (Parse-Response 201 "{`"event_id`":$eventIdJson,`"log_index`":$index,`"event_hash`":$hash,`"tree_head`":$head,`"inclusion_proof_url`":`"/api/v1/proofs/inclusion/$script:EncodedId`"}")
            }
            "GET api/v1/events/$script:EncodedId" {
                $script:ReadCount++
                $root = $script:FixtureDocument.RootElement
                $index = $root.GetProperty('inclusion_proof').GetProperty('leaf_index').GetInt64()
                $eventHash = ConvertTo-Json -InputObject $root.GetProperty('event_hash').GetString() -Compress
                $leafHash = ConvertTo-Json -InputObject $root.GetProperty('leaf_hash').GetString() -Compress
                return (Parse-Response 200 "{`"log_index`":$index,`"event_hash`":$eventHash,`"leaf_hash`":$leafHash,`"event`":$($script:Event.GetRawText())}")
            }
            "GET api/v1/proofs/inclusion/$script:EncodedId" {
                $script:ProofCount++
                return (Parse-Response 200 $script:FixtureDocument.RootElement.GetProperty('inclusion_proof').GetRawText())
            }
            "GET api/v1/bundles/$script:EncodedId" {
                $content = $script:FixtureDocument.RootElement.GetRawText()
                if ($SmokeFault -eq 'Tampered') { $content = $content.Replace('Fictional Simulation', 'Changed Simulation') }
                return (Parse-Response 200 $content)
            }
            default { throw 'Unexpected synthetic request' }
        }
    }
    $arguments = @{
        Uri = $uri; Method = $Method; Headers = $headers
        TimeoutSec = 10; MaximumRedirection = 0; MaximumRetryCount = 0
        SkipHttpErrorCheck = $true
    }
    if ($Body) { $arguments.Body = $Utf8.GetBytes($Body); $arguments.ContentType = 'application/json' }
    # The response limit is checked after buffering; not a streaming memory bound.
    $response = Invoke-WebRequest @arguments
    return (Parse-Response ([int]$response.StatusCode) ([string]$response.Content))
}

function Invoke-StrictVerifier([string]$BundlePath, [string]$ReportPath) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    if ($VerifierExecutable) { $start.FileName = $VerifierExecutable }
    else {
        $start.FileName = $PythonExecutable
        foreach ($argument in @('-I', '-m', 'ets.verifier.cli')) { $start.ArgumentList.Add($argument) }
    }
    foreach ($argument in @('offline', $BundlePath, '--expected-log-id', $ExpectedLogId, '--report', $ReportPath)) {
        $start.ArgumentList.Add($argument)
    }
    if ($TrustStore) {
        $start.ArgumentList.Add('--trust-store')
        $start.ArgumentList.Add((Resolve-Path -LiteralPath $TrustStore).Path)
    }
    foreach ($name in @('ETS_VERIFY_BEARER_TOKEN', 'ETS_VERIFY_API_KEY', 'ETS_BEARER_TOKEN', 'ETS_API_KEY', 'PYTHONHOME', 'PYTHONPATH')) {
        $null = $start.Environment.Remove($name)
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(30000)) { $process.Kill($true); throw 'Verifier timed out' }
        $text = $stdout.GetAwaiter().GetResult()
        Require ([string]::IsNullOrEmpty($stderr.GetAwaiter().GetResult())) 'Unexpected verifier diagnostic'
        Require ($process.ExitCode -in @(0, 1, 2)) 'Unexpected verifier exit code'
        $result = [Text.Json.JsonDocument]::Parse($text)
        try {
            $status = $result.RootElement.GetProperty('status').GetString()
            Write-Host "verifier_status=$status; verifier_exit=$($process.ExitCode)"
            if ($process.ExitCode -eq 0) {
                Require ($result.RootElement.GetProperty('valid').GetBoolean()) 'Inconsistent verifier success'
                Require ($status -eq 'valid') 'Unexpected successful verifier status'
            }
        } finally { $result.Dispose() }
        return $process.ExitCode
    } finally { $process.Dispose() }
}

$script:FixtureDocument = $null
$eventDocument = $null
try {
    Require (-not (Test-Path -LiteralPath $OutputDirectory)) 'Use a new output directory'
    $output = [IO.Path]::GetFullPath($OutputDirectory)
    Require ([IO.Directory]::Exists([IO.Path]::GetDirectoryName($output))) 'Output parent must exist'
    if ($TrustStore) { $null = Resolve-Path -LiteralPath $TrustStore }
    $script:DevelopmentScope = $false
    $script:ApiKey = $null
    if ($Smoke) {
        Require ([bool]$Fixture) 'Smoke requires -Fixture'
        $script:FixtureDocument = [Text.Json.JsonDocument]::Parse((Read-BoundedText $Fixture))
        $script:Event = $script:FixtureDocument.RootElement.GetProperty('event')
        $script:BaseUri = [Uri]'https://ets.example/'
        $script:Bearer = 'synthetic-not-a-secret'
    } else {
        Require ([bool]$EventPath) 'Live mode requires a prepared -EventPath'
        Require ($SmokeFault -eq 'None') 'Smoke faults are not allowed for live capture'
        $eventDocument = [Text.Json.JsonDocument]::Parse((Read-BoundedText $EventPath))
        $script:Event = $eventDocument.RootElement
        $script:BaseUri = [Uri]$env:ETS_BASE_URL
        Require ($script:BaseUri.IsAbsoluteUri -and -not $script:BaseUri.UserInfo -and -not $script:BaseUri.Query -and -not $script:BaseUri.Fragment -and $script:BaseUri.AbsolutePath -eq '/') 'Use an absolute root endpoint without embedded credentials'
        $script:Bearer = $env:ETS_BEARER_TOKEN
        $script:ApiKey = $env:ETS_API_KEY
        Require (-not ($script:Bearer -and $script:ApiKey)) 'Choose exactly one authentication mode'
        if ($AllowLocalDev) {
            Require ($script:BaseUri.Scheme -eq 'http' -and $script:BaseUri.IsLoopback -and -not $script:Bearer) 'Development mode requires loopback HTTP and no bearer token'
            $script:DevelopmentScope = $true
        } else {
            Require ($script:BaseUri.Scheme -eq 'https') 'Live mode requires HTTPS'
            Require (-not [string]::IsNullOrWhiteSpace($script:Bearer) -or -not [string]::IsNullOrWhiteSpace($script:ApiKey)) 'Provide one nonempty credential'
        }
    }
    $script:EventId = $script:Event.GetProperty('event_id').GetString()
    Require (-not [string]::IsNullOrWhiteSpace($script:EventId)) 'Prepared event ID is required'
    $timestampText = $script:Event.GetProperty('created_at_utc').GetString()
    Require ($timestampText -match '(Z|[+]00:00)$') 'Timestamp must contain an explicit UTC offset'
    $timestamp = [DateTimeOffset]::Parse($timestampText, [Globalization.CultureInfo]::InvariantCulture)
    Require ($timestamp.Offset -eq [TimeSpan]::Zero) 'Use an explicit stable UTC event timestamp'
    $script:EncodedId = [Uri]::EscapeDataString($script:EventId)
    # Reserve the directory before any capture. All individual writes still use CreateNew.
    $null = New-Item -ItemType Directory -Path $output -ErrorAction Stop
    Write-NewText (Join-Path $output 'attempted-event.json') $script:Event.GetRawText()
    $health = Invoke-EtsRequest 'GET' 'health'
    try { $null = $health.RootElement.GetProperty('status').GetString() } finally { $health.Dispose() }
    $version = Invoke-EtsRequest 'GET' 'version'
    try { Require ($version.RootElement.GetProperty('api_version').GetString() -eq 'v1') 'Unsupported API version' } finally { $version.Dispose() }
    $receipt = Invoke-EtsRequest 'POST' 'api/v1/events' $script:Event.GetRawText()
    try {
        Require ($receipt.RootElement.GetProperty('event_id').GetString() -ceq $script:EventId) 'Receipt event ID mismatch'
        Write-NewText (Join-Path $output 'api-append-response.json') $receipt.RootElement.GetRawText()
    } finally { $receipt.Dispose() }
    # Raw REST append response is not the language SDK's normalized receipt object.
    Write-Host 'capture=committed_local; independent_verification=not_yet_performed'
    foreach ($operation in @(@('events', 'event-record.json'), @('proofs/inclusion', 'inclusion-proof.json'), @('bundles', 'bundle.json'))) {
        $document = Invoke-EtsRequest 'GET' "api/v1/$($operation[0])/$script:EncodedId"
        try { Write-NewText (Join-Path $output $operation[1]) $document.RootElement.GetRawText() }
        finally { $document.Dispose() }
    }
    if ($Smoke) {
        Require ($script:CaptureCount -eq 1 -and $script:ReadCount -eq 1 -and $script:ProofCount -eq 1) 'Unexpected synthetic operation counts'
        Write-Host 'mode=simulated_transport; capture_read_proof_export=passed'
    }
    $exitCode = Invoke-StrictVerifier (Join-Path $output 'bundle.json') (Join-Path $output 'verification.json')
} catch {
    Write-Host "Sample failed: $($_.Exception.GetType().Name); inspect configuration locally. A failed capture may have committed; reconcile the retained event ID before retrying."
    $exitCode = 3
} finally {
    if ($null -ne $script:FixtureDocument) { $script:FixtureDocument.Dispose() }
    if ($null -ne $eventDocument) { $eventDocument.Dispose() }
}
exit $exitCode
