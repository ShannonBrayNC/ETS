#requires -Version 7.0
<#
.SYNOPSIS
    Safely processes GitHub issues one at a time with Codex for Lantern Protocol repositories.

.DESCRIPTION
    Optimized for unattended edits without approving every file change.
    Safety is enforced through issue labels, isolated branches, draft PRs, validation gates, blocked states, and follow-up review issues.

.EXAMPLE
    $env:GITHUB_REPOSITORY = "ShannonBrayNC/ETS"
    $env:LANTERN_PROTOCOL_COMPONENT = "ETS trust and consent layer"
    $env:CODEX_COMMAND = "codex"
    $env:CODEX_ARGS_TEMPLATE = "exec --full-auto --input {PromptPath}"
    pwsh ./scripts/Invoke-LanternProtocolCodexQueue.ps1 -Mode Full -MaxIssues 5
#>

[CmdletBinding()]
param(
    [ValidateSet("WorkQueue", "ReviewOnly", "Full")]
    [string] $Mode = "Full",
    [string] $Repository = $env:GITHUB_REPOSITORY,
    [string] $BaseBranch = "main",
    [string] $ReadyLabel = "codex-ready",
    [string] $InProgressLabel = "codex-in-progress",
    [string] $DoneLabel = "codex-done",
    [string] $BlockedLabel = "codex-blocked",
    [string] $ReviewLabel = "needs-technical-review",
    [string] $FollowUpLabel = "review-follow-up",
    [int] $MaxIssues = 10,
    [int] $MaxCodexAttempts = 2,
    [switch] $CreateDraftPr = $true,
    [switch] $DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param([string] $Message) Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Warn { param([string] $Message) Write-Host "WARN: $Message" -ForegroundColor Yellow }
function Write-Fail { param([string] $Message) Write-Host "ERROR: $Message" -ForegroundColor Red }

function Assert-Command {
    param([string] $Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "Required command '$Name' was not found on PATH." }
}

function Invoke-Logged {
    param([Parameter(Mandatory)][string] $Command, [string[]] $Arguments = @(), [switch] $AllowFailure)
    Write-Host "> $Command $($Arguments -join ' ')" -ForegroundColor DarkGray
    if ($DryRun) { return [pscustomobject]@{ ExitCode = 0; Output = "[dry-run] $Command $($Arguments -join ' ')" } }
    $output = & $Command @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not $AllowFailure) { throw "Command failed with exit code $exitCode.`n$Command $($Arguments -join ' ')`n$(($output | Out-String).Trim())" }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = ($output | Out-String).Trim() }
}

function Get-Json {
    param([string] $Command, [string[]] $Arguments)
    $result = Invoke-Logged -Command $Command -Arguments $Arguments
    if ([string]::IsNullOrWhiteSpace($result.Output)) { return $null }
    return $result.Output | ConvertFrom-Json
}

function Ensure-Repo {
    if ([string]::IsNullOrWhiteSpace($Repository)) { throw "Repository is required. Set `$env:GITHUB_REPOSITORY." }
    Assert-Command gh
    Assert-Command git
    $codexCommand = if ($env:CODEX_COMMAND) { $env:CODEX_COMMAND } else { "codex" }
    Assert-Command $codexCommand
    Invoke-Logged gh @("repo", "view", $Repository) | Out-Null
}

function Ensure-Labels {
    $labels = @(
        @{ Name=$ReadyLabel; Color="0e8a16"; Description="Ready for Codex implementation" },
        @{ Name=$InProgressLabel; Color="fbca04"; Description="Codex is processing this issue" },
        @{ Name=$DoneLabel; Color="5319e7"; Description="Codex implementation PR created" },
        @{ Name=$BlockedLabel; Color="d93f0b"; Description="Codex could not safely complete this issue" },
        @{ Name=$ReviewLabel; Color="1d76db"; Description="Needs technical review" },
        @{ Name=$FollowUpLabel; Color="b60205"; Description="Created by technical review" }
    )
    foreach ($label in $labels) {
        $existing = Invoke-Logged gh @("label", "list", "--repo", $Repository, "--search", $label.Name, "--json", "name") -AllowFailure
        if ($existing.Output -notmatch [regex]::Escape($label.Name)) {
            Invoke-Logged gh @("label", "create", $label.Name, "--repo", $Repository, "--color", $label.Color, "--description", $label.Description) | Out-Null
        }
    }
}

function Get-NextIssue {
    $issues = Get-Json gh @("issue", "list", "--repo", $Repository, "--state", "open", "--label", $ReadyLabel, "--json", "number,title,body,labels,url", "--limit", "100")
    if (-not $issues) { return $null }
    $eligible = @($issues | Where-Object {
        $names = @($_.labels | ForEach-Object { $_.name })
        ($names -notcontains $InProgressLabel) -and ($names -notcontains $DoneLabel) -and ($names -notcontains $BlockedLabel)
    } | Sort-Object number)
    if ($eligible.Count -eq 0) { return $null }
    return $eligible[0]
}

