[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = if (Test-Path -LiteralPath (Join-Path $repoRoot ".venv/Scripts/python.exe")) {
    Join-Path $repoRoot ".venv/Scripts/python.exe"
} else {
    "python"
}

$requiredFixtures = @(
    "tests/fixtures/verifier/event.json",
    "tests/fixtures/verifier/inclusion-proof.json",
    "tests/fixtures/verifier/consistency-proof.json",
    "tests/fixtures/verifier/bundle.json",
    "tests/fixtures/verifier/tree-head-previous.json",
    "tests/fixtures/verifier/tree-head-latest.json",
    "tests/fixtures/verifier/election-proof.json"
)

foreach ($fixture in $requiredFixtures) {
    $path = Join-Path $repoRoot $fixture
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing verifier CLI golden fixture: $fixture"
    }
}

Push-Location $repoRoot
try {
    & $python -m pytest tests/unit/test_verifier_cli_golden_paths.py
    if ($LASTEXITCODE -ne 0) {
        throw "Verifier CLI golden-path regression tests failed."
    }
} finally {
    Pop-Location
}

Write-Output "Verifier CLI golden fixtures verified."
