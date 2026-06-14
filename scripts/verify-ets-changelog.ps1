[CmdletBinding()]
param(
    [string]$Tag = "v0.1.0-alpha"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$changelogPath = Join-Path $repoRoot "CHANGELOG.md"
$releaseNotesPath = Join-Path $repoRoot "docs/release/$Tag-release-notes.md"
$policyPath = Join-Path $repoRoot "docs/release/RELEASE_NOTES_POLICY.md"

$requiredFiles = @($changelogPath, $releaseNotesPath, $policyPath)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required release document is missing: $path"
    }
}

$changelog = Get-Content -LiteralPath $changelogPath -Raw
$releaseNotes = Get-Content -LiteralPath $releaseNotesPath -Raw
$combined = "$changelog`n$releaseNotes"

if ($changelog -notmatch "(?m)^## \[$([regex]::Escape($Tag))\]") {
    throw "CHANGELOG.md is missing an entry for $Tag."
}

$requiredPatterns = @{
    "validation commands" = "(?is)(validation commands|validation required).*(```|-)"
    "known limitations" = "(?is)known limitations|important limitations"
    "non-claims" = "(?is)non-claims|does not claim|does not verify"
    "changelog pointer" = "(?is)CHANGELOG\.md"
}

foreach ($name in $requiredPatterns.Keys) {
    if ($combined -notmatch $requiredPatterns[$name]) {
        throw "Release notes/changelog are missing required boundary: $name."
    }
}

$blockedClaims = @(
    "production-ready trust infrastructure",
    "legal certification",
    "counsel-approved",
    "election correctness",
    "ballot validity",
    "tabulation accuracy",
    "official election results"
)

foreach ($claim in $blockedClaims) {
    $escaped = [regex]::Escape($claim)
    $allowedBoundary = "(?is)(does not claim|does not verify|not provide|not claim|not voting|non-claims).{0,220}$escaped"
    if ($combined -match $escaped -and $combined -notmatch $allowedBoundary) {
        throw "Potential overclaim found without nearby non-claim boundary: $claim"
    }
}

Write-Output "Changelog and release-note boundaries verified for $Tag."
