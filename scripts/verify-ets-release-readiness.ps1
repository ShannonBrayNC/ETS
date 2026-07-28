# scripts/verify-ets-release-readiness.ps1
# Verifies ETS public alpha release readiness gates.
# Run from the ETS repository root with PowerShell 7+.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$requiredFiles = @(
    "README.md",
    "PATENT_NOTICE.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/security_boundary.md",
    "ets/spec/protocol.md",
    "docs/release/PUBLIC_RELEASE_CHECKLIST.md",
    "docs/release/ALPHA_RELEASE_GATE.md",
    "docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md",
    "docs/research/README.md",
    "docs/research/non-claims.md",
    "docs/research/FORMAL_TRACEABILITY_MATRIX.md",
    "docs/research/FORMAL_MODEL_CLAIMS.md",
    "docs/research/reproducibility-matrix.md",
    "docs/research/REPRODUCIBILITY_APPENDIX.md",
    "docs/reports/CERTIFICATE_CLAIM_SAFETY.md",
    "docs/demo/election-rc-walkthrough.md",
    "scripts/verify-branch-protection-runbook.py",
    "scripts/verify-ets-release-readiness.ps1",
    "scripts/verify-ets-certificate-claim-safety.ps1",
    "scripts/verify-ets-formal-traceability.ps1",
    "tests/unit/test_release_readiness_docs.py"
)

$forbiddenPublicPaths = @(
    "docs/ip/INVENTION_DISCLOSURE.md",
    "docs/ip/PRIOR_ART_ANALYSIS.md",
    "docs/ip/CANDIDATE_CLAIMS.md",
    "docs/ip/PATENT_CLAIMS_CANDIDATES.md",
    "docs/ip/PATENT_DIAGRAMS.md",
    "docs/ip/PUBLIC_RELEASE_CHECKLIST.md"
)

$failures = New-Object System.Collections.Generic.List[string]

foreach ($path in $requiredFiles) {
    if (-not (Test-Path $path)) {
        $failures.Add("Missing required release gate artifact: $path")
    }
}

foreach ($path in $forbiddenPublicPaths) {
    if (Test-Path $path) {
        $failures.Add("Patent-sensitive artifact must not be published from this repo path: $path")
    }
}

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string[]]$Terms
    )

    if (-not (Test-Path $Path)) {
        return
    }

    $text = Get-Content -Raw -Path $Path
    foreach ($term in $Terms) {
        if ($text -notmatch [regex]::Escape($term)) {
            $failures.Add("$Path missing required term: $term")
        }
    }
}

function Get-RepoPython {
    $candidates = @(
        ".\.venv\Scripts\python.exe",
        ".\.venv\bin\python",
        ".\.venv312\Scripts\python.exe",
        ".\.venv312\bin\python"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    foreach ($commandName in @("python", "python3", "py")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }

    throw "Unable to locate a Python interpreter for ETS release validation."
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Description
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Assert-Contains -Path "PATENT_NOTICE.md" -Terms @(
    "patent pending",
    "Private Materials Excluded",
    "This repository does not include"
)

Assert-Contains -Path "SECURITY.md" -Terms @(
    "Do not submit real secrets",
    "real PII",
    "official election data",
    "public issues or pull requests"
)

Assert-Contains -Path "docs/release/PUBLIC_RELEASE_CHECKLIST.md" -Terms @(
    "Evidence Transparency System",
    "Research boundary",
    "Formal traceability",
    "Reproducibility matrix",
    "Certificate claim-safety",
    "IP review boundary",
    "Public contribution guardrails",
    "Election demo boundary",
    "No production overclaim",
    "ETS does not prove real-world truth"
)

Assert-Contains -Path "docs/release/ALPHA_RELEASE_GATE.md" -Terms @(
    "Gate Decision",
    "Required Artifacts",
    "Required Validation Commands",
    "Alpha Boundary",
    "Public IP Boundary",
    "Tagging Rule",
    "Do not create a public release"
)

Assert-Contains -Path "docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md" -Terms @(
    "What This Release Demonstrates",
    "What This Release Does Not Claim",
    "Validation Commands",
    "real-world truth",
    "election correctness",
    "Production trust-service readiness",
    "Patent allowance"
)

if (Test-Path "README.md") {
    $readme = Get-Content -Raw -Path "README.md"
    if ($readme -notmatch "Evidence Transparency System") {
        $failures.Add("README.md must use Evidence Transparency System public naming.")
    }
    foreach ($term in @("Patent Notice", "Claim Boundaries", "Public Repository Boundary")) {
        if ($readme -notmatch [regex]::Escape($term)) {
            $failures.Add("README.md missing public release guardrail: $term")
        }
    }
}

if (Test-Path "docs/demo/election-rc-walkthrough.md") {
    $demo = Get-Content -Raw -Path "docs/demo/election-rc-walkthrough.md"
    foreach ($term in @("not voting software", "tabulation", "vote of record")) {
        if ($demo -notmatch [regex]::Escape($term)) {
            $failures.Add("Election RC walkthrough missing boundary term: $term")
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "ETS release readiness verification failed:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

$python = Get-RepoPython

Invoke-CheckedCommand `
    -Executable $python `
    -Arguments @("scripts/verify-branch-protection-runbook.py") `
    -Description "Branch protection runbook verification"

Invoke-CheckedCommand `
    -Executable $python `
    -Arguments @("-c", "from ets.version import __version__; print(__version__)") `
    -Description "ETS version import verification"

$verifierCandidates = @(
    ".\.venv\Scripts\ets-verify.exe",
    ".\.venv\bin\ets-verify",
    ".\.venv312\Scripts\ets-verify.exe",
    ".\.venv312\bin\ets-verify"
)

$verifier = $null
foreach ($candidate in $verifierCandidates) {
    if (Test-Path $candidate) {
        $verifier = (Resolve-Path $candidate).Path
        break
    }
}

if ($null -ne $verifier) {
    Invoke-CheckedCommand `
        -Executable $verifier `
        -Arguments @("--version") `
        -Description "ETS verifier executable validation"
}
else {
    Invoke-CheckedCommand `
        -Executable $python `
        -Arguments @("-m", "ets.verifier.cli", "--version") `
        -Description "ETS verifier module validation"
}

Write-Host "ETS release readiness verification passed." -ForegroundColor Green
