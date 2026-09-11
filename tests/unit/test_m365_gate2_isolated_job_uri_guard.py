from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "m365" / "invoke-ets-sharepoint-workload-identity-isolated-job.ps1"
TEXT = SCRIPT.read_text(encoding="utf-8")


def test_isolated_job_arm_uri_delimits_powershell_variables() -> None:
    assert (
        '$jobUri = "https://management.azure.com${jobResourceId}?api-version=${jobApiVersion}"'
        in TEXT
    )
    assert (
        '$jobUri = "https://management.azure.com$jobResourceId?api-version=$jobApiVersion"'
        not in TEXT
    )


def test_isolated_job_stages_large_arm_body_in_temp_file_for_windows() -> None:
    assert "[System.IO.Path]::GetTempPath()" in TEXT
    assert "[System.IO.File]::WriteAllText(" in TEXT
    assert '[System.Text.UTF8Encoding]::new($false)' in TEXT
    assert '$jobBodyReference = "@$jobBodyPath"' in TEXT
    assert "--body $jobBodyReference" in TEXT
    assert "Remove-Item -LiteralPath $jobBodyPath -Force" in TEXT
    assert "$jobCreateExitCode = $LASTEXITCODE" in TEXT
