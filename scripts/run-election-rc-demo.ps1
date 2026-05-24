$ErrorActionPreference = "Stop"

$python = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $python = ".\.venv\Scripts\python.exe"
}

& $python -m ets.election.rc_demo
