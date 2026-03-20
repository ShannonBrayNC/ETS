param(
    [string]$RepoPath = "C:\GitHub\ETS"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

Write-Step "Validating repository path"

if (-not (Test-Path $RepoPath)) {
    throw "Repo path not found: $RepoPath"
}

Set-Location $RepoPath

if (-not (Test-Path ".git")) {
    throw "This is not a git repository: $RepoPath"
}

Write-Step "Creating folder structure"

$dirs = @(
    "docs",
    "ets",
    "ets/core",
    "ets/api",
    "ets/verifier",
    "ets/explorer",
    "ets/spec",
    "ets/demos",
    "tests",
    ".github",
    ".github/workflows"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Write-Step "Writing starter files"

@"
# ETS

ETS (Evidence Trust System) is a transparency log and verification platform for provable digital evidence.

## Initial components

- `ets/core` - hashing, append-only log, Merkle tree, proofs
- `ets/api` - ingestion and verification API
- `ets/verifier` - CLI and SDK verification tools
- `ets/explorer` - future UI for browsing and verification
- `ets/spec` - protocol docs and whitepaper
- `ets/demos` - example use cases

## Initial goal

Build a working transparency log prototype with:
- canonical JSON hashing
- append-only event log
- signed tree heads later
- inclusion proofs
- verifier tooling
"@ | Set-Content -Path "README.md" -Encoding utf8

@"
__pycache__/
*.pyc
.venv/
.env
*.db
*.sqlite
*.sqlite3
*.log
.vscode/
.DS_Store
Thumbs.db
"@ | Set-Content -Path ".gitignore" -Encoding utf8

@"
# ETS Core

Implements the trust engine:
- canonical JSON hashing
- append-only event storage
- Merkle tree root generation
- inclusion proofs
- consistency primitives later
"@ | Set-Content -Path "ets/core/README.md" -Encoding utf8

@"
# ETS API

Service surface for:
- POST event ingestion
- GET event lookup
- GET tree head
- GET inclusion proof
- POST payload verification
"@ | Set-Content -Path "ets/api/README.md" -Encoding utf8

@"
# ETS Verifier

CLI and SDK tools to:
- verify event hashes
- validate inclusion proofs
- compare tree heads
- verify future signatures
"@ | Set-Content -Path "ets/verifier/README.md" -Encoding utf8

@"
# ETS Explorer

Future web interface for:
- browsing the transparency log
- looking up entries
- visualizing tree state
- verifying proofs in-browser
"@ | Set-Content -Path "ets/explorer/README.md" -Encoding utf8

@"
# ETS Specification

Documents:
- event schema
- canonicalization rules
- hashing rules
- tree construction
- proof formats
- verification process
"@ | Set-Content -Path "ets/spec/README.md" -Encoding utf8

@"
# ETS Demos

Example applications:
- journalism verification
- legal evidence chain
- AI authenticity proofs
- PVTL voting integration
"@ | Set-Content -Path "ets/demos/README.md" -Encoding utf8

@"
name: ci

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Repo structure check
        run: |
          test -d ets/core
          test -d ets/api
          test -d ets/verifier
          test -d ets/spec
"@ | Set-Content -Path ".github/workflows/ci.yml" -Encoding utf8

@"
{
  "name": "ETS",
  "description": "Evidence Trust System",
  "version": "0.1.0"
}
"@ | Set-Content -Path "docs/project.json" -Encoding utf8

Write-Step "Reviewing changes"
git status

Write-Step "Committing"
git add .
git commit -m "Initialize ETS project structure"

Write-Step "Pushing"
git push -u origin main

Write-Step "Done"
Write-Host "ETS structure initialized successfully." -ForegroundColor Green