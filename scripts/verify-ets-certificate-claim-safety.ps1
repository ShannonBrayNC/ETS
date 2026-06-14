# scripts/verify-ets-certificate-claim-safety.ps1
# Verifies ETS certificate claim-safety sprint outputs.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$requiredFiles = @(
    "ets/version.py",
    "ets/__init__.py",
    "ets/verifier/cli.py",
    "ets/reports/certificate.py",
    "docs/reports/CERTIFICATE_CLAIM_SAFETY.md",
    "docs/sprints/SPRINT-CERTIFICATE-CLAIM-SAFETY.md",
    "tests/unit/test_certificate_claim_safety.py"
)

$failures = New-Object System.Collections.Generic.List[string]

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $failures.Add("Missing required file: $file")
    }
}

if ($failures.Count -eq 0) {
    $certificate = Get-Content -Raw -Path "ets/reports/certificate.py"
    $cli = Get-Content -Raw -Path "ets/verifier/cli.py"
    $version = Get-Content -Raw -Path "ets/version.py"
    $doc = Get-Content -Raw -Path "docs/reports/CERTIFICATE_CLAIM_SAFETY.md"

    foreach ($term in @(
        "WHAT_THIS_VERIFIES",
        "WHAT_THIS_DOES_NOT_VERIFY",
        "What This Verifies",
        "What This Does Not Verify",
        "real-world truth",
        "legal sufficiency",
        "election correctness"
    )) {
        if ($certificate -notmatch [regex]::Escape($term)) {
            $failures.Add("certificate.py missing required term: $term")
        }
    }

    if ($cli -notmatch "from ets.version import __version__") {
        $failures.Add("cli.py must import __version__ from ets.version.")
    }

    if ($version -notmatch "def get_version") {
        $failures.Add("ets/version.py must define get_version.")
    }

    foreach ($term in @("What This Verifies", "What This Does Not Verify", "must not claim")) {
        if ($doc -notmatch [regex]::Escape($term)) {
            $failures.Add("CERTIFICATE_CLAIM_SAFETY.md missing required term: $term")
        }
    }

    $sourceFiles = Get-ChildItem -Recurse -File -Path "ets" -Include *.py
    foreach ($file in $sourceFiles) {
        $sourceText = Get-Content -Raw -Path $file.FullName
        if ($sourceText -match "from ets import __version__") {
            $failures.Add("$($file.FullName) still uses from ets import __version__.")
        }
    }

    if (Test-Path ".\.venv\Scripts\python.exe") {
        & ".\.venv\Scripts\python.exe" -c "from ets.version import __version__; print(__version__)"
        & ".\.venv\Scripts\python.exe" -m ets.verifier.cli --version

        if (Test-Path ".\.venv\Scripts\ets-verify.exe") {
            & ".\.venv\Scripts\ets-verify.exe" --version
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "ETS certificate claim-safety verification failed:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host "ETS certificate claim-safety verification passed." -ForegroundColor Green
