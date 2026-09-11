from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "m365" / "invoke-ets-sharepoint-workload-identity-isolated-job.ps1"
TEXT = SCRIPT.read_text(encoding="utf-8")


def test_failed_execution_collects_sanitized_logs_before_reporting() -> None:
    assert "az containerapp job logs show" in TEXT
    assert "Get-SanitizedGate2FailureReason" in TEXT
    assert "sanitizedReason=$sanitizedFailureReason" in TEXT
    assert "Write-Output $logText" not in TEXT
    assert "Write-Host $logText" not in TEXT


def test_failure_path_reproves_cleanup_and_zero_runtime() -> None:
    assert "temporaryJobDeleted=$cleanupVerified" in TEXT
    assert "productionGatewayZeroRuntimeRestored=$productionGatewayZeroRuntimeRestored" in TEXT
    assert "CRITICAL: Gate 2 cleanup verification failed" in TEXT
    assert (
        "CRITICAL: production Gateway runtime is not at the required zero-runtime state"
        in TEXT
    )


def test_runtime_safety_boundary_remains_intact() -> None:
    assert "gatewayEntrypointStarted = $false" in TEXT
    assert "gatewayStateMounted = $false" in TEXT
    assert "azureRbacMutationPerformed = $false" in TEXT
    assert "az role assignment create" not in TEXT
    assert "az containerapp update" not in TEXT
