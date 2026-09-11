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