function New-BranchName { param([int] $IssueNumber, [string] $Title)
    $slug = ($Title.ToLowerInvariant() -replace "[^a-z0-9]+", "-").Trim("-")
    if ($slug.Length -gt 48) { $slug = $slug.Substring(0,48).Trim("-") }
    return "codex/issue-$IssueNumber-$slug"
}

function Get-ValidationCommands {
    $commands = New-Object System.Collections.Generic.List[string]
    if (Test-Path "package.json") {
        $pkg = Get-Content "package.json" -Raw | ConvertFrom-Json
        if ($pkg.scripts.lint) { $commands.Add("npm run lint") }
        if ($pkg.scripts.typecheck) { $commands.Add("npm run typecheck") }
        if ($pkg.scripts.test) { $commands.Add("npm test") }
        if ($pkg.scripts.build) { $commands.Add("npm run build") }
    }
    if (Test-Path "pyproject.toml") {
        if (Get-Command ruff -ErrorAction SilentlyContinue) { $commands.Add("ruff check .") }
        if (Get-Command pytest -ErrorAction SilentlyContinue) { $commands.Add("pytest") }
    }
    if (@(Get-ChildItem . -Filter "*.sln" -Recurse -ErrorAction SilentlyContinue).Count -gt 0 -and (Get-Command dotnet -ErrorAction SilentlyContinue)) {
        $commands.Add("dotnet build")
        $commands.Add("dotnet test --no-build")
    }
    if ($commands.Count -eq 0) { $commands.Add("git status --short") }
    return @($commands)
}

function Invoke-Validation {
    $failed = $false
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($line in Get-ValidationCommands) {
        Write-Step "Validation: $line"
        $split = $line -split " "
        $result = Invoke-Logged $split[0] @($split | Select-Object -Skip 1) -AllowFailure
        if ($result.ExitCode -ne 0) { $failed = $true }
        $status = if ($result.ExitCode -eq 0) { "PASS" } else { "FAIL" }
        $out = $result.Output
        if ($out.Length -gt 12000) { $out = $out.Substring(0,12000) + "`n...[truncated]" }
        $parts.Add("### $status`: `$line``n``````text`n$out`n``````")
    }
    return [pscustomobject]@{ Failed=$failed; Body=($parts -join "`n`n") }
}

function Invoke-CodexTemplate { param([string] $PromptPath)
    $cmd = if ($env:CODEX_COMMAND) { $env:CODEX_COMMAND } else { "codex" }
    $template = if ($env:CODEX_ARGS_TEMPLATE) { $env:CODEX_ARGS_TEMPLATE } else { "exec --input {PromptPath}" }
    $resolved = $template.Replace("{PromptPath}", $PromptPath)
    return Invoke-Logged $cmd @($resolved -split " " | Where-Object { $_ }) -AllowFailure
}

function Test-UnsafeChanges {
    $status = Invoke-Logged git @("status", "--porcelain")
    $patterns = @("\.env$", "\.pem$", "\.pfx$", "id_rsa", "secrets?\.", "node_modules/", "\.venv/", "dist/", "build/", "\.log$")
    foreach ($line in @($status.Output -split "`n")) {
        foreach ($pattern in $patterns) {
            if ($line -match $pattern) { return [pscustomobject]@{ Unsafe=$true; Reason="Unsafe or generated file matched '$pattern': $line" } }
        }
    }
    return [pscustomobject]@{ Unsafe=$false; Reason="" }
}

function Invoke-CodexForIssue { param([int] $IssueNumber, [string] $IssueTitle, [string] $IssueBody)
    New-Item -ItemType Directory -Path ".codex" -Force | Out-Null
    $promptPath = Join-Path ".codex" "issue-$IssueNumber.md"
    $component = if ($env:LANTERN_PROTOCOL_COMPONENT) { $env:LANTERN_PROTOCOL_COMPONENT } else { "Lantern Protocol component" }
    $prompt = @"
You are working in $Repository, part of the Lantern Protocol stack.

Component context: $component

Run mode:
- You may edit files without per-edit approval.
- The controller owns git, push, and PR operations.
- Do not merge, release, publish secrets, or call production services.

Hard scope:
- Implement only GitHub issue #$IssueNumber.
- Prefer the smallest safe vertical slice.
- Do not perform unrelated rewrites.
- Preserve consent, provenance, auditability, explainability, human override, and cross-stack integration contracts.
- Do not invent credentials, tenant IDs, secrets, or production endpoints.

Issue title:
$IssueTitle

Issue body:
$IssueBody

Return a concise Markdown summary with files changed, behavior implemented, validation performed, and follow-up risks.
"@
    Set-Content $promptPath $prompt -Encoding UTF8
    $last = ""
    for ($i = 1; $i -le $MaxCodexAttempts; $i++) {
        Write-Step "Running Codex for issue #$IssueNumber, attempt $i of $MaxCodexAttempts"
        $result = Invoke-CodexTemplate $promptPath
        $last = $result.Output
        if ($result.ExitCode -eq 0) { return $last }
    }
    throw "Codex failed after $MaxCodexAttempts attempts.`n$last"
}

