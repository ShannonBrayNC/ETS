# scripts/verify-ets-release-readiness.ps1
# Verifies ETS public alpha release readiness gates.
# Run from the ETS repository root with PowerShell 7+.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$requiredFiles = @(
    "README.md",
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
    "docs/ip",
    "tests/unit/test_release_readiness_docs.py"
)

$failures = New-Object System.Collections.Generic.List[string]

foreach ($path in $requiredFiles) {
    if (-not (Test-Path $path)) {
        $failures.Add("Missing required release gate artifact: $path")
    }
}

function Assert-Contains {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string[]]$Terms
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

Assert-Contains -Path "docs/release/PUBLIC_RELEASE_CHECKLIST.md" -Terms @(
    "Evidence Transparency System",
    "Research boundary",
    "Formal traceability",
    "Reproducibility matrix",
    "Certificate claim-safety",
    "IP review",
    "Election demo boundary",
    "No production overclaim",
    "ETS does not prove real-world truth"
)

Assert-Contains -Path "docs/release/ALPHA_RELEASE_GATE.md" -Terms @(
    "Gate Decision",
    "Required Artifacts",
    "Required Validation Commands",
    "Alpha Boundary",
    "Tagging Rule",
    "Do not create a public release"
)

Assert-Contains -Path "docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md" -Terms @(
    "What This Release Demonstrates",
    "What This Release Does Not Claim",
    "Validation Commands",
    "real-world truth",
    "election correctness",
    "Production trust-service readiness"
)

if (Test-Path "README.md") {
    $readme = Get-Content -Raw -Path "README.md"
    if ($readme -notmatch "Evidence Transparency System") {
        $failures.Add("README.md must use Evidence Transparency System public naming.")
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

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" -c "from ets.version import __version__; print(__version__)"
    if (Test-Path ".\.venv\Scripts\ets-verify.exe") {
        & ".\.venv\Scripts\ets-verify.exe" --version
    }
}

if ($failures.Count -gt 0) {
    Write-Host "ETS release readiness verification failed:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host "ETS release readiness verification passed." -ForegroundColor Green