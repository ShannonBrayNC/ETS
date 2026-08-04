[CmdletBinding()]
param(
    [ValidatePattern('^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Tag = "v0.1.0-alpha"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RequiredFileContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required release document is missing: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw
}

function Get-MarkdownSection {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Markdown,
        [Parameter(Mandatory = $true)]
        [string]$HeadingPattern
    )

    $match = [regex]::Match($Markdown, $HeadingPattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if (-not $match.Success) {
        return $null
    }

    $start = $match.Index
    $remaining = $Markdown.Substring($start + $match.Length)
    $nextHeading = [regex]::Match($remaining, "(?m)^##\s+")
    if ($nextHeading.Success) {
        return $Markdown.Substring($start, $match.Length + $nextHeading.Index)
    }

    return $Markdown.Substring($start)
}

function Assert-ContainsPattern {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string]$Pattern,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if ($Content -notmatch $Pattern) {
        throw $Message
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$changelogPath = Join-Path $repoRoot "CHANGELOG.md"
$releaseNotesPath = Join-Path $repoRoot "docs/release/$Tag-release-notes.md"
$policyPath = Join-Path $repoRoot "docs/release/RELEASE_NOTES_POLICY.md"

$changelog = Get-RequiredFileContent -Path $changelogPath
$releaseNotes = Get-RequiredFileContent -Path $releaseNotesPath
$null = Get-RequiredFileContent -Path $policyPath

$escapedTag = [regex]::Escape($Tag)
$changelogSection = Get-MarkdownSection -Markdown $changelog -HeadingPattern "(?m)^##\s+\[$escapedTag\](?:\s+-\s+.*)?\s*$"
if ($null -eq $changelogSection) {
    throw "CHANGELOG.md is missing an entry for $Tag."
}

Assert-ContainsPattern -Content $releaseNotes -Pattern "(?m)^#\s+ETS\s+$escapedTag\s+Release Notes\s*$" -Message "Release notes must have a title for $Tag."
Assert-ContainsPattern -Content $releaseNotes -Pattern "(?is)CHANGELOG\.md.*\[$escapedTag\]" -Message "Release notes must point to the matching CHANGELOG.md entry."

$requiredSections = @{
    "validation commands" = "(?im)^#+\s+Validation required before tag\s*$|(?im)^#+\s+Validation commands\s*$"
    "known limitations" = "(?im)^#+\s+(Known limitations|Important limitations)\s*:??\s*$"
    "non-claims" = "(?im)^#+\s+Non-claims\s*$"
}

foreach ($name in $requiredSections.Keys) {
    Assert-ContainsPattern -Content $changelogSection -Pattern $requiredSections[$name] -Message "CHANGELOG.md entry for $Tag is missing required section: $name."
    Assert-ContainsPattern -Content $releaseNotes -Pattern $requiredSections[$name] -Message "Release notes for $Tag are missing required section: $name."
}

$validationCommands = @(
    "ruff check .",
    "mypy",
    "pytest",
    "ets-verify --version"
)
foreach ($command in $validationCommands) {
    $escapedCommand = [regex]::Escape($command)
    Assert-ContainsPattern -Content $changelogSection -Pattern $escapedCommand -Message "CHANGELOG.md entry for $Tag is missing validation command: $command."
    Assert-ContainsPattern -Content $releaseNotes -Pattern $escapedCommand -Message "Release notes for $Tag are missing validation command: $command."
}

$nonClaimPatterns = @(
    "does not claim production readiness|not production trust infrastructure",
    "does not provide legal|legal certification|legal advice",
    "does not verify.*election correctness|election correctness",
    "does not verify.*ballot validity|ballot validity",
    "does not verify.*tabulation accuracy|tabulation accuracy",
    "official election results|official results",
    "not voting software|voting software",
    "not.*tabulation software|tabulation software"
)
foreach ($pattern in $nonClaimPatterns) {
    Assert-ContainsPattern -Content $changelogSection -Pattern "(?is)$pattern" -Message "CHANGELOG.md entry for $Tag is missing non-claim boundary pattern: $pattern."
    Assert-ContainsPattern -Content $releaseNotes -Pattern "(?is)$pattern" -Message "Release notes for $Tag are missing non-claim boundary pattern: $pattern."
}

$overclaimPatterns = @(
    "(?<!not\s)(?<!not\sfinal\s)(?<!not\sproduction\s)production-ready",
    "guarantees?\s+legal\s+correctness",
    "certifies?\s+election\s+correctness",
    "proves?\s+official\s+election\s+results",
    "guarantees?\s+authenticity",
    "guarantees?\s+completeness"
)
$combined = "$changelogSection`n$releaseNotes"
foreach ($pattern in $overclaimPatterns) {
    if ($combined -match $pattern) {
        throw "Potential release overclaim found for $Tag: $($Matches[0])"
    }
}

Write-Output "Changelog and release-note boundaries verified for $Tag."