function Set-Blocked { param([int] $IssueNumber, [string] $Reason)
    Invoke-Logged gh @("issue", "comment", $IssueNumber.ToString(), "--repo", $Repository, "--body", "Codex automation blocked this issue.`n`n``````text`n$Reason`n``````") -AllowFailure | Out-Null
    Invoke-Logged gh @("issue", "edit", $IssueNumber.ToString(), "--repo", $Repository, "--remove-label", $InProgressLabel, "--add-label", $BlockedLabel) -AllowFailure | Out-Null
}

function Invoke-OneIssue { param([object] $Issue)
    $n = [int]$Issue.number
    $title = [string]$Issue.title
    $branch = New-BranchName $n $title
    try {
        Write-Step "Processing #$n`: $title"
        Invoke-Logged gh @("issue", "edit", $n.ToString(), "--repo", $Repository, "--add-label", $InProgressLabel) | Out-Null
        Invoke-Logged git @("fetch", "origin", $BaseBranch) | Out-Null
        Invoke-Logged git @("checkout", $BaseBranch) | Out-Null
        Invoke-Logged git @("pull", "--ff-only", "origin", $BaseBranch) | Out-Null
        Invoke-Logged git @("checkout", "-B", $branch, "origin/$BaseBranch") | Out-Null
        $summary = Invoke-CodexForIssue $n $title ([string]$Issue.body)
        $changes = Invoke-Logged git @("status", "--porcelain")
        if ([string]::IsNullOrWhiteSpace($changes.Output)) { throw "Codex produced no repository changes." }
        $unsafe = Test-UnsafeChanges
        if ($unsafe.Unsafe) { throw $unsafe.Reason }
        $validation = Invoke-Validation
        Invoke-Logged git @("add", "-A") | Out-Null
        Invoke-Logged git @("commit", "-m", "Issue #$n`: $title") | Out-Null
        Invoke-Logged git @("push", "-u", "origin", $branch, "--force-with-lease") | Out-Null
        $body = "## Summary`nAutomated Codex implementation for #$n.`n`nCloses #$n`n`n## Codex Summary`n``````text`n$summary`n``````n`n## Validation`nValidation failed: **$($validation.Failed)**`n`n$($validation.Body)`n`n## Safety`n- One issue only`n- Isolated branch`n- Unsafe file patterns checked`n- Draft PR for review"
        $args = @("pr", "create", "--repo", $Repository, "--base", $BaseBranch, "--head", $branch, "--title", "Issue #$n`: $title", "--body", $body)
        if ($CreateDraftPr) { $args += "--draft" }
        $pr = Invoke-Logged gh $args
        Invoke-Logged gh @("pr", "edit", $pr.Output.Trim(), "--repo", $Repository, "--add-label", $ReviewLabel) -AllowFailure | Out-Null
        Invoke-Logged gh @("issue", "edit", $n.ToString(), "--repo", $Repository, "--remove-label", $InProgressLabel, "--add-label", $DoneLabel) | Out-Null
    }
    catch {
        Write-Fail $_.Exception.Message
        Set-Blocked $n $_.Exception.Message
    }
    finally { Invoke-Logged git @("checkout", $BaseBranch) -AllowFailure | Out-Null }
}

function Invoke-WorkQueue {
    Ensure-Repo; Ensure-Labels
    $count = 0
    while ($count -lt $MaxIssues) {
        $issue = Get-NextIssue
        if (-not $issue) { Write-Step "No eligible $ReadyLabel issues found."; break }
        Invoke-OneIssue $issue
        $count++
    }
}

function Invoke-TechnicalReview {
    Ensure-Repo; Ensure-Labels
    New-Item -ItemType Directory -Path ".codex" -Force | Out-Null
    $promptPath = Join-Path ".codex" "technical-review.md"
    $component = if ($env:LANTERN_PROTOCOL_COMPONENT) { $env:LANTERN_PROTOCOL_COMPONENT } else { "Lantern Protocol component" }
    Set-Content $promptPath @"
Perform a full code and technical review of $Repository.
Component context: $component

Do not modify files. Produce a Markdown backlog only.
Review architecture, security, privacy, consent, provenance, auditability, testing, CI/CD, Azure readiness, and integration contracts with ETS, Christina, SignalForge, EchoChamber, OpsHelm, EchoLiving, EchoMedia Content Engine, and Lantern Civic.

Use sections:
## Issue: <title>
Severity: Critical|High|Medium|Low
Labels: comma-separated labels
### Rationale
### Acceptance Criteria
### Affected Area
"@ -Encoding UTF8
    $review = Invoke-CodexTemplate $promptPath
    if ($review.ExitCode -ne 0) { throw "Technical review failed.`n$($review.Output)" }
    $body = "# Technical Review Follow-up Backlog`n`n$($review.Output)"
    Invoke-Logged gh @("issue", "create", "--repo", $Repository, "--title", "Technical review: follow-up backlog", "--body", $body, "--label", $FollowUpLabel, "--label", $ReadyLabel) | Out-Null
}

switch ($Mode) {
    "WorkQueue" { Invoke-WorkQueue }
    "ReviewOnly" { Invoke-TechnicalReview }
    "Full" { Invoke-WorkQueue; Invoke-TechnicalReview }
}
